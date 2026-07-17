#!/usr/bin/env node
// @ts-check
/**
 * P0-2 regression lock: the machine anchors documented in the Chinese templates must
 * stay parseable by validate_delivery_change.mjs.
 *
 * Guards against the R3 failure mode where tasks were written with near-synonym labels
 * ("文件/符号", "验证：") and --claim-verified silently failed, forcing a tasks rewrite
 * and a full revision re-bind.
 *
 * Checks:
 * 1. tasks-template.md task field labels -> FIELD_PATTERNS all match.
 * 2. verification-template.md 主验证证据 labels -> VERIFICATION_PATTERNS all match,
 *    and the filled sample passes the RFC3339/result-shape checks.
 *
 * Zero dependencies (Node >= 18). Exit 0 = consistent, 1 = drift detected.
 */

import { readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

import {
  TASK_START,
  FIELD_PATTERNS,
  VERIFICATION_PATTERNS,
  isPlaceholder,
  isRfc3339,
  containsAny,
} from "../scripts/validate_delivery_change.mjs";

const TESTS_DIR = dirname(fileURLToPath(import.meta.url));
const SKILL_DIR = resolve(TESTS_DIR, "..");
const TASKS_TEMPLATE = join(SKILL_DIR, "..", "delivery-plan-tasks", "references", "tasks-template.md");
const VERIFICATION_TEMPLATE = join(SKILL_DIR, "references", "verification-template.md");

// The three anchors every task block must carry (must stay in sync with FIELD_PATTERNS).
const REQUIRED_TASK_FIELDS = /** @type {const} */ (["target", "command", "expected"]);
const SAMPLE_TASK_VALUES = {
  target: "src/example.py::do_thing",
  command: "pytest tests/test_example.py -q",
  expected: "exit 0，全部通过",
};

/** @param {string} p */
function isFile(p) {
  try {
    return statSync(p).isFile();
  } catch {
    return false;
  }
}

/** @param {string[]} messages */
function fail(messages) {
  for (const message of messages) console.error(`ERROR: ${message}`);
  return 1;
}

/**
 * Return the indented '- <label>：' lines of the first checkbox task in the template.
 * @param {string} templateText
 * @returns {string[]}
 */
function extractTaskLabelLines(templateText) {
  const match = templateText.match(TASK_START);
  if (!match || match.index === undefined) return [];
  const tail = templateText.slice(match.index);
  const end = tail.indexOf("\n## ");
  const block = end === -1 ? tail : tail.slice(0, end);
  return [...block.matchAll(/^(\s+-\s+[^:：\n]+)[:：]\s*$/gm)].map((m) => m[1]);
}

/** @returns {string[]} */
function checkTasksTemplate() {
  /** @type {string[]} */
  const errors = [];
  if (!isFile(TASKS_TEMPLATE)) {
    return [`tasks template missing: ${TASKS_TEMPLATE}`];
  }
  const text = readFileSync(TASKS_TEMPLATE, "utf-8");

  const labelLines = extractTaskLabelLines(text);
  if (labelLines.length === 0) {
    return ["could not locate the example task block in tasks-template.md"];
  }

  // Rebuild the template's own task block with sample values filled in, then run the
  // exact production patterns against it.
  const filledLines = ["- [x] 任务 1：模板锚点一致性样例"];
  filledLines.push(...labelLines.map((label) => `${label}：占位样例值`));
  const synthetic = filledLines.join("\n") + "\n";
  // Overwrite the three machine-anchor values with realistic samples so the
  // placeholder filter cannot mask a label mismatch.
  for (const field of REQUIRED_TASK_FIELDS) {
    if (!FIELD_PATTERNS[field].test(synthetic)) {
      errors.push(
        `tasks-template.md label drift: FIELD_PATTERNS['${field}'] does not match ` +
          "any label line in the template task block"
      );
    }
  }

  // And the fully-valid sample must satisfy the real per-task check end to end.
  const validBlock = [
    "- [x] 任务 1：模板锚点一致性样例",
    `  - 目标文件/符号：${SAMPLE_TASK_VALUES.target}`,
    `  - 验证命令/动作：${SAMPLE_TASK_VALUES.command}`,
    `  - 预期结果：${SAMPLE_TASK_VALUES.expected}`,
  ].join("\n");
  for (const field of REQUIRED_TASK_FIELDS) {
    const match = validBlock.match(FIELD_PATTERNS[field]);
    if (!match || isPlaceholder(match[1])) {
      errors.push(`canonical sample task block failed FIELD_PATTERNS['${field}']`);
    }
  }
  return errors;
}

/** @returns {string[]} */
function checkVerificationTemplate() {
  /** @type {string[]} */
  const errors = [];
  if (!isFile(VERIFICATION_TEMPLATE)) {
    return [`verification template missing: ${VERIFICATION_TEMPLATE}`];
  }
  const text = readFileSync(VERIFICATION_TEMPLATE, "utf-8");

  for (const label of ["命令", "时间", "结果"]) {
    if (!new RegExp(`^\\s*-\\s*${label}[:：]`, "m").test(text)) {
      errors.push(`verification-template.md no longer contains the anchor line '- ${label}：'`);
    }
  }

  const sample =
    "### 主验证证据\n" +
    "- 命令：pytest -q\n" +
    "- 时间：2026-07-17T00:00:00Z\n" +
    "- 结果：exit 0 / 通过\n";
  /** @type {Record<string, string>} */
  const evidence = {};
  for (const [field, pattern] of Object.entries(VERIFICATION_PATTERNS)) {
    const match = sample.match(pattern);
    if (!match || isPlaceholder(match[1])) {
      errors.push(`canonical verification sample failed VERIFICATION_PATTERNS['${field}']`);
    } else {
      evidence[field] = match[1];
    }
  }
  if ("time" in evidence && !isRfc3339(evidence.time)) {
    errors.push("canonical verification sample time failed the RFC3339 check");
  }
  if (
    "result" in evidence &&
    !containsAny(evidence.result, [
      "\\bpass(?:ed)?\\b",
      "\\bfail(?:ed)?\\b",
      "exit\\s*code",
      "退出码",
      "通过",
      "失败",
      "exit\\s*\\d+",
    ])
  ) {
    errors.push("canonical verification sample result failed the pass/fail shape check");
  }
  return errors;
}

// P3-2 lock: the accepted limited synonym set, and writings that must stay rejected.
// Extending FIELD_PATTERNS without updating both lists here is a test failure by design.
const ACCEPTED_ALIASES = {
  target: ["目标文件/符号", "文件/符号", "Exact files/symbols", "Target files/symbols"],
  command: ["验证命令/动作", "验证命令", "验证动作", "验证", "Validation command/action", "Validation command"],
  expected: ["预期结果", "预期", "期望结果", "Expected result"],
};
const REJECTED_LABELS = {
  target: ["目标", "涉及文件", "改动文件"],
  command: ["最小验证", "命令", "测试命令", "失败测试或已批准替代验证"],
  expected: ["结果", "验收标准", "完成定义"],
};

/** @returns {string[]} */
function checkSynonymLock() {
  /** @type {string[]} */
  const errors = [];
  for (const [field, aliases] of Object.entries(ACCEPTED_ALIASES)) {
    const pattern = FIELD_PATTERNS[/** @type {keyof typeof FIELD_PATTERNS} */ (field)];
    for (const alias of aliases) {
      if (!pattern.test(`  - ${alias}：样例值\n`)) {
        errors.push(`accepted alias no longer matches FIELD_PATTERNS['${field}']: '${alias}'`);
      }
    }
  }
  for (const [field, labels] of Object.entries(REJECTED_LABELS)) {
    const pattern = FIELD_PATTERNS[/** @type {keyof typeof FIELD_PATTERNS} */ (field)];
    for (const label of labels) {
      if (pattern.test(`  - ${label}：样例值\n`)) {
        errors.push(
          `FIELD_PATTERNS['${field}'] became over-broad: undocumented label '${label}' matches`
        );
      }
    }
  }
  return errors;
}

function main() {
  const errors = [...checkTasksTemplate(), ...checkVerificationTemplate(), ...checkSynonymLock()];
  if (errors.length) return fail(errors);
  console.log("PASS: template machine anchors are consistent with validate_delivery_change.mjs");
  return 0;
}

process.exit(main());
