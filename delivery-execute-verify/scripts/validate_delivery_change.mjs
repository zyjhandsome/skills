#!/usr/bin/env node
// @ts-check
/**
 * Run deterministic, non-mutating checks on a Delivery/OpenSpec change directory.
 * Zero dependencies (Node >= 18).
 *
 * Usage:
 *   node validate_delivery_change.mjs <change_dir> [--tasks <path>] [--verification <path>]
 *                                     [--repo-root <path>] [--claim-verified]
 *                                     [--visual-report <path>] [--required-state-ids <additional-ids>]
 */

import { createHash } from "node:crypto";
import { readFileSync, readdirSync, statSync, existsSync, realpathSync } from "node:fs";
import { resolve, join, dirname, isAbsolute, normalize } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import process from "node:process";
import { parseGateRecord } from "../../delivery-frame-spec/scripts/gate_record.mjs";
import { CHECKBOX_LINE, hashChange, normalizeRevision } from "../../delivery-frame-spec/scripts/hash_change_artifacts.mjs";

export const TASK_START = /^- \[(?<status>[^\]\s]| )\] .+$/m;
// Field labels below are STABLE MACHINE ANCHORS shared with the Chinese/English templates
// (tasks-template.md, verification-template.md). Accept both ASCII ":" and fullwidth "："
// because the Chinese templates emit the fullwidth colon. Do not reword the labels in the
// templates without updating these patterns.
//
// Limited synonym set (delivery-family/1.5, P3-2): the aliases below are the near-synonym
// labels observed in real field use (R3). They are ACCEPTED on read so a hand-written task
// does not force a full revision re-bind, but templates and delivery_scaffold.mjs MUST keep
// emitting only the canonical labels (first alternative in each group). Do not extend this
// list without adding the new alias to tests/test_template_anchor_consistency.mjs first.
export const FIELD_PATTERNS = {
  target: /^\s+-\s+(?:目标文件\/符号|文件\/符号|Exact files\/symbols|Target files\/symbols)\s*[:：]\s*(\S.*)$/im,
  command:
    /^\s+-\s+(?:验证命令\/动作|验证命令|验证动作|验证|Validation command\/action|Validation command)\s*[:：]\s*(\S.*)$/im,
  expected: /^\s+-\s+(?:预期结果|预期|期望结果|Expected result)\s*[:：]\s*(\S.*)$/im,
  scenario: /^\s+-\s+(?:对应需求\/场景|Requirement\/Scenario)\s*[:：]\s*(\S.*)$/im,
  red: /^\s+-\s+(?:失败测试或已批准替代验证|Failing test or approved alternative)\s*[:：]\s*(\S.*)$/im,
};
// Existing template tools use these exports to recognize result-shaped text.
// Completion decisions use resultMatches, which also checks the observed outcome.
export const RESULT_PATTERNS = [
  "\\bpass(?:ed)?\\b", "\\bfail(?:ed)?\\b", "exit\\s*code", "退出码", "通过", "失败", "exit\\s*\\d+",
];

/** @param {string} text @param {string[]} patterns */
export function containsAny(text, patterns) {
  return patterns.some((pattern) => new RegExp(pattern, "im").test(text));
}

export const VERIFICATION_PATTERNS = {
  command: /^\s*(?:[-*]\s*)?(?:命令(?:\/动作)?|command(?:\/action)?)\s*[:：]\s*(\S.*)$/im,
  time: /^\s*(?:[-*]\s*)?(?:时间|timestamp|date)\s*[:：]\s*(\S.*)$/im,
  result: /^\s*(?:[-*]\s*)?(?:退出码\/结果|结果|退出码|result|exit\s*code)\s*[:：]\s*(\S.*)$/im,
};
const PLACEHOLDER = /^(?:<[^>]+>|tbd|todo|n\/?a|none|null|待定|待补)$/i;
const REVISION = /^[0-9a-f]{64}$/i;
const IMAGE_EXTENSION = /\.(png|jpe?g|webp|ppm)$/i;

/** @param {string} value */
function stripBackticks(value) {
  return value.trim().replace(/^`+|`+$/g, "");
}

/**
 * Split tasks text into checkbox task blocks.
 * @param {string} text
 * @returns {Array<{status: string, block: string}>}
 */
/**
 * Every checkbox OpenSpec archive would count, including nested and fenced lines.
 * A mark of x/X is complete; anything else is open.
 * @param {string} text
 * @returns {Array<{ line: number, text: string }>}
 */
