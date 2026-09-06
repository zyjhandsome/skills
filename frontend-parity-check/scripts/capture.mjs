#!/usr/bin/env node
// Capture one side (baseline or candidate) of a parity run.
// Usage: node capture.mjs --config parity-config.json --side baseline [--out DIR] [--only routeId,...] [--headed]
import fs from 'node:fs';
import path from 'node:path';
import { loadPlaywright, ensureDir, writeJson, readJson, parseArgs, slug } from './lib/pw.mjs';
import { domDigestFn, styleProbeFn, visibleCountFn, DEFAULT_PROBES, STYLE_PROPS } from './lib/probes.mjs';
import { landingVerdict, resolveProbes, mergeDomDigests } from './lib/parity-core.mjs';

const args = parseArgs(process.argv.slice(2));
const side = args.side;
if (!args.config || !['baseline', 'candidate'].includes(side)) {
  console.error('usage: node capture.mjs --config <file> --side <baseline|candidate> [--out DIR]');
  process.exit(2);
}

const configPath = path.resolve(args.config);
const cfg = readJson(configPath);
if (!cfg) {
  console.error(`cannot read config: ${configPath}`);
  process.exit(2);
}
// Relative outputDir is resolved against the config file, so runs are reproducible from any cwd.
const outRoot = args.out
  ? path.resolve(args.out)
  : path.resolve(path.dirname(configPath), cfg.outputDir || 'parity-run');
const sideCfg = cfg[side];
if (!sideCfg?.baseUrl) {
  console.error(`config.${side}.baseUrl is required`);
  process.exit(2);
}

const ctx = cfg.context || {};
const viewports = ctx.viewports?.length ? ctx.viewports : [{ name: 'desktop', width: 1440, height: 900 }];
const thresholds = cfg.thresholds || {};
const only = args.only ? String(args.only).split(',').map((s) => s.trim()) : null;
const routes = (cfg.routes || []).filter((r) => !only || only.includes(r.id));
const journeys = (cfg.journeys || []).filter((j) => !only || only.includes(j.id));

const pw = await loadPlaywright(process.cwd());
if (!pw) {
  console.error('Playwright not found. Run scripts/preflight.mjs and follow its install guidance.');
  process.exit(3);
}

const browserName = cfg.browser || 'chromium';
// `channel` / `executablePath` let a locked-down machine drive its own Chrome/Edge
// when the bundled Chromium cannot be downloaded. See references/playwright-setup.md.
const channel = args.channel || cfg.channel || null;
const executablePath = args.executablePath || cfg.executablePath || null;
const launchOptions = { headless: !args.headed };
if (channel) launchOptions.channel = channel;
if (executablePath) launchOptions.executablePath = executablePath;
const browser = await pw[browserName].launch(launchOptions);
const sideDir = path.join(outRoot, side);
ensureDir(sideDir);

const assertLanded = { ...(cfg.assertLanded || {}) };

const runLog = {
  schema: 'parity-capture/v1',
  side,
  baseUrl: sideCfg.baseUrl,
  browser: `${browserName}${channel ? ':' + channel : ''} ${browser.version()}`,
  capturedAt: new Date().toISOString(),
  context: { ...ctx, viewports },
  states: [],
  journeys: [],
  errors: [],
};

const FREEZE_SCRIPT = (iso, seed) => `
(() => {
  ${iso ? `
  const FIXED = new Date(${JSON.stringify(iso)}).getTime();
  const _Date = Date;
  const P = new Proxy(_Date, {
    construct(t, a) { return a.length ? new t(...a) : new t(FIXED); },
    apply() { return new _Date(FIXED).toString(); },
  });
  P.now = () => FIXED;
  P.parse = _Date.parse; P.UTC = _Date.UTC; P.prototype = _Date.prototype;
  globalThis.Date = P;
  ` : ''}
  ${seed !== undefined ? `
  let s = ${Number(seed) || 1} >>> 0;
  Math.random = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  ` : ''}
})();`;

