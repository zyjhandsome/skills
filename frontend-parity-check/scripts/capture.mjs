#!/usr/bin/env node
// Capture one side (baseline or candidate) of a parity run.
// Usage: node capture.mjs --config parity-config.json --side baseline [--out DIR] [--only routeId,...] [--headed]
import fs from 'node:fs';
import path from 'node:path';
import { loadPlaywright, ensureDir, writeJson, readJson, parseArgs, slug } from './lib/pw.mjs';
import { domDigestFn, styleProbeFn, DEFAULT_PROBES, STYLE_PROPS } from './lib/probes.mjs';

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
const browser = await pw[browserName].launch({ headless: !args.headed });
const sideDir = path.join(outRoot, side);
ensureDir(sideDir);

const runLog = {
  schema: 'parity-capture/v1',
  side,
  baseUrl: sideCfg.baseUrl,
  browser: `${browserName} ${browser.version()}`,
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
    await runActions(page, sideCfg.auth.actions, { record: [], baseUrl: sideCfg.baseUrl });
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
        case 'goto':
          await page.goto(new URL(a.path, acc.baseUrl).href, { waitUntil: a.waitUntil || 'networkidle' });
          break;
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
        case 'expectCount':
          step.observed = await page.locator(a.selector).count();
          break;
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

async function settle(page, route) {
  if (route?.waitFor?.selector) {
    await page.locator(route.waitFor.selector).first()
      .waitFor({ state: route.waitFor.state || 'visible', timeout: route.waitFor.timeout || 15000 })
      .catch(() => {});
  }
  await page.addStyleTag({ content: STABILIZE_CSS }).catch(() => {});
  await page.evaluate(() => document.fonts?.ready).catch(() => {});
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(Number(thresholds.settleMs ?? 400));
}

async function snapshot(page, dir, { route, stateId, viewport, sink }) {
  ensureDir(dir);
  const probes = [...DEFAULT_PROBES, ...(cfg.styleProbes || []), ...(route?.styleProbes || [])];
  const masks = [...(cfg.masks || []), ...(route?.masks || [])];

  const dom = await page.evaluate(domDigestFn).catch((e) => ({ error: String(e.message) }));
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
    title: await page.title().catch(() => null), masks, capturedAt: new Date().toISOString(),
  });
  return { shot, url: page.url() };
}

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
      try {
        const url = new URL(routePath, sideCfg.baseUrl).href;
        const resp = await page.goto(url, { waitUntil: route.waitUntil || 'networkidle', timeout: ctx.navTimeoutMs || 45000 });
        entry.httpStatus = resp?.status() ?? null;
        await settle(page, route);
        const preActions = [...(cfg.beforeEachState || []), ...(state.actions || [])];
        if (preActions.length) {
          entry.actions = await runActions(page, preActions, { record: [], baseUrl: sideCfg.baseUrl });
          await settle(page, route);
        }
        const s = await snapshot(page, dir, { route, stateId, viewport: viewport.name, sink });
        entry.url = s.url;
        entry.status = 'ok';
      } catch (e) {
        entry.status = 'error';
        entry.error = String(e.message || e).split('\n')[0].slice(0, 400);
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
      try {
        const start = journey.startPath || journey.path || '/';
        await page.goto(new URL(start, sideCfg.baseUrl).href, { waitUntil: 'networkidle', timeout: ctx.navTimeoutMs || 45000 });
        await settle(page, journey);
        for (let i = 0; i < (journey.steps || []).length; i++) {
          const step = journey.steps[i];
          await runActions(page, [step], { record, baseUrl: sideCfg.baseUrl });
          if (step.type === 'capture') {
            await settle(page, journey);
            const dir = path.join(sideDir, slug(viewport.name), slug(`${journey.id}__${step.id || i}`));
            await snapshot(page, dir, { route: journey, stateId: `${journey.id}__${step.id || i}`, viewport: viewport.name, sink });
            captures.push(path.relative(outRoot, dir));
          }
          if (record[record.length - 1]?.status === 'fail') break;
        }
      } catch (e) {
        record.push({ type: 'journey', status: 'fail', error: String(e.message || e).split('\n')[0].slice(0, 300) });
      }
      const entry = {
        id: journey.id, viewport: viewport.name, steps: record, captures,
        finalUrl: page.url(), console: sink.console, network: sink.network,
        status: record.some((s) => s.status === 'fail') ? 'fail' : 'ok',
      };
      runLog.journeys.push(entry);
      console.error(`[${side}] journey ${journey.id}: ${entry.status}`);
      await page.close();
    }
  }

  await context.close();
}

await browser.close();
writeJson(path.join(sideDir, 'capture-log.json'), runLog);
console.log(JSON.stringify({
  side, outDir: sideDir, states: runLog.states.length,
  journeys: runLog.journeys.length, errors: runLog.errors.length,
}, null, 2));
process.exit(runLog.errors.length && !args.keepGoing ? 1 : 0);
