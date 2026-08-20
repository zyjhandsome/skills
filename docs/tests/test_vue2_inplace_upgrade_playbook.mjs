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
  "Wave 5  独立功能验证",
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
assert.ok(playbook.includes("单一模型"), "inplace playbook must run a single model end to end without naming one");
assert.ok(playbook.includes("不按波换模型"), "inplace playbook must forbid per-wave model switching");
const vuePatchPins = [...new Set([...playbook.matchAll(/\b3\.5\.\d+\b/g)].map((match) => match[0]))];
assert.ok(vuePatchPins.length <= 1, `playbook must carry at most one Vue patch pin, found: ${vuePatchPins.join(", ")}`);
if (vuePatchPins.length === 1) {
  assert.ok(playbook.includes(`target_vue_version = ${vuePatchPins[0]}`), "a pinned Vue patch is only allowed as the target_vue_version default");
  assert.ok(/registry[\s\S]{0,40}可解析/.test(playbook), "the pinned default must still be registry-validated in Wave 1 before it reaches CONFIG");
}
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
const wave4 = section(playbook, "## 5. Wave 4", "## 6. Wave 5");
const wave5 = section(playbook, "## 6. Wave 5", "## 7. 失败回流");

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
assert.ok(wave4.includes("Delivery verified ≠ 仓内 verified"), "Wave 4 must not treat Delivery verified as in-repo verified");
assert.ok(wave4.includes("下一步 Wave 5"), "Wave 4 must stop for independent functional verification");
assert.ok(wave4.includes("G9"), "Wave 4 must close visual via Delivery G9");

assert.ok(wave5.includes("显式使用 delivery-execute-verify"), "Wave 5 must reuse Execute in verify-only mode");
assert.ok(wave5.includes("不得修改应用代码"), "Wave 5 must remain application-code read-only");
assert.ok(wave5.includes("干净") && wave5.includes("dev/preview"), "Wave 5 must start a clean runtime rather than reuse Wave 4 processes");
assert.ok(wave5.includes("named_validations"), "Wave 5 must re-run analysis named validations");
assert.ok(wave5.includes("仓内 verified ≠ 生产完成"), "Wave 5 must not claim production complete");
assert.ok(wave5.includes("不要改代码") || wave5.includes("不要在本波修复"), "Wave 5 must backflow defects instead of fixing them");
assert.ok(wave5.includes("回 Wave 4"), "Wave 5 implementation/G9 defects must return to Execute");

/**
 * @param {string} src
 */
function fence(src) {
  const match = src.match(/```text\r?\n([\s\S]*?)\r?\n```/);
  assert.ok(match, "prompt fence is missing");
  return match[1];
}

const header = section(playbook, "### 1.2", "### 1.3");
assert.ok(header.includes("仅 Wave 4"), "header must restrict application-code mutation to Wave 4");
assert.ok(header.includes("仅 Wave 5"), "header must defer in-repo verified to Wave 5");
assert.ok(header.includes("alignment_backflow") || header.includes("失败回流最小字段"), "header must carry backflow keys");
assert.ok(header.includes("仓内 verified"), "header must carry the in-repo verified gate");
assert.ok(
  header.includes("OUTPUT_DIR = ANALYSIS_ROOT = <EVIDENCE_ROOT>/vue2-to-vue3-upgrade"),
  "header must default analysis output under the OpenSpec change evidence dir"
);
assert.ok(
  !header.includes("OUTPUT_DIR = <workspace>/.vue2-to-vue3-upgrade-analysis"),
  "header must not default analysis output to the workspace-root analysis dir"
);
assert.ok(header.includes("不要复述"), "header must tell wave blocks not to restate shared protocol");