const STABILIZE_CSS = `*,*::before,*::after{animation-duration:0s!important;animation-delay:0s!important;
transition-duration:0s!important;transition-delay:0s!important;caret-color:transparent!important;}
html{scroll-behavior:auto!important;}`;

async function newContext(viewport) {
  const options = {
    viewport: { width: viewport.width, height: viewport.height },
    deviceScaleFactor: ctx.deviceScaleFactor ?? 1,
    locale: ctx.locale || 'zh-CN',
    timezoneId: ctx.timezoneId || 'Asia/Shanghai',
    colorScheme: ctx.colorScheme || 'light',
    ignoreHTTPSErrors: ctx.ignoreHTTPSErrors ?? true,
    reducedMotion: 'reduce',
  };
  if (sideCfg.userAgent) options.userAgent = sideCfg.userAgent;
  if (sideCfg.extraHTTPHeaders) options.extraHTTPHeaders = sideCfg.extraHTTPHeaders;
  const storageState = sideCfg.auth?.storageState && path.resolve(path.dirname(configPath), sideCfg.auth.storageState);
  if (storageState && fs.existsSync(storageState)) options.storageState = storageState;

  const context = await browser.newContext(options);
  context.setDefaultTimeout(Number(ctx.timeoutMs || 20000));
  if (ctx.freezeTime || ctx.seedRandom !== undefined) {
    await context.addInitScript(FREEZE_SCRIPT(ctx.freezeTime, ctx.seedRandom));
  }
  if (sideCfg.auth?.actions && !(storageState && fs.existsSync(storageState))) {
    const page = await context.newPage();
    const record = await runActions(page, sideCfg.auth.actions, { record: [], baseUrl: sideCfg.baseUrl });
    // A silently failed login makes every later state capture a login page, so it aborts the side.
    const failed = record.find((s) => s.status === 'fail');
    if (failed) {
      const at = `#${failed.index} ${failed.type} ${failed.id || ''}`.trim();
      throw new Error(`登录动作失败（${at}）：${failed.error} — 本侧证据作废，请修正 auth.actions 后重跑`);
    }
    const landed = landingVerdict(page.url(), assertLanded);
    if (!landed.ok) throw new Error(`登录后仍停留在登录/跳转页：${landed.reason}`);
    if (storageState) await context.storageState({ path: storageState });
    await page.close();
  }
  return context;
}

function attachObservers(page, sink) {
  page.on('console', (msg) => {
    if (['error', 'warning'].includes(msg.type())) {
      sink.console.push({ type: msg.type(), text: msg.text().slice(0, 400) });
    }
  });
  page.on('pageerror', (e) => sink.console.push({ type: 'pageerror', text: String(e.message).slice(0, 400) }));
  page.on('requestfailed', (r) =>
    sink.network.push({ status: 'failed', method: r.method(), url: r.url(), error: r.failure()?.errorText }));
  page.on('response', (r) => {
    if (r.status() >= 400) sink.network.push({ status: r.status(), method: r.request().method(), url: r.url() });
  });
}

