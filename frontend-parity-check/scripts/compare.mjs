#!/usr/bin/env node
// Compare a captured baseline vs candidate and emit parity-summary.json + parity-report.md.
// Usage: node compare.mjs --config parity-config.json [--out DIR]
import fs from 'node:fs';
import path from 'node:path';
import {
  loadPlaywright, ensureDir, writeJson, readJson, parseArgs, normalizeText,
  configFingerprint, stableStringify, slug,
} from './lib/pw.mjs';
import {
  buildPathTokens, normalizeRouteUrl, landingVerdict, aggregateStyleDrift, unreadableFrames,
  configValidationErrors,
} from './lib/parity-core.mjs';

const args = parseArgs(process.argv.slice(2));
if (!args.config) {
  console.error('usage: node compare.mjs --config <file> [--out DIR]');
  process.exit(2);
}
const configPath = path.resolve(args.config);
const cfg = readJson(configPath) || {};
if (!cfg.baseline?.baseUrl || !cfg.candidate?.baseUrl) {
  console.error('配置必须同时提供 baseline.baseUrl 与 candidate.baseUrl');
  process.exit(2);
}
const configErrors = configValidationErrors(cfg);
if (configErrors.length) {
  console.error(`配置校验失败：\n- ${configErrors.join('\n- ')}`);
  process.exit(2);
}
const outRoot = args.out
  ? path.resolve(args.out)
  : path.resolve(path.dirname(configPath), cfg.outputDir || path.join('parity-runs', slug(cfg.name || 'unnamed')));
const baseDir = path.join(outRoot, 'baseline');
const candDir = path.join(outRoot, 'candidate');

const baseLog = readJson(path.join(baseDir, 'capture-log.json'));
const candLog = readJson(path.join(candDir, 'capture-log.json'));
if (!baseLog || !candLog) {
  console.error(`missing capture-log.json under ${outRoot}. Run capture.mjs for both sides first.`);
  process.exit(2);
}

const th = cfg.thresholds || {};
const PIXEL_RATIO = Number(th.pixelDiffRatio ?? 0.005);
const CHANNEL_TOL = Number(th.pixelChannelTolerance ?? 32);
const LAYOUT_TOL = Number(th.layoutTolerancePx ?? 2);
const SIZE_TOL_RATIO = Number(th.layoutToleranceRatio ?? 0.02);
const DATA_PARITY = cfg.dataParity || 'different-data'; // same-data | different-data
const STYLE_INTENT = cfg.styleIntent || 'pixel-parity'; // pixel-parity | redesign-allowed
const RUNTIME_POLICY = cfg.runtimePolicy || {};
const HIGH_IMPACT_PROPS = ['font-family', 'font-size', 'font-weight', 'color', 'background-color', 'display', 'line-height'];
const MASK_PATTERNS = cfg.maskTextPatterns || [];
const ORIGINS = [cfg.baseline?.baseUrl, cfg.candidate?.baseUrl]
  .filter(Boolean)
  .map((u) => { try { return new URL(u).origin; } catch { return null; } })
  .filter(Boolean);

const findings = [];
const SEV_ORDER = { block: 0, major: 1, minor: 2, info: 3 };
const add = (f) => findings.push(f);
const nText = (s) => normalizeText(s, MASK_PATTERNS);
const CURRENT_FINGERPRINT = configFingerprint(cfg);
const contractIssues = [];
for (const [side, log] of [['baseline', baseLog], ['candidate', candLog]]) {
  if (!log.configFingerprint) contractIssues.push(`${side} capture 缺少 configFingerprint，请重新采集`);
  else if (log.configFingerprint !== CURRENT_FINGERPRINT) contractIssues.push(`${side} capture 使用了不同配置`);
}
if (baseLog.browser !== candLog.browser) {
  contractIssues.push(`浏览器环境不同：baseline=${baseLog.browser} / candidate=${candLog.browser}`);
}
if (stableStringify(baseLog.context) !== stableStringify(candLog.context)) {
  contractIssues.push('两侧 context（视口/locale/timezone 等）不同');
}
const contractComparable = contractIssues.length === 0;
if (!contractComparable) {
  add({
    layer: 'L0', severity: 'block', state: 'contract', item: '采集契约不一致', invalidates: true,
    detail: `${contractIssues.join('；')} — 禁止混用证据，请用同一配置重新采集两侧`,
  });
}

// A declared route migration (`pathOverrides` / `<side>Path` / `urlTokens`) is collapsed to a
// side-independent token, so "/order/list.do" vs "/orders" stops reading as a navigation defect
// while an *undeclared* path difference still does.
const TOKENS = { baseline: buildPathTokens(cfg, 'baseline'), candidate: buildPathTokens(cfg, 'candidate') };
const URL_RULES = cfg.urlNormalizeRules || [];
const nUrl = (s, side, mode = 'full') =>
  normalizeRouteUrl(s, { origins: ORIGINS, tokens: side ? TOKENS[side] : [], rules: URL_RULES, mode });
const ASSERT_LANDED = cfg.assertLanded || {};
const STYLE_AGGREGATE_MIN = Number(th.styleAggregateMinProbes ?? 3);
const journeyById = Object.fromEntries((cfg.journeys || []).map((j) => [j.id, j]));
const meta = (dir) => readJson(path.join(outRoot, dir, 'meta.json'), {});
/** Data-dependent differences drop to info when the two sides read different databases. */
const dataSev = (sev) => (DATA_PARITY === 'same-data' ? sev : 'info');

