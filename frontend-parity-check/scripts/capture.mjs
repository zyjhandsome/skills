#!/usr/bin/env node
// Capture one side (baseline or candidate) of a parity run.
// Usage: node capture.mjs --config parity-config.json --side baseline [--out DIR] [--only routeId,...] [--headed]
import fs from 'node:fs';
import path from 'node:path';
import { loadPlaywright, ensureDir, writeJson, readJson, parseArgs, slug, configFingerprint } from './lib/pw.mjs';
import { domDigestFn, styleProbeFn, visibleCountFn, DEFAULT_PROBES, STYLE_PROPS } from './lib/probes.mjs';
import {
  landingVerdict, resolveProbes, mergeDomDigests, resolveSurface, configValidationErrors,
} from './lib/parity-core.mjs';

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
  : path.resolve(path.dirname(configPath), cfg.outputDir || path.join('parity-runs', slug(cfg.name || 'unnamed')));
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
const configErrors = configValidationErrors(cfg);
if (configErrors.length) {
  console.error(`配置校验失败：\n- ${configErrors.join('\n- ')}`);
  process.exit(2);
}
const contractHash = configFingerprint(cfg);
const manifestPath = path.join(outRoot, 'run-manifest.json');
const existingManifest = readJson(manifestPath);
if (existingManifest?.configFingerprint && existingManifest.configFingerprint !== contractHash) {
  console.error(`输出目录已属于另一份契约：${outRoot}`);
  console.error('请更换带页面名/run-id 的 outputDir；不要覆盖并混用旧证据。');
  process.exit(2);
}
const configWarnings = [];
if ((cfg.fullPage === true || (cfg.routes || []).some((r) => r.fullPage === true))
  && (cfg.compareSurface || (cfg.masks || []).some((m) => /canvas|chart/i.test(m)))) {
  configWarnings.push('图表/显式比较面开启 fullPage 容易放大壳层与长页噪声；优先截业务 root 或首屏');
}
for (const warning of configWarnings) console.error(`[config warning] ${warning}`);

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
  schema: 'parity-capture/v2',
  side,
  baseUrl: sideCfg.baseUrl,
  browser: `${browserName}${channel ? ':' + channel : ''} ${browser.version()}`,
  capturedAt: new Date().toISOString(),
  configPath,
  configFingerprint: contractHash,
  context: { ...ctx, viewports },
  states: [],
  journeys: [],
  errors: [],
  configWarnings,
};

const DEFAULT_DATA_SELECTORS = [
  'tbody', '.el-table__body', '.vxe-table--body-wrapper', '.ant-table-tbody',
  '[data-parity-data]', '.chart-data', '.echarts-tooltip',
];

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
  // Authenticate against real time first. Freezing Date before SSO can invalidate token-expiry checks.
  if (ctx.freezeTime || ctx.seedRandom !== undefined) {
    await context.addInitScript(FREEZE_SCRIPT(ctx.freezeTime, ctx.seedRandom));
  }
  return context;
}

function attachObservers(page, sink) {
  const frameUrlOf = (request) => {
    try { return request.frame()?.url() || null; } catch { return null; }
  };
  page.on('console', (msg) => {
    if (['error', 'warning'].includes(msg.type())) {
      sink.console.push({ type: msg.type(), text: msg.text().slice(0, 400) });
    }
  });
  page.on('pageerror', (e) => sink.console.push({ type: 'pageerror', text: String(e.message).slice(0, 400) }));
  page.on('requestfailed', (r) =>
    sink.network.push({
      status: 'failed', method: r.method(), url: r.url(), error: r.failure()?.errorText,
      resourceType: r.resourceType(), frameUrl: frameUrlOf(r), navigation: r.isNavigationRequest(),
    }));
  page.on('response', (r) => {
    if (r.status() >= 400) {
      const req = r.request();
      sink.network.push({
        status: r.status(), method: req.method(), url: r.url(), resourceType: req.resourceType(),
        frameUrl: frameUrlOf(req), navigation: req.isNavigationRequest(),
      });
    }
  });
}

async function frameBySelector(page, selector, timeout) {
  const element = page.locator(selector).first();
  await element.waitFor({ state: 'attached', timeout });
  const handle = await element.elementHandle();
  const frame = await handle?.contentFrame();
  await handle?.dispose();
  if (!frame) throw new Error(`frame 未就绪：${selector}`);
  return frame;
}