async function runActions(page, actions = [], acc) {
  for (let i = 0; i < actions.length; i++) {
    const a = actions[i];
    const loc = a.selector ? page.locator(a.selector).nth(a.nth ?? 0) : null;
    const step = { index: i, type: a.type, id: a.id || a.selector || a.path, status: 'ok' };
    try {
      switch (a.type) {
        case 'goto': {
          const target = (a.id && acc.pathOverrides?.[a.id]) || a.path;
          await page.goto(new URL(target, acc.baseUrl).href, { waitUntil: a.waitUntil || 'networkidle' });
          break;
        }
        case 'click': await loc.click({ force: a.force }); break;
        case 'dblclick': await loc.dblclick(); break;
        case 'hover': await loc.hover(); break;
        case 'fill': await loc.fill(String(a.value)); break;
        case 'type': await loc.pressSequentially(String(a.value), { delay: a.delay ?? 20 }); break;
        case 'press': await (loc || page.keyboard).press(a.key); break;
        case 'select': await loc.selectOption(a.value); break;
        case 'check': await loc.check(); break;
        case 'uncheck': await loc.uncheck(); break;
        case 'scrollTo':
          if (a.selector) await loc.scrollIntoViewIfNeeded();
          else await page.evaluate((y) => window.scrollTo(0, y), a.y ?? 0);
          break;
        case 'waitFor': await page.locator(a.selector).nth(a.nth ?? 0).waitFor({ state: a.state || 'visible', timeout: a.timeout }); break;
        case 'waitForUrl': await page.waitForURL(new RegExp(a.pattern), { timeout: a.timeout }); break;
        case 'waitTimeout': await page.waitForTimeout(a.ms ?? 500); break;
        case 'expectVisible':
          step.observed = await loc.isVisible();
          break;
        case 'expectText':
          step.observed = ((await loc.innerText()) || '').replace(/\s+/g, ' ').trim().slice(0, 300);
          break;
        case 'expectCount': {
          // Default counts only what a user can see: `ng-hide` / `display:none` leftovers in the
          // old page used to inflate the count and produce a phantom "少了一项" finding.
          const nodes = page.locator(a.selector);
          step.observedTotal = await nodes.count();
          step.visibleOnly = a.visibleOnly !== false;
          step.observed = step.visibleOnly ? await nodes.evaluateAll(visibleCountFn) : step.observedTotal;
          break;
        }
        case 'expectValue':
          step.observed = await loc.inputValue();
          break;
        case 'expectUrl':
          step.observed = page.url();
          break;
        case 'capture':
          step.observed = a.id;
          break;
        default:
          step.status = 'unsupported';
      }
    } catch (e) {
      step.status = 'fail';
      step.error = String(e.message || e).split('\n')[0].slice(0, 300);
    }
    acc.record.push(step);
    if (step.status === 'fail' && a.stopOnFail !== false) break;
  }
  return acc.record;
}

/**
 * Wait for the page to be comparable.
 * `strict` (right after navigation): a missed `waitFor` means we are not on the page
 * under test, so it throws instead of producing evidence for the wrong page.
 * Non-strict (after in-page actions): records a warning, since actions may have
 * legitimately navigated away from the anchor selector.
 */
async function settle(page, route, { strict = false, warnings = null } = {}) {
  if (route?.waitFor?.selector) {
    const sel = route.waitFor.selector;
    try {
      await page.locator(sel).first()
        .waitFor({ state: route.waitFor.state || 'visible', timeout: route.waitFor.timeout || 15000 });
    } catch (e) {
      const detail = `waitFor 未命中（selector=${sel}，当前 URL=${page.url()}）：${String(e.message || e).split('\n')[0]}`;
      if (strict) throw new Error(detail);
      warnings?.push(detail);
    }
  }
  await page.addStyleTag({ content: STABILIZE_CSS }).catch(() => {});
  await page.evaluate(() => document.fonts?.ready).catch(() => {});
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(Number(thresholds.settleMs ?? 400));
}

/** Hard gate: refuse to treat a login / SSO redirect page as evidence. */
function assertLandedOn(page, route) {
  const rules = { ...assertLanded, ...(route?.assertLanded || {}) };
  const landed = landingVerdict(page.url(), rules);
  if (!landed.ok) throw new Error(landed.reason);
  return landed;
}

/** Screenshot + URL of a state that failed, so the operator can see *why* without a rerun. */
async function failureEvidence(page, dir, info) {
  try {
    ensureDir(dir);
    await page.screenshot({ path: path.join(dir, 'failure.png'), animations: 'disabled', caret: 'hide' });
    writeJson(path.join(dir, 'failure.json'), {
      ...info, url: page.url(), title: await page.title().catch(() => null), capturedAt: new Date().toISOString(),
    });
  } catch { /* the page may already be gone; the log entry still carries the error */ }
}

