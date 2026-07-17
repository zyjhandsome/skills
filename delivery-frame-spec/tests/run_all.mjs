#!/usr/bin/env node
// @ts-check
/**
 * One-command delivery-family self-check. Run before shipping the four delivery-* skills.
 *
 * Runs, in order:
 *   1. test_family_integrity.mjs         — references resolve, atomic set present, version majors
 *   2. ../../delivery-execute-verify/tests/test_template_anchor_consistency.mjs
 *                                        — machine anchors + limited synonym lock
 *   3. run_fixture_tests.mjs             — 12 pass/neg handoff fixtures (hard profile)
 *   4. test_single_chain.mjs             — Standard 4-stage chain + cascade + High slice
 *
 * Exit 0 only when every suite passes. Zero dependencies (Node >= 18).
 */

import { spawnSync } from "node:child_process";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

const TESTS_DIR = dirname(fileURLToPath(import.meta.url));
const SUITES = [
  join(TESTS_DIR, "test_family_integrity.mjs"),
  resolve(TESTS_DIR, "..", "..", "delivery-execute-verify", "tests", "test_template_anchor_consistency.mjs"),
  join(TESTS_DIR, "run_fixture_tests.mjs"),
  join(TESTS_DIR, "test_single_chain.mjs"),
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
