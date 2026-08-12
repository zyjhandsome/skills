#!/usr/bin/env node
// @ts-check

import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { validate } from "../scripts/validate_handoff.mjs";

const base = JSON.parse(readFileSync(new URL("./fixtures/pass-frame-transition.json", import.meta.url), "utf8"));
const sandbox = mkdtempSync(join(tmpdir(), "delivery-external-artifacts-"));
try {
  const packet = join(sandbox, "domain.json");
  writeFileSync(packet, "{}\n", "utf8");
  const digest = `sha256:${createHash("sha256").update(readFileSync(packet)).digest("hex")}`;
  const valid = structuredClone(base);
  valid.stage_payload.external_artifacts = [{ path: packet, digest, claims_used: ["runtime status"] }];
  assert.deepEqual(validate(valid, "hard", { baseDir: sandbox }), []);

  const missing = structuredClone(valid);
  missing.stage_payload.external_artifacts[0].path = join(sandbox, "missing.json");
  assert.ok(validate(missing, "hard", { baseDir: sandbox }).some((error) => error.includes("path does not exist")));

  const bogus = structuredClone(valid);
  bogus.stage_payload.external_artifacts[0].digest = "bogus";
  assert.ok(validate(bogus, "hard", { baseDir: sandbox }).some((error) => error.includes("sha256")));

  const tooMany = structuredClone(valid);
  tooMany.stage_payload.external_artifacts = Array.from({ length: 11 }, () => ({ path: packet, digest, claims_used: ["x"] }));
  assert.ok(validate(tooMany, "hard", { baseDir: sandbox }).some((error) => error.includes("at most 10")));

  const extra = structuredClone(valid);
  extra.stage_payload.external_artifacts[0].full_report = "forbidden";
  assert.ok(validate(extra, "hard", { baseDir: sandbox }).some((error) => error.includes("unsupported keys")));
} finally {
  rmSync(sandbox, { recursive: true, force: true });
}

console.log("PASS: external_artifacts paths, digests, limits, and field whitelist are enforced");
