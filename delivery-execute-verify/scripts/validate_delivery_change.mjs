#!/usr/bin/env node
// @ts-check
/**
 * Run deterministic, non-mutating checks on a Delivery/OpenSpec change directory.
 * Zero dependencies (Node >= 18).
 *
 * Usage:
 *   node validate_delivery_change.mjs <change_dir> [--tasks <path>] [--verification <path>]
 *                                     [--repo-root <path>] [--claim-verified]
 *                                     [--visual-required --visual-report <path>
 *                                      --expected-visual-revision <64-hex>]
 */

import { createHash } from "node:crypto";
import { readFileSync, statSync, existsSync, realpathSync } from "node:fs";
import { resolve, join, dirname, isAbsolute, normalize } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import process from "node:process";

export const TASK_START = /^- \[(?<status>[ xX])\] .+$/m;
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
};
export const VERIFICATION_PATTERNS = {
  command: /^\s*(?:[-*]\s*)?(?:命令(?:\/动作)?|command(?:\/action)?)\s*[:：]\s*(\S.*)$/im,
  time: /^\s*(?:[-*]\s*)?(?:时间|timestamp|date)\s*[:：]\s*(\S.*)$/im,
  result: /^\s*(?:[-*]\s*)?(?:退出码\/结果|结果|退出码|result|exit\s*code)\s*[:：]\s*(\S.*)$/im,
};
const PLACEHOLDER = /^(?:<[^>]+>|tbd|todo|n\/?a|none|null|待定|待补)$/i;
const REVISION = /^[0-9a-f]{64}$/i;
const IMAGE_EXTENSION = /\.(png|jpe?g|webp|ppm)$/i;
const VISUAL_CHECKS = ["V0", "V1", "V2", "V3", "V4", "P1", "P2", "P3", "P4", "P5", "P6", "P7"];

/** @param {string} value */
function stripBackticks(value) {
  return value.trim().replace(/^`+|`+$/g, "");
}

/**
 * Split tasks text into checkbox task blocks.
 * @param {string} text
 * @returns {Array<{status: string, block: string}>}
 */
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

/**
 * @param {string} text @param {string[]} patterns
 */