export function openCheckboxes(text) {
  /** @type {Array<{ line: number, text: string }>} */
  const open = [];
  text.split(/\r?\n/).forEach((line, index) => {
    const match = line.match(CHECKBOX_LINE);
    if (!match) return;
    const mark = match[2] ?? "";
    if (mark === "x" || mark === "X") return;
    open.push({ line: index + 1, text: line });
  });
  return open;
}

/**
 * Requirement titles under ADDED and MODIFIED delta sections.
 * @param {string} changeDir
 * @returns {string[]}
 */
export function requirementNames(changeDir) {
  /** @type {string[]} */
  const names = [];
  for (const file of listSpecFiles(changeDir)) {
    let inDelta = false;
    for (const line of readFileSync(file, "utf8").split(/\r?\n/)) {
      if (/^##\s+/.test(line)) {
        inDelta = /^##\s+(?:ADDED|MODIFIED)\s+Requirements\s*$/.test(line);
        continue;
      }
      if (!inDelta) continue;
      const match = line.match(/^###\s+Requirement:\s*(.+?)\s*$/);
      if (match) names.push(match[1]);
    }
  }
  return names;
}

/** @param {string} changeDir @returns {string[]} */
function listSpecFiles(changeDir) {
  const root = join(changeDir, "specs");
  if (!existsSync(root)) return [];
  /** @type {string[]} */
  const out = [];
  /** @param {string} dir */
  const walk = (dir) => {
    let entries;
    try {
      entries = readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.isFile() && entry.name.endsWith(".md")) out.push(full);
    }
  };
  walk(root);
  return out;
}

/** @param {string} changeDir */
function skipSpecsEnabled(changeDir) {
  const path = join(changeDir, ".openspec.yaml");
  if (!isFile(path)) return false;
  return readFileSync(path, "utf8")
    .split(/\r?\n/)
    .some((line) => /^skip_specs:\s*true\s*$/.test(line));
}

export function taskBlocks(text) {
  const re = new RegExp(TASK_START.source, "gm");
  const starts = [...text.matchAll(re)];
  return starts.map((match, index) => {
    const end = index + 1 < starts.length ? /** @type {number} */ (starts[index + 1].index) : text.length;
    return {
      status: /** @type {{status: string}} */ (match.groups).status,
      block: text.slice(/** @type {number} */ (match.index), end),
    };
  });
}

// Examples and archived comments do not constitute a command run or an approved matrix row.
function markdownContent(text) {
  let fence = "";
  return text.replace(/<!--[\s\S]*?(?:-->|$)/g, "").split(/\r?\n/).filter((line) => {
    const marker = /^ {0,3}(\x60{3,}|~{3,})(.*)$/.exec(line);
    if (!fence && marker) fence = marker[1];
    else if (fence && marker?.[1].startsWith(fence) && !marker[2].trim()) {
      fence = "";
      return false;
    }
    return !fence;
  }).join("\n");
}

/**
 * Read a table by its column headers. Preserve command text and reject broken rows.
 * @param {string} text @param {string} key @param {string[]} errors
 * @param {Record<string, string>} aliases
 * @returns {Record<string, string>[]}
 */
function tableRows(text, key, errors, aliases = {}) {
  const rows = [];
  let headers = null;
  for (const line of text.split(/\r?\n/)) {
    if (!line.trimStart().startsWith("|")) {
      headers = null;
      continue;
    }
    const cells = line.trim().replace(/^\||\|$/g, "").split(/(?<!\\)\|/)
      .map((s) => stripBackticks(s.replace(/\\\|/g, "|")));
    if (!headers) {
      const names = cells.map((s) => aliases[s.toLowerCase()] ?? s.toLowerCase());
      if (names.includes(key)) headers = names;
      continue;
    }
    if (cells.every((s) => /^:?-+:?$/.test(s))) continue;
    if (cells.length !== headers.length) {
      const hint = cells.length > headers.length ? " A literal | inside a cell must be written \\|." : "";
      errors.push("malformed table row (" + key + ")." + hint + " " + line);
      continue;
    }
    rows.push(Object.fromEntries(headers.map((name, i) => [name, cells[i]])));
  }
  return rows;
}

const EXIT_CODE = /(?:\bexit(?:\s*code)?|退出码)\s*[:：=]?\s*(-?\d+)\b/gi;
const PASSED_COUNT = /\b(\d+)\s+(?:tests?\s+)?passed\b/i;

