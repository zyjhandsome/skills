// Pure decision helpers shared by capture.mjs / compare.mjs and covered by selftest/unit.mjs.
// Nothing here touches the network or the filesystem, so it can be asserted without a browser.
import { normalizeUrl } from './pw.mjs';

/**
 * URL shapes that mean "we did not land on the page under test".
 * Overridable per config (`assertLanded.forbidUrl` replaces this list).
 */
export const DEFAULT_FORBID_URL = [
  '/login([/?#.]|$)',
  '/signin([/?#.]|$)',
  '/logon([/?#.]|$)',
  '^https?://[^/]*\\blog(in|on)[-.]',   // login-beta.example.com, sso-login.corp.com

  '/cas/login',
  '/oauth2?/authorize',
  '[?&]redirect(_uri|_url)?=',
  '[?&]service=[^&]*log(in|on)',
];

function firstMatch(text, patterns = []) {
  for (const p of patterns) {
    try {
      if (new RegExp(p, 'i').test(text)) return p;
    } catch { /* an invalid user regex must not crash a run */ }
  }
  return null;
}

export const matchesAny = (text, patterns = []) => firstMatch(String(text ?? ''), patterns) !== null;

/**
 * Decide whether a settled page counts as valid evidence.
 * `assertLanded`: { forbidUrl?: string[], allowUrl?: string[], requireUrl?: string }
 */
export function landingVerdict(url, assertLanded = {}) {
  const u = String(url ?? '');
  const allowed = !!(assertLanded.allowUrl?.length && matchesAny(u, assertLanded.allowUrl));
  const hit = firstMatch(u, assertLanded.forbidUrl ?? DEFAULT_FORBID_URL);
  // allowUrl is only an exception to forbidUrl. It must never bypass requireUrl.
  if (hit && !allowed) return {
    ok: false, gate: 'forbid-url', pattern: hit, url: u,
    reason: `落地 URL 命中禁止模式 /${hit}/ — ${u}`,
  };
  if (assertLanded.requireUrl && !matchesAny(u, [assertLanded.requireUrl])) {
    return { ok: false, gate: 'require-url', pattern: assertLanded.requireUrl, url: u,
      reason: `落地 URL 不满足 requireUrl /${assertLanded.requireUrl}/ — ${u}` };
  }
  return { ok: true, ...(allowed ? { allowed: true } : {}) };
}

const pathnameOf = (p) => {
  try {
    return new URL(p, 'http://parity.local').pathname;
  } catch {
    return null;
  }
};

/**
 * Every path this side is expected to serve, mapped to a side-independent token,
 * so a declared route migration stops looking like a navigation defect.
 */
export function buildPathTokens(cfg = {}, side) {
  const sideCfg = cfg[side] || {};
  const tokens = [];
  const push = (p, token) => {
    const pathname = p && pathnameOf(p);
    if (pathname && pathname !== '/') tokens.push({ pathname, token });
  };
  for (const r of cfg.routes || []) {
    push(sideCfg.pathOverrides?.[r.id] || r[`${side}Path`] || r.path, `{route:${r.id}}`);
  }
  for (const j of cfg.journeys || []) {
    push(sideCfg.pathOverrides?.[j.id] || j[`${side}StartPath`] || j.startPath || j.path, `{journey:${j.id}}`);
  }
  for (const [p, token] of Object.entries(sideCfg.urlTokens || {})) push(p, token);
  return tokens.sort((a, b) => b.pathname.length - a.pathname.length);
}

/**
 * Origin + volatile-param + declared-path normalization.
 * `mode: 'query'` keeps only search/hash — for `expectUrl` steps marked `ignorePath`.
 */
