import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { validateVisualEvidence } from "../scripts/validate_delivery_change.mjs";
import { emptyGateBlock } from "../../delivery-frame-spec/scripts/gate_record.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const REV = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
const VISUAL_TEMPLATE = readFileSync(resolve(HERE, "..", "references", "delivery-visual-evidence-template.md"), "utf8");
const GATE_CHECKS = readFileSync(resolve(HERE, "..", "references", "artifact-gate-checks.md"), "utf8");

for (const token of ["V0", "P7", "analysis_status", "remediation_status", "table_metrics", "style_closure_status", "baseline_state_ids"]) {
  assert.ok(!VISUAL_TEMPLATE.includes(token), `G9 template still carries ${token}`);
  assert.ok(!GATE_CHECKS.includes(token), `G9 gate still carries ${token}`);
}

/** @param {string} path */
function digest(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

/** @param {string} sandbox @param {string} name @param {string} body */
function ppm(sandbox, name, body) {
  const path = join(sandbox, "visual-artifacts", name);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, body, "utf8");
  return path;
}

/**
 * @param {string} sandbox
 * @param {string} changeDir
 * @param {"strict_parity" | "consistency_review" | "spec_assertion"} mode
 * @param {number} stateCount
 */
function buildReport(sandbox, changeDir, mode, stateCount) {
  const rows = [];
  for (let index = 0; index < stateCount; index += 1) {
    const current = ppm(sandbox, `current-${mode}-${index}.ppm`, `P3\n1 1\n255\n${index + 4} 5 6\n`);
    if (mode === "spec_assertion") {
      rows.push(
        `| state-${index} | /export | state-${index} | n/a | n/a | ${current} | ${digest(current)} | n/a | n/a | 按钮显示“导出为文本” | strict | pass |`
      );
      continue;
    }
    const baseline = ppm(sandbox, `baseline-${mode}.ppm`, "P3\n1 1\n255\n1 2 3\n");
    const diff = ppm(sandbox, `diff-${mode}-${index}.ppm`, `P3\n1 1\n255\n${index + 14} 15 16\n`);
    rows.push(
      `| state-${index} | /export | state-${index} | ${baseline} | ${digest(baseline)} | ${current} | ${digest(current)} | ${diff} | ${digest(diff)} | n/a | strict | pass |`
    );
  }
  const baselineLine =
    mode === "spec_assertion"
      ? "n/a"
      : mode === "consistency_review"
        ? `approved-substitute:design.md | user | ${REV}`
        : `${ppm(sandbox, `baseline-${mode}.ppm`, "P3\n1 1\n255\n1 2 3\n")} | ${digest(ppm(sandbox, `baseline-${mode}.ppm`, "P3\n1 1\n255\n1 2 3\n"))}`;
  return `# Delivery Visual Evidence

| 字段 | 取值 |
|---|---|
| schema | delivery-visual-evidence/v1 |
| producer | delivery-execute-verify |
| state_owner | openspec_change |
| change_dir | ${changeDir} |
| source_artifact_revision | ${REV} |
| assessment_mode | ${mode} |
| final_visual_result | pass |
| adapter / browser | Playwright / Chromium |
| viewport / device_scale_factor | 1440x900 / 1 |
| locale / timezone / theme | zh-CN / Asia-Shanghai / light |
| font_ready_condition | document.fonts.ready |
| animation_policy | disabled |
| data_fixture / dynamic_masks | seeded / clock |

- baseline_source / substitute_standard：${baselineLine}
- Implementation gate reference：user / 2026-11-24T10:00:00+08:00 / ${REV}

### Required state evidence

| id | route | state | baseline_path | baseline_digest | current_path | current_digest | diff_path | diff_digest | assertion | policy | result |
|---|---|---|---|---|---|---|---|---|---|---|---|
${rows.join("\n")}
`;
}