function setDiff(a = [], b = []) {
  const ca = new Map();
  const cb = new Map();
  for (const x of a) ca.set(x, (ca.get(x) || 0) + 1);
  for (const x of b) cb.set(x, (cb.get(x) || 0) + 1);
  const onlyBaseline = [];
  const onlyCandidate = [];
  for (const [k, n] of ca) if ((cb.get(k) || 0) < n) onlyBaseline.push(k);
  for (const [k, n] of cb) if ((ca.get(k) || 0) < n) onlyCandidate.push(k);
  return { onlyBaseline, onlyCandidate };
}

const patternHit = (value, patterns = []) => [].concat(patterns || []).some((pattern) => {
  try { return new RegExp(pattern, 'i').test(value); } catch { return false; }
});

function networkSeverity(entry) {
  if (patternHit(entry.url, RUNTIME_POLICY.ignoreRequestPatterns)) return 'info';
  if (patternHit(entry.url, RUNTIME_POLICY.blockRequestPatterns)) return 'block';
  if (patternHit(entry.url, RUNTIME_POLICY.majorRequestPatterns)) return 'major';
  if (entry.navigation && entry.resourceType === 'document') return 'block';
  return 'major';
}

// ---------- L5: pixel diff, computed inside Playwright's own Chromium ----------
let browser = null;
let browserLaunchError = null;
async function getBrowser() {
  if (browser) return browser;
  if (browserLaunchError) return null;
  const pw = await loadPlaywright(process.cwd());
  if (!pw) {
    browserLaunchError = 'playwright unavailable';
    return null;
  }
  // Same launch options as capture: on a locked-down machine only `channel` works.
  const options = { headless: true };
  const channel = args.channel || cfg.channel;
  const executablePath = args.executablePath || cfg.executablePath;
  if (channel) options.channel = channel;
  if (executablePath) options.executablePath = executablePath;
  try {
    browser = await pw[cfg.browser || 'chromium'].launch(options);
  } catch (error) {
    browserLaunchError = String(error?.message || error).split('\n')[0];
    return null;
  }
  return browser;
}

async function pixelDiff(aPath, bPath, outPath) {
  const b = await getBrowser();
  if (!b) return { skipped: browserLaunchError || 'playwright unavailable' };
  const page = await b.newPage();
  try {
    const toData = (p) => 'data:image/png;base64,' + fs.readFileSync(p).toString('base64');
    const res = await page.evaluate(async ({ a, bImg, tol }) => {
      const load = (src) => new Promise((ok, no) => {
        const i = new Image();
        i.onload = () => ok(i);
        i.onerror = () => no(new Error('decode failed'));
        i.src = src;
      });
      const [ia, ib] = await Promise.all([load(a), load(bImg)]);
      const w = Math.max(ia.width, ib.width);
      const h = Math.max(ia.height, ib.height);
      const data = (img) => {
        const c = document.createElement('canvas');
        c.width = w; c.height = h;
        const x = c.getContext('2d', { willReadFrequently: true });
        x.fillStyle = '#ffffff';
        x.fillRect(0, 0, w, h);
        x.drawImage(img, 0, 0);
        return x.getImageData(0, 0, w, h);
      };
      const da = data(ia);
      const db = data(ib);
      const out = document.createElement('canvas');
      out.width = w; out.height = h;
      const octx = out.getContext('2d');
      const od = octx.createImageData(w, h);
      const GX = 24;
      const GY = 24;
      const heat = new Array(GX * GY).fill(0);
      let diffPixels = 0;
      let minX = w, minY = h, maxX = -1, maxY = -1;
      for (let i = 0, p = 0; i < da.data.length; i += 4, p++) {
        const dr = Math.abs(da.data[i] - db.data[i]);
        const dg = Math.abs(da.data[i + 1] - db.data[i + 1]);
        const dbl = Math.abs(da.data[i + 2] - db.data[i + 2]);
        const changed = Math.max(dr, dg, dbl) > tol;
        const x = p % w;
        const y = (p / w) | 0;
        if (changed) {
          diffPixels++;
          od.data[i] = 255; od.data[i + 1] = 0; od.data[i + 2] = 90; od.data[i + 3] = 255;
          heat[((y * GY / h) | 0) * GX + ((x * GX / w) | 0)]++;
          if (x < minX) minX = x;
          if (y < minY) minY = y;
          if (x > maxX) maxX = x;
          if (y > maxY) maxY = y;
        } else {
          const lum = 255 - (255 - (da.data[i] * 0.299 + da.data[i + 1] * 0.587 + da.data[i + 2] * 0.114)) * 0.25;
          od.data[i] = od.data[i + 1] = od.data[i + 2] = lum;
          od.data[i + 3] = 255;
        }
      }
      octx.putImageData(od, 0, 0);
      const total = w * h;
      const topCells = heat
        .map((v, idx) => ({ v, col: idx % GX, row: (idx / GX) | 0 }))
        .filter((c) => c.v > 0)
        .sort((x, y2) => y2.v - x.v)
        .slice(0, 6)
        .map((c) => ({
          region: `x ${Math.round((c.col / GX) * 100)}%-${Math.round(((c.col + 1) / GX) * 100)}%, y ${Math.round((c.row / GY) * 100)}%-${Math.round(((c.row + 1) / GY) * 100)}%`,
          pixels: c.v,
        }));
      return {
        width: w, height: h,
        baselineSize: [ia.width, ia.height],
        candidateSize: [ib.width, ib.height],
        sizeMismatch: ia.width !== ib.width || ia.height !== ib.height,
        diffPixels, totalPixels: total, ratio: diffPixels / total,
        bbox: maxX < 0 ? null : { x: minX, y: minY, w: maxX - minX + 1, h: maxY - minY + 1 },
        hotspots: topCells,
        png: out.toDataURL('image/png'),
      };
    }, { a: toData(aPath), bImg: toData(bPath), tol: CHANNEL_TOL });

    if (res.png && res.diffPixels > 0) {
      ensureDir(path.dirname(outPath));
      fs.writeFileSync(outPath, Buffer.from(res.png.split(',')[1], 'base64'));
      res.diffImage = path.relative(outRoot, outPath).replace(/\\/g, '/');
    }
    delete res.png;
    return res;
  } catch (e) {
    return { error: String(e.message || e).slice(0, 300) };
  } finally {
    await page.close();
  }
}