/**
 * Semantic digest of the main frame plus every readable iframe.
 * Hosted legacy shells put the top bar / menu inside an iframe; reading only the main
 * frame reported those links as "missing". Frames we genuinely cannot read are labelled
 * `unreadable` so compare.mjs can say "unknown" instead of "missing".
 */
async function collectDom(page) {
  const main = await page.evaluate(domDigestFn).catch((e) => ({ error: String(e.message) }));
  const frames = [];
  for (const frame of page.frames()) {
    if (frame === page.mainFrame()) continue;
    const url = frame.url();
    if (!url || url === 'about:blank') continue;
    try {
      const el = await frame.frameElement();
      const box = await el.boundingBox();
      await el.dispose();
      if (!box || box.width < 20 || box.height < 20) continue; // tracking / hidden iframes
    } catch { /* detached from its parent; still try to read it */ }
    try {
      frames.push({ url, status: 'read', digest: await frame.evaluate(domDigestFn) });
    } catch (e) {
      frames.push({ url, status: 'unreadable', error: String(e.message || e).split('\n')[0].slice(0, 200) });
    }
  }
  return mergeDomDigests(main, frames);
}

async function snapshot(page, dir, { route, stateId, viewport, sink, warnings = [] }) {
  ensureDir(dir);
  const probes = resolveProbes(cfg, route || {}, DEFAULT_PROBES);
  const masks = [...(cfg.masks || []), ...(route?.masks || [])];

  const dom = await collectDom(page);
  const styles = await page.evaluate(styleProbeFn, { probes, props: STYLE_PROPS }).catch((e) => ({ error: String(e.message) }));

  const shot = path.join(dir, 'shot.png');
  await page.screenshot({
    path: shot,
    fullPage: route?.fullPage ?? cfg.fullPage ?? false,
    animations: 'disabled',
    caret: 'hide',
    scale: 'css',
    mask: masks.map((m) => page.locator(m)),
    maskColor: '#ff00ff',
  });

  writeJson(path.join(dir, 'dom.json'), dom);
  writeJson(path.join(dir, 'styles.json'), styles);
  writeJson(path.join(dir, 'runtime.json'), { console: sink.console, network: sink.network });
  writeJson(path.join(dir, 'meta.json'), {
    side, stateId, routeId: route?.id, viewport, url: page.url(),
    title: await page.title().catch(() => null), masks,
    probes: probes.map((p) => p.id),
    frames: dom.frames || [],
    warnings,
    capturedAt: new Date().toISOString(),
  });
  return { shot, url: page.url(), frames: dom.frames || [] };
}

