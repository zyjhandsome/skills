#!/usr/bin/env node
// Export a storageState file from a Chrome/Edge the user is ALREADY logged into,
// so a parity run reuses that SSO session instead of asking for credentials.
//
// 1) Start (or restart) the browser with a debugging port, then log in as usual:
//      Windows: "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
//      macOS:   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222
// 2) node scripts/export-storage-state.mjs --out auth/candidate.json --url https://app.example.com/home
// 3) Point config `<side>.auth.storageState` at that file.
//
// This script attaches to a browser it does not own: it never calls browser.close(),
// which would take the user's own windows down with it.
import path from 'node:path';
import fs from 'node:fs';
import { loadPlaywright, ensureDir, parseArgs } from './lib/pw.mjs';

const args = parseArgs(process.argv.slice(2));
if (args.help) {
  console.log('usage: node export-storage-state.mjs [--cdp http://127.0.0.1:9222] --out auth/side.json [--url URL] [--url URL2] [--keep-page]');
  process.exit(0);
}
const cdp = args.cdp || `http://127.0.0.1:${args.port || 9222}`;
const out = path.resolve(args.out || 'auth/storage-state.json');
const urls = [].concat(args.url || []).filter(Boolean);

const pw = await loadPlaywright(process.cwd());
if (!pw) {
  console.error('Playwright not found. Run scripts/preflight.mjs first.');
  process.exit(3);
}

let browser;
try {
  browser = await pw.chromium.connectOverCDP(cdp);
} catch (e) {
  console.error(`无法连接 ${cdp}：${String(e.message || e).split('\n')[0]}`);
  console.error('请用 --remote-debugging-port=9222 重新启动浏览器并登录后重试。');
  console.error('注意：已在运行的 Chrome 不会凭空开启调试端口，必须先完全退出再带参数启动。');
  process.exit(4);
}

const context = browser.contexts()[0];
if (!context) {
  console.error('CDP 连接成功但没有可用 context —— 浏览器里至少要开一个标签页。');
  process.exit(4);
}

// localStorage/sessionStorage is collected per origin from open pages, so visiting the
// business URL once makes token-in-localStorage logins exportable too.
const opened = [];
for (const u of urls) {
  const page = await context.newPage();
  try {
    await page.goto(u, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(1500);
    opened.push({ url: u, landedOn: page.url() });
  } catch (e) {
    console.error(`打开 ${u} 失败：${String(e.message || e).split('\n')[0]}`);
  }
  if (args['keep-page']) continue;
  await page.close();
}

ensureDir(path.dirname(out));
const state = await context.storageState({ path: out });
const origins = (state.origins || []).map((o) => o.origin);

console.log(JSON.stringify({
  cdp,
  out,
  cookies: state.cookies?.length ?? 0,
  cookieDomains: [...new Set((state.cookies || []).map((c) => c.domain))].slice(0, 20),
  localStorageOrigins: origins,
  visited: opened,
  bytes: fs.statSync(out).size,
  note: '未调用 browser.close()：CDP 连接的是用户自己的浏览器，关闭会连带关掉用户窗口。',
}, null, 2));

// Detach without touching the user's browser.
process.exit(0);