async function actionTarget(page, action, acc) {
  const scope = action.scope || {};
  const targetPage = scope.page ? acc.pages?.[scope.page] : page;
  if (!targetPage) throw new Error(`未找到 popup/page scope：${scope.page}`);
  const frameSelector = scope.frame || action.frame || (!scope.page ? acc.defaultFrame : null);
  const context = frameSelector
    ? await frameBySelector(targetPage, frameSelector, action.timeout)
    : targetPage;
  const rootSelector = scope.root || (!scope.page ? acc.defaultRoot : null);
  const locatorRoot = rootSelector ? context.locator(rootSelector).first() : context;
  return { targetPage, context, locatorRoot };
}

function actionValue(action) {
  if (!action.valueEnv) return action.value;
  const value = process.env[action.valueEnv];
  if (value === undefined) throw new Error(`环境变量 ${action.valueEnv} 未设置`);
  return value;
}

async function runActions(page, actions = [], acc) {
  for (let i = 0; i < actions.length; i++) {
    const a = actions[i];
    const selector = a[`${side}Selector`] || a.selector;
    const step = { index: i, type: a.type, id: a.id || selector || a.path, status: 'ok' };
    try {
      const { targetPage, context, locatorRoot } = await actionTarget(page, a, acc);
      const loc = selector ? locatorRoot.locator(selector).nth(a.nth ?? 0) : null;
      switch (a.type) {
        case 'goto': {
          const target = (a.id && acc.pathOverrides?.[a.id]) || a.path;
          await context.goto(new URL(target, acc.baseUrl).href, { waitUntil: a.waitUntil || 'networkidle' });
          break;
        }
        case 'click': await loc.click({ force: a.force }); break;
        case 'clickAndExpectPopup': {
          const popupId = a.popupId || a.id || 'popup';
          const popupPromise = targetPage.waitForEvent('popup', { timeout: a.timeout });
          const [, popup] = await Promise.all([loc.click({ force: a.force }), popupPromise]);
          acc.pages ||= { main: page };
          acc.pages[popupId] = popup;
          if (acc.sink) attachObservers(popup, acc.sink);
          await popup.waitForLoadState(a.waitUntil || 'domcontentloaded').catch(() => {});
          step.observed = popup.url();
          step.popupId = popupId;
          break;
        }
        case 'expectPopup': {
          const popupId = a.popupId || a.id || 'popup';
          const popup = await targetPage.waitForEvent('popup', { timeout: a.timeout });
          acc.pages ||= { main: page };
          acc.pages[popupId] = popup;
          if (acc.sink) attachObservers(popup, acc.sink);
          step.observed = popup.url();
          step.popupId = popupId;
          break;
        }
        case 'dblclick': await loc.dblclick(); break;
        case 'hover': await loc.hover(); break;
        case 'fill': await loc.fill(String(actionValue(a))); break;
        case 'type': await loc.pressSequentially(String(actionValue(a)), { delay: a.delay ?? 20 }); break;
        case 'press': await (loc || targetPage.keyboard).press(a.key); break;
        case 'select': await loc.selectOption(actionValue(a)); break;
        case 'check': await loc.check(); break;
        case 'uncheck': await loc.uncheck(); break;
        case 'scrollTo':
          if (selector) await loc.scrollIntoViewIfNeeded();
          else await context.evaluate((y) => window.scrollTo(0, y), a.y ?? 0);
          break;
        case 'waitFor': await loc.waitFor({ state: a.state || 'visible', timeout: a.timeout }); break;
        case 'waitForUrl': await context.waitForURL(new RegExp(a.pattern), { timeout: a.timeout }); break;
        case 'waitTimeout': await targetPage.waitForTimeout(a.ms ?? 500); break;
        case 'expectVisible':
          step.observed = await loc.isVisible();
          break;
        case 'expectText':
          step.observed = ((await loc.innerText()) || '').replace(/\s+/g, ' ').trim().slice(0, 300);
          break;
        case 'expectCount': {
          // Default counts only what a user can see: `ng-hide` / `display:none` leftovers in the
          // old page used to inflate the count and produce a phantom "少了一项" finding.
          const nodes = locatorRoot.locator(selector);
          step.observedTotal = await nodes.count();
          step.visibleOnly = a.visibleOnly !== false;
          step.observed = step.visibleOnly ? await nodes.evaluateAll(visibleCountFn) : step.observedTotal;
          break;
        }
        case 'expectValue':
          step.observed = await loc.inputValue();
          break;
        case 'expectUrl':
          step.observed = context.url();
          break;
        case 'capture':
          step.observed = a.id;
          break;
        default:
          throw new Error(`不支持的动作类型：${a.type}`);
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

const surfaceFrameSelector = (surface) => typeof surface?.frame === 'string' ? surface.frame : surface?.frame?.selector;

async function surfaceContext(page, route) {
  const surface = resolveSurface(cfg, route || {}, side);
  const frameSelector = surfaceFrameSelector(surface);
  const context = frameSelector
    ? await frameBySelector(page, frameSelector, surface.timeout)
    : page;
  return { surface, context, frameSelector };
}

/**
 * Wait for the page to be comparable.
 * `strict` (right after navigation): a missed `waitFor` means we are not on the page
 * under test, so it throws instead of producing evidence for the wrong page.
 * Non-strict (after in-page actions): records a warning, since actions may have
 * legitimately navigated away from the anchor selector.
 */
async function settle(page, route, { strict = false, warnings = null } = {}) {
  const { surface, context } = await surfaceContext(page, route);
  const sel = surface.readySelector || route?.waitFor?.[`${side}Selector`] || route?.waitFor?.selector;
  if (sel) {
    try {
      const locatorRoot = surface.root ? context.locator(surface.root).first() : context;
      await locatorRoot.locator(sel).first()
        .waitFor({ state: route?.waitFor?.state || 'visible', timeout: route?.waitFor?.timeout || surface.timeout || 15000 });
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

const sideLayer = (value = {}) => {
  const { baseline, candidate, ...shared } = value || {};
  return { ...shared, ...((value && value[side]) || {}) };
};

/** Hard gate: validate both the browser shell URL and the selected business surface. */
async function assertLandedOn(page, route) {
  const rules = { ...sideLayer(assertLanded), ...sideLayer(route?.assertLanded) };
  const landed = landingVerdict(page.url(), rules);
  if (!landed.ok) throw new Error(landed.reason);
  const { surface, context, frameSelector } = await surfaceContext(page, route);
  if (surface.mainUrlPattern && !new RegExp(surface.mainUrlPattern, 'i').test(page.url())) {
    throw new Error(`主 frame URL 不满足 compareSurface.mainUrlPattern /${surface.mainUrlPattern}/ — ${page.url()}`);
  }
  if (surface.frameUrlPattern && !new RegExp(surface.frameUrlPattern, 'i').test(context.url())) {
    throw new Error(`业务 frame URL 不满足 compareSurface.frameUrlPattern /${surface.frameUrlPattern}/ — ${context.url()}`);
  }
  if (surface.root) {
    await context.locator(surface.root).first().waitFor({ state: 'visible', timeout: surface.timeout || 15000 });
  }
  if (surface.frame && !frameSelector) throw new Error('compareSurface.frame 缺少 selector');
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
async function collectDom(page, route) {
  const { surface, context, frameSelector } = await surfaceContext(page, route);
  const dataSelectors = [...DEFAULT_DATA_SELECTORS, ...(cfg.dataSelectors || []), ...(route?.dataSelectors || [])];
  const options = { root: surface.root, exclude: surface.exclude || [], dataSelectors };
  const selected = await context.evaluate(domDigestFn, options);
  const explicitSurface = !!(cfg.compareSurface || route?.compareSurface);
  if (explicitSurface && surface.includeFrames !== true) {
    selected.frames = frameSelector
      ? [{ url: context.url(), status: 'read', selected: true, selector: frameSelector }]
      : [];
    selected.surface = { id: surface.id || 'comparison-surface', frame: frameSelector || null, root: surface.root || null };
    return selected;
  }

  const main = selected;
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
      frames.push({ url, status: 'read', digest: await frame.evaluate(domDigestFn, {
        exclude: surface.exclude || [], dataSelectors,
      }) });
    } catch (e) {
      frames.push({ url, status: 'unreadable', error: String(e.message || e).split('\n')[0].slice(0, 200) });
    }
  }
  return mergeDomDigests(main, frames);
}

async function snapshot(page, dir, { route, stateId, viewport, sink, warnings = [] }) {
  ensureDir(dir);
  const probes = resolveProbes(cfg, route || {}, DEFAULT_PROBES, side);
  const { surface, context, frameSelector } = await surfaceContext(page, route);
  const masks = [...(cfg.masks || []), ...(route?.masks || []), ...(surface.exclude || [])];

  const dom = await collectDom(page, route);
  const styles = await context.evaluate(styleProbeFn, {
    probes, props: STYLE_PROPS, root: surface.root, exclude: surface.exclude || [],
  });
  const invalidProbes = Object.entries(styles).filter(([, value]) => value?.error);
  if (invalidProbes.length) {
    throw new Error(`styleProbes 配置错误：${invalidProbes.map(([id, value]) => `${id} (${value.error})`).join('、')}`);
  }

  const shot = path.join(dir, 'shot.png');
  const screenshotOptions = {
    path: shot,
    animations: 'disabled',
    caret: 'hide',
    scale: 'css',
    mask: masks.map((m) => context.locator(m)),
    maskColor: '#ff00ff',
  };
  if (surface.root) {
    await context.locator(surface.root).first().screenshot(screenshotOptions);
  } else if (frameSelector) {
    await page.locator(frameSelector).first().screenshot(screenshotOptions);
  } else {
    await page.screenshot({ ...screenshotOptions, fullPage: route?.fullPage ?? cfg.fullPage ?? false });
  }

  writeJson(path.join(dir, 'dom.json'), dom);
  writeJson(path.join(dir, 'styles.json'), styles);
  writeJson(path.join(dir, 'runtime.json'), { console: sink.console, network: sink.network });
  writeJson(path.join(dir, 'meta.json'), {
    side, stateId, routeId: route?.id, viewport, url: page.url(),
    title: await page.title().catch(() => null), masks,
    probes: probes.map((p) => p.id),
    compareSurface: { id: surface.id || null, frame: frameSelector || null, root: surface.root || null, exclude: surface.exclude || [] },
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
        await assertLandedOn(page, route);
        await settle(page, route, { strict: true });
        const preActions = [...(cfg.beforeEachState || []), ...(state.actions || [])];
        if (preActions.length) {
          entry.actions = await runActions(page, preActions,
            {
              record: [], baseUrl: sideCfg.baseUrl, pathOverrides: sideCfg.pathOverrides,
              defaultFrame: surfaceFrameSelector(resolveSurface(cfg, route, side)),
              defaultRoot: resolveSurface(cfg, route, side).root || null,
            });
          await settle(page, route, { warnings });
          await assertLandedOn(page, route);
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
      const actionAcc = {
        record, baseUrl: sideCfg.baseUrl, pathOverrides: sideCfg.pathOverrides,
        pages: { main: page }, sink,
        defaultFrame: surfaceFrameSelector(resolveSurface(cfg, journey, side)),
        defaultRoot: resolveSurface(cfg, journey, side).root || null,
      };
      let fatal = null;
      try {
        // A journey start path migrates just like a route path, so it honours pathOverrides too.
        const start = sideCfg.pathOverrides?.[journey.id]
          || journey[`${side}StartPath`] || journey.startPath || journey.path || '/';
        await page.goto(new URL(start, sideCfg.baseUrl).href, { waitUntil: 'networkidle', timeout: ctx.navTimeoutMs || 45000 });
        await assertLandedOn(page, journey);
        await settle(page, journey, { strict: true });
        for (let i = 0; i < (journey.steps || []).length; i++) {
          const step = journey.steps[i];
          await runActions(page, [step], actionAcc);
          if (step.type === 'capture') {
            const capturePage = step.scope?.page ? actionAcc.pages[step.scope.page] : page;
            if (!capturePage) throw new Error(`capture 找不到 page scope：${step.scope?.page}`);
            const captureRoute = step.scope?.page
              ? { ...journey, compareSurface: { reset: true, ...(step.compareSurface || {}) } }
              : journey;
            await settle(capturePage, captureRoute, { warnings });
            const dir = path.join(sideDir, slug(viewport.name), slug(`${journey.id}__${step.id || i}`));
            await snapshot(capturePage, dir, { route: captureRoute, stateId: `${journey.id}__${step.id || i}`, viewport: viewport.name, sink, warnings });
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
writeJson(manifestPath, {
  schema: 'parity-run-manifest/v1',
  name: cfg.name || null,
  configPath,
  configFingerprint: contractHash,
  outputDir: outRoot,
  sides: {
    ...(existingManifest?.sides || {}),
    [side]: { capturedAt: runLog.capturedAt, browser: runLog.browser, fatal: runLog.fatal || null },
  },
});
console.log(JSON.stringify({
  side, outDir: sideDir, states: runLog.states.length,
  journeys: runLog.journeys.length, errors: runLog.errors.length,
  fatal: runLog.fatal || null,
}, null, 2));
if (runLog.fatal) process.exit(1);
process.exit(runLog.errors.length && !args.keepGoing ? 1 : 0);