// ---------- L0: reachability / runtime errors ----------
function compareRuntime(stateId, a, b) {
  if (a.httpStatus !== b.httpStatus) {
    add({ layer: 'L0', severity: 'block', state: stateId, item: 'HTTP 状态',
      detail: `baseline=${a.httpStatus} / candidate=${b.httpStatus}` });
  }
  let valid = true;
  for (const [side, entry] of [['baseline', a], ['candidate', b]]) {
    if (entry.status === 'error') {
      add({ layer: 'L0', severity: 'block', state: stateId, item: `${side} 采集失败`, invalidates: true,
        detail: `${entry.error}${entry.url ? `（停留在 ${entry.url}）` : ''} — 本状态证据作废` });
      valid = false;
      continue;
    }
    if (entry.httpStatus !== null && entry.httpStatus !== undefined && Number(entry.httpStatus) >= 400) {
      add({ layer: 'L0', severity: 'block', state: stateId, item: `${side} HTTP ${entry.httpStatus}`, invalidates: true,
        detail: `${entry.url || '未知 URL'} — 服务端错误页不能作为一致性证据` });
      valid = false;
      continue;
    }
    // Second line of defence: capture already refuses to snapshot a login page, but an
    // older run or a hand-relaxed assertLanded must not silently become a parity verdict.
    const landed = landingVerdict(meta(entry.dir).url || entry.url, ASSERT_LANDED);
    if (!landed.ok) {
      add({ layer: 'L0', severity: 'block', state: stateId, item: `${side} 落地页不是被测页面`, invalidates: true,
        detail: `${landed.reason} — 本状态证据作废，不得据此出一致性结论` });
      valid = false;
    }
    for (const w of meta(entry.dir).warnings || []) {
      add({ layer: 'L0', severity: 'info', state: stateId, item: `${side} 采集告警`, detail: w });
    }
  }
  if (!valid) return false;
  const rt = (dir) => readJson(path.join(outRoot, dir, 'runtime.json'), { console: [], network: [] });
  const ra = rt(a.dir);
  const rb = rt(b.dir);
  const errs = (r) => r.console.filter((c) => c.type !== 'warning').map((c) => nText(c.text));
  const d = setDiff(errs(ra), errs(rb));
  const ignoredErrors = d.onlyCandidate.filter((message) => patternHit(message, RUNTIME_POLICY.ignoreConsolePatterns));
  const blockingErrors = d.onlyCandidate.filter((message) => !patternHit(message, RUNTIME_POLICY.ignoreConsolePatterns));
  if (blockingErrors.length) {
    add({ layer: 'L0', severity: 'block', state: stateId, item: '新增 JS 报错',
      detail: blockingErrors.slice(0, 5).join(' ¶ ') });
  }
  if (ignoredErrors.length) {
    add({ layer: 'L0', severity: 'info', state: stateId, item: '新增 JS 报错（策略忽略）',
      detail: ignoredErrors.slice(0, 5).join(' ¶ ') });
  }
  if (d.onlyBaseline.length) {
    add({ layer: 'L0', severity: 'info', state: stateId, item: '旧版存在、新版消失的报错',
      detail: d.onlyBaseline.slice(0, 3).join(' ¶ ') });
  }
  const netKey = (n, side) => `${n.status} ${nUrl(n.url, side).replace(/^https?:\/\/[^/]+/, '')}`;
  const nd = setDiff(ra.network.map((n) => netKey(n, 'baseline')), rb.network.map((n) => netKey(n, 'candidate')));
  if (nd.onlyCandidate.length) {
    for (const key of nd.onlyCandidate.slice(0, 8)) {
      const entry = rb.network.find((n) => netKey(n, 'candidate') === key) || { url: key };
      const severity = networkSeverity(entry);
      add({
        layer: 'L0', severity, state: stateId,
        item: severity === 'info' ? '新增失败请求（策略忽略）' : '新增失败请求',
        detail: `${key}${entry.resourceType ? `；resourceType=${entry.resourceType}` : ''}${entry.frameUrl ? `；frame=${nUrl(entry.frameUrl, 'candidate')}` : ''}`,
      });
    }
  }
  return true;
}

