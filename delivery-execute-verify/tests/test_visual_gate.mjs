#!/usr/bin/env node
// @ts-check

import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { validateVisualEvidence } from "../scripts/validate_delivery_change.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const REVISION = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
const VISUAL_TEMPLATE = readFileSync(resolve(HERE, "..", "references", "delivery-visual-evidence-template.md"), "utf8");
const GATE_CHECKS = readFileSync(resolve(HERE, "..", "references", "artifact-gate-checks.md"), "utf8");
for (const claim of [
  "baseline_state_ids", "identity_route", "identity_marker", "comparison_boundary",
  "style_closure_status", "color_metrics", "typography_metrics", "icon_identity",
  "table_metrics", "rollback_fixture",
]) {
  assert.ok(VISUAL_TEMPLATE.includes(claim), `G9 template missing external claim ${claim}`);
  assert.ok(GATE_CHECKS.includes(claim), `G9 gate missing external claim ${claim}`);
}
assert.ok(VISUAL_TEMPLATE.includes("不能让 G9") || GATE_CHECKS.includes("不能替代 G9"), "external claims must not satisfy G9");

/** @param {string} path */
function digest(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

/** @param {string} sandbox @param {string} changeDir */
function buildReport(sandbox, changeDir) {
  const artifactDir = join(sandbox, "visual-artifacts");
  mkdirSync(artifactDir, { recursive: true });
  const baseline = join(artifactDir, "baseline.ppm");
  writeFileSync(baseline, "P3\n1 1\n255\n1 2 3\n", "utf8");
  const rows = [];
  for (const [index, state] of ["default", "wrapped", "empty", "data", "open"].entries()) {
    const current = join(artifactDir, `current-${state}.ppm`);
    const diff = join(artifactDir, `diff-${state}.ppm`);
    writeFileSync(current, `P3\n1 1\n255\n${index + 4} 5 6\n`, "utf8");
    writeFileSync(diff, `P3\n1 1\n255\n${index + 14} 15 16\n`, "utf8");
    rows.push(
      `| state-${index} | /users | ${state} | ${baseline} | ${digest(baseline)} | ${current} | ${digest(current)} | ${diff} | ${digest(diff)} | strict | pass |`
    );
  }
  const checks = ["V0", "V1", "V2", "V3", "V4", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]
    .map((id) => `| ${id} | pass | ok |`).join("\n");
  return `# UI Stack Visual Parity

| 字段 | 取值 |
|---|---|
| schema | delivery-visual-evidence/v1 |
| producer | delivery-execute-verify |
| state_owner | openspec_change |
| implementation_authority | delivery |
| change_dir | ${changeDir} |
| source_artifact_revision | ${REVISION} |
| analysis_status | complete |
| remediation_status | done |
| assessment_mode | strict_parity |
| visual_acceptance_required | yes |
| final_visual_result | pass |
| adapter / browser | Playwright / Chromium |
| viewport / device_scale_factor | 1440x900 / 1 |
| locale / timezone / theme | zh-CN / Asia-Shanghai / light |
| font_ready_condition | document.fonts.ready |
| animation_policy | disabled |
| data_fixture / dynamic_masks | seeded / clock |

- baseline_source / substitute_standard：${baseline} | ${digest(baseline)}
- Implementation gate reference：user / 2026-08-04T09:00:00+08:00 / ${REVISION}

### Required state evidence

| id | route | state | baseline_path | baseline_digest | current_path | current_digest | diff_path | diff_digest | policy | result |
|---|---|---|---|---|---|---|---|---|---|---|
${rows.join("\n")}

## Verification

| Id | 结果 | 备注 |
|---|---|---|
${checks}
`;
}

const sandbox = mkdtempSync(join(tmpdir(), "delivery-g9-"));
try {
  const changeDir = join(sandbox, "visual-change");
  const visualReport = join(sandbox, "visual-report.md");
  mkdirSync(changeDir, { recursive: true });
  const valid = buildReport(sandbox, changeDir);
  const options = { baseDir: sandbox, expectedChangeDir: changeDir };
  assert.deepEqual(validateVisualEvidence(valid, REVISION, options), [], "valid delivery visual evidence must pass G9");

  assert.ok(validateVisualEvidence(valid, "f".repeat(64), options).some((error) => error.includes("source_artifact_revision")));
  const stateLine = valid.split(/\r?\n/).find((line) => line.startsWith("| state-4 |"));
  assert.ok(stateLine);
  const missingState = valid.replace(`${stateLine}\n`, "");
  assert.ok(validateVisualEvidence(missingState, REVISION, options).some((error) => error.includes("at least five")));
  const failedCheck = valid.replace("| V4 | pass |", "| V4 | fail |");
  assert.ok(validateVisualEvidence(failedCheck, REVISION, options).some((error) => error.includes("V4=pass")));
  const missingCapture = valid.replace("| animation_policy | disabled |", "| animation_policy | <TBD> |");
  assert.ok(validateVisualEvidence(missingCapture, REVISION, options).some((error) => error.includes("animation_policy")));
  const missingGate = valid.replace(/^\- Implementation gate reference.*$/m, "- Implementation gate reference：nonsense");
  assert.ok(validateVisualEvidence(missingGate, REVISION, options).some((error) => error.includes("approver / RFC3339")));
  const wrongChange = valid.replace(`| change_dir | ${changeDir} |`, "| change_dir | Z:/missing/change |");
  assert.ok(validateVisualEvidence(wrongChange, REVISION, options).some((error) => error.includes("does not match")));
  const duplicateRows = valid.replace(/^\| state-[1-4].*$/gm, valid.split(/\r?\n/).find((line) => line.startsWith("| state-0 |")) ?? "");
  assert.ok(validateVisualEvidence(duplicateRows, REVISION, options).some((error) => error.includes("ids must be unique")));
  const missingArtifact = valid.replace(/current-default\.ppm/g, "not-generated.ppm");
  assert.ok(validateVisualEvidence(missingArtifact, REVISION, options).some((error) => error.includes("does not exist")));
  const badDigest = valid.replace(digest(join(sandbox, "visual-artifacts", "current-default.ppm")), "a".repeat(64));
  assert.ok(validateVisualEvidence(badDigest, REVISION, options).some((error) => error.includes("does not match file contents")));
  const invalidPolicy = valid.replace(/\| strict \| pass \|/g, "| banana | pass |");
  assert.ok(validateVisualEvidence(invalidPolicy, REVISION, options).some((error) => error.includes("policy must be")));

  writeFileSync(visualReport, valid, "utf-8");
  writeFileSync(
    join(changeDir, "tasks.md"),
    "# Tasks\n\n- [x] 1.1 Visual fix\n  - 目标文件/符号：src/App.vue\n  - 验证命令/动作：npm test\n  - 预期结果：pass\n",
    "utf-8"
  );
  writeFileSync(
    join(changeDir, "verification.md"),
    "# Verification\n\n- 命令：npm test\n- 时间：2026-08-04T10:00:00+08:00\n- 退出码/结果：exit code 0 / pass\n",
    "utf-8"
  );
  const close = spawnSync(
    process.execPath,
    [
      resolve(HERE, "..", "..", "delivery-frame-spec", "scripts", "delivery_scaffold.mjs"),
      "close-out", "--change-dir", changeDir, "--review-status", "pass", "--reviewer", "independent-reviewer",
      "--evidence", "npm test: pass", "--approved-by", "user", "--visual-required", "yes",
      "--visual-report", visualReport, "--expected-visual-revision", REVISION,
    ],
    { encoding: "utf-8" }
  );
  assert.equal(close.status, 0, `${close.stdout}\n${close.stderr}`);
  const handoff = JSON.parse(readFileSync(join(changeDir, "handoff.json"), "utf-8"));
  assert.deepEqual(handoff.stage_payload.visual_evidence, {
    required: true, report: visualReport, source_artifact_revision: REVISION, g9: "pass",
  });
} finally {
  rmSync(sandbox, { recursive: true, force: true });
}

console.log("PASS: G9 visual evidence contract and adversarial artifact checks passed");
