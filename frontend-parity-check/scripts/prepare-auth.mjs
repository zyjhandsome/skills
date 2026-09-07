#!/usr/bin/env node
// Prepare a verified storageState. Public pages stay headless; login/SSO opens an isolated visible browser.
// Usage: node prepare-auth.mjs --config parity-config.json --side baseline|candidate
//        [--force-interactive] [--skip-probe]
import fs from 'node:fs';
import path from 'node:path';
import {
  loadPlaywright, ensureDir, readJson, parseArgs,
} from './lib/pw.mjs';
import { configValidationErrors } from './lib/parity-core.mjs';
import {
  authProfilePath, authStoragePath, firstAuthTarget, inspectAuthReadiness,
  shouldOpenInteractive, shouldProbeFirst, shouldCommitAuthState,
  earlyAuthReadyWarning, resolvedAuthReadySelector, unsafeDailyProfileReason,
} from './lib/auth.mjs';

const args = parseArgs(process.argv.slice(2));
const side = args.side;
if (!args.config || !['baseline', 'candidate'].includes(side)) {
  console.error('usage: node prepare-auth.mjs --config <file> --side <baseline|candidate> [--force-interactive] [--skip-probe]');
  process.exit(2);
}

const configPath = path.resolve(args.config);
const cfg = readJson(configPath);
const sideCfg = cfg?.[side];
if (!cfg || !sideCfg?.baseUrl) {
  console.error(`配置不可读或缺少 ${side}.baseUrl：${configPath}`);
  process.exit(2);
}
const configErrors = configValidationErrors(cfg);
if (configErrors.length) {
  console.error(`配置校验失败：\n- ${configErrors.join('\n- ')}`);
  process.exit(2);
}

const pw = await loadPlaywright(process.cwd());
if (!pw) {
  console.error('Playwright not found. Run scripts/preflight.mjs and follow its install guidance.');
  process.exit(3);
}

const auth = sideCfg.auth || {};
const interactive = auth.interactive || {};
const storageState = authStoragePath(configPath, side, sideCfg);
const profileDir = authProfilePath(configPath, side, cfg, sideCfg);
const unsafeProfile = unsafeDailyProfileReason(profileDir);
if (unsafeProfile) {
  console.error(`${unsafeProfile}。请改用 Skill 专用目录（默认 ./auth/profiles/<name>/<side>）。`);
  process.exit(2);
}

const browserName = cfg.browser || 'chromium';
const channel = args.channel || interactive.channel || cfg.channel || null;
const executablePath = args.executablePath || interactive.executablePath || cfg.executablePath || null;
const launchOptions = {};
if (channel) launchOptions.channel = channel;
if (executablePath) launchOptions.executablePath = executablePath;

const ctx = cfg.context || {};
const contextOptions = {
  viewport: ctx.viewports?.[0]
    ? { width: ctx.viewports[0].width, height: ctx.viewports[0].height }
    : { width: 1440, height: 900 },
  deviceScaleFactor: ctx.deviceScaleFactor ?? 1,
  locale: ctx.locale || 'zh-CN',
  timezoneId: ctx.timezoneId || 'Asia/Shanghai',
  colorScheme: ctx.colorScheme || 'light',
  ignoreHTTPSErrors: ctx.ignoreHTTPSErrors ?? true,
};
if (sideCfg.userAgent) contextOptions.userAgent = sideCfg.userAgent;
if (sideCfg.extraHTTPHeaders) contextOptions.extraHTTPHeaders = sideCfg.extraHTTPHeaders;

const { url: targetUrl } = firstAuthTarget(cfg, side);
const probeTimeoutMs = Number(interactive.probeTimeoutMs || 4000);
const loginTimeoutMs = Number(interactive.timeoutMs || 600000);
const readinessTimeoutMs = Number(interactive.readinessTimeoutMs || 1200);
const readyHoldMs = Number(interactive.readyHoldMs ?? 1500);
const forceInteractive = !!args['force-interactive'];
const skipProbe = !!args['skip-probe'];

const readyWarning = earlyAuthReadyWarning(resolvedAuthReadySelector(cfg, side));
if (readyWarning) console.error(`[auth:${side}] ${readyWarning}`);

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function saveState(context) {
  ensureDir(path.dirname(storageState));
  const temp = `${storageState}.${process.pid}.tmp`;
  try {
    await context.storageState({ path: temp });
    fs.copyFileSync(temp, storageState);
    if (process.platform !== 'win32') fs.chmodSync(storageState, 0o600);
  } finally {
    fs.rmSync(temp, { force: true });
  }
}

async function waitUntilReady(context, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let last = { ok: false, reason: '尚未检查', url: targetUrl };
  let loginLikely = false;
  while (Date.now() < deadline) {
    const pages = context.pages();
    if (!pages.length) return { ok: false, closed: true, reason: '浏览器窗口已关闭' };
    for (const page of pages.slice().reverse()) {
      if (page.isClosed()) continue;
      last = await inspectAuthReadiness(page, cfg, side, readinessTimeoutMs);
      loginLikely ||= !!last.loginLikely;
      if (!last.ok) continue;
      const hold = Math.min(readyHoldMs, Math.max(0, deadline - Date.now()));
      if (hold > 0) await sleep(hold);
      if (page.isClosed()) continue;
      last = await inspectAuthReadiness(page, cfg, side, readinessTimeoutMs);
      loginLikely ||= !!last.loginLikely;
      if (last.ok) return { ...last, page };
    }
    await sleep(800);
  }
  return { ...last, loginLikely, timedOut: true };
}