export function containsAny(text, patterns) {
  return patterns.some((pattern) => new RegExp(pattern, "im").test(text));
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
function visualChecklist(text) {
  /** @type {Record<string, string>} */
  const rows = {};
  for (const line of text.split(/\r?\n/)) {
    const match = line.match(/^\|\s*`?([VP]\d+)`?\s*\|\s*([^|]+?)\s*\|/i);
    if (match) rows[match[1].toUpperCase()] = cleanVisualValue(match[2]).toLowerCase();
  }
  return rows;
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
 * @param {{baseDir?: string, expectedChangeDir?: string}} [options]
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
    implementation_authority: "delivery",
    analysis_status: "complete",
    remediation_status: "done",
    visual_acceptance_required: "yes",
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
  if (!REVISION.test(expectedRevision)) {
    errors.push("G9 expected visual revision must be 64-hex");
  } else if ((fields.source_artifact_revision ?? "").toLowerCase() !== expectedRevision.toLowerCase()) {
    errors.push("G9 visual report source_artifact_revision does not match the approved artifact revision");
  }
  if (!new Set(["strict_parity", "consistency_review"]).has(fields.assessment_mode ?? "")) {
    errors.push("G9 visual report requires assessment_mode=strict_parity or consistency_review");
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
    const match = gateReference.match(/^([^/]+?)\s*\/\s*([^/]+?)\s*\/\s*([0-9a-f]{64})$/i);
    if (!match || !match[1].trim() || !isRfc3339(match[2].trim()) || match[3].toLowerCase() !== expectedRevision.toLowerCase()) {
      errors.push("G9 implementation gate reference must be approver / RFC3339 / approved revision");
    }
  }
  const baseline = visualSectionValue(text, "baseline_source / substitute_standard");
  if (baseline === null || isPlaceholder(baseline)) {
    errors.push("G9 visual report requires a traceable baseline or approved substitute standard");
  } else if (!baseline.startsWith("approved-substitute:")) {
    const parts = baseline.split("|").map((part) => part.trim());
    const pathValue = parts[0] ?? "";
    const digestValue = parts[1] ?? "";
    const absolute = isAbsolute(pathValue) ? pathValue : resolve(options.baseDir ?? process.cwd(), pathValue);
    if (!pathValue || !REVISION.test(digestValue) || !existsSync(absolute) || !IMAGE_EXTENSION.test(pathValue) || (existsSync(absolute) && sha256(absolute) !== digestValue.toLowerCase())) {
      errors.push("G9 baseline must be image-path | sha256-digest, or an approved-substitute reference");
    }
  } else {
    const parts = baseline.split("|").map((part) => part.trim());
    if (!nonEmptyVisual(parts[0]?.slice("approved-substitute:".length)) || !nonEmptyVisual(parts[1]) || parts[2]?.toLowerCase() !== expectedRevision.toLowerCase()) {
      errors.push("G9 approved substitute must be approved-substitute:<reference> | approver | approved revision");
    }
  }
  const checks = visualChecklist(text);
  for (const check of VISUAL_CHECKS) {
    if (checks[check] !== "pass") errors.push(`G9 visual report requires ${check}=pass`);
  }
  const stateRows = requiredStateRows(text);
  if (stateRows.length < 5) {
    errors.push("G9 visual report requires at least five required-state evidence rows");
  } else {
    const requiredColumns = ["id", "route", "state", "baseline_path", "baseline_digest", "current_path", "current_digest", "diff_path", "diff_digest", "policy", "result"];
    const ids = [];
    const stateKeys = [];
    const currentDigests = [];
    const diffDigests = [];
    for (const [index, row] of stateRows.entries()) {
      const label = `G9 required-state row ${index + 1}`;
      for (const column of requiredColumns) {
        if (!nonEmptyVisual(row[column]) || isPlaceholder(row[column])) errors.push(`${label} requires ${column}`);
      }
      ids.push(row.id);
      stateKeys.push(`${row.route}::${row.state}`);
      currentDigests.push(row.current_digest);
      diffDigests.push(row.diff_digest);
      if (!new Set(["strict", "tolerance_bound", "explicitly_accepted"]).has((row.policy ?? "").toLowerCase())) {
        errors.push(`${label} policy must be strict, tolerance_bound, or explicitly_accepted`);
      }
      if ((row.result ?? "").toLowerCase() !== "pass") errors.push(`${label} result must be pass`);
      for (const [pathColumn, digestColumn] of [["baseline_path", "baseline_digest"], ["current_path", "current_digest"], ["diff_path", "diff_digest"]]) {
        const pathValue = row[pathColumn] ?? "";
        const digestValue = row[digestColumn] ?? "";
        const absolute = isAbsolute(pathValue) ? pathValue : resolve(options.baseDir ?? process.cwd(), pathValue);
        if (!IMAGE_EXTENSION.test(pathValue)) errors.push(`${label} ${pathColumn} must be an image artifact`);
        if (!REVISION.test(digestValue)) errors.push(`${label} ${digestColumn} must be SHA-256`);
        if (!existsSync(absolute)) errors.push(`${label} ${pathColumn} does not exist`);
        else if (REVISION.test(digestValue) && sha256(absolute) !== digestValue.toLowerCase()) errors.push(`${label} ${digestColumn} does not match file contents`);
      }
    }
    if (new Set(ids).size !== ids.length) errors.push("G9 required-state ids must be unique");
    if (new Set(stateKeys).size !== stateKeys.length) errors.push("G9 required-state route/state pairs must be unique");
    if (new Set(currentDigests).size !== currentDigests.length) errors.push("G9 required-state current artifacts must be distinct");
    if (new Set(diffDigests).size !== diffDigests.length) errors.push("G9 required-state diff artifacts must be distinct");
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
  /** @type {{tasks: string | null, verification: string | null, repoRoot: string | null, claimVerified: boolean, visualRequired: boolean, visualReport: string | null, expectedVisualRevision: string | null}} */
  const opts = {
    tasks: null,
    verification: null,
    repoRoot: null,
    claimVerified: false,
    visualRequired: false,
    visualReport: null,
    expectedVisualRevision: null,
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
      default:
        positional.push(args[i]);
    }
  }
  if (positional.length !== 1) {
    console.error(
      "usage: node validate_delivery_change.mjs <change_dir> [--tasks <path>] " +
        "[--verification <path>] [--repo-root <path>] [--claim-verified] " +
        "[--visual-required --visual-report <path> --expected-visual-revision <64-hex>]"
    );
    return 2;
  }

  /** @type {string[]} */
  const errors = [];
  const changeDir = resolve(positional[0]);
  if (!isDir(changeDir)) {
    console.error(`ERROR: change directory does not exist: ${changeDir}`);
    return 2;
  }

  const tasksPath = resolve(opts.tasks ?? join(changeDir, "tasks.md"));
  const verificationPath = resolve(opts.verification ?? join(changeDir, "verification.md"));

  /** @type {Array<{status: string, block: string}>} */
  let blocks = [];
  if (!isFile(tasksPath)) {
    errors.push(`tasks artifact missing: ${tasksPath}`);
  } else {
    const tasksText = readFileSync(tasksPath, "utf-8");
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

  if (opts.repoRoot) {
    const repoRoot = resolve(opts.repoRoot);
    for (const name of ["brief.md", "workflow-state.yaml"]) {
      const candidate = join(repoRoot, name);
      if (existsSync(candidate)) {
        errors.push(`possible competing root state source: ${candidate}`);
      }
    }
  }

  if (opts.claimVerified) {
    const incomplete = blocks
      .map(({ status }, index) => ({ status, number: index + 1 }))
      .filter(({ status }) => status === " ")
      .map(({ number }) => number);
    if (incomplete.length) {
      errors.push(`verified claim has incomplete tasks: ${incomplete.join(", ")}`);
    }
    if (!isFile(verificationPath)) {
      errors.push(`verification artifact missing: ${verificationPath}`);
    } else {
      const verification = readFileSync(verificationPath, "utf-8");
      /** @type {Record<string, string>} */
      const evidence = {};
      for (const [label, pattern] of Object.entries(VERIFICATION_PATTERNS)) {
        const match = verification.match(pattern);
        if (!match || isPlaceholder(match[1])) {
          errors.push(`verification artifact missing ${label} evidence`);
        } else {
          evidence[label] = match[1];
        }
      }
      if ("time" in evidence && !isRfc3339(evidence.time)) {
        errors.push("verification time evidence must be RFC3339");
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
        ])
      ) {
        errors.push("verification result must state pass/fail or an exit code");
      }
    }
  }

  if (opts.visualRequired) {
    if (!opts.visualReport) {
      errors.push("G9 visual report path is required when visual acceptance is required");
    } else {
      const visualReportPath = resolve(opts.visualReport);
      if (!isFile(visualReportPath)) {
        errors.push(`G9 visual report missing: ${visualReportPath}`);
      } else {
        errors.push(
          ...validateVisualEvidence(
            readFileSync(visualReportPath, "utf-8"),
            opts.expectedVisualRevision ?? "",
            { baseDir: dirname(visualReportPath), expectedChangeDir: changeDir }
          )
        );
      }
    }
  }

  if (errors.length) {
    for (const error of errors) console.error(`ERROR: ${error}`);
    return 1;
  }
  console.log("PASS: delivery change checks passed");
  return 0;
}

if (
  process.argv[1] && process.argv[1] !== "-" && existsSync(resolve(process.argv[1])) &&
  pathToFileURL(realpathSync(resolve(process.argv[1]))).href.toLowerCase() ===
    pathToFileURL(realpathSync(fileURLToPath(import.meta.url))).href.toLowerCase()
) {
  process.exit(main());
}