/** Result cells hold a verdict, an observed exit code and/or test counts. Unknowns fail closed. */
export function resultMatches(actual, expected = "") {
  const expectedCodes = [...expected.matchAll(EXIT_CODE)].map((m) => Number(m[1]));
  const required = expectedCodes[0] ?? 0;
  if (expectedCodes.some((n) => n !== required)) return false;
  let value = stripBackticks(actual).toLowerCase();
  if (/^-?\d+$/.test(value)) value = "exit " + value;
  const codes = [...value.matchAll(EXIT_CODE)].map((m) => Number(m[1]));
  if (codes.some((code) => code !== required) || (required !== 0 && !codes.length)) return false;

  const passed = value.match(PASSED_COUNT)?.[1];
  const expectedCount = expected.match(PASSED_COUNT)?.[1];
  if (expectedCount !== undefined && passed !== expectedCount) return false;
  const success = /\b(?:pass(?:ed)?|ok|success)\b|通过|成功/i;
  const positive = codes.length > 0 || (passed ? Number(passed) > 0 : success.test(value));
  // Consume only supported result tokens. A leftover negation or a nonzero failure count blocks.
  const rest = value.replace(EXIT_CODE, " ").replace(PASSED_COUNT, " ")
    .replace(/\b0\s+(?:failed|failures?|errors?)\b/g, " ")
    .replace(/\b(?:all tests passed|tests? passed|pass(?:ed)?|ok|success)\b|(?:测试|全部)?(?:通过|成功)/g, " ")
    .replace(/\bin\s+\d+(?:\.\d+)?s\b/g, " ");
  return positive && /^[\s/|,，;；.。()（）]*$/.test(rest);
}

const COMMAND_HEADERS = {
  "命令/动作": "command", "command/action": "command", "预期结果": "expected", "expected result": "expected",
  "时间": "time", timestamp: "time", "退出码/结果": "result", "exit code/result": "result",
  "失败数": "failures", "failure count": "failures",
};