// ---------- L2: semantic structure ----------
function compareDom(stateId, a, b) {
  const da = readJson(path.join(outRoot, a.dir, 'dom.json'));
  const db = readJson(path.join(outRoot, b.dir, 'dom.json'));
  if (!da || !db) return { da, db };

  // Content inside an iframe we could not read is *unknown*, not missing. Reporting it as
  // missing was the single biggest source of false positives on hosted legacy shells.
  const blind = [...unreadableFrames(da), ...unreadableFrames(db)];
  const blindNote = blind.length
    ? `；⚠️ 存在 ${blind.length} 个无法读取的 iframe（${blind.map((f) => f.url).slice(0, 2).join('、')}），缺失项可能只是读不到，请人工核对截图`
    : '';
  /** Downgrade a "missing" verdict when part of the page was unreadable. */
  const blindSev = (sev) => (blind.length ? (sev === 'block' ? 'major' : 'info') : sev);
  if (blind.length) {
    add({ layer: 'L2', severity: 'info', state: stateId, item: 'iframe 不可读',
      detail: blind.map((f) => `${f.url} — ${f.error || 'evaluate 失败'}`).slice(0, 4).join(' ¶ ') });
  }

  if (nText(da.title) !== nText(db.title)) {
    add({ layer: 'L2', severity: 'minor', state: stateId, item: '页面标题',
      detail: `${da.title} → ${db.title}` });
  }

  const headings = (d) => (d.headings || []).map((h) => `${h.source || 'surface'}|${h.tag}:${nText(h.text)}`);
  const hd = setDiff(headings(da), headings(db));
  if (hd.onlyBaseline.length || hd.onlyCandidate.length) {
    add({ layer: 'L2', severity: 'major', state: stateId, item: '标题结构',
      detail: `缺失 ${JSON.stringify(hd.onlyBaseline.slice(0, 6))} / 新增 ${JSON.stringify(hd.onlyCandidate.slice(0, 6))}` });
  }

  const actions = (d) => (d.actions || []).map((x) => `${x.source || 'surface'}|${nText(x.text)}${x.disabled ? '(禁用)' : ''}`);
  const ad = setDiff(actions(da), actions(db));
  if (ad.onlyBaseline.length) {
    add({ layer: 'L2', severity: blindSev('block'), state: stateId, item: '缺失的可操作按钮',
      detail: ad.onlyBaseline.slice(0, 10).join(' / ') + blindNote });
  }
  if (ad.onlyCandidate.length) {
    add({ layer: 'L2', severity: 'minor', state: stateId, item: '新增的按钮',
      detail: ad.onlyCandidate.slice(0, 10).join(' / ') });
  }

  const fields = (d) => (d.fields || []).map((f) =>
    `${f.source || 'surface'}|${f.tag}${f.type ? '[' + f.type + ']' : ''} name=${f.name} label=${nText(f.label)} ph=${nText(f.placeholder)}${f.required ? ' *' : ''}${f.disabled ? ' disabled' : ''}`);
  const fd = setDiff(fields(da), fields(db));
  if (fd.onlyBaseline.length) {
    add({ layer: 'L2', severity: blindSev('block'), state: stateId, item: '缺失的表单字段',
      detail: fd.onlyBaseline.slice(0, 10).join(' ¶ ') + blindNote });
  }
  if (fd.onlyCandidate.length) {
    add({ layer: 'L2', severity: 'minor', state: stateId, item: '新增/变更的表单字段',
      detail: fd.onlyCandidate.slice(0, 10).join(' ¶ ') });
  }

  const ga = da.grids || [];
  const gb = db.grids || [];
  if (ga.length !== gb.length) {
    add({ layer: 'L2', severity: 'major', state: stateId, item: '表格数量',
      detail: `baseline=${ga.length} / candidate=${gb.length}` });
  }
  for (let i = 0; i < Math.min(ga.length, gb.length); i++) {
    const cd = setDiff(ga[i].columns.map(nText), gb[i].columns.map(nText));
    if (cd.onlyBaseline.length || cd.onlyCandidate.length) {
      add({ layer: 'L2', severity: 'block', state: stateId, item: `表格#${i + 1} 列定义`,
        detail: `缺失 ${JSON.stringify(cd.onlyBaseline)} / 新增 ${JSON.stringify(cd.onlyCandidate)}` });
    }
    if (ga[i].rowCount !== gb[i].rowCount) {
      add({ layer: 'L2', severity: dataSev('major'), state: stateId, item: `表格#${i + 1} 行数`,
        detail: `baseline=${ga[i].rowCount} / candidate=${gb[i].rowCount}` });
    }
  }

  const links = (d, side, dependent) => (d.links || [])
    .filter((l) => !!l.dataDependent === dependent)
    .map((l) => `${l.source || 'surface'}|${nText(l.text)} → ${nUrl(l.href, side)}`);
  for (const dependent of [false, true]) {
    const ld = setDiff(links(da, 'baseline', dependent), links(db, 'candidate', dependent));
    if (ld.onlyBaseline.length) {
      add({
        layer: 'L2', severity: blindSev(dependent ? dataSev('major') : 'major'), state: stateId,
        item: dependent ? '缺失的数据区链接' : '缺失的固定链接',
        detail: ld.onlyBaseline.slice(0, 8).join(' ¶ ') + blindNote,
      });
    }
  }

  const textItems = (d, dependent) => d.textItems
    ? d.textItems.filter((x) => !!x.dataDependent === dependent).map((x) => `${x.source || 'surface'}|${nText(x.text)}`)
    : (dependent ? (d.textOutline || []).map(nText) : []);
  for (const dependent of [false, true]) {
    const td = setDiff(textItems(da, dependent), textItems(db, dependent));
    if (td.onlyBaseline.length || td.onlyCandidate.length) {
      add({
        layer: 'L2', severity: blindSev(dependent ? dataSev('minor') : 'minor'), state: stateId,
        item: dependent ? '数据区可见文案差异' : '固定可见文案差异',
        detail: `仅旧版 ${td.onlyBaseline.length} 条 / 仅新版 ${td.onlyCandidate.length} 条；示例 旧「${td.onlyBaseline.slice(0, 3).join('｜')}」新「${td.onlyCandidate.slice(0, 3).join('｜')}」${blindNote}`,
      });
    }
  }

  const brokenImgs = (db.images || []).filter((i) => i.natural?.[0] === 0);
  if (brokenImgs.length) {
    add({ layer: 'L2', severity: 'major', state: stateId, item: '新版图片加载失败',
      detail: brokenImgs.slice(0, 5).map((i) => i.src).join(' ¶ ') });
  }
  return { da, db };
}