try {
for (const viewport of viewports) {
  const context = await newContext(viewport);

  for (const route of routes) {
    const routePath = sideCfg.pathOverrides?.[route.id] || route[`${side}Path`] || route.path;
    const states = route.states?.length ? route.states : [{ id: 'default', actions: [] }];
    for (const state of states) {
      const stateId = `${route.id}__${state.id}`;
      const dir = path.join(sideDir, slug(viewport.name), slug(stateId));
      const sink = { console: [], network: [] };
      const page = await context.newPage();
      attachObservers(page, sink);
      const entry = { id: stateId, routeId: route.id, stateId: state.id, viewport: viewport.name, dir: path.relative(outRoot, dir) };
      const warnings = [];
      try {
        const url = new URL(routePath, sideCfg.baseUrl).href;
        const resp = await page.goto(url, { waitUntil: route.waitUntil || 'networkidle', timeout: ctx.navTimeoutMs || 45000 });
        entry.httpStatus = resp?.status() ?? null;
        assertLandedOn(page, route);
        await settle(page, route, { strict: true });
        const preActions = [...(cfg.beforeEachState || []), ...(state.actions || [])];
        if (preActions.length) {
          entry.actions = await runActions(page, preActions,
            { record: [], baseUrl: sideCfg.baseUrl, pathOverrides: sideCfg.pathOverrides });
          await settle(page, route, { warnings });
          assertLandedOn(page, route);
        }
        const s = await snapshot(page, dir, { route, stateId, viewport: viewport.name, sink, warnings });
        entry.url = s.url;
        entry.frames = s.frames;
        if (warnings.length) entry.warnings = warnings;
        entry.status = 'ok';
      } catch (e) {
        entry.status = 'error';
        entry.error = String(e.message || e).split('\n')[0].slice(0, 400);
        entry.url = page.url();
        await failureEvidence(page, dir, { stateId, routeId: route.id, error: entry.error, waitFor: route.waitFor });
        runLog.errors.push({ state: stateId, error: entry.error });
      }
      runLog.states.push(entry);
      console.error(`[${side}] ${viewport.name} ${stateId}: ${entry.status}`);
      await page.close();
    }
  }

  if (viewport === viewports[0]) {
    for (const journey of journeys) {
      const sink = { console: [], network: [] };
      const page = await context.newPage();
      attachObservers(page, sink);
      const record = [];
      const captures = [];
      const warnings = [];
      let fatal = null;
      try {
        // A journey start path migrates just like a route path, so it honours pathOverrides too.
        const start = sideCfg.pathOverrides?.[journey.id]
          || journey[`${side}StartPath`] || journey.startPath || journey.path || '/';
        await page.goto(new URL(start, sideCfg.baseUrl).href, { waitUntil: 'networkidle', timeout: ctx.navTimeoutMs || 45000 });
        assertLandedOn(page, journey);
        await settle(page, journey, { strict: true });
        for (let i = 0; i < (journey.steps || []).length; i++) {
          const step = journey.steps[i];
          await runActions(page, [step], { record, baseUrl: sideCfg.baseUrl, pathOverrides: sideCfg.pathOverrides });
          if (step.type === 'capture') {
            await settle(page, journey, { warnings });
            const dir = path.join(sideDir, slug(viewport.name), slug(`${journey.id}__${step.id || i}`));
            await snapshot(page, dir, { route: journey, stateId: `${journey.id}__${step.id || i}`, viewport: viewport.name, sink, warnings });
            captures.push(path.relative(outRoot, dir));
          }
          if (record[record.length - 1]?.status === 'fail') break;
        }
      } catch (e) {
        fatal = String(e.message || e).split('\n')[0].slice(0, 300);
        record.push({ type: 'journey', status: 'fail', error: fatal });
        await failureEvidence(page, path.join(sideDir, slug(viewport.name), slug(`${journey.id}__failure`)),
          { journeyId: journey.id, error: fatal, waitFor: journey.waitFor });
      }
      const entry = {
        id: journey.id, viewport: viewport.name, steps: record, captures,
        finalUrl: page.url(), console: sink.console, network: sink.network,
        warnings: warnings.length ? warnings : undefined,
        invalid: fatal ? fatal : undefined,
        status: record.some((s) => s.status === 'fail') ? 'fail' : 'ok',
      };
      if (fatal) runLog.errors.push({ state: `journey:${journey.id}`, error: fatal });
      runLog.journeys.push(entry);
      console.error(`[${side}] journey ${journey.id}: ${entry.status}`);
      await page.close();
    }
  }

  await context.close();
}
} catch (e) {
  // Context-level failures (broken login, unusable browser) invalidate the whole side:
  // there is no point capturing 20 states of a login page.
  runLog.fatal = String(e.message || e).split('\n')[0].slice(0, 400);
  runLog.errors.push({ state: `side:${side}`, error: runLog.fatal });
  console.error(`[${side}] FATAL ${runLog.fatal}`);
}

await browser.close();
writeJson(path.join(sideDir, 'capture-log.json'), runLog);
console.log(JSON.stringify({
  side, outDir: sideDir, states: runLog.states.length,
  journeys: runLog.journeys.length, errors: runLog.errors.length,
  fatal: runLog.fatal || null,
}, null, 2));
if (runLog.fatal) process.exit(1);
process.exit(runLog.errors.length && !args.keepGoing ? 1 : 0);