async function coldStartVerify() {
  if (!fs.existsSync(storageState)) {
    return { ok: false, reason: 'storageState 未写出', url: targetUrl };
  }
  const browser = await pw[browserName].launch({ ...launchOptions, headless: true });
  try {
    const context = await browser.newContext({ ...contextOptions, storageState });
    try {
      const page = await context.newPage();
      await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: Number(ctx.navTimeoutMs || 45000) });
      return await waitUntilReady(context, probeTimeoutMs);
    } finally {
      await context.close();
    }
  } finally {
    await browser.close();
  }
}

async function commitSession(sourceContext) {
  await saveState(sourceContext);
  const verified = await coldStartVerify();
  if (!shouldCommitAuthState({ windowReady: true, coldStartReady: !!verified.ok })) {
    fs.rmSync(storageState, { force: true });
    return { ok: false, reason: `冷启动校验失败：${verified.reason || '未知'}`, url: verified.url };
  }
  return { ok: true, url: verified.url };
}

async function probe() {
  const hadStorageState = fs.existsSync(storageState);
  const browser = await pw[browserName].launch({ ...launchOptions, headless: true });
  try {
    const options = { ...contextOptions };
    if (hadStorageState) options.storageState = storageState;
    const context = await browser.newContext(options);
    try {
      const page = await context.newPage();
      await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: Number(ctx.navTimeoutMs || 45000) });
      const result = await waitUntilReady(context, probeTimeoutMs);
      if (!result.ok) return { ...result, reused: hadStorageState };
      if (hadStorageState) return { ...result, reused: true };
      const committed = await commitSession(context);
      return { ...committed, reused: false };
    } finally {
      await context.close();
    }
  } finally {
    await browser.close();
  }
}

let probeResult = null;
if (shouldProbeFirst({ skipProbe, forceInteractive })) {
  try {
    probeResult = await probe();
  } catch (error) {
    probeResult = { ok: false, stage: 'probe', reason: String(error?.message || error).split('\n')[0] };
  }
}

if (probeResult?.ok) {
  console.log(JSON.stringify({
    status: 'ready', side, mode: 'headless-probe', url: probeResult.url,
    storageState, reused: probeResult.reused,
  }, null, 2));
  process.exit(0);
}

if (!shouldOpenInteractive({
  forceInteractive,
  loginLikely: !!probeResult?.loginLikely,
  openOnUnready: interactive.openOnUnready,
})) {
  console.error(`[auth:${side}] 无头探测未就绪，但未识别出登录页：${probeResult?.reason || '未知原因'}`);
  console.error(`[auth:${side}] 已显式设置 openOnUnready=false。确认是登录问题后去掉该开关，或加 --force-interactive。`);
  process.exit(4);
}

ensureDir(profileDir);
console.error(`[auth:${side}] 无头探测未通过：${probeResult?.reason || (skipProbe ? '已跳过无头探测' : '已要求交互登录')}`);
console.error(`[auth:${side}] 正在打开登录窗口。请在该窗口完成登录（扫码 / SSO / 账号均可），不用回复「登录好了」。`);
console.error(`[auth:${side}] 登录后请让页面回到：${targetUrl}`);
console.error(`[auth:${side}] 成功后会自动保存会话并关闭这个专用窗口；最长等待 ${Math.round(loginTimeoutMs / 60000)} 分钟。`);

let persistent = null;
try {
  persistent = await pw[browserName].launchPersistentContext(profileDir, {
    ...launchOptions,
    ...contextOptions,
    headless: args['headless-interactive'] ? true : false,
  });
  persistent.setDefaultTimeout(Number(ctx.timeoutMs || 20000));
  const page = persistent.pages()[0] || await persistent.newPage();
  await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: Number(ctx.navTimeoutMs || 45000) });
  const deadline = Date.now() + loginTimeoutMs;
  let last = { ok: false, reason: '尚未检查', url: targetUrl };
  while (Date.now() < deadline) {
    last = await waitUntilReady(persistent, Math.max(0, deadline - Date.now()));
    if (!last.ok) {
      const suffix = last.closed ? '用户关闭了窗口' : `等待超时；最后状态：${last.reason || '未知'}`;
      throw new Error(`交互式登录未完成：${suffix}`);
    }
    const committed = await commitSession(persistent);
    if (committed.ok) {
      console.log(JSON.stringify({
        status: 'ready', side, mode: 'interactive', url: committed.url, storageState, profileDir,
      }, null, 2));
      process.exitCode = 0;
      last = committed;
      break;
    }
    console.error(`[auth:${side}] ${committed.reason}；登录窗口保持打开，继续等待会话写稳。`);
    last = committed;
    await sleep(800);
  }
  if (!last.ok) throw new Error(`交互式登录未完成：冷启动校验一直未通过；最后状态：${last.reason || '未知'}`);
} catch (error) {
  console.error(`[auth:${side}] ${String(error?.message || error).split('\n')[0]}`);
  process.exitCode = 4;
} finally {
  if (persistent) await persistent.close().catch(() => {});
}