// ---------- L3 + L4: layout geometry and computed style ----------
function compareStyles(stateId, a, b, doms) {
  const sa = readJson(path.join(outRoot, a.dir, 'styles.json'));
  const sb = readJson(path.join(outRoot, b.dir, 'styles.json'));
  if (!sa || !sb) return;
  const drift = [];

  for (const id of Object.keys(sa)) {
    const pa = sa[id];
    const pb = sb[id];
    if (!pb) continue;
    if (pa.found && !pb.found) {
      add({ layer: 'L3', severity: 'major', state: stateId, item: `探针 ${id} 在新版不可见`,
        detail: `selector=${pa.selector}` });
      continue;
    }
    if (!pa.found || !pb.found) continue;

    for (const dim of ['w', 'h']) {
      const va = pa.box[dim];
      const vb = pb.box[dim];
      const delta = Math.abs(va - vb);
      if (delta > LAYOUT_TOL && delta / Math.max(va, 1) > SIZE_TOL_RATIO) {
        add({ layer: 'L3', severity: 'minor', state: stateId, item: `探针 ${id} 尺寸(${dim})`,
          detail: `${va}px → ${vb}px (Δ${vb - va})` });
      }
    }

    const changed = [];
    for (const prop of Object.keys(pa.style || {})) {
      const va = pa.style[prop];
      const vb = pb.style?.[prop];
      if (vb !== undefined && va !== vb) changed.push(`${prop}: ${va} → ${vb}`);
    }
    if (changed.length) drift.push({ probe: id, changes: changed });
  }

  // One theme/token change touching every probe is one regression, not a dozen.
  const { global, perProbe } = aggregateStyleDrift(drift, STYLE_AGGREGATE_MIN);
  const sevFor = (changes) => {
    if (STYLE_INTENT === 'redesign-allowed') return 'info';
    const hitsHighImpact = changes.some((c) => HIGH_IMPACT_PROPS.includes(c.split(':')[0]));
    return (changes.length > 6 || hitsHighImpact) ? 'major' : 'minor';
  };
  for (const g of global) {
    add({ layer: 'L4', severity: sevFor([g.sample]), state: stateId,
      item: `全局样式漂移 ${g.prop}（命中 ${g.probes.length} 个探针）`,
      detail: `${g.sample}；探针：${g.probes.slice(0, 8).join('、')}${g.probes.length > 8 ? ' …' : ''} — 属于主题/令牌级改动，修一处即可` });
  }
  for (const p of perProbe) {
    add({ layer: 'L4', severity: sevFor(p.changes), state: stateId,
      item: `探针 ${p.probe} 计算样式(${p.changes.length} 项)`, detail: p.changes.slice(0, 10).join('; ') });
  }

  const ha = doms.da?.documentHeight;
  const hb = doms.db?.documentHeight;
  if (ha && hb && Math.abs(ha - hb) / ha > 0.05) {
    add({ layer: 'L3', severity: dataSev('minor'), state: stateId, item: '页面总高度',
      detail: `${ha}px → ${hb}px` });
  }
}

