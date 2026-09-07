#!/usr/bin/env node
// Unit tests for the decision rules that turn "captured something" into
// "captured the right thing". No browser, no network — runs in well under a second.
import {
  landingVerdict, buildPathTokens, normalizeRouteUrl, resolveProbes,
  aggregateStyleDrift, unreadableFrames, mergeDomDigests, DEFAULT_FORBID_URL,
  resolveSurface, configValidationErrors,
} from '../lib/parity-core.mjs';
import { DEFAULT_PROBES } from '../lib/probes.mjs';

let failed = 0;
const check = (label, cond, extra = '') => {
  if (!cond) failed++;
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${label}${cond || !extra ? '' : ` — ${extra}`}`);
};
const eq = (label, actual, expected) =>
  check(label, JSON.stringify(actual) === JSON.stringify(expected), `got ${JSON.stringify(actual)}, want ${JSON.stringify(expected)}`);

// ---- 登录 / 跳转页识别 ----------------------------------------------------
check('SSO 域名判为无效落地', !landingVerdict('https://login-beta.huawei.com/login/authorize?service=x').ok);
check('/login 路径判为无效落地', !landingVerdict('https://app.corp.com/login?redirect=%2Fdashboard').ok);
check('redirect_uri 判为无效落地', !landingVerdict('https://app.corp.com/portal?redirect_uri=https%3A%2F%2Fsso').ok);
check('业务页不误判', landingVerdict('https://app.corp.com/hiapm/project/dashboard.do?id=7').ok);
check('含 login 字样的业务路径不误判', landingVerdict('https://app.corp.com/hiapm/login-history.do').ok);
check('allowUrl 可放行（被测页本身就是登录页）',
  landingVerdict('https://app.corp.com/login', { allowUrl: ['/login'] }).ok);
check('allowUrl 不能绕过 requireUrl',
  !landingVerdict('https://app.corp.com/login', { allowUrl: ['/login'], requireUrl: '/target-login' }).ok);
check('forbidUrl 置空即关闭该校验', landingVerdict('https://login-beta.huawei.com/', { forbidUrl: [] }).ok);
check('requireUrl 不匹配也算无效',
  !landingVerdict('https://app.corp.com/other', { requireUrl: '/dashboard' }).ok);
check('默认禁止模式全部可编译', DEFAULT_FORBID_URL.every((p) => { try { new RegExp(p); return true; } catch { return false; } }));

// ---- pathOverrides 归一化 ------------------------------------------------
const cfg = {
  baseline: { baseUrl: 'https://old.corp.com' },
  candidate: { baseUrl: 'https://new.corp.com', pathOverrides: { dashboard: '/hiapm/project/dashboard' } },
  routes: [{ id: 'dashboard', path: '/hiapm/project/dashboard.do' }, { id: 'orders', path: '/order/list' }],
  journeys: [{ id: 'notice', startPath: '/hiapm/notice.do' }],
};
const origins = ['https://old.corp.com', 'https://new.corp.com'];
const tokens = { baseline: buildPathTokens(cfg, 'baseline'), candidate: buildPathTokens(cfg, 'candidate') };
const norm = (url, side, mode) => normalizeRouteUrl(url, { origins, tokens: tokens[side], mode });

eq('已声明的路径迁移归一化后相等',
  norm('https://old.corp.com/hiapm/project/dashboard.do?tab=1', 'baseline'),
  norm('https://new.corp.com/hiapm/project/dashboard?tab=1', 'candidate'));
check('未声明的路径差异仍然不同',
  norm('https://old.corp.com/order/list', 'baseline') !== norm('https://new.corp.com/order/unknown', 'candidate'));
check('query 差异不会被路径归一化掩盖',
  norm('https://old.corp.com/order/list?id=1', 'baseline') !== norm('https://new.corp.com/order/list?id=2', 'candidate'));
eq('journey 的 startPath 也进入词表',
  norm('https://old.corp.com/hiapm/notice.do', 'baseline'), '{origin}{journey:notice}');
eq('ignorePath 只比 query/hash',
  norm('https://new.corp.com/whatever/else?tab=1#a', 'candidate', 'query'), '?tab=1#a');
eq('长路径优先替换，避免前缀互相污染',
  normalizeRouteUrl('https://x/shell-v2', {
    origins: ['https://x'],
    tokens: buildPathTokens({ candidate: { urlTokens: { '/shell': '{s}', '/shell-v2': '{s}' } } }, 'candidate'),
  }), '{origin}{s}');

// ---- 探针可裁剪 ----------------------------------------------------------
eq('默认全量探针', resolveProbes({}, {}, DEFAULT_PROBES).length, DEFAULT_PROBES.length);
eq('defaultProbes:false 只留自定义探针',
  resolveProbes({ defaultProbes: false, styleProbes: [{ id: 'kpi', selector: '.kpi' }] }, {}, DEFAULT_PROBES)
    .map((p) => p.id), ['kpi']);
eq('defaultProbes 可挑子集',
  resolveProbes({ defaultProbes: ['heading', 'table-header-cell'] }, {}, DEFAULT_PROBES).map((p) => p.id),
  ['heading', 'table-header-cell']);
eq('同 id 自定义探针覆盖内置选择器',
  resolveProbes({ defaultProbes: ['body'], styleProbes: [{ id: 'body', selector: '.app-shell' }] }, {}, DEFAULT_PROBES),
  [{ id: 'body', selector: '.app-shell' }]);
eq('探针支持两侧独立 CSS 选择器',
  resolveProbes({ defaultProbes: false, styleProbes: [{ id: 'card', baselineSelector: '.old', candidateSelector: '.new' }] }, {}, DEFAULT_PROBES, 'candidate'),
  [{ id: 'card', baselineSelector: '.old', candidateSelector: '.new', selector: '.new' }]);
check('styleProbes 拒绝 Playwright :has-text 语法',
  configValidationErrors({ styleProbes: [{ id: 'send', selector: 'button:has-text("发送")' }] }).length === 1);
check('未知 journey 动作在采集前即报配置错误',
  configValidationErrors({ journeys: [{ id: 'x', steps: [{ type: 'magicClick', selector: 'button' }] }] }).length === 1);

eq('比较面合并共享与分侧配置',
  resolveSurface({ compareSurface: { exclude: ['.header'], baseline: { frame: '#old-frame' }, candidate: { root: '#new' } } }, {}, 'baseline'),
  { exclude: ['.header'], frame: '#old-frame' });
eq('route 可重置全局比较面（popup）',
  resolveSurface({ compareSurface: { baseline: { frame: '#old-frame' } } }, { compareSurface: { reset: true, root: '#popup' } }, 'baseline'),
  { root: '#popup', exclude: [] });

// ---- L4 降噪 -------------------------------------------------------------
const drift = aggregateStyleDrift([
  { probe: 'body', changes: ['font-family: A → B', 'color: #111 → #222'] },
  { probe: 'button', changes: ['font-family: A → B', 'border-radius: 4px → 10px'] },
  { probe: 'link', changes: ['font-family: A → B'] },
], 3);
eq('跨探针同属性收敛成一条全局漂移', drift.global.map((g) => g.prop), ['font-family']);
eq('全局属性从逐探针结果里移除',
  drift.perProbe.map((p) => `${p.probe}:${p.changes.join('|')}`),
  ['body:color: #111 → #222', 'button:border-radius: 4px → 10px']);
eq('未达阈值的属性不聚合', aggregateStyleDrift([{ probe: 'a', changes: ['gap: 8px → 12px'] }], 3).global, []);

// ---- iframe 合并与不可读标记 --------------------------------------------
const merged = mergeDomDigests(
  { links: [{ text: '首页', href: '/' }], textOutline: ['看板'], counts: { elements: 10 } },
  [
    { url: 'https://x/topbar', status: 'read', digest: { links: [{ text: '我的待办', href: '/todo' }], textOutline: ['待办'] } },
    { url: 'https://y/ad', status: 'unreadable', error: 'evaluate blocked' },
  ],
);
eq('同域/可读 iframe 的链接并入摘要', merged.links.map((l) => l.text), ['首页', '我的待办']);
eq('主文档统计不被 iframe 覆盖', merged.counts, { elements: 10 });
eq('不可读 iframe 被标记而非丢弃', unreadableFrames(merged).map((f) => f.url), ['https://y/ad']);
eq('frames 摘要不携带原始 digest', Object.keys(merged.frames[0]), ['url', 'status', 'error']);

console.log(failed ? `\n${failed} unit check(s) failed` : '\nunit tests OK');
process.exit(failed ? 1 : 0);
