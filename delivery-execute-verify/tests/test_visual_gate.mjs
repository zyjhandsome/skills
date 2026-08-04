#!/usr/bin/env node
// @ts-check

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { validateVisualEvidence } from "../scripts/validate_delivery_change.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const REVISION = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
const valid = `# UI Stack Visual Parity

| 字段 | 取值 |
|---|---|
| schema | delivery-visual-evidence/v1 |
| producer | delivery-execute-verify |
| state_owner | openspec_change |
| implementation_authority | delivery |
| change_dir | openspec/changes/visual-change |
| source_artifact_revision | ${REVISION} |
| analysis_status | complete |
| strategy_status | decided |
| remediation_status | done |
| assessment_mode | strict_parity |
| visual_acceptance_required | yes |
| final_visual_result | pass |

- baseline_source / substitute_standard：git:before/screenshots

| 字段 | 值 |
|---|---|
| adapter / browser | Playwright / Chromium |
| viewport / device_scale_factor | 1440x900 / 1 |
| locale / timezone / theme | zh-CN / Asia-Shanghai / light |
| font_ready_condition | document.fonts.ready |
| animation_policy | disabled |
| data_fixture / dynamic_masks | seeded / clock |

### Required state evidence

| id | route | state | result |
|---|---|---|---|
| search-default | /users | default | pass |
| search-wrap | /users | wrapped | pass |
| table-empty | /users | empty | pass |
| table-data | /users | data | pass |
| cell-popper | /users | open | pass |

## Verification

| Id | 结果 | 备注 |
|---|---|---|
${["V0", "V1", "V2", "V3", "V4", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]
  .map((id) => `| ${id} | pass | ok |`)
  .join("\n")}

- Implementation gate reference：user / 2026-08-04T09:00:00+08:00 / ${REVISION}
`;

assert.deepEqual(validateVisualEvidence(valid, REVISION), [], "valid delivery visual evidence must pass G9");

const revisionErrors = validateVisualEvidence(valid, "f".repeat(64));
assert.ok(
  revisionErrors.some((error) => error.includes("source_artifact_revision")),
  "G9 must bind the visual report to the approved artifact revision"
);

const missingState = valid.replace(/^\| cell-popper.*$/m, "");
assert.ok(
  validateVisualEvidence(missingState, REVISION).some((error) => error.includes("at least five")),
  "G9 must require the minimum required-state matrix"
);

const failedCheck = valid.replace("| V4 | pass |", "| V4 | fail |");
assert.ok(
  validateVisualEvidence(failedCheck, REVISION).some((error) => error.includes("V4=pass")),
  "G9 must reject failed visual verification rows"
);

const missingCapture = valid.replace("| animation_policy | disabled |", "| animation_policy | <TBD> |");
assert.ok(
  validateVisualEvidence(missingCapture, REVISION).some((error) => error.includes("animation_policy")),
  "G9 must require deterministic capture context"
);

const missingGate = valid.replace(
  `Implementation gate reference：user / 2026-08-04T09:00:00+08:00 / ${REVISION}`,
  "Implementation gate reference：TBD"
);
assert.ok(
  validateVisualEvidence(missingGate, REVISION).some((error) => error.includes("implementation gate reference")),
  "G9 must require its own implementation gate binding"
);

const sandbox = mkdtempSync(join(tmpdir(), "delivery-g9-"));
try {
  const changeDir = join(sandbox, "visual-change");
  const visualReport = join(sandbox, "visual-report.md");
  mkdirSync(changeDir, { recursive: true });
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
      "close-out",
      "--change-dir",
      changeDir,
      "--review-status",
      "pass",
      "--reviewer",
      "independent-reviewer",
      "--evidence",
      "npm test: pass",
      "--approved-by",
      "user",
      "--visual-required",
      "yes",
      "--visual-report",
      visualReport,
      "--expected-visual-revision",
      REVISION,
    ],
    { encoding: "utf-8" }
  );
  assert.equal(close.status, 0, `${close.stdout}\n${close.stderr}`);
  const handoff = JSON.parse(readFileSync(join(changeDir, "handoff.json"), "utf-8"));
  assert.deepEqual(handoff.stage_payload.visual_evidence, {
    required: true,
    report: visualReport,
    source_artifact_revision: REVISION,
    g9: "pass",
  });
} finally {
  rmSync(sandbox, { recursive: true, force: true });
}

console.log("PASS: G9 visual evidence contract checks passed");
