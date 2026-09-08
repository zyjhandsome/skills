#!/usr/bin/env node
// Prepare a verified storageState. Public pages stay headless; login/SSO opens an isolated visible browser.
// Usage: node prepare-auth.mjs --config parity-config.json --side baseline|candidate
//        [--force-interactive] [--skip-probe] [--confirm]
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
  authConfirmPath, consumeUserConfirm, writeUserConfirm,
  interactiveWaitDecision, shouldPrintHeartbeat,
  authWaitStatePath, readAuthWaitState, writeAuthWaitState,
  clearAuthWaitState, isProcessAlive,
} from './lib/auth.mjs';

const args = parseArgs(process.argv.slice(2));
const side = args.side;
if (!args.config || !['baseline', 'candidate'].includes(side)) {
  console.error('usage: node prepare-auth.mjs --config <file> --side <baseline|candidate> [--force-interactive] [--skip-probe] [--confirm]');
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

const confirmPath = authConfirmPath(configPath, side, sideCfg);
const waitStatePath = authWaitStatePath(configPath, side, sideCfg);
if (args.confirm) {
  const waiting = readAuthWaitState(waitStatePath);
  const sameRun = waiting?.status === 'waiting-for-login'
    && waiting.side === side
    && path.resolve(waiting.configPath || '') === configPath;
  if (!sameRun || !isProcessAlive(waiting?.pid)) {
    clearAuthWaitState(waitStatePath);
    console.error(`[auth:${side}] 没有正在等待的登录窗口；确认未发送。请重新运行 prepare-auth，并等到 LOGIN_WINDOW_READY 后再登录。`);
    process.exit(4);
  }
  writeUserConfirm(confirmPath);
  console.log(JSON.stringify({ status: 'confirm-written', side, confirmPath, waitingPid: waiting.pid }, null, 2));
  process.exit(0);
}

const existingWait = readAuthWaitState(waitStatePath);
if (existingWait && isProcessAlive(existingWait.pid)) {
  console.error(`[auth:${side}] 已有登录窗口正在等待（PID ${existingWait.pid}，目标 ${existingWait.targetUrl || '未知'}）。请使用该窗口，不要重复启动。`);
  console.error(`[auth:${side}] LOGIN_WINDOW_READY ${JSON.stringify(existingWait)}`);
  process.exit(4);
}
clearAuthWaitState(waitStatePath);
// A confirm marker without a live lease belongs to an earlier/failed run.
consumeUserConfirm(confirmPath);

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
const waitSliceMs = Number(interactive.waitSliceMs || 2000);
const heartbeatMs = Number(interactive.heartbeatMs || 15000);

const readyWarning = earlyAuthReadyWarning(resolvedAuthReadySelector(cfg, side));
if (readyWarning) console.error(`[auth:${side}] ${readyWarning}`);

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function saveState(context, destination) {
  ensureDir(path.dirname(destination));
  await context.storageState({ path: destination });
  if (process.platform !== 'win32') fs.chmodSync(destination, 0o600);
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

async function coldStartVerify(statePath = storageState) {
  if (!fs.existsSync(statePath)) {
    return { ok: false, reason: 'storageState 未写出', url: targetUrl };
  }
  const browser = await pw[browserName].launch({ ...launchOptions, headless: true });
  try {
    const context = await browser.newContext({ ...contextOptions, storageState: statePath });
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
  ensureDir(path.dirname(storageState));
  const candidateState = `${storageState}.${process.pid}.${Date.now()}.candidate`;
  try {
    await saveState(sourceContext, candidateState);
    const verified = await coldStartVerify(candidateState);
    if (!shouldCommitAuthState({ windowReady: true, coldStartReady: !!verified.ok })) {
      return { ok: false, reason: `冷启动校验失败：${verified.reason || '未知'}`, url: verified.url };
    }
    // Do not replace the last known state until the new candidate has passed cold start.
    fs.copyFileSync(candidateState, storageState);
    if (process.platform !== 'win32') fs.chmodSync(storageState, 0o600);
    return { ok: true, url: verified.url };
  } finally {
    fs.rmSync(candidateState, { force: true });
  }
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
console.error(`[auth:${side}] 准备创建登录窗口，请等待成功握手。`);

let persistent = null;
try {
  const visible = !args['headless-interactive'];
  persistent = await pw[browserName].launchPersistentContext(profileDir, {
    ...launchOptions,
    ...contextOptions,
    headless: !visible,
  });
  persistent.setDefaultTimeout(Number(ctx.timeoutMs || 20000));
  const page = persistent.pages()[0] || await persistent.newPage();
  await page.bringToFront().catch(() => {});
  let navigationWarning = null;
  try {
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: Number(ctx.navTimeoutMs || 45000) });
  } catch (error) {
    // The window is still useful for certificate interstitials, manual reload, and SSO recovery.
    navigationWarning = String(error?.message || error).split('\n')[0];
  }
  await page.bringToFront().catch(() => {});
  const waiting = {
    status: 'waiting-for-login', side, pid: process.pid, configPath, targetUrl,
    currentUrl: page.url(), profileDir, visible, startedAt: new Date().toISOString(),
    ...(navigationWarning ? { navigationWarning } : {}),
  };
  writeAuthWaitState(waitStatePath, waiting);
  console.error(`[auth:${side}] LOGIN_WINDOW_READY ${JSON.stringify(waiting)}`);
  console.error(`[auth:${side}] 登录窗口已创建${visible ? '' : '（自检无头模式）'}。请在该窗口完成登录（扫码 / SSO / 账号均可）。`);
  console.error(`[auth:${side}] 登录完成后请在对话回复「已登录」，不要把密码发给我。`);
  console.error(`[auth:${side}] 登录后请让页面回到：${targetUrl}`);
  if (navigationWarning) console.error(`[auth:${side}] 首次导航未完成，窗口保持打开，可在窗口内重试：${navigationWarning}`);
  console.error(`[auth:${side}] 页面自己就绪也会自动保存；收到确认后会立刻校验。最长等待 ${Math.round(loginTimeoutMs / 60000)} 分钟。`);
  const deadline = Date.now() + loginTimeoutMs;
  let last = { ok: false, reason: '尚未检查', url: targetUrl };
  let userConfirmed = false;
  let lastHeartbeat = 0;
  while (Date.now() < deadline) {
    if (!userConfirmed && consumeUserConfirm(confirmPath)) {
      userConfirmed = true;
      console.error(`[auth:${side}] 收到「已登录」确认，立即校验并保存会话。`);
    }
    const slice = userConfirmed
      ? Math.max(readinessTimeoutMs, readyHoldMs + 200)
      : Math.min(waitSliceMs, Math.max(0, deadline - Date.now()));
    last = await waitUntilReady(persistent, slice);
    const decision = interactiveWaitDecision({
      windowReady: !!last.ok,
      userConfirmed,
      timedOut: Date.now() >= deadline,
      closed: !!last.closed,
    });
    if (decision === 'keep-waiting') {
      if (shouldPrintHeartbeat(lastHeartbeat, Date.now(), heartbeatMs)) {
        console.error(`[auth:${side}] 仍未就绪：${last.reason || '未知'} | ${last.url || targetUrl}`);
        console.error(`[auth:${side}] 若你已经登录，请在对话回复「已登录」。`);
        lastHeartbeat = Date.now();
      }
      continue;
    }
    if (decision === 'closed') {
      throw new Error('交互式登录未完成：用户关闭了窗口');
    }
    if (decision === 'timeout') {
      throw new Error(`交互式登录未完成：等待超时；最后状态：${last.reason || '未知'} | ${last.url || targetUrl}`);
    }
    if (last.ok) {
      const committed = await commitSession(persistent);
      if (committed.ok) {
        console.log(JSON.stringify({
          status: 'ready', side, mode: 'interactive', url: committed.url, storageState, profileDir,
        }, null, 2));
        process.exitCode = 0;
        last = committed;
        break;
      }
      last = committed;
      if (userConfirmed) {
        throw new Error(`你确认已登录，但冷启动校验失败：${committed.reason || '未知'} | ${committed.url || targetUrl}`);
      }
      console.error(`[auth:${side}] ${committed.reason}；登录窗口保持打开，继续等待会话写稳。`);
      await sleep(800);
      continue;
    }
    throw new Error(`你确认已登录，但目标页仍未就绪：${last.reason || '未知'} | ${last.url || targetUrl}`);
  }
  if (!last.ok) throw new Error(`交互式登录未完成：冷启动校验一直未通过；最后状态：${last.reason || '未知'}`);
} catch (error) {
  console.error(`[auth:${side}] ${String(error?.message || error).split('\n')[0]}`);
  process.exitCode = 4;
} finally {
  clearAuthWaitState(waitStatePath, process.pid);
  consumeUserConfirm(confirmPath);
  if (persistent) await persistent.close().catch(() => {});
}
