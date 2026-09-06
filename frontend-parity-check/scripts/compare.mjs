#!/usr/bin/env node
// Compare a captured baseline vs candidate and emit parity-summary.json + parity-report.md.
// Usage: node compare.mjs --config parity-config.json [--out DIR]
import fs from 'node:fs';
import path from 'node:path';
import { loadPlaywright, ensureDir, writeJson, readJson, parseArgs, normalizeUrl, normalizeText } from './lib/pw.mjs';

const args = parseArgs(process.argv.slice(2));
if (!args.config) {
  console.error('usage: node compare.mjs --config <file> [--out DIR]');
  process.exit(2);
}
const configPath = path.resolve(args.config);
const cfg = readJson(configPath) || {};
const outRoot = args.out
  ? path.resolve(args.out)
  : path.resolve(path.dirname(configPath), cfg.outputDir || 'parity-run');
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
const nUrl = (s) => normalizeUrl(s, ORIGINS);
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

// ---------- L5: pixel diff, computed inside Playwright's own Chromium ----------
let browser = null;
async function getBrowser() {
  if (browser) return browser;
  const pw = await loadPlaywright(process.cwd());
  if (!pw) return null;
  browser = await pw[cfg.browser || 'chromium'].launch({ headless: true });
  return browser;
}

async function pixelDiff(aPath, bPath, outPath) {
  const b = await getBrowser();
  if (!b) return { skipped: 'playwright unavailable' };
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
  for (const [side, entry] of [['baseline', a], ['candidate', b]]) {
    if (entry.status === 'error') {
      add({ layer: 'L0', severity: 'block', state: stateId, item: `${side} 采集失败`, detail: entry.error });
    }
  }
  const rt = (dir) => readJson(path.join(outRoot, dir, 'runtime.json'), { console: [], network: [] });
  const ra = rt(a.dir);
  const rb = rt(b.dir);
  const errs = (r) => r.console.filter((c) => c.type !== 'warning').map((c) => nText(c.text));
  const d = setDiff(errs(ra), errs(rb));
  if (d.onlyCandidate.length) {
    add({ layer: 'L0', severity: 'block', state: stateId, item: '新增 JS 报错',
      detail: d.onlyCandidate.slice(0, 5).join(' ¶ ') });
  }
  if (d.onlyBaseline.length) {
    add({ layer: 'L0', severity: 'info', state: stateId, item: '旧版存在、新版消失的报错',
      detail: d.onlyBaseline.slice(0, 3).join(' ¶ ') });
  }
  const net = (r) => r.network.map((n) => `${n.status} ${nUrl(n.url).replace(/^https?:\/\/[^/]+/, '')}`);
  const nd = setDiff(net(ra), net(rb));
  if (nd.onlyCandidate.length) {
    add({ layer: 'L0', severity: 'major', state: stateId, item: '新增失败请求',
      detail: nd.onlyCandidate.slice(0, 5).join(' ¶ ') });
  }
}

