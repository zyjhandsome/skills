#!/usr/bin/env node
// @ts-check
/**
 * One-command delivery-family self-check. Run before shipping the four delivery-* skills.
 *
 * Family suites, in order (always):
 *   1. test_family_integrity.mjs
 *   2. test_routing_and_session_overlay.mjs
 *   3. test_cli_entrypoints.mjs
 *   4. test_external_artifacts.mjs
 *   5. ../../delivery-execute-verify/tests/test_template_anchor_consistency.mjs
 *   6. ../../delivery-execute-verify/tests/test_visual_gate.mjs
 *   7. ../../delivery-execute-verify/tests/test_task_gate.mjs
 *   8. run_fixture_tests.mjs
 *   9. test_handoff_additive_checks.mjs
 *   10. test_single_chain.mjs
 *   11. test_run_all_scope.mjs
 *   12. test_revision_stability.mjs
 *   13. test_scaffold_quick_and_gate.mjs
 *   14. test_openspec_alignment.mjs
 *
 * Consumer playbook suite (only with --with-consumers, and only when found):
 *   docs/tests/run_all.mjs
 *
 * Exit 0 only when every suite passes. Zero dependencies (Node >= 18).
 */

import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

const TESTS_DIR = dirname(fileURLToPath(import.meta.url));
// Orchestration playbooks compose the delivery family; run their suites too when
// this skill lives in the full skills repo (skipped in standalone distribution).
// Node realpaths the main module, so a junction/symlink install may put docs/
// next to the invocation cwd rather than next to this file — probe both.
const DOCS_SUITE = [
  resolve(TESTS_DIR, "..", "..", "docs", "tests", "run_all.mjs"),
  resolve(process.cwd(), "docs", "tests", "run_all.mjs"),
].find((candidate) => existsSync(candidate));
const WITH_CONSUMERS = process.argv.includes("--with-consumers");
const SUITES = [
  join(TESTS_DIR, "test_family_integrity.mjs"),
  join(TESTS_DIR, "test_routing_and_session_overlay.mjs"),
  join(TESTS_DIR, "test_cli_entrypoints.mjs"),
  join(TESTS_DIR, "test_external_artifacts.mjs"),
  resolve(TESTS_DIR, "..", "..", "delivery-execute-verify", "tests", "test_template_anchor_consistency.mjs"),
  resolve(TESTS_DIR, "..", "..", "delivery-execute-verify", "tests", "test_visual_gate.mjs"),
  resolve(TESTS_DIR, "..", "..", "delivery-execute-verify", "tests", "test_task_gate.mjs"),
  join(TESTS_DIR, "run_fixture_tests.mjs"),
  join(TESTS_DIR, "test_handoff_additive_checks.mjs"),
  join(TESTS_DIR, "test_single_chain.mjs"),
  join(TESTS_DIR, "test_run_all_scope.mjs"),
  join(TESTS_DIR, "test_revision_stability.mjs"),
  join(TESTS_DIR, "test_scaffold_quick_and_gate.mjs"),
  join(TESTS_DIR, "test_openspec_alignment.mjs"),
  ...(WITH_CONSUMERS && DOCS_SUITE ? [DOCS_SUITE] : []),
];

function main() {
  /** @type {string[]} */
  const failed = [];
  for (const suite of SUITES) {
    console.log(`\n=== ${basename(suite)} ===`);
    const result = spawnSync(process.execPath, [suite], { stdio: "inherit" });
    if (result.status !== 0) failed.push(basename(suite));
  }
  if (failed.length) {
    console.error(`\nSELF-CHECK FAILED: ${failed.join(", ")}`);
    return 1;
  }
  console.log(`\nSELF-CHECK PASSED: all ${SUITES.length} suites green — family is shippable`);
  return 0;
}

process.exit(main());
