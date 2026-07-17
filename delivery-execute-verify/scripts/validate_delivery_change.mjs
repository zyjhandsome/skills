#!/usr/bin/env node
// @ts-check
/**
 * Run deterministic, non-mutating checks on a Delivery/OpenSpec change directory.
 * Zero dependencies (Node >= 18).
 *
 * Usage:
 *   node validate_delivery_change.mjs <change_dir> [--tasks <path>] [--verification <path>]
 *                                     [--repo-root <path>] [--claim-verified]
 */

import { readFileSync, statSync, existsSync } from "node:fs";
import { resolve, join } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

export const TASK_START = /^- \[(?<status>[ xX])\] .+$/m;
// Field labels below are STABLE MACHINE ANCHORS shared with the Chinese/English templates
// (tasks-template.md, verification-template.md). Accept both ASCII ":" and fullwidth "："
// because the Chinese templates emit the fullwidth colon. Do not reword the labels in the
// templates without updating these patterns.
//
// Limited synonym set (delivery-family/1.3, P3-2): the aliases below are the near-synonym
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
  /** @type {{tasks: string | null, verification: string | null, repoRoot: string | null, claimVerified: boolean}} */
  const opts = { tasks: null, verification: null, repoRoot: null, claimVerified: false };
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
      default:
        positional.push(args[i]);
    }
  }
  if (positional.length !== 1) {
    console.error(
      "usage: node validate_delivery_change.mjs <change_dir> [--tasks <path>] " +
        "[--verification <path>] [--repo-root <path>] [--claim-verified]"
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

  if (errors.length) {
    for (const error of errors) console.error(`ERROR: ${error}`);
    return 1;
  }
  console.log("PASS: delivery change checks passed");
  return 0;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exit(main());
}