// ---------- L2: semantic structure ----------
function compareDom(stateId, a, b) {
  const da = readJson(path.join(outRoot, a.dir, 'dom.json'));
  const db = readJson(path.join(outRoot, b.dir, 'dom.json'));
  if (!da || !db) return { da, db };

  if (nText(da.title) !== nText(db.title)) {
    add({ layer: 'L2', severity: 'minor', state: stateId, item: '页面标题',
      detail: `${da.title} → ${db.title}` });
  }

  const headings = (d) => (d.headings || []).map((h) => `${h.tag}:${nText(h.text)}`);
  const hd = setDiff(headings(da), headings(db));
  if (hd.onlyBaseline.length || hd.onlyCandidate.length) {
    add({ layer: 'L2', severity: 'major', state: stateId, item: '标题结构',
      detail: `缺失 ${JSON.stringify(hd.onlyBaseline.slice(0, 6))} / 新增 ${JSON.stringify(hd.onlyCandidate.slice(0, 6))}` });
  }

  const actions = (d) => (d.actions || []).map((x) => `${nText(x.text)}${x.disabled ? '(禁用)' : ''}`);
  const ad = setDiff(actions(da), actions(db));
  if (ad.onlyBaseline.length) {
    add({ layer: 'L2', severity: 'block', state: stateId, item: '缺失的可操作按钮',
      detail: ad.onlyBaseline.slice(0, 10).join(' / ') });
  }
  if (ad.onlyCandidate.length) {
    add({ layer: 'L2', severity: 'minor', state: stateId, item: '新增的按钮',
      detail: ad.onlyCandidate.slice(0, 10).join(' / ') });
  }

  const fields = (d) => (d.fields || []).map((f) =>
    `${f.tag}${f.type ? '[' + f.type + ']' : ''} name=${f.name} label=${nText(f.label)} ph=${nText(f.placeholder)}${f.required ? ' *' : ''}${f.disabled ? ' disabled' : ''}`);
  const fd = setDiff(fields(da), fields(db));
  if (fd.onlyBaseline.length) {
    add({ layer: 'L2', severity: 'block', state: stateId, item: '缺失的表单字段',
      detail: fd.onlyBaseline.slice(0, 10).join(' ¶ ') });
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

  const links = (d) => (d.links || []).map((l) => `${nText(l.text)} → ${nUrl(l.href)}`);
  const ld = setDiff(links(da), links(db));
  if (ld.onlyBaseline.length) {
    add({ layer: 'L2', severity: dataSev('major'), state: stateId, item: '缺失的链接',
      detail: ld.onlyBaseline.slice(0, 8).join(' ¶ ') });
  }

  const td = setDiff((da.textOutline || []).map(nText), (db.textOutline || []).map(nText));
  if (td.onlyBaseline.length || td.onlyCandidate.length) {
    add({ layer: 'L2', severity: dataSev('minor'), state: stateId, item: '可见文案差异',
      detail: `仅旧版 ${td.onlyBaseline.length} 条 / 仅新版 ${td.onlyCandidate.length} 条；示例 旧「${td.onlyBaseline.slice(0, 3).join('｜')}」新「${td.onlyCandidate.slice(0, 3).join('｜')}」` });
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
    if (changed.length) {
      const hitsHighImpact = changed.some((c) => HIGH_IMPACT_PROPS.includes(c.split(':')[0]));
      const severity = STYLE_INTENT === 'redesign-allowed'
        ? 'info'
        : (changed.length > 6 || hitsHighImpact) ? 'major' : 'minor';
      add({ layer: 'L4', severity, state: stateId,
        item: `探针 ${id} 计算样式(${changed.length} 项)`, detail: changed.slice(0, 10).join('; ') });
    }
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
      if (x.observed !== undefined || y.observed !== undefined) {
        const va = typeof x.observed === 'string' ? nText(x.observed) : x.observed;
        const vb = typeof y.observed === 'string' ? nText(y.observed) : y.observed;
        const cmpA = x.type === 'expectUrl' ? nUrl(String(va)) : va;
        const cmpB = y.type === 'expectUrl' ? nUrl(String(vb)) : vb;
        if (JSON.stringify(cmpA) !== JSON.stringify(cmpB)) {
          add({ layer: 'L1', severity: x.type === 'expectUrl' ? 'block' : dataSev('major'),
            state: `journey:${id}`, item: `步骤 #${i} ${x.type} ${x.id || ''} 观测值`,
            detail: `baseline=${JSON.stringify(cmpA)} / candidate=${JSON.stringify(cmpB)}` });
        }
      }
    }
    if (nUrl(a.finalUrl) !== nUrl(b.finalUrl)) {
      add({ layer: 'L1', severity: 'major', state: `journey:${id}`, item: '流程结束 URL',
        detail: `${nUrl(a.finalUrl)} → ${nUrl(b.finalUrl)}` });
    }
    const newErrs = setDiff(a.console.map((c) => nText(c.text)), b.console.map((c) => nText(c.text))).onlyCandidate;
    if (newErrs.length) {
      add({ layer: 'L1', severity: 'major', state: `journey:${id}`, item: '流程中新增控制台报错',
        detail: newErrs.slice(0, 4).join(' ¶ ') });
    }
  }
}

// ---------- run ----------
const baseStates = Object.fromEntries(baseLog.states.map((s) => [`${s.viewport}|${s.id}`, s]));
const candStates = Object.fromEntries(candLog.states.map((s) => [`${s.viewport}|${s.id}`, s]));
const stateKeys = [...new Set([...Object.keys(baseStates), ...Object.keys(candStates)])].sort();
const stateResults = [];

