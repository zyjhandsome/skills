import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

/** @param {string} rel */
function read(rel) {
  return readFileSync(join(ROOT, rel), "utf8");
}

const spec = read("references/spec-template.md");
for (const heading of [
  "## ADDED Requirements",
  "## MODIFIED Requirements",
  "## REMOVED Requirements",
  "### Requirement:",
  "#### Scenario:",
  "**WHEN**",
  "**THEN**",
  "MUST",
  "skip_specs: true",
  "**Reason**",
  "**Migration**",
]) {
  assert.ok(spec.includes(heading), `spec template missing ${heading}`);
}
for (const heading of ["## 需求", "### 需求：", "#### 场景：", "## 验收矩阵", "#### 失败行为"]) {
  assert.ok(!spec.includes(heading), `spec template still has non-OpenSpec heading ${heading}`);
}
const adapter = read("references/openspec-adapter.md");
assert.ok(!adapter.includes("/opsx-"), "adapter must not list retired /opsx-* commands");
const createRow = adapter.split("\n").find((line) => line.startsWith("| `create_change`"));
assert.ok(createRow && !createRow.includes("propose"), "create_change must not resolve to propose");
for (const text of [
  "openspec new change",
  "openspec instructions",
  "openspec list --specs",
  "skip_specs",
  "retire_capabilities",
  "items[].valid",
]) {
  assert.ok(adapter.includes(text), `adapter missing ${text}`);
}
for (const op of [
  "initialize_repo",
  "create_change",
  "inspect_change",
  "continue_artifacts",
  "apply_tasks",
  "validate_structure",
  "verify_coherence",
  "archive_change",
]) {
  assert.ok(adapter.includes("`" + op + "`"), `adapter dropped operation ${op}`);
}
assert.ok(
  !read("SKILL.md").includes("one Requirement + Scenario) — do not expand"),
  "Frame must not tell Quick to invent a minimal spec unconditionally"
);
console.log("PASS: delta spec template and adapter match OpenSpec 2.1.1");
