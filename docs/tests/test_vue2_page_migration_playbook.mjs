#!/usr/bin/env node
// @ts-check

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const DOCS = resolve(HERE, "..");
const PLAYBOOK = resolve(DOCS, "vue2-page-migration-playbook.md");
const USAGE = resolve(DOCS, "migrate-vue2-pages-to-vue3-host-delivery-usage.md");
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

console.log("PASS: vue2 page migration playbook and usage share one High, Frame-after-design sequence");