const headerFences = [...header.matchAll(/```text\r?\n([\s\S]*?)\r?\n```/g)].map((m) => m[1]);
assert.equal(headerFences.length, 2, "header must split every-wave vs Wave 2-5 append");
assert.ok(!headerFences[0].includes("search_graph"), "every-wave header must not include Memory protocol");
assert.ok(headerFences[1].includes("search_graph"), "Wave 2-5 append must include Memory protocol");
assert.ok(!headerFences[0].includes("不要让 vue2 分析 Skill 改代码"), "Wave 1 must not be told not to create the decision packet");

const inplaceWaves = [
  ["Wave 1", wave1],
  ["Wave 2", wave2],
  ["Wave 3", wave3],
  ["Wave 4", wave4],
  ["Wave 5", wave5],
];
for (const [name, wave] of inplaceWaves) {
  assert.ok(fence(wave).includes("应已存在"), `${name} prompt must declare required upstream artifacts`);
}

assert.ok(wave1.includes("confirm:output-dir"), "Wave 1 must suppress the analysis skill output-dir confirm prompt");
assert.ok(wave1.includes("evidence/vue2-to-vue3-upgrade"), "Wave 1 must write analysis under the change evidence dir");
assert.ok(wave1.includes("不写 OpenSpec 状态") || wave1.includes("不 init OpenSpec"), "Wave 1 must not write OpenSpec state");
assert.ok(wave2.includes("同一 CHANGE_ID") || wave2.includes("不要另建 change"), "Wave 2 must recover the Wave 1 change directory");
assert.ok(wave4.includes("frozen install"), "Wave 4 must state lockfile-safe install");
assert.ok(wave4.includes("Codebase Memory"), "Wave 4 must refresh the graph before fresh verification");

const COMPOSITION_MARKER = "Composition API 全仓重写：另立项，本次不评估工作量";
const wave1Prompt = fence(wave1);
const wave2Prompt = fence(wave2);
const wave3Prompt = fence(wave3);
const wave4Prompt = fence(wave4);
const wave5Prompt = fence(wave5);
assert.ok(wave1Prompt.includes("3. 推荐迁移路径"), "Wave 1 must name the analysis report H2, not a playbook section number");
assert.ok(wave1Prompt.includes(COMPOSITION_MARKER), "Wave 1 must use the analysis validator's exact Composition marker");
assert.ok(!wave1Prompt.includes("写进"), "Wave 1 must not insert author notes into the Composition marker");
assert.ok(!wave1Prompt.includes("search_graph"), "Wave 1 paste must not include Memory protocol");
assert.ok(!wave1Prompt.includes("仓内 verified"), "Wave 1 paste must not include the verified checklist");
assert.ok(!wave1Prompt.includes("vue2-page-migration-playbook.md"), "Wave 1 must not require the sibling playbook as input");
assert.ok(!wave2Prompt.includes("vue2-page-migration-playbook.md"), "Wave 2 must not require the sibling playbook as input");
assert.ok(wave1Prompt.includes("不得加载其他剧本") || wave1Prompt.includes("不要加载其他剧本"), "Wave 1 host-port stop must stay inside this playbook");
assert.ok(wave2Prompt.includes("不要加载其他剧本"), "Wave 2 host-port stop must stay inside this playbook");
assert.ok(!wave2Prompt.includes("A→B 剧本"), "Wave 2 must not dangle to an unpasted playbook nickname");
assert.ok(!wave2Prompt.includes("改走"), "Wave 2 must stop, not redirect to another document");
assert.ok(!wave2Prompt.includes("点名章节"), "Wave 2 must name the report file instead of 点名章节");
assert.ok(wave2Prompt.includes("vue2-to-vue3-upgrade-report.md"), "Wave 2 must name the analysis report file");
assert.ok(wave3Prompt.includes("decision-records"), "Wave 3 must name the decision-records directory");
assert.ok(!wave3Prompt.includes("点名 decision-records"), "Wave 3 must not say 点名 decision-records");
assert.ok(wave4Prompt.includes("index_repository"), "Wave 4 must name index_repository instead of 按 Execute Skill");
assert.ok(!wave4Prompt.includes("仓内 verified ≠ 生产完成"), "Wave 4 paste must not claim in-repo verified");
assert.ok(wave5Prompt.includes("named_validations"), "Wave 5 paste must re-run named_validations");
assert.ok(wave5Prompt.includes("干净"), "Wave 5 paste must require a clean runtime");
assert.ok(!wave5Prompt.includes("vue2-page-migration-playbook.md"), "Wave 5 must not require the sibling playbook as input");
assert.ok(!wave5Prompt.includes("A→B 剧本"), "Wave 5 must not dangle to an unpasted playbook nickname");
for (const [name, wave] of inplaceWaves) {
  assert.ok(!fence(wave).includes("§"), `${name} paste block must not use bare § (unpasted playbook/report section numbers)`);
  assert.ok(
    !fence(wave).includes("vue2-page-migration-playbook.md"),
    `${name} paste block must not require the sibling playbook as input`
  );
}

