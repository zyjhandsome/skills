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

const run = (script, extra, configFile = config, captureStderr = false) => spawnSync(process.execPath,
  [path.join(here, '..', script), '--config', configFile, ...extra],
  { stdio: ['ignore', 'pipe', captureStderr ? 'pipe' : 'inherit'], encoding: 'utf8' });

const unit = spawnSync(process.execPath, [path.join(here, 'unit.mjs')], { stdio: 'inherit' });

try {
  // Auth gate behavior: a login page opens the interactive browser; a broken readiness anchor does not.
  const authCase = (name, routePath, selector, extraInteractive = {}) => {
    const file = path.join(outDir, `${name}.json`);
    fs.mkdirSync(outDir, { recursive: true });
    fs.writeFileSync(file, JSON.stringify({
      name,
      baseline: {
        baseUrl: 'http://127.0.0.1:9401',
        auth: {
          mode: 'auto-interactive',
          storageState: `./${name}-state.json`,
          interactive: {
            timeoutMs: 600, probeTimeoutMs: 600, readinessTimeoutMs: 150,
            profileDir: `./${name}-profile`,
            ...extraInteractive,
          },
        },
      },
      routes: [{ id: name, path: routePath, waitFor: { selector } }],
    }, null, 2));
    return file;
  };
  const loginCase = run('prepare-auth.mjs', ['--side', 'baseline', '--headless-interactive'],
    authCase('auth-login-detection', '/gate', '.wrap'), true);
  if (loginCase.status !== 4 || !loginCase.stderr.includes('正在打开登录窗口')) {
    throw new Error('prepare-auth did not open interactive mode for a detected login page');
  }
  const unreadyCase = run('prepare-auth.mjs', ['--side', 'baseline', '--headless-interactive'],
    authCase('auth-unready-opens', '/', '.definitely-missing'), true);
  if (unreadyCase.status !== 4 || !unreadyCase.stderr.includes('正在打开登录窗口')) {
    throw new Error('prepare-auth did not open a login window when the page was unready');
  }
  const refuseCase = run('prepare-auth.mjs', ['--side', 'baseline', '--headless-interactive'],
    authCase('auth-broken-page', '/', '.definitely-missing', { openOnUnready: false }), true);
  if (refuseCase.status !== 4 || !refuseCase.stderr.includes('未识别出登录页')
    || refuseCase.stderr.includes('正在打开登录窗口')) {
    throw new Error('prepare-auth ignored explicit openOnUnready=false');
  }
  const flashCase = run('prepare-auth.mjs', ['--side', 'baseline', '--headless-interactive'],
    authCase('auth-flash-shell', '/flash-shell', '.cus-item-title', {
      probeTimeoutMs: 4000, readyHoldMs: 1200, timeoutMs: 1500,
    }), true);
  if (flashCase.status === 0 || flashCase.stdout.includes('"status": "ready"')) {
    throw new Error('prepare-auth treated a pre-login shell flash as ready');
  }
  if (!flashCase.stderr.includes('壳节点')) {
    throw new Error('prepare-auth did not warn that .cus-item-title is a pre-login shell');
  }
  const forceStillProbes = run('prepare-auth.mjs',
    ['--side', 'baseline', '--force-interactive', '--headless-interactive'],
    authCase('auth-force-still-probes', '/', '.wrap'), true);
  if (forceStillProbes.status !== 0 || !forceStillProbes.stdout.includes('"mode": "headless-probe"')) {
    throw new Error('--force-interactive skipped the headless probe on a public page');
  }
  if (forceStillProbes.stderr.includes('正在打开登录窗口')) {
    throw new Error('--force-interactive opened a window even though the probe succeeded');
  }
  console.log('PASS  未就绪默认开登录窗；显式 openOnUnready=false 才拒绝');
  console.log('PASS  登录前壳节点闪现不落盘；--force-interactive 仍先探测');

  for (const side of ['baseline', 'candidate']) {
    // Baseline uses --skip-probe to exercise the persistent-context branch; candidate covers the clean probe.
    const authArgs = side === 'baseline'
      ? ['--side', side, '--skip-probe', '--headless-interactive']
      : ['--side', side];
    const auth = run('prepare-auth.mjs', authArgs);
    if (auth.status !== 0) throw new Error(`prepare-auth ${side} exited ${auth.status}`);
    const expectedMode = side === 'baseline' ? 'interactive' : 'headless-probe';
    if (!auth.stdout.includes(`\"mode\": \"${expectedMode}\"`)) {
      throw new Error(`prepare-auth ${side} did not exercise ${expectedMode}`);
    }
    const r = run('capture.mjs', ['--side', side, '--keepGoing']);
    if (r.status !== 0) throw new Error(`capture ${side} exited ${r.status}`);
  }
  const reuse = run('prepare-auth.mjs',
    ['--side', 'baseline', '--force-interactive', '--headless-interactive'],
    config, true);
  if (reuse.status !== 0 || !reuse.stdout.includes('"mode": "headless-probe"')
    || !reuse.stdout.includes('"reused": true')) {
    throw new Error('--force-interactive did not reuse a valid storageState');
  }
  if (reuse.stderr.includes('正在打开登录窗口')) {
    throw new Error('--force-interactive reopened a login window despite a valid session');
  }
  console.log('PASS  已有会话时 --force-interactive 复用，不再开窗');
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
  ['iframe 顶栏里缺失的链接被发现', /缺失的固定链接[\s\S]{0,160}帮助/],
];

// Regressions this skill must NOT report — the three false positives from the field run.
const forbidden = [
  ['隐藏 ng-hide 节点不再制造计数误报', /notices 观测值/],
  ['已声明的路径迁移不再误判 expectUrl', /shell-url 观测值/],
  ['已声明的路径迁移不再误判流程结束 URL', /journey:dashboard-notices","item":"流程结束 URL/],
  ['iframe + popup 主链路不应失败', /journey:frame-popup-report[\s\S]{0,160}(步骤|流程).*(fail|失败|中断)/],
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
if (summary.verdict !== 'inconclusive' || summary.parityVerdict !== 'fail' || summary.evidenceStatus !== 'partial') {
  console.log('FAIL  invalid states should yield inconclusive + partial evidence, while valid evidence still fails parity');
  failed++;
}
console.log(failed ? `\n${failed} check(s) failed` : '\nself-test OK');
process.exit(failed ? 1 : 0);
