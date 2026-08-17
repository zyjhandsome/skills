#!/usr/bin/env node
// @ts-check

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const DOCS = resolve(HERE, "..");
const ROOT = resolve(DOCS, "..");
const PLAYBOOK = resolve(DOCS, "vue2-to-vue3-inplace-upgrade-playbook.md");
const USAGE = resolve(DOCS, "vue2-to-vue3-upgrade-impact-analysis-usage.md");
const README = resolve(ROOT, "README.md");
const AB_PLAYBOOK = resolve(DOCS, "vue2-page-migration-playbook.md");

const read = (path) => readFileSync(path, "utf8");

assert.ok(existsSync(PLAYBOOK), "inplace playbook is missing");
assert.ok(existsSync(USAGE), "vue2 analysis usage doc is missing");

const playbook = read(PLAYBOOK);
const usage = read(USAGE);
const readme = read(README);
const corpus = `${playbook}\n${usage}\n${readme}`;

assert.ok(playbook.includes("这不是 Skill") || playbook.includes("用户粘贴剧本"), "playbook must not pose as a Skill");
assert.ok(!/^---\r?\nname:/m.test(playbook), "playbook must not have Skill frontmatter");
assert.ok(!/^---\r?\nname:/m.test(usage), "usage must not have Skill frontmatter");

const orderNeedles = [
  "Wave 1  vue2 分析（只出决策包）",
  "Wave 2  Frame 规格批准",
  "Wave 3  Delivery Plan go",
  "Wave 4  Delivery Execute",
];
let lastIndex = -1;
for (const needle of orderNeedles) {
  const index = playbook.indexOf(needle);
  assert.ok(index !== -1, `playbook missing wave order line: ${needle}`);
  assert.ok(index > lastIndex, `playbook wave order is out of sequence at: ${needle}`);
  lastIndex = index;
}

assert.ok(playbook.includes("固定 High"), "playbook must state the High route");
assert.ok(playbook.includes("会话停点覆盖"), "playbook must enable the Delivery session-stop overlay");
assert.ok(playbook.includes("唯一应用代码 mutation owner") || playbook.includes("唯一代码 mutation owner"), "playbook must name Delivery as the sole code mutation owner");
assert.ok(playbook.includes("search_graph") && playbook.includes("trace_path"), "playbook must default code discovery to Codebase Memory MCP");
assert.ok(playbook.includes("get_code_snippet") && playbook.includes("query_graph"), "playbook must state the graph discovery order");
assert.ok(playbook.includes("不得因图谱没有 Route 节点"), "empty route graph results must not prove that routes are absent");
assert.ok(playbook.includes("baseline_state_ids"), "playbook must cite the G9 external-claim whitelist");
assert.ok(playbook.includes("delivery-visual-evidence/v1"), "playbook must use Delivery G9 schema");
assert.ok(playbook.includes("Name, never run"), "playbook must keep analysis recipes unexecuted until Execute");
assert.ok(playbook.includes("Composition API"), "playbook must keep Composition rewrite out of this change");
assert.ok(playbook.includes("proceed:path:"), "playbook must require verbatim path tokens");
assert.ok(playbook.includes("vue2-page-migration-playbook.md"), "host-port must redirect to the A→B playbook");

assert.ok(!/可(?:偏|走)?\s*Quick|否则可\s*Quick|Quick\s*直接\s*execute/i.test(corpus), "docs must not offer a Quick bypass");
assert.ok(!/mode=execute|migrate execute/i.test(playbook), "inplace playbook must not invoke migrate execute");
assert.ok(!playbook.includes("expected_model="), "inplace playbook must stay host-neutral (no Claude Code model pins)");
assert.ok(playbook.includes("GLM 5.2"), "inplace playbook may run entirely on GLM 5.2");
assert.ok(!playbook.includes("frontend-ui-stack-visual-parity"), "inplace playbook must not mention the visual-parity skill");

/**
 * @param {string} src
 * @param {string} start
 * @param {string} end
 */
