// 验证简报 HTML 的亮色 / 暗黑双模式截图。
// 用法: node verify-theme.mjs <report.html> [outDir]
//   report.html  必填，简报文件路径
//   outDir       可选，截图输出目录，默认为报告同目录下的 theme-check/
// 依赖: playwright-core（npm i playwright-core），以及本机已安装的 Edge 或 Chrome。
// 生成后请逐张查看截图，确认首屏、表格 chips、sticky 导航、页脚在两种模式下对比度正常。

import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const htmlArg = process.argv[2];
if (!htmlArg) {
  console.error("用法: node verify-theme.mjs <report.html> [outDir]");
  process.exit(1);
}
const html = path.resolve(htmlArg);
if (!fs.existsSync(html)) {
  console.error("找不到文件:", html);
  process.exit(1);
}
const out = path.resolve(process.argv[3] ?? path.join(path.dirname(html), "theme-check"));
fs.mkdirSync(out, { recursive: true });
const url = pathToFileURL(html).href;

async function launchBrowser() {
  const exe = process.env.BRIEF_BROWSER_PATH;
  if (exe) return chromium.launch({ executablePath: exe, headless: true });
  for (const channel of ["msedge", "chrome"]) {
    try {
      return await chromium.launch({ channel, headless: true });
    } catch {
      // 该渠道未安装，尝试下一个
    }
  }
  throw new Error(
    "未找到 Edge / Chrome。请安装其一，或设置环境变量 BRIEF_BROWSER_PATH 指向浏览器可执行文件。"
  );
}

const browser = await launchBrowser();

async function shot(theme, viewport, suffix, { fullPage = false, scrollTo = null } = {}) {
  const page = await browser.newPage({ viewport, colorScheme: theme });
  await page.addInitScript((t) => {
    localStorage.setItem("ai-agent-brief-theme", t);
  }, theme);
  await page.goto(url, { waitUntil: "domcontentloaded" });
  await page.evaluate((t) => {
    document.documentElement.setAttribute("data-theme", t);
    document.querySelectorAll("[data-theme-set]").forEach((btn) => {
      btn.setAttribute("aria-pressed", btn.getAttribute("data-theme-set") === t ? "true" : "false");
    });
  }, theme);
  if (scrollTo) {
    await page.locator(scrollTo).scrollIntoViewIfNeeded();
    await page.waitForTimeout(200);
  }
  const file = path.join(out, `${theme}-${suffix}.png`);
  await page.screenshot({ path: file, fullPage, animations: "disabled" });
  await page.close();
  console.log("wrote", file);
}

const desktop = { width: 1280, height: 900 };
const mobile = { width: 390, height: 844 };

for (const theme of ["light", "dark"]) {
  await shot(theme, desktop, "first");                      // 首屏（header + 核心结论）
  await shot(theme, desktop, "footer", { scrollTo: "footer" }); // 页脚
  await shot(theme, desktop, "full", { fullPage: true });   // 整页（表格、chips、各区块）
  await shot(theme, mobile, "mobile");                      // 移动端首屏
}

await browser.close();
console.log("完成。请逐张检查", out, "下的截图，确认两种模式的对比度与配色。");
