import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { deriveRepoRoot, validate } from "../scripts/validate_handoff.mjs";

/** @param {string} name */
function clone(name) {
  return JSON.parse(readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8"));
}

const HEX = "ab".repeat(32);
const plan = clone("pass-plan-transition.json");
plan.source_revision.artifact_revision = `sha256:${HEX}`;
plan.gate_status.binds_to_revision = HEX.toUpperCase();
assert.deepEqual(validate(plan, "hard"), []);

plan.stage_payload.quality_profiles = { visual: "required" };
plan.stage_payload.visual_validation_plan = [];
assert.ok(validate(plan, "hard").some((error) => error.includes("visual_validation_plan")));

const exec = clone("pass-execute-verified.json");
assert.deepEqual(validate(exec, "hard"), []);
exec.source_revision.revision_algo = 2;
assert.ok(validate(exec, "hard").some((error) => error.includes("implementation_gate")));
exec.stage_payload.implementation_gate = {
  approved_by: "user",
  approved_at: "2026-11-24T10:00:00+08:00",
  binds_to_revision: "sha256:" + "cd".repeat(32),
};
assert.ok(validate(exec, "hard").some((error) => error.includes("stale")));
exec.stage_payload.visual_evidence = {
  required: true,
  report: "r.md",
  source_artifact_revision: null,
  g9: "not_required",
};
assert.ok(validate(exec, "hard").some((error) => error.includes("g9")));

exec.source_revision.artifact_revision = "sha256:" + HEX;
exec.stage_payload.implementation_gate.binds_to_revision = HEX;
exec.stage_payload.visual_evidence.g9 = "pass";
exec.stage_payload.visual_evidence.source_artifact_revision = "cd".repeat(32);
assert.ok(validate(exec, "hard").some((error) => error.includes("visual evidence revision")));
exec.stage_payload.visual_evidence.source_artifact_revision = HEX.toUpperCase();
assert.deepEqual(validate(exec, "hard").filter((error) => error.includes("visual evidence revision")), []);

const root = mkdtempSync(join(tmpdir(), "handoff-root-"));
assert.equal(deriveRepoRoot(join(root, "openspec", "changes", "x", "handoff.json"), "Z:/elsewhere"), root);
assert.equal(deriveRepoRoot(null, root), root);

console.log("PASS: additive handoff checks accept equivalent revisions and require visual and gate links");
