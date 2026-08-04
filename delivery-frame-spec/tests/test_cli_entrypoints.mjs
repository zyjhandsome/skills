#!/usr/bin/env node
// @ts-check

import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

const TESTS_DIR = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(TESTS_DIR, "..", "..");
const SCRIPTS = [
  resolve(ROOT, "delivery-frame-spec", "scripts", "hash_change_artifacts.mjs"),
  resolve(ROOT, "delivery-frame-spec", "scripts", "delivery_scaffold.mjs"),
  resolve(ROOT, "delivery-frame-spec", "scripts", "validate_handoff.mjs"),
  resolve(ROOT, "delivery-execute-verify", "scripts", "validate_delivery_change.mjs"),
];

const failures = [];
for (const script of SCRIPTS) {
  const result = spawnSync(process.execPath, [script], { encoding: "utf-8" });
  const output = `${result.stdout ?? ""}${result.stderr ?? ""}`.trim();
  if (result.status === 0 || !output) {
    failures.push(`${script}: expected nonzero usage response, got status=${result.status}, output=${JSON.stringify(output)}`);
  } else {
    console.log(`[OK ] ${script}: CLI main executed (status ${result.status})`);
  }
}

if (failures.length) {
  for (const failure of failures) console.error(`ERROR: ${failure}`);
  process.exit(1);
}
console.log("PASS: delivery Node CLI entrypoints execute on this platform");
