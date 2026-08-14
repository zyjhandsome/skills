#!/usr/bin/env node
// @ts-check

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const TESTS_DIR = dirname(fileURLToPath(import.meta.url));
const FRAME = resolve(TESTS_DIR, "..");
const ROOT = resolve(FRAME, "..");
const FAMILY = ["delivery-explore", "delivery-frame-spec", "delivery-plan-tasks", "delivery-execute-verify"];

const routing = readFileSync(join(FRAME, "references", "routing-and-gates.md"), "utf8");
const family = readFileSync(join(FRAME, "references", "family-contract.md"), "utf8");
const frameSkill = readFileSync(join(FRAME, "SKILL.md"), "utf8");

assert.ok(routing.includes("跨仓把源仓页面原生迁入已有宿主"), "routing table must list cross-repo page host-port");
assert.ok(routing.includes("不得当成「只有数据 schema 迁移才算」") || routing.includes("不得当成"), "page host-port must not collapse to data-schema migration");
assert.ok(routing.includes("跨仓页面迁入"), "high-risk features must include cross-repo page host-port");
assert.ok(frameSkill.includes("cross-repo page host-port"), "Frame High trigger must name cross-repo page host-port");
assert.ok(!routing.includes("migrate-vue2-pages-to-vue3-host"), "routing must stay lifecycle-generic");
assert.ok(!routing.includes("vue2-to-vue3-upgrade-impact-analysis"), "routing must not name the Vue analysis skill");

assert.ok(family.includes("会话停点覆盖"), "family contract must define the session-stop overlay");
assert.ok(family.includes("不要加载下一个 Skill") || family.includes("不要加载下一个"), "overlay signals must include the playbook stop phrase");
assert.ok(family.includes("建档停点覆盖"), "family contract must define the Frame scaffold-only overlay");
assert.ok(frameSkill.includes("建档停点覆盖"), "Frame must honor 建档停点覆盖");

for (const skill of FAMILY) {
  const text = readFileSync(join(ROOT, skill, "SKILL.md"), "utf8");
  assert.ok(text.includes("会话停点覆盖"), `${skill} must honor 会话停点覆盖 in the chain-relay rule`);
}

console.log("PASS: cross-repo page host-port is a High red line; session-stop overlay is family-wide");