/** @param {string} sandbox @param {string} changeDir */
function buildLegacyV1(sandbox, changeDir) {
  const artifactDir = join(sandbox, "legacy-artifacts");
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
    .map((id) => `| ${id} | pass | ok |`)
    .join("\n");
  return `# UI Stack Visual Parity

| 字段 | 取值 |
|---|---|
| schema | delivery-visual-evidence/v1 |
| producer | delivery-execute-verify |
| state_owner | openspec_change |
| implementation_authority | delivery |
| change_dir | ${changeDir} |
| source_artifact_revision | ${REV} |
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
- Implementation gate reference：user / 2026-08-04T09:00:00+08:00 / ${REV}

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
  mkdirSync(changeDir, { recursive: true });
  const opts = { baseDir: sandbox, expectedChangeDir: changeDir };
  const build = (mode, count) => buildReport(sandbox, changeDir, mode, count);

  assert.deepEqual(validateVisualEvidence(build("strict_parity", 1), REV, opts), []);
  assert.deepEqual(validateVisualEvidence(build("spec_assertion", 2), REV, opts), []);
  assert.deepEqual(validateVisualEvidence(build("strict_parity", 1), `sha256:${REV}`, opts), []);
  assert.deepEqual(
    validateVisualEvidence(build("strict_parity", 2), REV, { ...opts, requiredStateIds: ["state-0", "state-1"] }),
    []
  );
  assert.ok(
    validateVisualEvidence(build("strict_parity", 1), REV, { ...opts, requiredStateIds: ["state-0", "state-9"] }).some((error) =>
      error.includes("missing required state id: state-9")
    )
  );
  assert.ok(
    validateVisualEvidence(build("spec_assertion", 1).replace(/\| 按钮显示“导出为文本” \|/, "| <TBD> |"), REV, opts).some((error) =>
      error.includes("assertion")
    )
  );
  assert.ok(
    validateVisualEvidence(
      build("strict_parity", 1).replace(/^- baseline_source.*$/m, "- baseline_source / substitute_standard：n/a"),
      REV,
      opts
    ).some((error) => error.includes("baseline"))
  );
  assert.deepEqual(validateVisualEvidence(buildLegacyV1(sandbox, changeDir), REV, opts), []);
  assert.ok(validateVisualEvidence(build("strict_parity", 0), REV, opts).some((error) => error.includes("at least one")));

  const valid = build("strict_parity", 2);
  assert.ok(validateVisualEvidence(valid, "f".repeat(64), opts).some((error) => error.includes("source_artifact_revision")));
  const missingCapture = valid.replace("| animation_policy | disabled |", "| animation_policy | <TBD> |");
  assert.ok(validateVisualEvidence(missingCapture, REV, opts).some((error) => error.includes("animation_policy")));
  const missingGate = valid.replace(/^- Implementation gate reference.*$/m, "- Implementation gate reference：nonsense");
  assert.ok(validateVisualEvidence(missingGate, REV, opts).some((error) => error.includes("approver / RFC3339")));
  const wrongChange = valid.replace(`| change_dir | ${changeDir} |`, "| change_dir | Z:/missing/change |");
  assert.ok(validateVisualEvidence(wrongChange, REV, opts).some((error) => error.includes("does not match")));
  const firstRow = valid.split(/\r?\n/).find((line) => line.startsWith("| state-0 |")) ?? "";
  const duplicateRows = valid.replace(/^\| state-1 \|.*$/m, firstRow);
  assert.ok(validateVisualEvidence(duplicateRows, REV, opts).some((error) => error.includes("ids must be unique")));
  const missingArtifact = valid.replace(/current-strict_parity-0\.ppm/g, "not-generated.ppm");
  assert.ok(validateVisualEvidence(missingArtifact, REV, opts).some((error) => error.includes("does not exist")));
  const currentPath = valid.match(/current-strict_parity-0\.ppm/)?.[0];
  assert.ok(currentPath);
  const badDigest = valid.replace(digest(join(sandbox, "visual-artifacts", "current-strict_parity-0.ppm")), "a".repeat(64));
  assert.ok(validateVisualEvidence(badDigest, REV, opts).some((error) => error.includes("does not match file contents")));
  const invalidPolicy = valid.replace(/\| strict \| pass \|/g, "| banana | pass |");
  assert.ok(validateVisualEvidence(invalidPolicy, REV, opts).some((error) => error.includes("policy must be")));

  const visualReport = join(sandbox, "visual-report.md");
  writeFileSync(visualReport, build("strict_parity", 1), "utf8");
  writeFileSync(
    join(changeDir, "tasks.md"),
    "# Tasks\n\n- [x] 1.1 Visual fix\n  - 对应需求/场景：外观状态 / 默认\n  - 目标文件/符号：src/App.vue\n  - 验证命令/动作：npm test\n  - 预期结果：pass\n  - 失败测试或已批准替代验证：npm test\n",
    "utf8"
  );
  writeFileSync(
    join(changeDir, "verification.md"),
    "# Verification\n\n- 命令：npm test\n- 时间：2026-08-04T10:00:00+08:00\n- 退出码/结果：exit code 0 / pass\n",
    "utf8"
  );
  writeFileSync(join(changeDir, "proposal.md"), `## Why\n视觉验收。\n\n### 状态源与工件位置\n${emptyGateBlock()}`, "utf8");
  writeFileSync(join(changeDir, "design.md"), [
    "### Visual validation matrix（visual=required 时）",
    "| ID | required_for_verified |",
    "|---|---|",
    "| state-0 | yes |",
    "| state-1 | yes |",
    "| state-2 | no |",
  ].join("\n"));
  const recorded = spawnSync(
    process.execPath,
    [
      resolve(HERE, "..", "..", "delivery-frame-spec", "scripts", "delivery_scaffold.mjs"),
      "record-gate",
      "--change-dir",
      changeDir,
      "--gate",
      "impl",
      "--approved-by",
      "user",
    ],
    { encoding: "utf8" }
  );
  assert.equal(recorded.status, 0, recorded.stderr);
  const revision = recorded.stdout.match(/sha256:[0-9a-f]{64}/)[0];
  function close(...extra) {
    return spawnSync(process.execPath, [
      resolve(HERE, "..", "..", "delivery-frame-spec", "scripts", "delivery_scaffold.mjs"),
      "close-out", "--change-dir", changeDir, "--review-status", "pass",
      "--reviewer", "independent-reviewer", "--evidence", "npm test: pass", ...extra,
    ], { encoding: "utf8" });
  }
  function report(count, rev) {
    writeFileSync(visualReport, build("spec_assertion", count).replaceAll(REV, rev));
  }
  report(2, REV);
  const stale = close("--visual-required", "yes", "--visual-report", visualReport,
    "--expected-visual-revision", REV, "--required-state-ids", "state-0,state-1");
  assert.notEqual(stale.status, 0, "a caller-supplied stale revision cannot close the change");
  assert.notEqual(close("--visual-report", visualReport).status, 0, "report itself is stale");
  report(1, revision);
  assert.notEqual(close().status, 0, "omitting flags must not disable G9");
  assert.notEqual(close("--visual-required", "no").status, 0);
  assert.match(close("--visual-report", visualReport).stderr, /state-1/);
  assert.match(close("--visual-report", visualReport, "--required-state-ids", "state-0").stderr, /state-1/);
  report(2, revision);
  const conflict = close("--visual-report", visualReport, "--evidence", "npm test: exit 1");
  assert.notEqual(conflict.status, 0, "contradictory handoff evidence must block");
  const done = close("--visual-report", visualReport);
  assert.equal(done.status, 0, done.stderr);
  const handoff = JSON.parse(readFileSync(join(changeDir, "handoff.json"), "utf8"));
  assert.deepEqual(handoff.stage_payload.visual_evidence, {
    required: true, report: visualReport, source_artifact_revision: revision, g9: "pass",
  });
  console.log("PASS: G9 accepts parity, consistency, and spec assertion evidence");
} finally {
  rmSync(sandbox, { recursive: true, force: true });
}
