#!/usr/bin/env node
// Report whether Playwright + a usable browser are available, and how to get them.
// Exit 0 = ready, 3 = missing (see JSON `install` for the commands to offer the user).
import fs from 'node:fs';
import path from 'node:path';
import { loadPlaywright, browserCacheDir, parseArgs } from './lib/pw.mjs';

const args = parseArgs(process.argv.slice(2));
const cwd = args.cwd ? path.resolve(args.cwd) : process.cwd();
const browserName = args.browser || 'chromium';

const report = {
  schema: 'parity-preflight/v1',
  node: process.version,
  cwd,
  playwright: { available: false, source: null, version: null },
  browsers: { cacheDir: browserCacheDir(), installed: [], launchable: false, launchError: null },
  ready: false,
  install: {},
};

const pw = await loadPlaywright(cwd);
if (pw) {
  report.playwright.available = true;
  report.playwright.source = pw.source;
  try {
    const [name, dir] = pw.source.split(' @ ');
    const pkg = path.join(dir, name, 'package.json');
    if (fs.existsSync(pkg)) report.playwright.version = JSON.parse(fs.readFileSync(pkg, 'utf8')).version;
  } catch { /* version is informational only */ }
}

try {
  if (fs.existsSync(report.browsers.cacheDir)) {
    report.browsers.installed = fs
      .readdirSync(report.browsers.cacheDir)
      .filter((d) => !d.startsWith('.'));
  }
} catch { /* cache dir unreadable */ }

if (pw) {
  const engine = pw[browserName];
  if (!engine) {
    report.browsers.launchError = `unknown browser: ${browserName}`;
  } else {
    try {
      const b = await engine.launch({ headless: true });
      const page = await (await b.newContext()).newPage();
      await page.setContent('<h1>ok</h1>');
      report.browsers.launchable = (await page.textContent('h1')) === 'ok';
      report.browsers.browserVersion = b.version();
      await b.close();
    } catch (e) {
      report.browsers.launchError = String(e.message || e).split('\n').slice(0, 6).join(' | ');
    }
  }
}

report.ready = report.playwright.available && report.browsers.launchable;

if (!report.ready) {
  report.install = {
    note: '安装前必须获得用户明确授权；不要在未授权时执行任何 install 命令。',
    projectLocal: ['npm i -D playwright', `npx playwright install ${browserName}`],
    globalNoProjectChange: ['npm i -g playwright', `npx playwright install ${browserName}`],
    browsersOnly: [`npx playwright install ${browserName}`],
    linuxSystemDeps: [`npx playwright install --with-deps ${browserName}`],
    offlineHint: 'PLAYWRIGHT_DOWNLOAD_HOST / PLAYWRIGHT_BROWSERS_PATH 可指向内网镜像或共享缓存目录。',
  };
}

console.log(JSON.stringify(report, null, 2));
process.exit(report.ready ? 0 : 3);
