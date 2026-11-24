import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const src = readFileSync(new URL("./run_all.mjs", import.meta.url), "utf8");
assert.ok(src.includes('process.argv.includes("--with-consumers")'), "consumer suites must be opt-in");
assert.ok(!/\.\.\.\(DOCS_SUITE \? \[DOCS_SUITE\] : \[\]\)/.test(src), "docs suite must not be appended unconditionally");
assert.ok(src.includes("test_run_all_scope.mjs"), "this suite must be registered");
console.log("PASS: run_all runs family suites by default; consumers are opt-in");