// ---------- L1: functional journeys ----------
function compareJourneys() {
  const byId = (log) => Object.fromEntries((log.journeys || []).map((j) => [j.id, j]));
  const ja = byId(baseLog);
  const jb = byId(candLog);
  for (const id of Object.keys(ja)) {
    const a = ja[id];
    const b = jb[id];
    if (!b) {
      add({ layer: 'L1', severity: 'block', state: `journey:${id}`, item: '新版未执行该流程', detail: '缺少候选侧记录' });
      continue;
    }
    let invalid = false;
    for (const [side, entry] of [['baseline', a], ['candidate', b]]) {
      if (entry.invalid) {
        add({ layer: 'L1', severity: 'block', state: `journey:${id}`, item: `${side} 流程无法开始`,
          invalidates: true, detail: `${entry.invalid} — 本流程证据作废` });
        invalid = true;
      }
      for (const w of entry.warnings || []) {
        add({ layer: 'L1', severity: 'info', state: `journey:${id}`, item: `${side} 流程告警`, detail: w });
      }
    }
    if (invalid) continue;
    const steps = journeyById[id]?.steps || [];
    const n = Math.max(a.steps.length, b.steps.length);
    for (let i = 0; i < n; i++) {
      const x = a.steps[i];
      const y = b.steps[i];
      if (!x || !y) {
        add({ layer: 'L1', severity: 'block', state: `journey:${id}`, item: `步骤 #${i} 执行长度不一致`,
          detail: `baseline=${a.steps.length} 步 / candidate=${b.steps.length} 步（新版在「${(y || x)?.type} ${(y || x)?.id}」处中断）` });
        break;
      }
      if (x.status !== y.status) {
        add({ layer: 'L1', severity: 'block', state: `journey:${id}`, item: `步骤 #${i} ${x.type} ${x.id || ''}`,
          detail: `baseline=${x.status} / candidate=${y.status}${y.error ? ' — ' + y.error : ''}` });
        continue;
      }
      if (x.status === 'fail' && y.status === 'fail') {
        add({
          layer: 'L1', severity: 'block', state: `journey:${id}`, item: `步骤 #${i} 两侧均失败`, invalidates: true,
          detail: `baseline=${x.error || 'fail'} / candidate=${y.error || 'fail'} — 流程没有被验证，优先检查 selector/scope 配置`,
        });
        break;
      }
      if (x.observed !== undefined || y.observed !== undefined) {
        const va = typeof x.observed === 'string' ? nText(x.observed) : x.observed;
        const vb = typeof y.observed === 'string' ? nText(y.observed) : y.observed;
        const mode = steps[i]?.ignorePath ? 'query' : 'full';
        const urlObservation = ['expectUrl', 'clickAndExpectPopup', 'expectPopup'].includes(x.type);
        const cmpA = urlObservation ? nUrl(String(va), 'baseline', mode) : va;
        const cmpB = urlObservation ? nUrl(String(vb), 'candidate', mode) : vb;
        if (JSON.stringify(cmpA) !== JSON.stringify(cmpB)) {
          const detail = urlObservation
            ? `baseline=${JSON.stringify(cmpA)} / candidate=${JSON.stringify(cmpB)}（已按 pathOverrides/urlNormalizeRules 归一化；仍不同说明是未声明的跳转差异，若是有意迁移请在配置里声明）`
            : `baseline=${JSON.stringify(cmpA)} / candidate=${JSON.stringify(cmpB)}`
              + (x.type === 'expectCount' && x.visibleOnly !== false
                ? `（只计可见节点；含隐藏节点 baseline=${x.observedTotal} / candidate=${y.observedTotal}）` : '');
          const dataDependent = steps[i]?.dataDependent ?? (x.type === 'expectCount');
          add({ layer: 'L1', severity: urlObservation ? 'block' : (dataDependent ? dataSev('major') : 'major'),
            state: `journey:${id}`, item: `步骤 #${i} ${x.type} ${x.id || ''} 观测值`, detail });
        }
      }
    }
    const finalA = nUrl(a.finalUrl, 'baseline');
    const finalB = nUrl(b.finalUrl, 'candidate');
    if (finalA !== finalB) {
      add({ layer: 'L1', severity: 'major', state: `journey:${id}`, item: '流程结束 URL',
        detail: `${finalA} → ${finalB}` });
    }
    for (const [side, entry] of [['baseline', a], ['candidate', b]]) {
      const landed = landingVerdict(entry.finalUrl, ASSERT_LANDED);
      if (!landed.ok) {
        add({ layer: 'L1', severity: 'block', state: `journey:${id}`, item: `${side} 流程结束在登录/跳转页`,
          invalidates: true, detail: `${landed.reason} — 本流程结论作废` });
      }
    }
    const newErrs = setDiff(a.console.map((c) => nText(c.text)), b.console.map((c) => nText(c.text))).onlyCandidate;
    if (newErrs.length) {
      add({ layer: 'L1', severity: 'major', state: `journey:${id}`, item: '流程中新增控制台报错',
        detail: newErrs.slice(0, 4).join(' ¶ ') });
    }
  }
}

// ---------- run ----------
for (const [side, log] of [['baseline', baseLog], ['candidate', candLog]]) {
  for (const warning of log.configWarnings || []) {
    add({ layer: 'L0', severity: 'info', state: `side:${side}`, item: '配置告警', detail: warning });
  }
  if (log.fatal) {
    add({ layer: 'L0', severity: 'block', state: `side:${side}`, item: `${side} 整侧采集作废`,
      invalidates: true, detail: `${log.fatal} — 本次不产生任何一致性结论` });
  }
}

const baseStates = Object.fromEntries(baseLog.states.map((s) => [`${s.viewport}|${s.id}`, s]));
const candStates = Object.fromEntries(candLog.states.map((s) => [`${s.viewport}|${s.id}`, s]));
const stateKeys = contractComparable
  ? [...new Set([...Object.keys(baseStates), ...Object.keys(candStates)])].sort()
  : [];
const stateResults = [];

