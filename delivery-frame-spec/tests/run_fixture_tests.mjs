#!/usr/bin/env node
// @ts-check
/**
 * P0-1 regression lock: run validate_handoff (hard profile) against the fixture set.
 *
 * Fixture naming convention:
 *   fixtures/pass-*.json  -> must validate PASS
 *   fixtures/neg-*.json   -> must validate FAIL (the R2/R3 negative probes)
 *
 * If a neg-* fixture starts passing, a guardrail was weakened: either restore it or add a
 * documented replacement control plus a new probe before merging.
 *
 * Zero dependencies (Node >= 18). Exit 0 = all expectations hold, 1 = regression.
 */

import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

import { validate } from "../scripts/validate_handoff.mjs";

const TESTS_DIR = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(TESTS_DIR, "fixtures");

function main() {
  let names;
  try {
    names = readdirSync(FIXTURES).filter((n) => n.endsWith(".json")).sort();
  } catch {
    names = [];
  }
  if (names.length === 0) {
    console.error(`ERROR: no fixtures found in ${FIXTURES}`);
    return 1;
  }

  let regressions = 0;
  for (const name of names) {
    const expectPass = name.startsWith("pass-");
    const data = JSON.parse(readFileSync(join(FIXTURES, name), "utf-8"));
    const errors = validate(data, "hard");
    const passed = errors.length === 0;
    const ok = passed === expectPass;
    console.log(
      `[${ok ? "OK " : "REGRESSION"}] ${name}: ${passed ? "PASS" : "FAIL"}` +
        ` (expected ${expectPass ? "PASS" : "FAIL"})`
    );
    if (!ok) {
      regressions += 1;
      for (const error of errors) console.log(`        - ${error}`);
    }
  }

  if (regressions) {
    console.error(`\nRESULT: ${regressions} regression(s) — do not merge`);
    return 1;
  }
  console.log(`\nRESULT: all ${names.length} fixture expectations hold`);
  return 0;
}

process.exit(main());
