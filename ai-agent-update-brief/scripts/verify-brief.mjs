// 校验简报 HTML 的机械可判规则（章节、工具覆盖、日期窗口、主题契约、中文残片）。
// 用法:
//   node verify-brief.mjs <report.html> [--en] [--check-links] [--strict] [--today YYYY-MM-DD]
// 退出码: 0 = 无 ERROR（可有 WARN）; 1 = 有 ERROR; 2 = 用法错误。
// 依赖: 仅 Node 标准库。--check-links 才会发网络请求。

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const REQUIRED_SECTIONS = [
  "conclusions",
  "actions",
  "automation",
  "multi-agent",
  "security",
  "quota",
  "choose-tool",
  "pool",
  "sources",
];

export const TOOL_TIERS = {
  core: [
    { id: "cursor", aliases: ["Cursor"] },
    { id: "codex", aliases: ["OpenAI Codex", "Codex"] },
    { id: "claude-code", aliases: ["Claude Code"] },
    { id: "antigravity", aliases: ["Antigravity", "Antigravity CLI", "Gemini CLI", "Google Antigravity"] },
    { id: "vscode-copilot", aliases: ["VS Code", "GitHub Copilot", "Copilot"] },
  ],
  secondary: [
    { id: "cowork", aliases: ["Claude Cowork", "Cowork"] },
    { id: "claude-tag", aliases: ["Claude Tag", "Claude in Slack"] },
    { id: "jetbrains", aliases: ["JetBrains", "Junie", "AI Assistant"] },
    { id: "devin", aliases: ["Devin", "Windsurf", "Devin Desktop"] },
    { id: "amp", aliases: ["Sourcegraph Amp", "Amp"] },
    { id: "factory", aliases: ["Factory Droid", "Factory"] },
  ],
  tail: [
    { id: "aider", aliases: ["Aider"] },
    { id: "continue", aliases: ["Continue"] },
    { id: "replit", aliases: ["Replit Agent", "Replit"] },
    { id: "copilot-workspace", aliases: ["Copilot Workspace", "GitHub Copilot Workspace"] },
  ],
};

export const ALL_TOOLS = [
  ...TOOL_TIERS.core,
  ...TOOL_TIERS.secondary,
  ...TOOL_TIERS.tail,
];

const FORBIDDEN_ZH = [
  /No qualifying official update found/i,
  /No qualifying update found/i,
  /official releases/i,
  /release page checked/i,
  /billed to organization/i,
  /Beginner glossary/i,
  /小白术语表/,
];

const ISO = /^\d{4}-\d{2}-\d{2}$/;

export function parseArgs(argv) {
  const opts = {
    file: null,
    en: false,
    checkLinks: false,
    strict: false,
    today: null,
  };
  const args = argv.slice(2);
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === "--en") opts.en = true;
    else if (a === "--check-links") opts.checkLinks = true;
    else if (a === "--strict") opts.strict = true;
    else if (a === "--today") opts.today = args[++i];
    else if (a.startsWith("-")) throw new Error(`未知参数: ${a}`);
    else opts.file = a;
  }
  return opts;
}

function attr(html, name) {
  const m = html.match(new RegExp(`${name}\\s*=\\s*"([^"]*)"`, "i"));
  return m ? m[1] : null;
}

function allAttrs(html, name) {
  const out = [];
  const re = new RegExp(`${name}\\s*=\\s*"([^"]*)"`, "gi");
  let m;
  while ((m = re.exec(html))) out.push(m[1]);
  return out;
}

function sectionChunk(html, id) {
  const re = new RegExp(
    `<section\\b[^>]*data-section="${id}"[^>]*>([\\s\\S]*?)</section>`,
    "i"
  );
  return html.match(re);
}

function parseDate(value) {
  if (!value || !ISO.test(value)) return null;
  const t = Date.parse(`${value}T00:00:00Z`);
  return Number.isNaN(t) ? null : t;
}

