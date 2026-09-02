#!/usr/bin/env node
// @ts-check

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const DOCS = resolve(HERE, "..");
const PLAYBOOK = resolve(DOCS, "angularjs-to-vue3-host-migration-playbook.md");
const USAGE = resolve(DOCS, "angularjs-to-vue3-host-migration-usage.md");
const APPENDIX = resolve(DOCS, "angularjs-host-migration-hiapm-appendix.md");
const SKILL_ID = "angularjs-to-vue3-host-migration";

const read = (path) => readFileSync(path, "utf8");

assert.ok(existsSync(PLAYBOOK), "AngularJS host migration playbook is missing");
assert.ok(existsSync(USAGE), "AngularJS host migration usage doc is missing");
assert.ok(existsSync(APPENDIX), "hiapm appendix is missing");

const playbook = read(PLAYBOOK);
const usage = read(USAGE);
const appendix = read(APPENDIX);

assert.ok(playbook.includes("这不是 Skill"), "playbook must not pose as a Skill");
assert.ok(!/^---\r?\nname:/m.test(playbook), "playbook must not have Skill frontmatter");
assert.ok(playbook.includes(SKILL_ID), "playbook must use the complete skill id");
assert.ok(!playbook.includes("angularjs-to-vue3-migration`"), "playbook must not use the shortened skill id");
assert.ok(playbook.includes("canonical_skill_id"), "session header must pin the canonical skill id");

const orderNeedles = [
  "Wave 1  建 change（无规格闸门）",
  "Wave 2  angularjs assess",
  "Wave 3  angularjs design",
  "Wave 4  Delivery Frame 规格批准",
  "Wave 5  Delivery Plan + 实施 go",
  "Wave 6  Delivery Execute + Fresh Verification",
  "Wave 7  angularjs verify",
];
let lastIndex = -1;
for (const needle of orderNeedles) {
  const index = playbook.indexOf(needle);
  assert.ok(index !== -1, `playbook missing wave order line: ${needle}`);
  assert.ok(index > lastIndex, `playbook wave order is out of sequence at: ${needle}`);
  lastIndex = index;
}

function section(src, start, end) {
  const i = src.indexOf(start);
  const j = src.indexOf(end);
  assert.ok(i !== -1 && j > i, `missing section ${start} .. ${end}`);
  return src.slice(i, j);
}

function fence(src) {
  const match = src.match(/```text\r?\n([\s\S]*?)\r?\n```/);
  assert.ok(match, "prompt fence is missing");
  return match[1];
}

const header = section(playbook, "### 1.2", "### 1.3");
const wave1 = section(playbook, "## 2. Wave 1", "## 3. Wave 2");
const wave2 = section(playbook, "## 3. Wave 2", "## 4. Wave 3");
const wave3 = section(playbook, "## 4. Wave 3", "## 5. Wave 4");
const wave4 = section(playbook, "## 5. Wave 4", "## 6. Wave 5");
const wave5 = section(playbook, "## 6. Wave 5", "## 7. Wave 4R");
const wave4r = section(playbook, "## 7. Wave 4R", "## 8. Wave 6");
const wave6 = section(playbook, "## 8. Wave 6", "## 9. Wave 7");
const wave7 = section(playbook, "## 9. Wave 7", "## 10. 失败回流");

for (const [name, wave] of [
  ["Wave 1", wave1],
  ["Wave 2", wave2],
  ["Wave 3", wave3],
  ["Wave 4", wave4],
  ["Wave 5", wave5],
  ["Wave 4R", wave4r],
  ["Wave 6", wave6],
  ["Wave 7", wave7],
]) {
  assert.ok(fence(wave).includes("应已存在"), `${name} prompt must declare upstream artifacts`);
}

assert.ok(header.includes("<DOMAIN_ROOT>"), "header must name the domain evidence root");
assert.ok(header.includes("<FRESHNESS_MANIFEST>"), "header must name the freshness manifest");
assert.ok(header.includes("_live-eval"), "header must reject live-eval as authority");
assert.ok(header.includes("唯一状态源"), "header must pin one state source");
assert.ok(header.includes("不得缩写"), "header must forbid shortened skill ids");

assert.ok(fence(wave1).includes("<FRESHNESS_MANIFEST>"), "Wave 1 must initialize freshness manifest");
assert.ok(fence(wave2).includes("artifact_level=baseline-only"), "Wave 2 must mark generator output baseline-only");
assert.ok(fence(wave3).includes("人填 design-ready"), "Wave 3 must require human-filled design-ready evidence");
assert.ok(fence(wave4).includes("人填 design-ready"), "Wave 4 must bind the filled packet, not a skeleton");
assert.ok(fence(wave5).includes("denied") && fence(wave5).includes("重新进入 Wave 5"), "Wave 5 must define go reopen");
assert.ok(fence(wave4r).includes("不得把两次问询压成一次"), "4R must keep two approval gates");
assert.ok(fence(wave4r).includes("design-scope 是 new-landing"), "4R must reject new-landing");
assert.ok(fence(wave6).includes("不要调用 angularjs-to-vue3-host-migration"), "Wave 6 must not load the domain skill");
assert.ok(fence(wave6).includes("lint 基线"), "Wave 6 must explain lint baseline fallback");
assert.ok(fence(wave6).includes("dev proxy") && fence(wave6).includes("public/"), "Wave 6 must check proxy/public conflicts");
assert.ok(fence(wave7).includes("Delivery verified_with_residuals"), "Wave 7 must reject residual verification as complete");

assert.ok(playbook.includes("附录"), "playbook must point project-specific traps to an appendix");
assert.ok(!playbook.includes("top_bar.do"), "hiapm-specific URLs must not stay in the generic paste block");
assert.ok(appendix.includes("top_bar.do"), "appendix must carry hiapm-specific traps");
assert.ok(appendix.includes("taskReport"), "appendix must carry report traps");
assert.ok(usage.includes("angularjs-to-vue3-host-migration-playbook.md"), "usage must point to the playbook");
assert.ok(usage.includes(SKILL_ID), "usage must pin the complete skill id");
assert.ok(usage.includes("_live-eval"), "usage must warn that live-eval output is not authoritative");

console.log("PASS: AngularJS host migration playbook keeps skill id, gates, and state authority pinned");
