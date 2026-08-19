#!/usr/bin/env node
// @ts-check
// Runs every docs playbook test suite so red playbook tests cannot go unnoticed.

import { spawnSync } from "node:child_process";
import { readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const suites = readdirSync(HERE)
  .filter((name) => name.startsWith("test_") && name.endsWith(".mjs"))
  .sort();

let failures = 0;
for (const suite of suites) {
  const result = spawnSync(process.execPath, [join(HERE, suite)], { stdio: "inherit" });
  if (result.status !== 0) {
    failures += 1;
    console.error(`FAIL: ${suite}`);
  }
}

if (failures > 0) {
  console.error(`${failures}/${suites.length} docs suites failed`);
  process.exit(1);
}
console.log(`PASS: ${suites.length}/${suites.length} docs suites`);