function section(src, start, end) {
  const i = src.indexOf(start);
  const j = src.indexOf(end);
  assert.ok(i !== -1 && j > i, `missing section ${start} .. ${end}`);
  return src.slice(i, j);
}

const wave1 = section(playbook, "## 2. Wave 1", "## 3. Wave 2");
const wave2 = section(playbook, "## 3. Wave 2", "## 4. Wave 3");
const wave3 = section(playbook, "## 4. Wave 3", "## 5. Wave 4");
const wave4 = section(playbook, "## 5. Wave 4", "## 6. 失败回流");

assert.ok(wave1.includes("显式使用 vue2-to-vue3-upgrade-impact-analysis"), "Wave 1 must invoke the analysis skill");
assert.ok(wave1.includes("不改代码") && wave1.includes("不跑 codemod"), "Wave 1 must remain analysis-only");
assert.ok(wave1.includes("不得填写其他 Skill 名称"), "Wave 1 reports must stay skill-name free");
assert.ok(wave1.includes("不要加载或执行下一个 Skill") || playbook.includes("不要加载或执行下一个 Skill"), "session-stop must forbid same-session relay");
assert.ok(
  wave1.includes("host-port-direct") && wave1.includes("停止本剧本"),
  "Wave 1 must abort in-place when host-port is recommended"
);
assert.ok(!wave1.includes("显式使用 delivery-frame-spec"), "Wave 1 must not weld Frame into analysis");
assert.ok(!wave1.includes("OpenSpec 已初始化"), "Wave 1 must not require OpenSpec");

assert.ok(wave2.includes("显式使用 delivery-frame-spec"), "Wave 2 must invoke Frame");
assert.ok(wave2.includes("禁止 Quick") || wave2.includes("固定 High"), "Wave 2 must keep High");
assert.ok(wave2.includes("external_artifacts"), "Wave 2 must cite the analysis bundle as external artifacts");
assert.ok(playbook.includes("不要调用 migrate-vue2-pages-to-vue3-host"), "playbook must not invoke migrate");
assert.ok(wave2.includes("quality_profiles.visual"), "Wave 2 must recompute visual from evidence");

assert.ok(wave3.includes("显式使用 delivery-plan-tasks"), "Wave 3 must invoke Plan");
assert.ok(wave3.includes("基线捕获发生在升级之前") || wave3.includes("基线捕获发生在"), "Wave 3 must capture visual baseline before upgrade");
assert.ok(wave3.includes("本波不跑") || wave3.includes("仍不执行"), "Wave 3 must not run named recipes");

assert.ok(wave4.includes("显式使用 delivery-execute-verify"), "Wave 4 must invoke Execute");
assert.ok(wave4.includes("唯一应用代码 mutation owner"), "Wave 4 must be the sole mutation owner");
assert.ok(wave4.includes("不要 archive"), "Wave 4 must defer OpenSpec archive");
assert.ok(wave4.includes("verified ≠ 生产完成") || wave4.includes("仓内 verified ≠ 生产完成"), "Wave 4 must not claim production complete");
assert.ok(wave4.includes("G9"), "Wave 4 must close visual via Delivery G9");

assert.ok(usage.includes("vue2-to-vue3-inplace-upgrade-playbook.md"), "usage must point at the inplace playbook");
assert.ok(usage.includes("batch_implementation_gate"), "usage must explain the analysis gate");
assert.ok(usage.includes("proceed:path:compat-big-bang"), "usage must show verbatim path tokens");
assert.ok(usage.includes("implementation_readiness"), "usage must keep implementation_readiness unset");
assert.ok(!usage.includes("开始实施并改 package.json"), "usage must not authorize implementation");

assert.ok(readme.includes("docs/vue2-to-vue3-inplace-upgrade-playbook.md"), "README must link the inplace playbook");
assert.ok(readme.includes("docs/vue2-to-vue3-upgrade-impact-analysis-usage.md"), "README must link the analysis usage doc");
assert.ok(existsSync(AB_PLAYBOOK), "A→B playbook should still exist as the host-port redirect target");

console.log("PASS: vue2 in-place upgrade playbook and usage keep analysis independent and High-only delivery");
