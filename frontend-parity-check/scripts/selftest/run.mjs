#!/usr/bin/env node
// End-to-end smoke test: serves two diverging pages, runs the full pipeline,
// and asserts that every planted regression was detected.
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import { readJson } from '../lib/pw.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const config = path.join(here, 'config.json');
const outDir = path.join(here, 'parity-run');
fs.rmSync(outDir, { recursive: true, force: true });

// The fixture must live in its own process: spawnSync below blocks this event loop.
const fixture = spawn(process.execPath, [path.join(here, 'fixture.mjs')], { stdio: 'inherit' });
const reachable = async () => {
  for (let i = 0; i < 40; i++) {
    try {
      const [a, b] = await Promise.all([fetch('http://127.0.0.1:9401'), fetch('http://127.0.0.1:9402')]);
      if (a.ok && b.ok) return true;
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 250));
  }
  return false;
};
if (!(await reachable())) {
  fixture.kill();
  console.error('FAIL: fixture did not start on 127.0.0.1:9401/9402 (ports in use?)');
  process.exit(1);
}

const run = (script, extra) => spawnSync(process.execPath,
  [path.join(here, '..', script), '--config', config, ...extra],
  { stdio: ['ignore', 'pipe', 'inherit'], encoding: 'utf8' });

const unit = spawnSync(process.execPath, [path.join(here, 'unit.mjs')], { stdio: 'inherit' });

try {
  for (const side of ['baseline', 'candidate']) {
    const r = run('capture.mjs', ['--side', side, '--keepGoing']);
    if (r.status !== 0) throw new Error(`capture ${side} exited ${r.status}`);
  }
  run('compare.mjs', []);
} finally {
  fixture.kill();
}

const summary = readJson(path.join(outDir, 'parity-summary.json'));
if (!summary) {
  console.error('FAIL: no parity-summary.json produced');
  process.exit(1);
}

const text = JSON.stringify(summary.findings);
const expected = [
  ['缺失的可操作按钮 (导出)', /缺失的可操作按钮[\s\S]{0,40}导出/],
  ['缺失的表单字段 (status)', /缺失的表单字段[\s\S]{0,60}status/],
  ['表格列改名', /表格#1 列定义/],
  ['详情流程中断', /journey:search-open-detail[\s\S]{0,200}(fail|中断|长度不一致)/],
  ['新增控制台报错', /新增控制台报错|新增 JS 报错/],
  ['主题色 / 圆角漂移', /background-color: rgb\(64, 158, 255\)/],
  ['字号漂移', /font-size: 14px → 13px/],
  ['像素差异超阈值', /像素差异/],
  ['落地在登录页即作废', /采集失败[\s\S]{0,240}禁止模式/],
  ['waitFor 未命中即作废', /采集失败[\s\S]{0,240}waitFor 未命中/],
  ['iframe 顶栏里缺失的链接被发现', /缺失的链接[\s\S]{0,160}帮助/],
];

// Regressions this skill must NOT report — the three false positives from the field run.
const forbidden = [
  ['隐藏 ng-hide 节点不再制造计数误报', /notices 观测值/],
  ['已声明的路径迁移不再误判 expectUrl', /shell-url 观测值/],
  ['已声明的路径迁移不再误判流程结束 URL', /journey:dashboard-notices","item":"流程结束 URL/],
];

let failed = 0;
if (unit.status !== 0) {
  failed++;
  console.log('FAIL  unit.mjs（判定规则单测）');
}
for (const [label, re] of expected) {
  const ok = re.test(text);
  if (!ok) failed++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}`);
}
for (const [label, re] of forbidden) {
  const ok = !re.test(text);
  if (!ok) failed++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}（不应出现）`);
}
console.log(`\nverdict=${summary.verdict} counts=${JSON.stringify(summary.counts)}`);
if (summary.verdict !== 'fail') {
  console.log('FAIL  verdict should be "fail" for this fixture');
  failed++;
}
console.log(failed ? `\n${failed} check(s) failed` : '\nself-test OK');
process.exit(failed ? 1 : 0);
