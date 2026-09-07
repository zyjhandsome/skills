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

export function authStoragePath(configPath, side, sideCfg = {}) {
  const configured = sideCfg.auth?.storageState || `./auth/${side}.json`;
  return path.resolve(path.dirname(configPath), configured);
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
