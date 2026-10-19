import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import {
  ALL_TOOLS,
  REQUIRED_SECTIONS,
  verifyBrief,
  verifyFile,
  parseArgs,
} from "../verify-brief.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const skillDir = path.resolve(here, "../..");
const cli = path.join(skillDir, "scripts", "verify-brief.mjs");
const skeleton = path.join(skillDir, "references", "report-skeleton.html");

function poolRows(spec = {}) {
  return ALL_TOOLS.map((t) => {
    const row = spec[t.id] ?? { status: "update", date: "2026-09-16" };
    const attrs = [
      `data-tool="${t.id}"`,
      `data-status="${row.status}"`,
    ];
    if (row.date) attrs.push(`data-date="${row.date}"`);
    if (row.latest) attrs.push(`data-latest="${row.latest}"`);
    return `<tr ${attrs.join(" ")}><td>${t.id}</td></tr>`;
  }).join("");
}

const THEMED = ["automation", "multi-agent", "security", "quota", "choose-tool"];

function sections(extra = "") {
  return REQUIRED_SECTIONS.map((id) => {
    if (id === "pool") {
      return `<section data-section="pool"><p>联合更新池已按工具列齐，状态列只表示有无合格更新。</p><table><thead><tr><th>工具</th><th>日期</th><th>官方更新</th><th>状态</th></tr></thead><tbody>${extra || poolRows()}</tbody></table></section>`;
    }
    if (id === "sources") {
      return `<section data-section="sources"><p>以下链接对应当轮打开的官方页面。</p><a href="https://cursor.com/changelog">Cursor changelog</a></section>`;
    }
    if (THEMED.includes(id)) {
      return `<section data-section="${id}"><table><thead><tr><th>工具</th><th>日期</th><th>官方更新</th><th>实际影响 / 示例</th></tr></thead><tbody><tr><td>${id}</td><td>2026-09-16</td><td>更新条目</td><td>适合维护者调整工作流。示例：在仓库里按官方说明改一条命令并跑通。</td></tr></tbody></table></section>`;
    }
    return `<section data-section="${id}"><p>本段已写成可执行结论，供结构校验使用。</p></section>`;
  }).join("");
}

function withoutTool(rows, id) {
  return rows.replace(new RegExp(`<tr data-tool="${id}"[\\s\\S]*?<\\/tr>`), "");
}

