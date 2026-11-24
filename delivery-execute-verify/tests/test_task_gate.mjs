import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const CLI = resolve(dirname(fileURLToPath(import.meta.url)), "..", "scripts", "validate_delivery_change.mjs");
const scratch = mkdtempSync(join(tmpdir(), "task-gate-"));
const dir = join(scratch, "change");
mkdirSync(join(dir, "specs", "cap"), { recursive: true });

const tasksText = `- [x] 任务 1：导出纯文本
  - 对应需求/场景：导出纯文本 / 基本行为
  - 目标文件/符号：src/export.py::export_txt
  - 验证命令/动作：pytest tests/test_export.py::test_export -q
  - 预期结果：exit 0，测试通过
  - 失败测试或已批准替代验证：tests/test_export.py::test_export
`;

/** @param {string} name @param {string} text */
function write(name, text) {
  writeFileSync(join(dir, name), text);
}

/** @param {string} name */
function read(name) {
  return readFileSync(join(dir, name), "utf8");
}

/** @param {string} name @param {string} text */
function append(name, text) {
  write(name, read(name) + text);
}

write(".openspec.yaml", "schema: spec-driven\ncreated: 2026-11-24\n");
write("specs/cap/spec.md", "## ADDED Requirements\n\n### Requirement: 导出纯文本\n系统 MUST 导出纯文本。\n");
write("tasks.md", tasksText);
write(
  "verification.md",
  "# 验证记录\n\n- 命令：pytest tests/test_export.py::test_export -q\n- 时间：2026-11-24T10:00:00+08:00\n- 退出码/结果：pass\n"
);

/** @param {string} dirPath @param {...string} args */
function run(dirPath, ...args) {
  return spawnSync(process.execPath, [CLI, dirPath, ...args], { encoding: "utf8" });
}

/** @param {string} value */
function setVerificationResult(value) {
  write("verification.md", read("verification.md").replace(/^(-\s*退出码\/结果：).*$/m, `$1${value}`));
}

function restoreTasks() {
  write("tasks.md", tasksText);
}

/** @param {string} extra */
function appendToTasks(extra) {
  write("tasks.md", `${tasksText}\n${extra}\n`);
}

/** @param {string} label */
function removeTaskLine(label) {
  write(
    "tasks.md",
    read("tasks.md")
      .split(/\r?\n/)
      .filter((line) => !line.includes(label))
      .join("\n")
  );
}

/** @param {string} value */
function setScenarioValue(value) {
  write("tasks.md", tasksText.replace(/(-\s*对应需求\/场景：).*/, `$1${value}`));
}

function removeSpecsDir() {
  rmSync(join(dir, "specs"), { recursive: true, force: true });
}

try {
  assert.equal(run(dir, "--claim-verified").status, 0);
  setVerificationResult("exit 0");
  assert.equal(run(dir, "--claim-verified").status, 0);
  for (const result of ["exit 1", "fail", "exit 1 / pass", "exit 0 / 2 failed", "未通过", "exit 0 / not passed"]) {
    setVerificationResult(result);
    assert.notEqual(run(dir, "--claim-verified").status, 0, result);
  }
  setVerificationResult("exit 0 / 0 failed");
  assert.equal(run(dir, "--claim-verified").status, 0);

  const positive = read("verification.md");
  const finalChecks = "\n## 最终验证\n| 命令/动作 | 覆盖范围 | 预期结果 |\n|---|---|---|\n" +
    "| pytest tests/test_export.py::test_export -q | suite | exit 0 |\n| validate-invalid | negative input | exit 2 |\n";
  appendToTasks(finalChecks);
  assert.notEqual(run(dir, "--claim-verified").status, 0, "missing mandatory negative case");
  const row = "| 时间 | 命令/动作 | 退出码/结果 | 失败数 | 覆盖范围 |\n|---|---|---|---|---|\n" +
    "| 2026-11-24T10:00:00Z | validate-invalid | exit 2 | 0 | negative input |\n";
  write("verification.md", positive + "\n```markdown\n" + row + "```\n");
  assert.notEqual(run(dir, "--claim-verified").status, 0, "a documentation example is not a run");
  write("verification.md", positive + row);
  assert.equal(run(dir, "--claim-verified").status, 0, "approved expected exit 2");
  write("verification.md", positive + row.replace("exit 2", "pass"));
  assert.notEqual(run(dir, "--claim-verified").status, 0, "missing expected exit 2");
  write("verification.md", positive + row + "\n- 运行/静态检查：失败\n");
  assert.notEqual(run(dir, "--claim-verified").status, 0, "summary contradicts actual results");
  write("verification.md", positive + row.replace("exit 2", "exit 3"));
  assert.notEqual(run(dir, "--claim-verified").status, 0, "wrong exit code");
  write("verification.md", positive + row.replace(" | 0 |", " | 1 |"));
  assert.notEqual(run(dir, "--claim-verified").status, 0, "reported failures");
  write("verification.md", positive + "\n- 命令：npm run lint\n- 时间：2026-11-24T10:00:00Z\n- 结果：fail\n");
  assert.notEqual(run(dir, "--claim-verified").status, 0, "secondary failure");
  restoreTasks();
  write("verification.md", positive);
  for (const extra of ["  - [ ] 1.1 子项", "- [~] 任务 2：部分完成", "```\n- [ ] 示例\n```"]) {
    appendToTasks(extra);
    const result = run(dir, "--claim-verified");
    assert.notEqual(result.status, 0);
    assert.match(result.stderr ?? "", /open checkboxes/);
    restoreTasks();
  }
  removeTaskLine("失败测试或已批准替代验证");
  assert.match(run(dir).stderr ?? "", /task 1 missing non-empty red field/);
  restoreTasks();
  setScenarioValue("别的需求 / 基本行为");
  assert.match(run(dir).stderr ?? "", /requirement not traced by any task: 导出纯文本/);
  restoreTasks();
  removeSpecsDir();
  append(".openspec.yaml", "skip_specs: true\n");
  setScenarioValue("不适用（skip_specs）");
  assert.equal(run(dir).status, 0);
  console.log("PASS: task gate counts OpenSpec checkboxes and checks requirement and failing-test links");
} finally {
  rmSync(scratch, { recursive: true, force: true });
}