for (const key of stateKeys) {
  const a = baseStates[key];
  const b = candStates[key];
  if (!a || !b) {
    add({ layer: 'L0', severity: 'block', state: key, item: '单侧缺失该状态',
      detail: a ? '候选侧未采集' : '基线侧未采集' });
    continue;
  }
  compareRuntime(key, a, b);
  const doms = compareDom(key, a, b);
  compareStyles(key, a, b, doms);

  const shotA = path.join(outRoot, a.dir, 'shot.png');
  const shotB = path.join(outRoot, b.dir, 'shot.png');
  let pixel = { skipped: 'screenshot missing' };
  if (fs.existsSync(shotA) && fs.existsSync(shotB)) {
    pixel = await pixelDiff(shotA, shotB, path.join(outRoot, 'diff', `${key.replace(/[|/\\]/g, '__')}.png`));
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
  }
  stateResults.push({
    key, routeId: a.routeId, viewport: a.viewport, pixel,
    baselineShot: path.relative(outRoot, shotA).replace(/\\/g, '/'),
    candidateShot: path.relative(outRoot, shotB).replace(/\\/g, '/'),
  });
}

compareJourneys();

findings.sort((x, y) => SEV_ORDER[x.severity] - SEV_ORDER[y.severity] || x.layer.localeCompare(y.layer));
const count = (sev) => findings.filter((f) => f.severity === sev).length;
const verdict = count('block') ? 'fail' : count('major') ? 'warn' : 'pass';

const summary = {
  schema: 'parity-summary/v1',
  generatedAt: new Date().toISOString(),
  outputDir: outRoot,
  baseline: { baseUrl: baseLog.baseUrl, capturedAt: baseLog.capturedAt, browser: baseLog.browser },
  candidate: { baseUrl: candLog.baseUrl, capturedAt: candLog.capturedAt, browser: candLog.browser },
  context: baseLog.context,
  dataParity: DATA_PARITY,
  styleIntent: STYLE_INTENT,
  thresholds: { pixelDiffRatio: PIXEL_RATIO, pixelChannelTolerance: CHANNEL_TOL, layoutTolerancePx: LAYOUT_TOL },
  verdict,
  counts: { block: count('block'), major: count('major'), minor: count('minor'), info: count('info') },
  states: stateResults.map((s) => ({
    key: s.key,
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
md.push(`- 结论：**${{ pass: '✅ 通过', warn: '⚠️ 有重要差异', fail: '❌ 不一致（存在阻断项）' }[verdict]}**`);
md.push(`- 基线（升级前）：${baseLog.baseUrl}`);
md.push(`- 候选（升级后）：${candLog.baseUrl}`);
md.push(`- 采集环境：${baseLog.browser}｜视口 ${(baseLog.context.viewports || []).map((v) => `${v.name} ${v.width}x${v.height}`).join('、')}｜locale ${baseLog.context.locale || 'zh-CN'}｜timezone ${baseLog.context.timezoneId || 'Asia/Shanghai'}`);
md.push(`- 数据前提：\`dataParity=${DATA_PARITY}\`${DATA_PARITY === 'different-data' ? '（两侧数据源可能不同，数据类差异已降级为参考项，不能据此断言「数据一致」）' : ''}`);
md.push(`- 样式口径：\`styleIntent=${STYLE_INTENT}\`${STYLE_INTENT === 'redesign-allowed' ? '（允许改版，计算样式差异仅作参考，不构成失败）' : '（要求视觉对齐，字体/颜色/字号等高影响属性变化按重要项处理）'}`);
md.push(`- 生成时间：${summary.generatedAt}`, '');
md.push(`| 阻断 | 重要 | 次要 | 参考 |`, `|---|---|---|---|`,
  `| ${count('block')} | ${count('major')} | ${count('minor')} | ${count('info')} |`, '');

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
  '```text', `${outRoot}`, '  baseline/<viewport>/<state>/{shot.png,dom.json,styles.json,runtime.json,meta.json}',
  '  candidate/<viewport>/<state>/...', '  diff/<viewport>__<state>.png', '  parity-summary.json', '  parity-report.md', '```', '');
md.push('> 判定口径：`block` 必须修复；`major` 需要逐条给出「修复」或「已确认为有意变更」的结论；',
  '> `minor`/`info` 由负责人签署接受。像素层不是唯一依据——L0–L2 通过而 L5 超阈值，通常是样式漂移；',
  '> L5 通过而 L1/L2 失败，说明外观像但功能已经不同。', '');

ensureDir(outRoot);
fs.writeFileSync(path.join(outRoot, 'parity-report.md'), md.join('\n'), 'utf8');
if (browser) await browser.close();

console.log(JSON.stringify({
  verdict, counts: summary.counts,
  report: path.join(outRoot, 'parity-report.md'),
  summary: path.join(outRoot, 'parity-summary.json'),
}, null, 2));
process.exit(verdict === 'fail' ? 1 : 0);