/** Read the approved final checks. Older changes can record an aggregate run in their final table. */
function verificationChecks(tasks, verification, summaries, errors, approvedAt) {
  tasks = markdownContent(tasks);
  verification = markdownContent(verification);
  const checks = new Map();
  function expect(command, expectation) {
    const key = stripBackticks(command);
    if (!key || isPlaceholder(key)) errors.push("missing concrete final verification command");
    if (!checks.has(key) || expectation) checks.set(key, expectation);
  }
  const finalSection = tasks.split(/^##[ \t]+(?:最终验证|Final verification)[ \t]*\r?$/im)[1]?.split(/^#{1,2} /m)[0];
  for (const row of tableRows(finalSection ?? "", "command", errors, COMMAND_HEADERS)) {
    if (!row.expected || isPlaceholder(row.expected)) errors.push("missing expected result for " + row.command);
    expect(row.command, row.expected);
  }
  // A final suite may cover several task-level checks. Without a final list use their own commands.
  const mustRun = tasks.match(/^[ \t]*-[ \t]*(?:必须执行的最终验证|Required final verification)[ \t]*[:：][ \t]*(.*)$/im)?.[1]?.trim();
  if (mustRun && !(checks.size && /^(?:见(?:下表|最终验证表)|see (?:below|final verification table))$/i.test(mustRun))) {
    expect(mustRun, "");
  }
  const taskExpected = new Map();
  for (const { block } of taskBlocks(tasks)) {
    const command = stripBackticks(block.match(FIELD_PATTERNS.command)?.[1] ?? "");
    taskExpected.set(command, block.match(FIELD_PATTERNS.expected)?.[1] ?? "");
  }
  if (!checks.size) for (const [command, expected] of taskExpected) expect(command, expected);

  const observed = new Map();
  const evidence = [];
  function record(command, time, result, failures) {
    command = stripBackticks(command ?? "");
    const expected = checks.get(command) || taskExpected.get(command) || "";
    if (!command || isPlaceholder(command)) errors.push("verification artifact missing command evidence");
    if (!time || !isRfc3339(time)) errors.push("verification time evidence must be RFC3339");
    else if (approvedAt && Date.parse(stripBackticks(time)) < Date.parse(approvedAt)) {
      errors.push("verification predates implementation approval for " + command);
    }
    if (!resultMatches(result ?? "", expected)) {
      errors.push("verification result for " + command + ": expected " + (expected || "pass / exit 0") +
        ", recorded " + (result || "(missing)"));
    }
    if (failures !== undefined && !/^0+$/.test(failures)) {
      errors.push("verification requires zero unexpected failures for " + command + ", recorded " + (failures || "(missing)"));
    }
    const prior = observed.get(command);
    const count = result?.match(PASSED_COUNT)?.[1];
    if (count !== undefined && prior?.count !== undefined && prior.count !== count) {
      errors.push("conflicting test counts for " + command);
    }
    observed.set(command, { expected, count: count ?? prior?.count });
    evidence.push(command + ": " + result);
  }
  let anchor = null;
  function finish() {
    if (anchor) record(anchor.command, anchor.time, anchor.result);
    anchor = null;
  }
  for (const line of verification.split(/\r?\n/)) {
    for (const [field, pattern] of Object.entries(VERIFICATION_PATTERNS)) {
      const match = line.match(pattern);
      if (!match) continue;
      if (anchor && field in anchor) finish();
      anchor ??= {};
      anchor[field] = match[1];
    }
  }
  finish();
  for (const row of tableRows(verification, "result", errors, COMMAND_HEADERS)) {
    if ("command" in row) record(row.command, row.time, row.result, row.failures);
  }
  if (!evidence.length) errors.push("verification artifact missing command/time/result evidence");
  for (const command of checks.keys()) {
    if (!observed.has(command)) errors.push("missing final verification evidence: " + command);
  }
  for (const line of summaries) {
    for (const [command, { expected, count }] of observed) {
      const suffix = line.slice(command.length).match(/^[ \t]*[:：][ \t]*(.*)$/);
      if (!line.startsWith(command) || !suffix) continue;
      const reportedCount = suffix[1].match(PASSED_COUNT)?.[1];
      if (!resultMatches(suffix[1], expected) ||
          (reportedCount !== undefined && count !== undefined && reportedCount !== count)) {
        errors.push("handoff evidence conflicts with verified result for " + command);
      }
    }
  }
  for (const line of verification.split(/\r?\n/)) {
    const gate = line.match(/^\s*-\s*(运行\/静态检查|是否达到已验证)\s*[:：]\s*(.+?)\s*$/);
    if (gate && !/^(是|通过|pass(?:ed)?|yes)$/i.test(gate[2])) errors.push("unresolved final gate: " + gate[1]);
  }
  return evidence;
}

/** The approved proposal and Plan (Quick uses tasks.md) determine G9's minimum coverage. */
function approvedVisualScope(changeDir, errors) {
  const contents = (file) => isFile(join(changeDir, file)) ? markdownContent(readFileSync(join(changeDir, file), "utf8")) : "";
  const proposal = contents("proposal.md");
  const design = contents("design.md");
  const matrix = design || contents("tasks.md");
  const states = new Map();
  const rows = tableRows(matrix, "required_for_verified", errors);
  const seen = new Set();
  for (const row of rows) {
    const flag = row.required_for_verified.toLowerCase();
    if (!row.id || isPlaceholder(row.id) || seen.has(row.id) || !["yes", "no"].includes(flag)) {
      errors.push("invalid or duplicate row in approved visual matrix: " + (row.id ?? "(missing id)"));
    }
    seen.add(row.id);
    if (flag === "yes") {
      if (!row.route || isPlaceholder(row.route) || !row.state || isPlaceholder(row.state)) {
        errors.push("G9 approved matrix requires route and state for " + row.id);
      }
      states.set(row.id, row);
    }
  }
  const profile = /^\s*\|\s*`?visual`?\s*\|\s*`?required`?\s*\|/im;
  return { states, required: states.size > 0 || profile.test(proposal) || profile.test(design) };
}

/** @param {string} value */
export function isPlaceholder(value) {
  return PLACEHOLDER.test(stripBackticks(value));
}

// Mirrors Python datetime.fromisoformat (with Z -> +00:00).
const RFC3339_RE =
  /^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?(Z|[+-]\d{2}:\d{2}(:\d{2})?)?)?$/;

/** @param {string} value */
export function isRfc3339(value) {
  const cleaned = stripBackticks(value);
  if (!RFC3339_RE.test(cleaned)) return false;
  const normalized = cleaned.replace(" ", "T").replace(/([+-]\d{2}:\d{2}):\d{2}$/, "$1");
  return !Number.isNaN(Date.parse(normalized));
}

/** @param {string} value */
function cleanVisualValue(value) {
  return stripBackticks(value).trim();
}

