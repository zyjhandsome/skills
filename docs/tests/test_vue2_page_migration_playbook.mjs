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

console.log("PASS: vue2 page migration playbook and usage share one High, Frame-after-design sequence");
