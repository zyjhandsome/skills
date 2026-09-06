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
  channels: [],
  useConfig: null,
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

/** Try to actually drive a browser; `channel`/`executablePath` cover locked-down machines. */
async function probeLaunch(engine, options) {
  const b = await engine.launch({ headless: true, ...options });
  try {
    const page = await (await b.newContext()).newPage();
    await page.setContent('<h1>ok</h1>');
    const ok = (await page.textContent('h1')) === 'ok';
    return { launchable: ok, version: b.version() };
  } finally {
    await b.close();
  }
}

if (pw) {
  const engine = pw[browserName];
  if (!engine) {
    report.browsers.launchError = `unknown browser: ${browserName}`;
  } else {
    // 1) bundled engine
    try {
      const r = await probeLaunch(engine, {});
      report.browsers.launchable = r.launchable;
      report.browsers.browserVersion = r.version;
      if (r.launchable) report.useConfig = { browser: browserName };
    } catch (e) {
      report.browsers.launchError = String(e.message || e).split('\n').slice(0, 6).join(' | ');
    }
    // 2) the machine's own Chrome / Edge — the way out when the download is blocked by a
    //    corporate proxy or a self-signed certificate.
    const candidates = args.channel ? [args.channel] : (browserName === 'chromium' ? ['chrome', 'msedge'] : []);
    if (!report.browsers.launchable) {
      for (const ch of candidates) {
        try {
          const r = await probeLaunch(engine, { channel: ch });
          report.channels.push({ channel: ch, launchable: r.launchable, version: r.version });
          if (r.launchable && !report.useConfig) report.useConfig = { browser: browserName, channel: ch };
        } catch (e) {
          report.channels.push({ channel: ch, launchable: false, error: String(e.message || e).split('\n')[0].slice(0, 200) });
        }
      }
    }
  }
}

report.ready = report.playwright.available && (report.browsers.launchable || report.channels.some((c) => c.launchable));

if (!report.ready) {
  report.install = {
    note: '安装前必须获得用户明确授权；不要在未授权时执行任何 install 命令。',
    projectLocal: ['npm i -D playwright', `npx playwright install ${browserName}`],
    globalNoProjectChange: ['npm i -g playwright', `npx playwright install ${browserName}`],
    browsersOnly: [`npx playwright install ${browserName}`],
    linuxSystemDeps: [`npx playwright install --with-deps ${browserName}`],
    useSystemBrowser: {
      when: '企业代理 / 自签证书导致内核下载中断（证书拦截、DNS 失败），或规定只能用本机浏览器',
      needs: '只需 playwright 包本身（可 npm i 成功），不下载内核',
      config: { browser: 'chromium', channel: 'chrome' },
      alt: { channel: 'msedge' },
      verify: `node scripts/preflight.mjs --channel chrome`,
      executablePathHint: '浏览器装在非标准路径时，改用配置项 "executablePath": "C:\\\\...\\\\chrome.exe"',
    },
    enterpriseNetworkHints: [
      'npm 证书/代理：npm config set proxy / https-proxy；必要时 NODE_EXTRA_CA_CERTS=<企业根证书.pem>',
      'PLAYWRIGHT_DOWNLOAD_HOST 指向内网镜像；PLAYWRIGHT_BROWSERS_PATH 指向共享或拷贝来的缓存目录',
      'PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 只装 JS 包，配合 channel 用本机浏览器',
    ],
    offlineHint: 'PLAYWRIGHT_DOWNLOAD_HOST / PLAYWRIGHT_BROWSERS_PATH 可指向内网镜像或共享缓存目录。',
  };
}

console.log(JSON.stringify(report, null, 2));
process.exit(report.ready ? 0 : 3);