export function verifyBrief(html, options = {}) {
  const errors = [];
  const warns = [];
  const en = Boolean(options.en);
  const today = parseDate(options.today) ?? Date.parse(new Date().toISOString().slice(0, 10) + "T00:00:00Z");

  const lang = attr(html.match(/<html\b[^>]*>/i)?.[0] ?? "", "lang");
  if (en) {
    if (!lang || !/^en\b/i.test(lang)) errors.push(`html lang 应为 en，实际为 ${lang ?? "(缺失)"}`);
  } else if (lang !== "zh-CN") {
    errors.push(`html lang 应为 zh-CN，实际为 ${lang ?? "(缺失)"}`);
  }

  for (const id of REQUIRED_SECTIONS) {
    if (!sectionChunk(html, id)) errors.push(`缺少 data-section="${id}"`);
  }

  const scopeOpen = html.match(/<[^>]*class="[^"]*\brule\b[^"]*\bscope\b[^"]*"[^>]*>/i)
    ?? html.match(/<[^>]*class="[^"]*\bscope\b[^"]*\brule\b[^"]*"[^>]*>/i);
  const start = scopeOpen ? attr(scopeOpen[0], "data-window-start") : null;
  const end = scopeOpen ? attr(scopeOpen[0], "data-window-end") : null;
  if (!start || !end) {
    errors.push("缺少 .rule.scope 上的 data-window-start / data-window-end");
  } else {
    const a = parseDate(start);
    const b = parseDate(end);
    if (!a || !b) errors.push("日期窗口不是 YYYY-MM-DD");
    else if (a > b) errors.push("日期窗口起点晚于终点");
    else if (b > today + 86400000) warns.push("日期窗口终点晚于今天");
  }

  const pool = sectionChunk(html, "pool");
  const poolHtml = pool ? pool[1] : "";
  const rows = [...poolHtml.matchAll(/<tr\b[^>]*>[\s\S]*?<\/tr>/gi)].map((m) => m[0]);
  const byTool = new Map();
  for (const row of rows) {
    const open = row.match(/<tr\b[^>]*>/i)?.[0] ?? "";
    const id = attr(open, "data-tool");
    if (!id) continue;
    byTool.set(id, {
      status: attr(open, "data-status"),
      date: attr(open, "data-date"),
      latest: attr(open, "data-latest"),
    });
  }

  const degrade = /data-degrade="1"/.test(html);
  const skipped = [];
  for (const tool of ALL_TOOLS) {
    const row = byTool.get(tool.id);
    if (!row) {
      errors.push(`联合更新池缺少 data-tool="${tool.id}"`);
      continue;
    }
    if (!["update", "none", "skipped"].includes(row.status)) {
      errors.push(`${tool.id}: data-status 必须是 update|none|skipped`);
    }
    if (row.status === "skipped") skipped.push(tool.id);
    if (row.status === "update") {
      const d = parseDate(row.date);
      if (!d) errors.push(`${tool.id}: update 行缺少有效 data-date`);
      else if (start && end) {
        const a = parseDate(start);
        const b = parseDate(end);
        if (a && b && (d < a || d > b)) {
          if (!["1", "2", "3"].includes(row.latest ?? "")) {
            errors.push(`${tool.id}: 日期 ${row.date} 落在 7 天窗口外，但未标 data-latest="1|2|3"`);
          }
        }
      }
    }
  }

  const coreMissing = TOOL_TIERS.core.filter((t) => {
    const row = byTool.get(t.id);
    return !row || row.status === "skipped";
  });
  if (coreMissing.length) {
    errors.push(`核心工具不可跳过: ${coreMissing.map((t) => t.id).join(", ")}`);
  }
  if (skipped.length && !degrade) {
    errors.push(`存在 skipped 行（${skipped.join(", ")}）但缺少 data-degrade="1"`);
  }

  if (!en) {
    for (const re of FORBIDDEN_ZH) {
      if (re.test(html)) errors.push(`中文简报含英文残片: ${re.source}`);
    }
  }

  if (!/data-theme-set="light"/.test(html) || !/data-theme-set="dark"/.test(html)) {
    errors.push("缺少主题开关 data-theme-set=light/dark");
  }
  if (!/ai-agent-brief-theme/.test(html)) {
    errors.push("缺少 localStorage 键 ai-agent-brief-theme");
  }
  if (!/--ink\s*:/.test(html) || !/\[data-theme="dark"\]/.test(html)) {
    errors.push("缺少主题 CSS 变量或 [data-theme=dark] 规则");
  }
  if (!/class="[^"]*\btoc\b/.test(html)) {
    errors.push("缺少 nav.toc / .toc");
  }
  if (!/class="[^"]*\btheme-switch\b/.test(html)) {
    errors.push("缺少 .theme-switch");
  }

  if (/data-placeholder="1"/.test(html)) {
    const msg = "报告仍带 data-placeholder=\"1\"（骨架未填完）";
    if (options.strict) errors.push(msg);
    else warns.push(msg);
  }

  const hrefs = [];
  const sources = sectionChunk(html, "sources");
  if (sources) {
    for (const href of allAttrs(sources[1], "href")) {
      if (/^https?:\/\//i.test(href)) hrefs.push(href);
    }
    if (hrefs.length === 0) errors.push("官方来源区没有 http(s) 链接");
  }

  return { errors, warns, hrefs, skipped, degrade };
}

export async function checkLinks(hrefs, fetchImpl = fetch) {
  const errors = [];
  const warns = [];
  for (const href of hrefs) {
    try {
      const res = await fetchImpl(href, { method: "HEAD", redirect: "follow" });
      if (res.status >= 400) {
        const again = await fetchImpl(href, { method: "GET", redirect: "follow" });
        if (again.status >= 400) errors.push(`链接不可达 ${again.status}: ${href}`);
      }
    } catch (err) {
      warns.push(`链接检查失败: ${href} (${err.message})`);
    }
  }
  return { errors, warns };
}

export async function verifyFile(file, options = {}) {
  const html = fs.readFileSync(file, "utf8");
  const result = verifyBrief(html, options);
  if (options.checkLinks && result.hrefs.length) {
    const net = await checkLinks(result.hrefs, options.fetchImpl);
    result.errors.push(...net.errors);
    result.warns.push(...net.warns);
  }
  return result;
}

function printReport(file, result) {
  for (const w of result.warns) console.warn(`WARN  ${path.basename(file)}: ${w}`);
  for (const e of result.errors) console.error(`ERROR ${path.basename(file)}: ${e}`);
  if (result.errors.length === 0) {
    console.log(`OK    ${path.basename(file)}  (${result.warns.length} warn)`);
  }
}

function isMain(metaUrl) {
  const here = path.normalize(fileURLToPath(metaUrl));
  const invoked = process.argv[1] ? path.normalize(path.resolve(process.argv[1])) : "";
  return here.toLowerCase() === invoked.toLowerCase();
}

if (isMain(import.meta.url)) {
  let opts;
  try {
    opts = parseArgs(process.argv);
  } catch (err) {
    console.error(err.message);
    process.exit(2);
  }
  if (!opts.file) {
    console.error("用法: node verify-brief.mjs <report.html> [--en] [--check-links] [--strict] [--today YYYY-MM-DD]");
    process.exit(2);
  }
  const file = path.resolve(opts.file);
  if (!fs.existsSync(file)) {
    console.error("找不到文件:", file);
    process.exit(2);
  }
  const result = await verifyFile(file, opts);
  printReport(file, result);
  process.exit(result.errors.length ? 1 : 0);
}
