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

function sections(extra = "") {
  return REQUIRED_SECTIONS.map((id) => {
    if (id === "pool") {
      return `<section data-section="pool"><table>${extra || poolRows()}</table></section>`;
    }
    if (id === "sources") {
      return `<section data-section="sources"><a href="https://cursor.com/changelog">Cursor changelog</a></section>`;
    }
    return `<section data-section="${id}"></section>`;
  }).join("");
}

export function makeBrief(opts = {}) {
  const lang = opts.lang ?? "zh-CN";
  const start = opts.start ?? "2026-09-11";
  const end = opts.end ?? "2026-09-18";
  const degrade = opts.degrade ? ` data-degrade="1"` : "";
  const placeholder = opts.placeholder ? ` data-placeholder="1"` : "";
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
<p class="rule scope" data-window-start="${start}" data-window-end="${end}">窗口</p>
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

test("placeholder is warn unless --strict", () => {
  const html = makeBrief({ placeholder: true });
  const soft = verifyBrief(html, { today: "2026-09-18" });
  assert.deepEqual(soft.errors, []);
  assert.ok(soft.warns.some((w) => w.includes("placeholder")));
  const hard = verifyBrief(html, { today: "2026-09-18", strict: true });
  assert.ok(hard.errors.some((e) => e.includes("placeholder")));
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

test("skeleton passes structural gate (warn on placeholder)", async () => {
  if (!fs.existsSync(skeleton)) {
    throw new Error("missing report-skeleton.html");
  }
  const r = await verifyFile(skeleton, { today: "2026-09-18" });
  assert.deepEqual(r.errors, []);
  assert.ok(r.warns.some((w) => w.includes("placeholder")));
});