for (const key of stateKeys) {
  const a = baseStates[key];
  const b = candStates[key];
  if (!a || !b) {
    add({ layer: 'L0', severity: 'block', state: key, item: '单侧缺失该状态',
      invalidates: true, detail: a ? '候选侧未采集' : '基线侧未采集' });
    continue;
  }
  if (!compareRuntime(key, a, b)) {
    // Invalid evidence on either side: comparing DOM / style / pixels of a login or
    // half-loaded page only manufactures noise.
    stateResults.push({
      key, routeId: a.routeId, viewport: a.viewport, pixel: { skipped: '证据作废，未比对' },
      baselineShot: null, candidateShot: null, valid: false,
    });
    continue;
  }
  const doms = compareDom(key, a, b);
  compareStyles(key, a, b, doms);

  const shotA = path.join(outRoot, a.dir, 'shot.png');
  const shotB = path.join(outRoot, b.dir, 'shot.png');
  let pixel = { skipped: 'screenshot missing' };
  if (fs.existsSync(shotA) && fs.existsSync(shotB)) {
    pixel = await pixelDiff(shotA, shotB, path.join(outRoot, 'diff', `${key.replace(/[|/\\]/g, '__')}.png`));
    if ((pixel.skipped || pixel.error) && STYLE_INTENT === 'pixel-parity') {
      add({ layer: 'L5', severity: 'block', state: key, item: '像素证据生成失败', invalidates: true,
        detail: `${pixel.skipped || pixel.error} — 本状态不能宣称视觉一致` });
    }
    if (pixel.sizeMismatch) {
      add({ layer: 'L5', severity: 'minor', state: key, item: '截图尺寸不一致',
        detail: `baseline=${pixel.baselineSize?.join('x')} / candidate=${pixel.candidateSize?.join('x')}` });
    }
    if (pixel.ratio > PIXEL_RATIO) {
      add({ layer: 'L5', severity: pixel.ratio > PIXEL_RATIO * 10 ? 'major' : 'minor', state: key,
        item: `像素差异 ${(pixel.ratio * 100).toFixed(2)}%（阈值 ${(PIXEL_RATIO * 100).toFixed(2)}%）`,
        detail: `热点区域：${(pixel.hotspots || []).map((h) => h.region).slice(0, 3).join('；') || '分散'}`,
        image: pixel.diffImage });
    }
  } else if (STYLE_INTENT === 'pixel-parity') {
    add({ layer: 'L5', severity: 'block', state: key, item: '截图证据缺失', invalidates: true,
      detail: `${!fs.existsSync(shotA) ? 'baseline' : 'candidate'} 截图不存在 — 本状态不能宣称视觉一致` });
  }
  stateResults.push({
    key, routeId: a.routeId, viewport: a.viewport, pixel,
    valid: STYLE_INTENT !== 'pixel-parity' || !(pixel.skipped || pixel.error),
    baselineShot: path.relative(outRoot, shotA).replace(/\\/g, '/'),
    candidateShot: path.relative(outRoot, shotB).replace(/\\/g, '/'),
  });
}

if (contractComparable) compareJourneys();

findings.sort((x, y) => SEV_ORDER[x.severity] - SEV_ORDER[y.severity] || x.layer.localeCompare(y.layer));
const count = (sev) => findings.filter((f) => f.severity === sev).length;
const invalidated = findings.filter((f) => f.invalidates);
const parityFindings = findings.filter((f) => !f.invalidates);
const parityCount = (sev) => parityFindings.filter((f) => f.severity === sev).length;
const parityVerdict = parityCount('block') ? 'fail' : parityCount('major') ? 'warn' : 'pass';
const validJourneyEvidence = contractComparable && (baseLog.journeys || []).some((a) => {
  const b = (candLog.journeys || []).find((j) => j.id === a.id);
  return b && a.status === 'ok' && b.status === 'ok' && !a.invalid && !b.invalid;
});
const evidenceStatus = invalidated.length
  ? (stateResults.some((s) => s.valid) || validJourneyEvidence ? 'partial' : 'invalid')
  : 'valid';
const verdict = evidenceStatus === 'valid' ? parityVerdict : 'inconclusive';

const summary = {
  schema: 'parity-summary/v2',
  generatedAt: new Date().toISOString(),
  outputDir: outRoot,
  baseline: { baseUrl: baseLog.baseUrl, capturedAt: baseLog.capturedAt, browser: baseLog.browser },
  candidate: { baseUrl: candLog.baseUrl, capturedAt: candLog.capturedAt, browser: candLog.browser },
  context: baseLog.context,
  dataParity: DATA_PARITY,
  styleIntent: STYLE_INTENT,
  evidenceStatus,
  parityVerdict,
  contract: { configFingerprint: CURRENT_FINGERPRINT, comparable: contractComparable, issues: contractIssues },
  thresholds: { pixelDiffRatio: PIXEL_RATIO, pixelChannelTolerance: CHANNEL_TOL, layoutTolerancePx: LAYOUT_TOL },
  verdict,
  counts: { block: count('block'), major: count('major'), minor: count('minor'), info: count('info') },
  parityCounts: { block: parityCount('block'), major: parityCount('major'), minor: parityCount('minor'), info: parityCount('info') },
  invalidEvidence: invalidated.length,
  states: stateResults.map((s) => ({
    key: s.key,
    evidenceValid: !!s.valid,
    pixelRatio: s.pixel?.ratio ?? null,
    diffImage: s.pixel?.diffImage ?? null,
    baselineShot: s.baselineShot ?? null,
    candidateShot: s.candidateShot ?? null,
  })),
  findings,
};
writeJson(path.join(outRoot, 'parity-summary.json'), summary);

