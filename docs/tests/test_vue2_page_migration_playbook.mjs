#!/usr/bin/env node
// @ts-check

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const DOCS = resolve(HERE, "..");
const PLAYBOOK = resolve(DOCS, "vue2-page-migration-playbook.md");
const USAGE = resolve(DOCS, "vue2-pages-to-vue3-host-migration-delivery-usage.md");
const RETIRED_LATEST = resolve(DOCS, "vue2-page-migration-orchestration-latest.md");

const read = (path) => readFileSync(path, "utf8");

assert.ok(existsSync(PLAYBOOK), "playbook is missing");
assert.ok(existsSync(USAGE), "usage doc is missing");
assert.ok(!existsSync(RETIRED_LATEST), "retired latest orchestration file must be deleted");

const playbook = read(PLAYBOOK);
const usage = read(USAGE);
const corpus = `${playbook}\n${usage}`;

assert.ok(playbook.includes("这不是 Skill") || playbook.includes("用户粘贴剧本"), "playbook must not pose as a Skill");
assert.ok(!/^---\r?\nname:/m.test(playbook), "playbook must not have Skill frontmatter");

const orderNeedles = [
  "Wave 1  建 change（无规格闸门）",
  "Wave 2  migrate assess",
  "Wave 3  migrate design",
  "Wave 4  Frame 规格批准",
  "Wave 5  Delivery Plan go",
  "Wave 6  Delivery Execute",
  "Wave 7  migrate verify",
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
assert.ok(playbook.includes("唯一代码 mutation owner"), "playbook must name Delivery as the sole code mutation owner");
assert.ok(playbook.includes("source_revision + host_revision"), "implementation go must bind both repository revisions");
assert.ok(playbook.includes("search_graph") && playbook.includes("trace_path"), "playbook must default code discovery to Codebase Memory MCP");
assert.ok(playbook.includes("get_code_snippet") && playbook.includes("query_graph"), "playbook must state the graph discovery order");
assert.ok(playbook.includes("不得因图谱没有 Route 节点"), "empty route graph results must not prove that routes are absent");
assert.ok(playbook.includes("codebase-index-manifest.json"), "playbook must persist an index revision manifest");
assert.ok(playbook.includes("runtime-service-manifest.json"), "playbook must persist runtime and service evidence");
assert.ok(playbook.includes("用户先执行 `/status` 和 `/model`"), "the user must own Claude Code slash-command checks");
assert.ok(!playbook.includes("先用 /status 和 /model 确认"), "Wave prompts must not ask the model to execute slash commands");
assert.ok(playbook.includes("npm run dev，不是 npm run serve"), "the Vue2 reference command must use the repository-native dev script");
assert.ok(playbook.includes("preinstall 强制 pnpm，禁止 npm install 和 npm run serve"), "the Vue3 reference must forbid npm commands rejected by the repository");
assert.ok(playbook.includes("本波禁止规格闸门"), "Wave 1 must defer the specification gate");
assert.ok(playbook.includes("建档停点覆盖"), "Wave 1 must enable the Frame scaffold-only overlay");
assert.ok(playbook.includes("baseline_state_ids"), "playbook must cite the G9 external-claim whitelist");
assert.ok(!/可(?:偏|走)?\s*Quick|否则可\s*Quick|Quick\s*直接\s*execute/i.test(corpus), "docs must not offer a Quick bypass");
assert.ok(!/delivery-execute-verify\s*(?:↔|→).*migrate[^\n]*execute/i.test(corpus), "docs must not assign execution to both Delivery and migrate");
assert.ok(!/mode=execute|migrate execute/i.test(playbook), "playbook must not invoke migrate execute");

assert.ok(!/显式使用\s+frontend-dependency-upgrade-impact-analysis/.test(playbook), "playbook must not invoke dependency analysis");
assert.ok(!/显式使用\s+frontend-ui-stack-visual-parity/.test(playbook), "playbook must not invoke CSS repair");

assert.ok(usage.includes("vue2-page-migration-playbook.md"), "usage must point at the playbook");
assert.ok(usage.includes("已作废"), "usage must retire the conflicting sequence");
assert.ok(!usage.includes("](./vue2-page-migration-orchestration-latest.md)"), "usage must not link to the retired latest file");
assert.ok(usage.indexOf("已作废") < usage.indexOf("assess + design 先于建 change"), "retired assess-first order must sit in the obsolete section");

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

const wave2 = section(playbook, "## 3. Wave 2", "## 4. Wave 3");
const wave2Fence = wave2.match(/```text\r?\n([\s\S]*?)\r?\n```/);
assert.ok(wave2Fence, "Wave 2 prompt fence is missing");
const wave2Prompt = wave2Fence[1];
assert.ok(wave2Prompt.includes("visual_chain=unavailable"), "Wave 2 must name visual_chain=unavailable");
assert.ok(wave2Prompt.includes("blocked:visual-chain"), "Wave 2 must emit blocked:visual-chain");
assert.ok(wave2Prompt.includes("不得进入 Wave 3"), "Wave 2 must hard-stop Wave 3 when the visual chain is unavailable");
assert.ok(
  /仅当视觉处理链可用[\s\S]*下一步为 Wave 3/.test(wave2Prompt),
  "Wave 2 may name Wave 3 only after the visual chain and baseline are unblocked"
);
assert.ok(!playbook.includes("不要向用户索要参考截图"), "playbook must allow user-provided screenshots");
assert.ok(!playbook.includes("也不把用户粘贴图当视觉事实"), "user screenshots are an allowed image source, not banned as facts a priori");
assert.ok(playbook.includes("用户提供的") && playbook.includes("多状态截图"), "playbook must accept user-provided multi-state screenshots");
assert.ok(playbook.includes("不得因已有截图跳过检索"), "screenshots must not skip code retrieval");
assert.ok(playbook.includes("截图与代码矛盾时，以代码事实为准"), "code facts must win when screenshots contradict code");
assert.ok(wave2Prompt.includes("用户未提供覆盖这些") || wave2Prompt.includes("用户未提供覆盖所需状态"), "Wave 2 may freeze baseline images from user-provided running-A screenshots");
assert.ok(wave2Prompt.includes("截图与代码矛盾以代码为准") || wave2Prompt.includes("不能覆盖与代码矛盾"), "Wave 2 must keep code authoritative over screenshots");
assert.ok(wave2Prompt.includes("颜色以 A 代码"), "Wave 2 must take colors from A code, not from screenshots alone");
const wave3NextSentences = wave2Prompt
  .split(/[。\n]/)
  .map((line) => line.trim())
  .filter((line) => line.includes("下一步为 Wave 3"));
assert.ok(wave3NextSentences.length >= 1, "Wave 2 must still name the unblocked next wave");
assert.ok(
  wave3NextSentences.every((line) => line.includes("仅当") || line.includes("才说明")),
  "Wave 2 must not unconditionally send a blocked assess to Wave 3"
);

const wave3 = section(playbook, "## 4. Wave 3", "## 5. Wave 4");
assert.ok(
  wave3.includes("blocked:visual-chain") && /停止/.test(wave3),
  "Wave 3 must refuse a blocked:visual-chain assess packet"
);

const wave1 = section(playbook, "## 2. Wave 1", "## 3. Wave 2");
const wave4 = section(playbook, "## 5. Wave 4", "## 6. Wave 5");
const wave5 = section(playbook, "## 6. Wave 5", "## 7. Wave 6");
const wave6 = section(playbook, "## 7. Wave 6", "## 8. Wave 7");
const wave7 = section(playbook, "## 8. Wave 7", "## 9. 失败回流");
const expectedModels = [
  [wave1, "expected_model=GLM 5.2"],
  [wave2, "expected_model=Kimi K2.6"],
  [wave3, "expected_model=GLM 5.2"],
  [wave4, "expected_model=GLM 5.2"],
  [wave5, "expected_model=GLM 5.2"],
  [wave6, "expected_model=GLM 5.2"],
  [wave7, "expected_model=GLM 5.2"],
];
for (const [wave, expectedModel] of expectedModels) {
  assert.ok(wave.includes(expectedModel), `Wave prompt missing model marker: ${expectedModel}`);
}
assert.ok(
  playbook.includes("Agent 不得声称执行过 slash command") || playbook.includes("Agent 不执行 slash command"),
  "Wave prompt must not delegate slash commands to the model"
);
assert.ok(wave1.includes("index_repository") && wave1.includes("<INDEX_MANIFEST>"), "Wave 1 must establish graph indexes and the revision manifest");
assert.ok(wave2.includes("一次性副本") && wave2.includes("<RUNTIME_MANIFEST>"), "Wave 2 must isolate installs and record runtime services");
assert.ok(wave6.includes("重新 index_repository 索引 B"), "Wave 6 must rebuild the B graph after implementation");
assert.ok(wave7.includes("stale 图谱") && wave7.includes("启动干净 dev 服务"), "Wave 7 must reject stale graphs and use a fresh B service");

/**
 * @param {string} src
 */
function fence(src) {
  const match = src.match(/```text\r?\n([\s\S]*?)\r?\n```/);
  assert.ok(match, "prompt fence is missing");
  return match[1];
}

const header = section(playbook, "### 1.2", "### 1.3");
assert.ok(header.includes("仅 Wave 6"), "header must restrict application-code mutation to Wave 6");
assert.ok(header.includes("失败回流最小字段"), "header must carry backflow keys for independent sessions");
assert.ok(header.includes("页面升级迁移完成"), "header must carry the completion gate for Wave 7");
assert.ok(header.includes("用户提供的") && header.includes("多状态截图"), "session header must accept user-provided screenshots");
assert.ok(header.includes("不得因已有截图跳过检索"), "session header must require code retrieval even when screenshots exist");
assert.ok(header.includes("截图与代码矛盾时，以代码事实为准"), "session header must make code authoritative over screenshots");

const wavePrompts = [
  ["Wave 1", wave1],
  ["Wave 2", wave2],
  ["Wave 3", wave3],
  ["Wave 4", wave4],
  ["Wave 5", wave5],
  ["Wave 6", wave6],
  ["Wave 7", wave7],
];
for (const [name, wave] of wavePrompts) {
  assert.ok(fence(wave).includes("应已存在"), `${name} prompt must declare required upstream artifacts`);
}

assert.ok(!wave2Prompt.includes("按 1.4"), "Wave 2 must inline install rules instead of dangling to §1.4");
assert.ok(wave1.includes("initialize_repo"), "Wave 1 must recover uninitialized OpenSpec via initialize_repo");
assert.ok(fence(wave4).includes("design-ready"), "Wave 4 must refuse assess-only packets");
assert.ok(fence(wave5).includes("G1–G3") || fence(wave5).includes("G1-G3"), "Wave 5 must name readiness G-checks");
assert.ok(fence(wave6).includes("不能单独宣布整次迁移完成"), "Wave 6 paste block must not claim migration complete");
assert.ok(!fence(wave7).includes("本文完成条件"), "Wave 7 must not dangle to unpasted completion section");
assert.ok(fence(wave7).includes("通用头完成判定"), "Wave 7 must judge completion from the session header");
assert.ok(fence(wave7).includes("validate_runtime_evidence.mjs"), "Wave 7 must name the runtime validator");
assert.ok(fence(wave7).includes("validate_visual_evidence.mjs"), "Wave 7 must name the visual validator");
assert.ok(fence(wave7).includes("validate_domain_packet.mjs"), "Wave 7 must name the domain packet validator");
assert.ok(!fence(wave7).includes("三个验证器"), "Wave 7 must not dangle to unnamed validators");
assert.ok(fence(wave1).includes("缺什么"), "Wave 1 must name the Frame three-line report keys");
for (const [name, wave] of wavePrompts) {
  assert.ok(!fence(wave).includes("§"), `${name} paste block must not use bare §`);
  assert.ok(
    !fence(wave).includes("vue2-to-vue3-inplace-upgrade-playbook.md"),
    `${name} paste block must not require the sibling in-place playbook`
  );
}
assert.ok(fence(wave6).includes("packageManager"), "Wave 6 must take B install rules from the host repo, not a reference project");
assert.ok(!fence(wave6).includes("参考 B 禁止"), "Wave 6 must not cite unpasted §1.4 reference-project commands");

console.log("PASS: vue2 page migration playbook and usage share one High, Frame-after-design sequence");