// Cross-contract facts the playbook references must stay real upstream.
assert.ok(wave2Prompt.includes("lockfile_digests"), "Wave 2 staleness check must use the inventory lockfile_digests producer, not an invented lock digest");
assert.ok(wave2Prompt.includes("profile_inventory.py"), "Wave 2 staleness check must name the analysis script path");
assert.ok(wave2Prompt.includes("5 个唯一状态"), "Wave 2 must top visual states up to the downstream G9 floor of five before spec approval");
assert.ok(wave3Prompt.includes("truncated"), "Wave 3 interaction assertions must guard against a truncated inventory scan");
assert.ok(wave3Prompt.includes("worktree"), "Wave 3 must plan the rollback-rehearsal worktree authorization and fallback");
assert.ok(wave4Prompt.includes("worktree"), "Wave 4 rollback rehearsal must carry the worktree authorization/fallback rules");
assert.ok(wave5Prompt.includes("inrepo-verification.md"), "Wave 5 must persist the in-repo verified verdict as an artifact");
assert.ok(wave5Prompt.includes("handoff-wave4.json"), "Wave 5 must archive the Wave 4 handoff before overwriting handoff.json");

// The header checklist is authoritative; section 8 must not diverge from it again.
const section8 = playbook.slice(playbook.indexOf("## 8. 完成判定"));
for (const needle of ["回滚演练", "console-evidence", "inrepo-verification.md", "交互断言"]) {
  assert.ok(headerFences[1].includes(needle), `header verified checklist must include ${needle}`);
  assert.ok(section8.includes(needle), `section 8 verified checklist must include ${needle}`);
}
const backflow = section(playbook, "## 7. 失败回流", "## 8. 完成判定");
assert.ok(backflow.includes("连续 2 次 G9 fail"), "backflow table must route the double G9 failure escalation to Wave 2");

assert.ok(usage.includes("vue2-to-vue3-inplace-upgrade-playbook.md"), "usage must point at the inplace playbook");
assert.ok(usage.includes("openspec/changes/vue2-to-vue3-inplace-<SLUG>/evidence/vue2-to-vue3-upgrade"), "usage must document the playbook analysis path under the change dir");
assert.ok(usage.includes("batch_implementation_gate"), "usage must explain the analysis gate");
assert.ok(usage.includes("proceed:path:compat-big-bang"), "usage must show verbatim path tokens");
assert.ok(usage.includes("implementation_readiness"), "usage must keep implementation_readiness unset");
assert.ok(!usage.includes("开始实施并改 package.json"), "usage must not authorize implementation");

assert.ok(readme.includes("docs/vue2-to-vue3-inplace-upgrade-playbook.md"), "README must link the inplace playbook");
assert.ok(readme.includes("docs/vue2-to-vue3-upgrade-impact-analysis-usage.md"), "README must link the analysis usage doc");
assert.ok(existsSync(AB_PLAYBOOK), "A→B playbook should still exist as the host-port redirect target");

console.log("PASS: vue2 in-place upgrade playbook and usage keep analysis independent and High-only delivery");