/** @param {string} text */
function visualTableMap(text) {
  /** @type {Record<string, string>} */
  const values = {};
  for (const line of text.split(/\r?\n/)) {
    const match = line.match(/^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|/);
    if (!match) continue;
    const key = cleanVisualValue(match[1]);
    if (!key || ["字段", "Id", "id", "---"].includes(key) || /^[-:]+$/.test(key)) continue;
    if (!(key in values)) values[key] = cleanVisualValue(match[2]);
  }
  return values;
}

/** @param {string} text @param {string} label */
function visualSectionValue(text, label) {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = text.match(new RegExp(`^-\\s*${escaped}\\s*[：:]\\s*(.+)$`, "im"));
  return match ? cleanVisualValue(match[1]) : null;
}

/** @param {string} text */
function requiredStateRows(text) {
  const heading = /^###\s+Required state evidence\s*$/im.exec(text);
  if (!heading) return [];
  const tail = text.slice((heading.index ?? 0) + heading[0].length);
  const nextHeading = tail.search(/^#{2,3}\s/m);
  const section = nextHeading >= 0 ? tail.slice(0, nextHeading) : tail;
  /** @type {string[] | null} */
  let headers = null;
  /** @type {Array<Record<string, string>>} */
  const rows = [];
  for (const line of section.split(/\r?\n/)) {
    if (!line.trim().startsWith("|")) continue;
    const cells = line.split("|").slice(1, -1).map(cleanVisualValue);
    if (cells.length < 2 || cells.every((cell) => /^[-:]+$/.test(cell))) continue;
    if (headers === null) {
      headers = cells.map((cell) => cell.toLowerCase());
      continue;
    }
    if (cells.length !== headers.length) continue;
    rows.push(Object.fromEntries(headers.map((header, index) => [header, cells[index]])));
  }
  return rows;
}

/** @param {string} path */
function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

/**
 * Validate the delivery-owned visual acceptance evidence used by G9.
 * @param {string} text
 * @param {string} expectedRevision
 * @param {{baseDir?: string, expectedChangeDir?: string, requiredStateIds?: string[], approvedStates?: Map<string, Record<string,string>>}} [options]
 * @returns {string[]}
 */
export function validateVisualEvidence(text, expectedRevision, options = {}) {
  /** @type {string[]} */
  const errors = [];
  const fields = visualTableMap(text);
  const required = {
    schema: "delivery-visual-evidence/v1",
    producer: "delivery-execute-verify",
    state_owner: "openspec_change",
    final_visual_result: "pass",
  };
  for (const [field, expected] of Object.entries(required)) {
    if ((fields[field] ?? "").toLowerCase() !== expected.toLowerCase()) {
      errors.push(`G9 visual report requires ${field}=${expected}`);
    }
  }
  const changeDir = fields.change_dir ?? "";
  if (!changeDir || isPlaceholder(changeDir)) {
    errors.push("G9 visual report requires a concrete change_dir");
  } else if (options.expectedChangeDir) {
    const actual = normalize(isAbsolute(changeDir) ? changeDir : resolve(options.baseDir ?? process.cwd(), changeDir));
    if (actual.toLowerCase() !== normalize(resolve(options.expectedChangeDir)).toLowerCase()) {
      errors.push("G9 visual report change_dir does not match the validated OpenSpec change");
    }
  }
  const expectedNorm = normalizeRevision(expectedRevision);
  const actualNorm = normalizeRevision(fields.source_artifact_revision ?? "");
  if (!expectedNorm) {
    errors.push("G9 expected visual revision must be 64-hex");
  } else if (actualNorm !== expectedNorm) {
    errors.push("G9 visual report source_artifact_revision does not match the approved artifact revision");
  }
  if (!new Set(["strict_parity", "consistency_review", "spec_assertion"]).has(fields.assessment_mode ?? "")) {
    errors.push("G9 visual report requires assessment_mode=strict_parity, consistency_review, or spec_assertion");
  }
  for (const field of [
    "adapter / browser",
    "viewport / device_scale_factor",
    "locale / timezone / theme",
    "font_ready_condition",
    "animation_policy",
    "data_fixture / dynamic_masks",
  ]) {
    const value = fields[field] ?? "";
    if (!value || isPlaceholder(value)) errors.push(`G9 visual report capture context missing ${field}`);
  }
  const gateReference = visualSectionValue(text, "Implementation gate reference");
  if (gateReference === null || !gateReference || isPlaceholder(gateReference)) {
    errors.push("G9 visual report requires an implementation gate reference");
  } else {
    const match = gateReference.match(/^([^/]+?)\s*\/\s*([^/]+?)\s*\/\s*((?:sha256:)?[0-9a-f]{64})$/i);
    if (
      !match ||
      !match[1].trim() ||
      !isRfc3339(match[2].trim()) ||
      normalizeRevision(match[3]) !== expectedNorm
    ) {
      errors.push("G9 implementation gate reference must be approver / RFC3339 / approved revision");
    }
  }
  const mode = fields.assessment_mode ?? "";
  const isNotApplicable = (/** @type {string | undefined} */ value) => (value ?? "").trim().toLowerCase() === "n/a";
  const baseline = visualSectionValue(text, "baseline_source / substitute_standard");
  if (mode === "spec_assertion") {
    if (!isNotApplicable(baseline ?? undefined)) errors.push("G9 baseline must be n/a for spec_assertion");
  } else if (mode === "consistency_review") {
    const parts = (baseline ?? "").split("|").map((part) => part.trim());
    const reference = parts[0]?.startsWith("approved-substitute:") ? parts[0].slice("approved-substitute:".length) : "";
    if (
      !nonEmptyVisual(reference) ||
      isPlaceholder(reference) ||
      !nonEmptyVisual(parts[1]) ||
      isPlaceholder(parts[1]) ||
      normalizeRevision(parts[2]) !== expectedNorm
    ) {
      errors.push("G9 baseline must be approved-substitute:<reference> | approver | revision");
    }
  } else if (baseline === null || isNotApplicable(baseline) || isPlaceholder(baseline)) {
    errors.push("G9 baseline must be an image path and digest for strict_parity");
  } else {
    const parts = baseline.split("|").map((part) => part.trim());
    const pathValue = parts[0] ?? "";
    const digestValue = parts[1] ?? "";
    const absolute = isAbsolute(pathValue) ? pathValue : resolve(options.baseDir ?? process.cwd(), pathValue);
    if (!pathValue || !REVISION.test(digestValue) || !existsSync(absolute) || !IMAGE_EXTENSION.test(pathValue) || (existsSync(absolute) && sha256(absolute) !== digestValue.toLowerCase())) {
      errors.push("G9 baseline must be image-path | sha256-digest");
    }
  }
  const stateRows = requiredStateRows(text);
  if (stateRows.length < 1) {
    errors.push("G9 visual report requires at least one required-state evidence row");
  } else {
    const textColumns = ["id", "route", "state", "current_path", "current_digest", "policy", "result"];
    const ids = [];
    const stateKeys = [];
    const currentDigests = [];
    const diffDigests = [];
    for (const [index, row] of stateRows.entries()) {
      const label = `G9 required-state row ${index + 1}`;
      for (const column of textColumns) {
        if (!nonEmptyVisual(row[column]) || isPlaceholder(row[column])) errors.push(`${label} requires ${column}`);
      }
      if (mode === "spec_assertion") {
        if (!nonEmptyVisual(row.assertion) || isPlaceholder(row.assertion)) errors.push(`${label} requires assertion`);
        for (const column of ["baseline_path", "baseline_digest", "diff_path", "diff_digest"]) {
          if (!isNotApplicable(row[column])) errors.push(`${label} ${column} must be n/a`);
        }
      }
      const planned = options.approvedStates?.get(row.id);
      if (planned && (row.route !== planned.route || row.state !== planned.state)) {
        errors.push("G9 " + row.id + " must match approved route/state " + planned.route + " / " + planned.state);
      }
      ids.push(row.id);
      stateKeys.push(`${row.route}::${row.state}`);
      currentDigests.push(row.current_digest);
      if (!isNotApplicable(row.diff_digest)) diffDigests.push(row.diff_digest);
      if (!new Set(["strict", "tolerance_bound", "explicitly_accepted"]).has((row.policy ?? "").toLowerCase())) {
        errors.push(`${label} policy must be strict, tolerance_bound, or explicitly_accepted`);
      }
      if ((row.result ?? "").toLowerCase() !== "pass") errors.push(`${label} result must be pass`);
      const imagePairs =
        mode === "spec_assertion"
          ? [["current_path", "current_digest"]]
          : [["baseline_path", "baseline_digest"], ["current_path", "current_digest"], ["diff_path", "diff_digest"]];
      for (const [pathColumn, digestColumn] of imagePairs) {
        const pathValue = row[pathColumn] ?? "";
        const digestValue = row[digestColumn] ?? "";
        const absolute = isAbsolute(pathValue) ? pathValue : resolve(options.baseDir ?? process.cwd(), pathValue);
        if (!IMAGE_EXTENSION.test(pathValue)) errors.push(`${label} ${pathColumn} must be an image artifact`);
        if (!REVISION.test(digestValue)) errors.push(`${label} ${digestColumn} must be SHA-256`);
        if (!existsSync(absolute)) errors.push(`${label} ${pathColumn} does not exist`);
        else if (REVISION.test(digestValue) && sha256(absolute) !== digestValue.toLowerCase()) {
          errors.push(`${label} ${digestColumn} does not match file contents`);
        }
      }
    }
    if (new Set(ids).size !== ids.length) errors.push("G9 required-state ids must be unique");
    if (new Set(stateKeys).size !== stateKeys.length) errors.push("G9 required-state route/state pairs must be unique");
    if (new Set(currentDigests).size !== currentDigests.length) errors.push("G9 required-state current artifacts must be distinct");
    if (new Set(diffDigests).size !== diffDigests.length) errors.push("G9 required-state diff artifacts must be distinct");
  }
  for (const id of options.requiredStateIds ?? []) {
    if (!stateRows.some((row) => row.id === id)) errors.push(`G9 missing required state id: ${id}`);
  }
  return errors;
}

/** @param {unknown} value */
function nonEmptyVisual(value) {
  return typeof value === "string" && value.trim().length > 0;
}

/** @param {string} p */
function isFile(p) {
  try {
    return statSync(p).isFile();
  } catch {
    return false;
  }
}

/** @param {string} p */
function isDir(p) {
  try {
    return statSync(p).isDirectory();
  } catch {
    return false;
  }
}

function main() {
  const args = process.argv.slice(2);
  /** @type {{tasks: string | null, verification: string | null, repoRoot: string | null, claimVerified: boolean, visualRequired: boolean, visualReport: string | null, expectedVisualRevision: string | null, requiredStateIds: string[]}} */
  const opts = {
    tasks: null,
    verification: null,
    repoRoot: null,
    claimVerified: false,
    visualRequired: false,
    visualReport: null,
    expectedVisualRevision: null,
    requiredStateIds: [],
  };
  /** @type {string[]} */
  const positional = [];
  for (let i = 0; i < args.length; i += 1) {
    switch (args[i]) {
      case "--tasks":
        opts.tasks = args[++i];
        break;
      case "--verification":
        opts.verification = args[++i];
        break;
      case "--repo-root":
        opts.repoRoot = args[++i];
        break;
      case "--claim-verified":
        opts.claimVerified = true;
        break;
      case "--visual-required":
        opts.visualRequired = true;
        break;
      case "--visual-report":
        opts.visualReport = args[++i];
        break;
      case "--expected-visual-revision":
        opts.expectedVisualRevision = args[++i];
        break;
      case "--required-state-ids":
        opts.requiredStateIds = (args[++i] ?? "").split(",").map((id) => id.trim()).filter((id) => id.length > 0);
        break;
      default:
        positional.push(args[i]);
    }
  }
  if (positional.length !== 1) {
    console.error(
      "usage: node validate_delivery_change.mjs <change_dir> [--tasks <path>] " +
        "[--verification <path>] [--repo-root <path>] [--claim-verified] " +
        "[--visual-report <path>] [--expected-visual-revision <assertion>] [--required-state-ids <additional-ids>]"
    );
    return 2;
  }

  const changeDir = resolve(positional[0]);
  if (!isDir(changeDir)) {
    console.error("ERROR: change directory does not exist: " + changeDir);
    return 2;
  }
  const { errors } = checkChange(changeDir, opts);
  if (errors.length) {
    for (const error of errors) console.error("ERROR: " + error);
    return 1;
  }
  console.log("PASS: delivery change checks passed");
  return 0;
}

/**
 * @param {string} changeDir
 * @param {{tasks?: string|null, verification?: string|null, repoRoot?: string|null, claimVerified?: boolean,
 *   visualRequired?: boolean, visualReport?: string|null, expectedVisualRevision?: string|null,
 *   requiredStateIds?: string[], summaries?: string[]}} opts
 */
export function checkChange(changeDir, opts) {
  const errors = [];
  let evidence = [];
  const tasksPath = resolve(opts.tasks ?? join(changeDir, "tasks.md"));
  const verificationPath = resolve(opts.verification ?? join(changeDir, "verification.md"));

  /** @type {Array<{status: string, block: string}>} */
  let blocks = [];
  let tasksText = "";
  if (!isFile(tasksPath)) {
    errors.push(`tasks artifact missing: ${tasksPath}`);
  } else {
    tasksText = readFileSync(tasksPath, "utf-8");
    blocks = taskBlocks(tasksText);
    if (blocks.length === 0) {
      errors.push("tasks artifact has no checkbox task blocks");
    }
    blocks.forEach(({ block }, index) => {
      const number = index + 1;
      for (const [field, pattern] of Object.entries(FIELD_PATTERNS)) {
        const match = block.match(pattern);
        if (!match || isPlaceholder(match[1])) {
          errors.push(`task ${number} missing non-empty ${field} field`);
        }
      }
    });
  }

  if (!skipSpecsEnabled(changeDir) && listSpecFiles(changeDir).length > 0) {
    for (const name of requirementNames(changeDir)) {
      const traced = blocks.some((block) => {
        const match = block.block.match(FIELD_PATTERNS.scenario);
        return Boolean(match && match[1].includes(name));
      });
      if (!traced) errors.push(`requirement not traced by any task: ${name}`);
    }
  }

  if (opts.repoRoot) {
    const repoRoot = resolve(opts.repoRoot);
    for (const name of ["brief.md", "workflow-state.yaml"]) {
      const candidate = join(repoRoot, name);
      if (existsSync(candidate)) {
        errors.push(`possible competing root state source: ${candidate}`);
      }
    }
  }

  const proposal = join(changeDir, "proposal.md");
  const impl = opts.claimVerified && isFile(proposal) ? parseGateRecord(readFileSync(proposal, "utf8")).impl : null;
  if (opts.claimVerified) {
    const incomplete = blocks
      .map(({ status }, index) => ({ status, number: index + 1 }))
      .filter(({ status }) => status === " ")
      .map(({ number }) => number);
    if (incomplete.length) {
      errors.push(`verified claim has incomplete tasks: ${incomplete.join(", ")}`);
    }
    const open = openCheckboxes(tasksText);
    if (open.length) {
      errors.push(
        `verified claim has open checkboxes (OpenSpec archive counts them): ${open
          .map((item) => `line ${item.line}`)
          .join(", ")}`
      );
    }
    if (!isFile(verificationPath)) {
      errors.push(`verification artifact missing: ${verificationPath}`);
    } else {
      const verification = readFileSync(verificationPath, "utf-8");
      evidence = verificationChecks(tasksText, verification, opts.summaries ?? [], errors, impl?.approvedAt);
    }
  }

  const scope = (opts.claimVerified || opts.visualRequired || opts.visualReport)
    ? approvedVisualScope(changeDir, errors) : { required: false, states: new Map() };
  const required = scope.required || !!opts.visualRequired || !!opts.visualReport;
  let visualEvidence = { required: false, report: null, source_artifact_revision: null, g9: "not_required" };
  if (required) {
    if (!scope.states.size && opts.claimVerified) errors.push("G9 requires state IDs in the approved visual matrix");
    if (!opts.visualReport) {
      errors.push("G9 visual report path is required when visual acceptance is required");
    } else {
      const path = resolve(opts.visualReport);
      let revision = normalizeRevision(opts.expectedVisualRevision);
      if (opts.claimVerified) {
        const approved = normalizeRevision(impl?.revision);
        if (impl?.status !== "approved" || approved !== hashChange(changeDir).revision) {
          errors.push("G9 implementation gate missing or stale");
        }
        if (opts.expectedVisualRevision && revision !== approved) {
          errors.push("G9 caller revision differs from the approved implementation revision");
        }
        revision = approved;
      }
      if (!isFile(path)) errors.push("G9 visual report missing: " + path);
      else errors.push(...validateVisualEvidence(readFileSync(path, "utf8"), revision ?? "", {
        baseDir: dirname(path), expectedChangeDir: changeDir,
        approvedStates: scope.states,
        requiredStateIds: [...new Set([...scope.states.keys(), ...(opts.requiredStateIds ?? [])])],
      }));
      visualEvidence = { required: true, report: path, source_artifact_revision: revision, g9: "pass" };
    }
  }
  return { errors, evidence, visualEvidence };
}

if (
  process.argv[1] && process.argv[1] !== "-" && existsSync(resolve(process.argv[1])) &&
  pathToFileURL(realpathSync(resolve(process.argv[1]))).href.toLowerCase() ===
    pathToFileURL(realpathSync(fileURLToPath(import.meta.url))).href.toLowerCase()
) {
  process.exit(main());
}