export function makeBrief(opts = {}) {
  const lang = opts.lang ?? "zh-CN";
  const start = opts.start ?? "2026-09-12";
  const end = opts.end ?? "2026-09-18";
  const degrade = opts.degrade ? ` data-degrade="1"` : "";
  const placeholder = opts.placeholder ? ` data-placeholder="1"` : "";
  const toolsAttr = opts.tools ? ` data-tools="${opts.tools}"` : "";
  const customAttr = opts.customScope ? ` data-custom-scope="1"` : "";
  const scopeText = opts.scopeText ?? `覆盖窗口：${start} 至 ${end}${opts.tools ? ` 工具：${opts.tools}` : ""}`;
  const leak = opts.leak ?? "";
  const theme = opts.theme !== false;
  return `<!doctype html>
<html lang="${lang}"${placeholder}>
<head>
<meta charset="utf-8">
${theme ? `<script>localStorage.getItem("ai-agent-brief-theme")</script>
<style>
:root { --ink: #1b1d21; }
[data-theme="dark"] { --ink: #ece8e1; }
</style>` : ""}
</head>
<body>
<p class="rule scope" data-window-start="${start}" data-window-end="${end}"${toolsAttr}${customAttr}>${scopeText}</p>
<aside class="rule degrade"${degrade}></aside>
${theme ? `<nav class="toc"><div class="theme-switch">
<button data-theme-set="light">亮色</button>
<button data-theme-set="dark">暗黑</button>
</div></nav>` : ""}
${opts.body ?? sections(opts.pool)}
${leak}
</body>
</html>`;
}

test("parseArgs", () => {
  const opts = parseArgs(["node", "x", "a.html", "--en", "--strict", "--today", "2026-09-18"]);
  assert.equal(opts.file, "a.html");
  assert.equal(opts.en, true);
  assert.equal(opts.strict, true);
  assert.equal(opts.today, "2026-09-18");
});

test("valid Chinese brief passes", () => {
  const r = verifyBrief(makeBrief(), { today: "2026-09-18" });
  assert.deepEqual(r.errors, []);
});

test("wrong lang fails", () => {
  const r = verifyBrief(makeBrief({ lang: "en" }), { today: "2026-09-18" });
  assert.ok(r.errors.some((e) => e.includes("zh-CN")));
});

test("--en accepts lang=en", () => {
  const r = verifyBrief(makeBrief({ lang: "en" }), { en: true, today: "2026-09-18" });
  assert.deepEqual(r.errors, []);
});

test("missing core tool fails", () => {
  const rows = poolRows();
  const r = verifyBrief(makeBrief({ pool: rows.replace('data-tool="cursor"', 'data-tool="other"') }), {
    today: "2026-09-18",
  });
  assert.ok(r.errors.some((e) => e.includes('data-tool="cursor"')));
});

test("core tool cannot be skipped", () => {
  const r = verifyBrief(
    makeBrief({
      degrade: true,
      pool: poolRows({ cursor: { status: "skipped" } }),
    }),
    { today: "2026-09-18" }
  );
  assert.ok(r.errors.some((e) => e.includes("核心工具不可跳过")));
});

test("skipped tail without degrade fails", () => {
  const r = verifyBrief(
    makeBrief({ pool: poolRows({ aider: { status: "skipped" } }) }),
    { today: "2026-09-18" }
  );
  assert.ok(r.errors.some((e) => e.includes("data-degrade")));
});

test("skipped tail with degrade passes", () => {
  const r = verifyBrief(
    makeBrief({
      degrade: true,
      pool: poolRows({ aider: { status: "skipped" } }),
    }),
    { today: "2026-09-18" }
  );
  assert.deepEqual(r.errors, []);
});

test("date outside window needs data-latest", () => {
  const r = verifyBrief(
    makeBrief({ pool: poolRows({ cursor: { status: "update", date: "2026-08-01" } }) }),
    { today: "2026-09-18" }
  );
  assert.ok(r.errors.some((e) => e.includes("data-latest")));
});

test("date outside window with latest passes", () => {
  const r = verifyBrief(
    makeBrief({
      pool: poolRows({ cursor: { status: "update", date: "2026-08-01", latest: "1" } }),
    }),
    { today: "2026-09-18" }
  );
  assert.deepEqual(r.errors, []);
});

test("English leftovers fail in zh report", () => {
  const r = verifyBrief(makeBrief({ leak: "No qualifying official update found" }), {
    today: "2026-09-18",
  });
  assert.ok(r.errors.some((e) => e.includes("英文残片")));
});

test("placeholder attribute is always an error", () => {
  const r = verifyBrief(makeBrief({ placeholder: true }), { today: "2026-09-18" });
  assert.ok(r.errors.some((e) => e.includes("data-placeholder")));
});

test("mentioning the placeholder attribute in copy is not the html flag", () => {
  const r = verifyBrief(makeBrief({ leak: '<code>data-placeholder="1"</code>' }), {
    today: "2026-09-18",
  });
  assert.deepEqual(r.errors, []);
});

test("leftover 占位 is an error", () => {
  const r = verifyBrief(makeBrief({ leak: "占位：替换为官方版本" }), { today: "2026-09-18" });
  assert.ok(r.errors.some((e) => e.includes("占位")));
});

test("window must be 7 inclusive days", () => {
  const r = verifyBrief(makeBrief({ start: "2026-09-11", end: "2026-09-18" }), {
    today: "2026-09-18",
  });
  assert.ok(r.errors.some((e) => e.includes("7 天")));
});

test("window must end on the as-of date", () => {
  const r = verifyBrief(makeBrief({ start: "2026-09-10", end: "2026-09-16" }), {
    today: "2026-09-18",
  });
  assert.ok(r.errors.some((e) => e.includes("生成日")));
});

test("empty section fails", () => {
  const html = makeBrief().replace(
    '<section data-section="conclusions"><p>本段已写成可执行结论，供结构校验使用。</p></section>',
    '<section data-section="conclusions"></section>'
  );
  const r = verifyBrief(html, { today: "2026-09-18" });
  assert.ok(r.errors.some((e) => e.includes("conclusions") && e.includes("内容过短")));
});

test("glossary section is required", () => {
  const html = makeBrief().replace(/<section data-section="glossary">[\s\S]*?<\/section>/, "");
  const r = verifyBrief(html, { today: "2026-09-18" });
  assert.ok(r.errors.some((e) => e.includes('data-section="glossary"')));
});

test("themed table needs an impact header", () => {
  const html = makeBrief().replace("实际影响 / 示例", "备注");
  const r = verifyBrief(html, { today: "2026-09-18" });
  assert.ok(r.errors.some((e) => e.includes("实际影响")));
});

test("themed impact cell needs a concrete example", () => {
  const html = makeBrief().replace("示例：在仓库里按官方说明改一条命令并跑通。", "调整工作流即可。");
  const r = verifyBrief(html, { today: "2026-09-18" });
  assert.ok(r.errors.some((e) => e.includes("示例")));
});

test("themed empty state does not require an example", () => {
  const html = makeBrief().replace(
    '<tr><td>automation</td><td>2026-09-16</td><td>更新条目</td><td>适合维护者调整工作流。示例：在仓库里按官方说明改一条命令并跑通。</td></tr>',
    '<tr><td colspan="4">本窗口无相关更新</td></tr>'
  );
  const r = verifyBrief(html, { today: "2026-09-18" });
  assert.deepEqual(r.errors, []);
});

test("custom scope does not require the default roster", () => {
  const r = verifyBrief(
    makeBrief({
      tools: "cursor",
      customScope: true,
      pool: '<tr data-tool="cursor" data-status="update" data-date="2026-09-16"><td>Cursor</td></tr>',
    }),
    { today: "2026-09-18" }
  );
  assert.deepEqual(r.errors, []);
});

test("narrow roster without data-custom-scope fails", () => {
  const r = verifyBrief(
    makeBrief({
      tools: "cursor",
      pool: '<tr data-tool="cursor" data-status="update" data-date="2026-09-16"><td>Cursor</td></tr>',
    }),
    { today: "2026-09-18" }
  );
  assert.ok(r.errors.some((e) => e.includes("data-custom-scope")));
});

test("custom scope rejects tools outside data-tools", () => {
  const r = verifyBrief(
    makeBrief({
      tools: "cursor",
      customScope: true,
      pool: `<tr data-tool="cursor" data-status="update" data-date="2026-09-16"><td>Cursor</td></tr>
             <tr data-tool="aider" data-status="none"><td>Aider</td></tr>`,
    }),
    { today: "2026-09-18" }
  );
  assert.ok(r.errors.some((e) => e.includes("不在 data-tools")));
});

test("custom scope must list ids in the visible sentence", () => {
  const r = verifyBrief(
    makeBrief({
      tools: "cursor",
      customScope: true,
      scopeText: "覆盖窗口：2026-09-12 至 2026-09-18",
      pool: '<tr data-tool="cursor" data-status="update" data-date="2026-09-16"><td>Cursor</td></tr>',
    }),
    { today: "2026-09-18" }
  );
  assert.ok(r.errors.some((e) => e.includes("可见范围未列出")));
});

test("earlier pool row is validated, not replaced by a later row", () => {
  const hidden = '<tr data-tool="cursor" data-status="update" data-date="2026-08-01"><td>cursor</td></tr>';
  const r = verifyBrief(makeBrief({ pool: hidden + poolRows() }), { today: "2026-09-18" });
  assert.ok(r.errors.some((e) => e.includes("data-latest")));
});

test("three out-of-window rows with unique data-latest pass", () => {
  const three = [1, 2, 3]
    .map(
      (n, i) =>
        `<tr data-tool="cursor" data-status="update" data-date="2026-08-0${i + 1}" data-latest="${n}"><td>cursor</td></tr>`
    )
    .join("");
  const r = verifyBrief(makeBrief({ pool: three + withoutTool(poolRows(), "cursor") }), {
    today: "2026-09-18",
  });
  assert.deepEqual(r.errors, []);
});

test("a fourth out-of-window row fails", () => {
  const four = [1, 2, 3, 1]
    .map(
      (n, i) =>
        `<tr data-tool="cursor" data-status="update" data-date="2026-08-0${i + 1}" data-latest="${n}"><td>cursor</td></tr>`
    )
    .join("");
  const r = verifyBrief(makeBrief({ pool: four + withoutTool(poolRows(), "cursor") }), {
    today: "2026-09-18",
  });
  assert.ok(r.errors.some((e) => e.includes("超过 3")));
});

test("duplicate data-latest fails", () => {
  const dup = [1, 2]
    .map(
      (i) =>
        `<tr data-tool="cursor" data-status="update" data-date="2026-08-0${i}" data-latest="1"><td>cursor</td></tr>`
    )
    .join("");
  const r = verifyBrief(makeBrief({ pool: dup + withoutTool(poolRows(), "cursor") }), {
    today: "2026-09-18",
  });
  assert.ok(r.errors.some((e) => e.includes("data-latest") && e.includes("重复")));
});

test("degrade instruction text does not satisfy the attribute", () => {
  const r = verifyBrief(
    makeBrief({
      pool: poolRows({ aider: { status: "skipped" } }),
      leak: '<p><code>data-degrade="1"</code></p>',
    }),
    { today: "2026-09-18" }
  );
  assert.ok(r.errors.some((e) => e.includes("data-degrade")));
});

test("missing theme contract fails", () => {
  const r = verifyBrief(makeBrief({ theme: false }), { today: "2026-09-18" });
  assert.ok(r.errors.some((e) => e.includes("主题")));
});

test("CLI rejects missing file", () => {
  const run = spawnSync(process.execPath, [cli], { encoding: "utf8" });
  assert.equal(run.status, 2);
});

test("CLI on a temp valid file exits 0", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "brief-"));
  const file = path.join(dir, "ok.html");
  fs.writeFileSync(file, makeBrief());
  const run = spawnSync(process.execPath, [cli, file, "--today", "2026-09-18"], {
    encoding: "utf8",
  });
  assert.equal(run.status, 0, run.stderr + run.stdout);
});

test("delivered gate rejects the raw skeleton", async () => {
  if (!fs.existsSync(skeleton)) {
    throw new Error("missing report-skeleton.html");
  }
  const r = await verifyFile(skeleton, { today: "2026-09-18" });
  assert.ok(r.errors.some((e) => e.includes("占位") || e.includes("data-placeholder")));
});

test("skeleton structure passes once placeholder copy is removed", () => {
  let html = fs.readFileSync(skeleton, "utf8");
  html = html.replace(/\sdata-placeholder="1"/, "");
  html = html.replaceAll("占位", "条目");
  assert.ok(!html.includes("占位"));
  assert.ok(!/<html\b[^>]*data-placeholder="1"/i.test(html));
  const r = verifyBrief(html, { today: "2026-09-18" });
  assert.deepEqual(r.errors, []);
});

test("skeleton pool tools match TOOL_TIERS order", () => {
  const html = fs.readFileSync(skeleton, "utf8");
  const pool = html.match(/data-section="pool"[\s\S]*?<\/section>/)?.[0] ?? "";
  const ids = [...pool.matchAll(/data-tool="([^"]+)"/g)].map((m) => m[1]);
  assert.deepEqual(ids, ALL_TOOLS.map((t) => t.id));
});
