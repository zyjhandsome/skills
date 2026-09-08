import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { landingVerdict, resolveSurface } from './parity-core.mjs';

export const AUTO_INTERACTIVE_AUTH = 'auto-interactive';

/** Unready pages open a login window by default. Only an explicit false keeps the old refuse-first gate. */
export function shouldOpenInteractive({
  forceInteractive = false,
  loginLikely = false,
  openOnUnready,
} = {}) {
  if (forceInteractive || loginLikely) return true;
  return openOnUnready !== false;
}

/** Headless probe runs unless an explicit --skip-probe. --force-interactive never skips reuse. */
export function shouldProbeFirst({ skipProbe = false } = {}) {
  return !skipProbe;
}

/** Persist storageState only when the live window AND a cold-start reload both look ready. */
export function shouldCommitAuthState({ windowReady = false, coldStartReady = false } = {}) {
  return !!(windowReady && coldStartReady);
}

const EARLY_AUTH_READY = [
  'html', 'body', '#app', '#root', '#__nuxt', '#__next', '#__vue',
  '.cus-item-title', 'header', 'nav', '.el-header', '.el-aside',
  '.breadcrumb', '.el-breadcrumb', '.el-menu',
];

function selectorLooksEarly(selector, token) {
  const s = String(selector).trim().toLowerCase();
  const t = token.toLowerCase();
  return s === t || s.startsWith(`${t} `) || s.startsWith(`${t}.`) || s.startsWith(`${t}#`) || s.startsWith(`${t}[`);
}

/** Shell/header nodes exist before SSO finishes; they must not count as login success. */
export function earlyAuthReadyWarning(selector) {
  if (!selector) return null;
  const hit = EARLY_AUTH_READY.find((token) => selectorLooksEarly(selector, token));
  if (!hit) return null;
  return `就绪选择器「${selector}」像登录前就有的壳节点（${hit}）。请改成登录后才出现的节点，否则会把未完成的登录存成 ready。`;
}

export function resolvedAuthReadySelector(cfg, side) {
  const { item, surface, readySelector } = firstAuthTarget(cfg, side);
  return readySelector
    || surface.readySelector
    || item?.waitFor?.[`${side}Selector`]
    || item?.waitFor?.selector
    || null;
}

export function authStoragePath(configPath, side, sideCfg = {}) {
  const configured = sideCfg.auth?.storageState || `./auth/${side}.json`;
  return path.resolve(path.dirname(configPath), configured);
}

/** Marker file the agent writes after the user replies「已登录」. */
export function authConfirmPath(configPath, side, sideCfg = {}) {
  const configured = sideCfg.auth?.interactive?.confirmPath;
  if (configured) return path.resolve(path.dirname(configPath), configured);
  return path.join(path.dirname(authStoragePath(configPath, side, sideCfg)), `.confirm-${side}`);
}

/** Lease proving that a prepare-auth process really owns a live login context. */
export function authWaitStatePath(configPath, side, sideCfg = {}) {
  return `${authConfirmPath(configPath, side, sideCfg)}.waiting.json`;
}

export function readAuthWaitState(waitStatePath) {
  try {
    return JSON.parse(fs.readFileSync(waitStatePath, 'utf8'));
  } catch {
    return null;
  }
}

export function writeAuthWaitState(waitStatePath, state) {
  fs.mkdirSync(path.dirname(waitStatePath), { recursive: true });
  const temp = `${waitStatePath}.${process.pid}.tmp`;
  fs.writeFileSync(temp, `${JSON.stringify(state, null, 2)}\n`, 'utf8');
  fs.copyFileSync(temp, waitStatePath);
  fs.rmSync(temp, { force: true });
  return waitStatePath;
}

export function clearAuthWaitState(waitStatePath, expectedPid = null) {
  if (!waitStatePath || !fs.existsSync(waitStatePath)) return false;
  const state = readAuthWaitState(waitStatePath);
  if (expectedPid !== null && Number(state?.pid) !== Number(expectedPid)) return false;
  fs.rmSync(waitStatePath, { force: true });
  return true;
}

export function isProcessAlive(pid) {
  const n = Number(pid);
  if (!Number.isInteger(n) || n <= 0) return false;
  try {
    process.kill(n, 0);
    return true;
  } catch (error) {
    // EPERM means the process exists but this account cannot signal it.
    return error?.code === 'EPERM';
  }
}

export function consumeUserConfirm(confirmPath) {
  if (!confirmPath || !fs.existsSync(confirmPath)) return false;
  fs.rmSync(confirmPath, { force: true });
  return true;
}

export function writeUserConfirm(confirmPath) {
  fs.mkdirSync(path.dirname(confirmPath), { recursive: true });
  fs.writeFileSync(confirmPath, `confirmed ${new Date().toISOString()}\n`);
  return confirmPath;
}

/**
 * After the login window is open:
 * ready pages still auto-commit; a user「已登录」confirm ends the wait immediately.
 */
export function interactiveWaitDecision({
  windowReady = false,
  userConfirmed = false,
  timedOut = false,
  closed = false,
} = {}) {
  if (closed) return 'closed';
  if (windowReady) return 'commit';
  if (userConfirmed) return 'commit-or-fail';
  if (timedOut) return 'timeout';
  return 'keep-waiting';
}

export function shouldPrintHeartbeat(lastPrintedAt = 0, now = 0, intervalMs = 15000) {
  if (!lastPrintedAt) return true;
  return now - lastPrintedAt >= intervalMs;
}