// ---------- report ----------
const LAYER_NAME = {
  L0: 'L0 可达性与运行时错误',
  L1: 'L1 功能行为（用户流程）',
  L2: 'L2 语义结构与内容',
  L3: 'L3 布局几何',
  L4: 'L4 计算样式',
  L5: 'L5 像素外观',
};
const SEV_LABEL = { block: '🔴 阻断', major: '🟠 重要', minor: '🟡 次要', info: '⚪ 参考' };
const cell = (s) => String(s).replace(/\|/g, '\\|');
const md = [];
md.push('# 前端一致性比对报告', '');
const verdictLabel = {
  pass: '✅ 通过', warn: '⚠️ 有重要差异', fail: '❌ 不一致（存在阻断项）',
  inconclusive: `⛔ 证据${evidenceStatus === 'partial' ? '不完整' : '无效'}；有效证据范围内${{ pass: '通过', warn: '有重要差异', fail: '不一致' }[parityVerdict]}`,
};
md.push(`- 结论：**${verdictLabel[verdict]}**`);
md.push(`- 证据状态：\`evidenceStatus=${evidenceStatus}\`；有效证据对等结论：\`parityVerdict=${parityVerdict}\``);
md.push(`- 基线（升级前）：${baseLog.baseUrl}`);
md.push(`- 候选（升级后）：${candLog.baseUrl}`);
md.push(`- 采集环境：${baseLog.browser}｜视口 ${(baseLog.context.viewports || []).map((v) => `${v.name} ${v.width}x${v.height}`).join('、')}｜locale ${baseLog.context.locale || 'zh-CN'}｜timezone ${baseLog.context.timezoneId || 'Asia/Shanghai'}`);
md.push(`- 数据前提：\`dataParity=${DATA_PARITY}\`${DATA_PARITY === 'different-data' ? '（两侧数据源可能不同，数据类差异已降级为参考项，不能据此断言「数据一致」）' : ''}`);
md.push(`- 样式口径：\`styleIntent=${STYLE_INTENT}\`${STYLE_INTENT === 'redesign-allowed' ? '（允许改版，计算样式差异仅作参考，不构成失败）' : '（要求视觉对齐，字体/颜色/字号等高影响属性变化按重要项处理）'}`);
md.push(`- 配置指纹：\`${CURRENT_FINGERPRINT.slice(0, 12)}\`｜比较面：\`${JSON.stringify(cfg.compareSurface || { mode: 'full-page' })}\``);
md.push(`- 覆盖：routes=${(cfg.routes || []).map((r) => r.id).join('、') || '无'}｜journeys=${(cfg.journeys || []).map((j) => j.id).join('、') || '无'}`);
md.push(`- 生成时间：${summary.generatedAt}`, '');
if (invalidated.length) {
  md.push(`> ⛔ **有 ${invalidated.length} 处证据作废**（契约不一致 / 登录页 / 落地页错误 / 采集失败）：`,
    ...invalidated.slice(0, 6).map((f) => `> - \`${f.state}\` ${f.item}`),
    '>',
    '> 作废的状态不参与比对，其余层的"通过"不能推广到这些页面 —— 先修登录态或路径映射再重跑。', '');
}
md.push(`| 口径 | 阻断 | 重要 | 次要 | 参考 |`, `|---|---|---|---|---|`,
  `| 全部发现（含作废证据） | ${count('block')} | ${count('major')} | ${count('minor')} | ${count('info')} |`,
  `| 有效证据对等项 | ${parityCount('block')} | ${parityCount('major')} | ${parityCount('minor')} | ${parityCount('info')} |`, '');

md.push('## 分层结论', '');
md.push('| 层 | 阻断 | 重要 | 次要 |', '|---|---|---|---|');
for (const layer of Object.keys(LAYER_NAME)) {
  const f = findings.filter((x) => x.layer === layer);
  md.push(`| ${LAYER_NAME[layer]} | ${f.filter((x) => x.severity === 'block').length} | ${f.filter((x) => x.severity === 'major').length} | ${f.filter((x) => x.severity === 'minor').length} |`);
}
md.push('');

for (const layer of Object.keys(LAYER_NAME)) {
  const f = findings.filter((x) => x.layer === layer);
  if (!f.length) continue;
  md.push(`## ${LAYER_NAME[layer]}`, '');
  for (const x of f) {
    md.push(`- ${SEV_LABEL[x.severity]} \`${x.state}\` **${x.item}**：${x.detail}`);
    if (x.image) md.push(`  - 差异图：\`${x.image}\``);
  }
  md.push('');
}

md.push('## 逐状态像素差异', '', '| 状态 | 差异比例 | 差异图 | 基线截图 | 候选截图 |', '|---|---|---|---|---|');
for (const s of stateResults) {
  const r = s.pixel?.ratio;
  const ratio = r === undefined || r === null ? (s.pixel?.skipped || s.pixel?.error || 'n/a') : (r * 100).toFixed(3) + '%';
  md.push(`| \`${cell(s.key)}\` | ${cell(ratio)} | ${s.pixel?.diffImage ? '`' + s.pixel.diffImage + '`' : '—'} | \`${cell(s.baselineShot || '—')}\` | \`${cell(s.candidateShot || '—')}\` |`);
}
md.push('');
md.push('## 证据目录', '',
  '```text', `${outRoot}`, '  run-manifest.json', '  baseline/<viewport>/<state>/{shot.png,dom.json,styles.json,runtime.json,meta.json}',
  '  candidate/<viewport>/<state>/...', '  diff/<viewport>__<state>.png', '  parity-summary.json', '  parity-report.md', '```', '');
md.push('> 判定口径：`block` 必须修复；`major` 需要逐条给出「修复」或「已确认为有意变更」的结论；',
  '> `minor`/`info` 由负责人签署接受。像素层不是唯一依据——L0–L2 通过而 L5 超阈值，通常是样式漂移；',
  '> L5 通过而 L1/L2 失败，说明外观像但功能已经不同。', '');

ensureDir(outRoot);
fs.writeFileSync(path.join(outRoot, 'parity-report.md'), md.join('\n'), 'utf8');
if (browser) await browser.close();

console.log(JSON.stringify({
  verdict, evidenceStatus, parityVerdict, counts: summary.counts,
  report: path.join(outRoot, 'parity-report.md'),
  summary: path.join(outRoot, 'parity-summary.json'),
}, null, 2));
process.exit(verdict === 'pass' || verdict === 'warn' ? 0 : 1);
