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

assert.ok(routing.includes("把代码或页面跨仓库/跨运行时迁入已有系统"), "routing table must list cross-boundary code moves as a migration red line");
assert.ok(routing.includes("不只数据 schema 迁移才算"), "migration red line must not collapse to data-schema migration");
assert.ok(routing.includes("调用方车道下限"), "routing must honor a caller-pinned route floor");
assert.ok(frameSkill.includes("caller-pinned High floor"), "Frame High trigger must name the caller-pinned floor");
for (const token of ["host-port", "跨仓页面迁入", "iframe"]) {
  assert.ok(!routing.includes(token) && !frameSkill.includes(token), `routing must stay domain-neutral: ${token}`);
}

assert.ok(family.includes("会话停点覆盖"), "family contract must define the session-stop overlay");
assert.ok(family.includes("不要加载下一个 Skill") || family.includes("不要加载下一个"), "overlay signals must include the playbook stop phrase");
assert.ok(family.includes("建档停点覆盖"), "family contract must define the Frame scaffold-only overlay");
assert.ok(frameSkill.includes("建档停点覆盖"), "Frame must honor 建档停点覆盖");

for (const skill of FAMILY) {
  const text = readFileSync(join(ROOT, skill, "SKILL.md"), "utf8");
  assert.ok(text.includes("会话停点覆盖"), `${skill} must honor 会话停点覆盖 in the chain-relay rule`);
}

const readiness = readFileSync(join(ROOT, "delivery-plan-tasks", "references", "readiness-review.md"), "utf8");
assert.ok(readiness.includes("record-gate"), "readiness review must point the implementation go at record-gate");
assert.ok(!readiness.includes("批准人/日期"), "readiness review must not keep a second free-text approval record");
assert.ok(routing.includes("闸门记录块"), "routing must record gates in the proposal gate-record block");

console.log("PASS: cross-boundary code moves are a High red line; session-stop overlay is family-wide");