export function authProfilePath(configPath, side, cfg = {}, sideCfg = {}) {
  const configured = sideCfg.auth?.interactive?.profileDir;
  if (configured) return path.resolve(path.dirname(configPath), configured);
  const name = String(cfg.name || 'unnamed').replace(/[^\w.-]+/g, '-').replace(/^-|-$/g, '') || 'unnamed';
  return path.resolve(path.dirname(configPath), 'auth', 'profiles', name, side);
}

/** Never attach a persistent context directly to the user's daily Chrome/Edge profile. */
export function unsafeDailyProfileReason(profileDir) {
  const target = path.resolve(profileDir).toLowerCase();
  const home = os.homedir();
  const known = [
    path.join(home, 'AppData', 'Local', 'Google', 'Chrome', 'User Data'),
    path.join(home, 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data'),
    path.join(home, 'Library', 'Application Support', 'Google', 'Chrome'),
    path.join(home, 'Library', 'Application Support', 'Microsoft Edge'),
    path.join(home, '.config', 'google-chrome'),
    path.join(home, '.config', 'microsoft-edge'),
  ].map((p) => path.resolve(p).toLowerCase());
  const hit = known.find((p) => target === p || target.startsWith(`${p}${path.sep}`));
  return hit ? `profileDir 指向日常浏览器用户目录：${profileDir}` : null;
}

function sideLayer(value = {}, side) {
  const { baseline, candidate, ...shared } = value || {};
  return { ...shared, ...((side && value?.[side]) || {}) };
}

export function firstAuthTarget(cfg = {}, side) {
  const sideCfg = cfg[side] || {};
  const item = (cfg.routes || [])[0] || (cfg.journeys || [])[0] || {};
  const interactive = sideCfg.auth?.interactive || {};
  const pathValue = interactive.startPath
    || sideCfg.pathOverrides?.[item.id]
    || item[`${side}Path`]
    || item[`${side}StartPath`]
    || item.path
    || item.startPath
    || '/';
  return {
    item,
    url: new URL(pathValue, sideCfg.baseUrl).href,
    rules: {
      ...sideLayer(cfg.assertLanded, side),
      ...sideLayer(item.assertLanded, side),
      ...(interactive.successUrlPattern ? { requireUrl: interactive.successUrlPattern } : {}),
    },
    surface: resolveSurface(cfg, item, side),
    readySelector: interactive.readySelector,
  };
}

const frameSelectorOf = (surface) => typeof surface?.frame === 'string'
  ? surface.frame
  : surface?.frame?.selector;

async function frameBySelector(page, selector, timeout) {
  const element = page.locator(selector).first();
  await element.waitFor({ state: 'attached', timeout });
  const handle = await element.elementHandle();
  const frame = await handle?.contentFrame();
  await handle?.dispose();
  if (!frame) throw new Error(`frame 未就绪：${selector}`);
  return frame;
}

async function looksLikeLoginPage(page) {
  for (const frame of page.frames()) {
    try {
      const password = await frame.locator('input[type="password"], input[autocomplete="current-password"]').count();
      if (password) return true;
      const identity = await frame.locator('input[type="email"], input[autocomplete="username"], input[name*="user" i]').count();
      const submit = await frame.locator('button[type="submit"], input[type="submit"]').count();
      if (identity && submit) return true;
    } catch { /* inaccessible/detached frames are not evidence either way */ }
  }
  return false;
}

/** Validate the same URL/surface/readiness gates capture will use, without storing secrets in logs. */
export async function inspectAuthReadiness(page, cfg, side, timeout = 1000) {
  const { item, rules, surface, readySelector, url: targetUrl } = firstAuthTarget(cfg, side);
  const landed = landingVerdict(page.url(), rules);
  if (!landed.ok) return {
    ok: false, stage: 'landing', reason: landed.reason, url: page.url(),
    loginLikely: landed.gate === 'forbid-url' || await looksLikeLoginPage(page),
  };
  if (surface.mainUrlPattern && !new RegExp(surface.mainUrlPattern, 'i').test(page.url())) {
    return {
      ok: false, stage: 'surface', reason: `主 frame URL 不满足 /${surface.mainUrlPattern}/`, url: page.url(),
      loginLikely: await looksLikeLoginPage(page),
    };
  }
  try {
    const frameSelector = frameSelectorOf(surface);
    if (surface.frame && !frameSelector) throw new Error('compareSurface.frame 缺少 selector');
    const context = frameSelector ? await frameBySelector(page, frameSelector, timeout) : page;
    if (surface.frameUrlPattern && !new RegExp(surface.frameUrlPattern, 'i').test(context.url())) {
      throw new Error(`业务 frame URL 不满足 /${surface.frameUrlPattern}/`);
    }
    const root = surface.root ? context.locator(surface.root).first() : context;
    if (surface.root) await root.waitFor({ state: 'visible', timeout });
    const selector = readySelector
      || surface.readySelector
      || item?.waitFor?.[`${side}Selector`]
      || item?.waitFor?.selector;
    if (selector) {
      await root.locator(selector).first().waitFor({
        state: item?.waitFor?.state || 'visible',
        timeout,
      });
    }
    return { ok: true, url: page.url(), targetUrl };
  } catch (error) {
    return {
      ok: false,
      stage: 'ready',
      reason: String(error?.message || error).split('\n')[0],
      url: page.url(),
      loginLikely: await looksLikeLoginPage(page),
    };
  }
}