export function normalizeRouteUrl(url, { origins = [], tokens = [], rules = [], mode = 'full' } = {}) {
  if (typeof url !== 'string' || !url) return url;
  let out = normalizeUrl(url, origins);
  for (const rule of rules) {
    try {
      out = out.replace(new RegExp(rule.pattern, 'g'), rule.replace ?? '{norm}');
    } catch { /* invalid user regex is ignored */ }
  }
  for (const t of tokens) out = out.split(t.pathname).join(t.token);
  if (mode === 'query') {
    const i = out.search(/[?#]/);
    return i === -1 ? '' : out.slice(i);
  }
  return out;
}

/**
 * Which style probes actually run: `defaultProbes` can drop or narrow the built-in set,
 * and a custom probe reusing a built-in id replaces it.
 */
export function resolveProbes(cfg = {}, route = {}, defaults = [], side = null) {
  const pick = cfg.defaultProbes;
  let base;
  if (pick === false) base = [];
  else if (Array.isArray(pick)) base = defaults.filter((p) => pick.includes(p.id));
  else base = defaults;
  const byId = new Map();
  for (const p of [...base, ...(cfg.styleProbes || []), ...(route.styleProbes || [])]) {
    const selector = side && p?.[`${side}Selector`] ? p[`${side}Selector`] : p?.selector;
    if (p?.id && selector) byId.set(p.id, { ...p, selector });
  }
  return [...byId.values()];
}

/** Resolve a shared + side-specific comparison surface, with route values winning. */
export function resolveSurface(cfg = {}, route = {}, side) {
  const layer = (value = {}) => {
    const { baseline, candidate, ...shared } = value || {};
    return { ...shared, ...((side && value?.[side]) || {}) };
  };
  const global = layer(cfg.compareSurface);
  const local = layer(route.compareSurface);
  if (local.reset) {
    const { reset, ...rest } = local;
    return { ...rest, exclude: rest.exclude || [] };
  }
  const exclude = [...(global.exclude || []), ...(local.exclude || [])];
  return { ...global, ...local, exclude };
}

/** styleProbes execute in document.querySelectorAll, not Playwright's selector engine. */
export function configValidationErrors(cfg = {}) {
  const errors = [];
  if (cfg.channel && cfg.executablePath) errors.push('channel 与 executablePath 只能配置一个');
  const playwrightOnly = /:has-text\s*\(|(^|[\s,])text=|>>|(^|[\s,])role=/i;
  const inspect = (p, where) => {
    if (!p?.id) errors.push(`${where}.id 必填`);
    if (!p?.selector && (!p?.baselineSelector || !p?.candidateSelector)) {
      errors.push(`${where} 必须提供 selector，或同时提供 baselineSelector/candidateSelector`);
    }
    for (const key of ['selector', 'baselineSelector', 'candidateSelector']) {
      const selector = p?.[key];
      if (selector && playwrightOnly.test(selector)) {
        errors.push(`${where}.${key} 必须是原生 CSS，不能使用 Playwright 语法：${selector}`);
      }
    }
  };
  (cfg.styleProbes || []).forEach((p, i) => inspect(p, `styleProbes[${i}]`));
  (cfg.routes || []).forEach((r, ri) => (r.styleProbes || []).forEach((p, i) => inspect(p, `routes[${ri}].styleProbes[${i}]`)));

  const actionTypes = new Set([
    'goto', 'click', 'clickAndExpectPopup', 'expectPopup', 'dblclick', 'hover', 'fill', 'type',
    'press', 'select', 'check', 'uncheck', 'scrollTo', 'waitFor', 'waitForUrl', 'waitTimeout',
    'expectVisible', 'expectText', 'expectCount', 'expectValue', 'expectUrl', 'capture',
  ]);
  const selectorRequired = new Set([
    'click', 'clickAndExpectPopup', 'dblclick', 'hover', 'fill', 'type', 'select', 'check', 'uncheck',
    'waitFor', 'expectVisible', 'expectText', 'expectCount', 'expectValue',
  ]);
  const inspectAction = (action, where) => {
    if (!actionTypes.has(action?.type)) errors.push(`${where}.type 不支持：${action?.type}`);
    if (selectorRequired.has(action?.type)
      && !action.selector && (!action.baselineSelector || !action.candidateSelector)) {
      errors.push(`${where} 必须提供 selector，或同时提供 baselineSelector/candidateSelector`);
    }
  };
  for (const side of ['baseline', 'candidate']) {
    const auth = cfg[side]?.auth || {};
    if (auth.mode && auth.mode !== 'auto-interactive') {
      errors.push(`${side}.auth.mode 不支持：${auth.mode}（当前仅需为交互模式显式设置 auto-interactive）`);
    }
    if (auth.mode === 'auto-interactive' && auth.actions?.length) {
      errors.push(`${side}.auth 不能同时使用 mode=auto-interactive 与 actions`);
    }
    if (auth.interactive?.channel && auth.interactive?.executablePath) {
      errors.push(`${side}.auth.interactive.channel 与 executablePath 只能配置一个`);
    }
    for (const key of ['timeoutMs', 'probeTimeoutMs', 'readinessTimeoutMs']) {
      const value = auth.interactive?.[key];
      if (value !== undefined && (!Number.isFinite(Number(value)) || Number(value) <= 0)) {
        errors.push(`${side}.auth.interactive.${key} 必须是正数`);
      }
    }
    (auth.actions || []).forEach((a, i) => inspectAction(a, `${side}.auth.actions[${i}]`));
  }
  (cfg.beforeEachState || []).forEach((a, i) => inspectAction(a, `beforeEachState[${i}]`));
  (cfg.routes || []).forEach((r, ri) => (r.states || []).forEach((s, si) =>
    (s.actions || []).forEach((a, i) => inspectAction(a, `routes[${ri}].states[${si}].actions[${i}]`))));
  (cfg.journeys || []).forEach((j, ji) => (j.steps || []).forEach((a, i) => inspectAction(a, `journeys[${ji}].steps[${i}]`)));
  return errors;
}

/**
 * A property that drifted on many probes at once is one theme/token regression,
 * not N findings. Splits probe diffs into global drift + probe-specific leftovers.
 */
export function aggregateStyleDrift(entries = [], minProbes = 3) {
  const propOf = (change) => String(change).split(':')[0].trim();
  const byProp = new Map();
  for (const e of entries) {
    for (const c of e.changes || []) {
      const rec = byProp.get(propOf(c)) || { probes: [], sample: c };
      rec.probes.push(e.probe);
      byProp.set(propOf(c), rec);
    }
  }
  const global = [...byProp.entries()]
    .filter(([, r]) => r.probes.length >= minProbes)
    .map(([prop, r]) => ({ prop, probes: r.probes, sample: r.sample }));
  const globalProps = new Set(global.map((g) => g.prop));
  const perProbe = entries
    .map((e) => ({ probe: e.probe, changes: (e.changes || []).filter((c) => !globalProps.has(propOf(c))) }))
    .filter((e) => e.changes.length);
  return { global, perProbe };
}

/** Frames whose DOM could not be read — their content must not be reported as "missing". */
export const unreadableFrames = (dom) => (dom?.frames || []).filter((f) => f.status === 'unreadable');

/** Fold same-origin and readable cross-origin frame digests into the page digest. */
export function mergeDomDigests(main = {}, frames = []) {
  const out = { ...main };
  const lists = ['headings', 'actions', 'fields', 'links', 'images', 'grids', 'textOutline', 'textItems'];
  const annotate = (value, source) => value && typeof value === 'object' && !Array.isArray(value)
    ? { ...value, source: value.source || source }
    : value;
  for (const key of lists) {
    if (Array.isArray(out[key])) out[key] = out[key].map((value) => annotate(value, 'main'));
  }
  for (let index = 0; index < frames.length; index++) {
    const f = frames[index];
    if (!f.digest) continue;
    for (const key of lists) {
      if (Array.isArray(f.digest[key])) {
        out[key] = [...(out[key] || []), ...f.digest[key].map((value) => annotate(value, `frame:${index}`))];
      }
    }
  }
  if (Array.isArray(out.textOutline)) out.textOutline = out.textOutline.slice(0, 900);
  out.frames = frames.map((f) => ({
    url: f.url, status: f.status, error: f.error,
    ...(f.selected !== undefined ? { selected: f.selected } : {}),
    ...(f.selector !== undefined ? { selector: f.selector } : {}),
  }));
  return out;
}
