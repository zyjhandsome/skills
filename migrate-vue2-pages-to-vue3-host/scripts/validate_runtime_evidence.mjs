#!/usr/bin/env node
// @ts-check

import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const SHA256 = /^(?:sha256:)?[0-9a-f]{64}$/i;
const DISPOSITIONS = new Set(["reuse-B", "reuse-B-major-review", "add-to-B", "replace-as-B-stack", "copy-local", "retire", "unknown"]);

/** @param {unknown} value */
function nonEmpty(value) {
  return typeof value === "string" && value.trim().length > 0;
}

/**
 * Validate runtime-compatibility-evidence/v1 readiness and pass claims.
 * @param {any} evidence
 * @param {{currentSourceRevision?: string, currentHostRevision?: string}} [options]
 */
export function validateRuntimeEvidence(evidence, options = {}) {
  /** @type {string[]} */
  const errors = [];
  const require = (condition, message) => { if (!condition) errors.push(message); };

  require(evidence?.schema === "runtime-compatibility-evidence/v1", "schema must be runtime-compatibility-evidence/v1");
  require(evidence?.producer === "migrate-vue2-pages-to-vue3-host", "producer must be migrate-vue2-pages-to-vue3-host");
  require(evidence?.authority === "domain_evidence_only", "authority must be domain_evidence_only");
  require(nonEmpty(evidence?.source_revision), "source_revision is required");
  require(nonEmpty(evidence?.host_revision), "host_revision is required");
  if (options.currentSourceRevision !== undefined) require(evidence?.source_revision === options.currentSourceRevision, "source revision is stale");
  if (options.currentHostRevision !== undefined) require(evidence?.host_revision === options.currentHostRevision, "host revision is stale");

  for (const [name, runtime] of [["source_runtime", evidence?.source_runtime], ["host_runtime", evidence?.host_runtime]]) {
    for (const key of ["required_node", "package_manager", "lock_owner_format", "selected_runtime", "isolation_method"]) {
      require(nonEmpty(runtime?.[key]), `${name}.${key} is required`);
    }
    require(Array.isArray(runtime?.evidence) && runtime.evidence.length > 0, `${name}.evidence is required`);
    require(["ready", "blocked", "unknown"].includes(runtime?.command_readiness), `${name}.command_readiness is invalid`);
  }

  require(Array.isArray(evidence?.dependency_demands), "dependency_demands must be an array");
  for (const [index, demand] of (evidence?.dependency_demands || []).entries()) {
    const label = `dependency_demands[${index}]`;
    require(nonEmpty(demand?.package), `${label}.package is required`);
    require(nonEmpty(demand?.source_exact_version), `${label}.source_exact_version is required`);
    require(nonEmpty(demand?.license), `${label}.license is required`);
    require(DISPOSITIONS.has(demand?.disposition), `${label}.disposition is invalid`);
    require(nonEmpty(demand?.decision_status), `${label}.decision_status is required`);
  }
  for (const key of ["approved_runtime_actions", "restoration_plan", "verification_commands"]) {
    require(Array.isArray(evidence?.[key]), `${key} must be an array`);
  }
  require(["not_run", "fail", "pass"].includes(evidence?.final_runtime_result), "final_runtime_result is invalid");

  if (evidence?.final_runtime_result === "pass") {
    require(evidence?.source_runtime?.command_readiness === "ready", "runtime pass requires source command_readiness=ready");
    require(evidence?.host_runtime?.command_readiness === "ready", "runtime pass requires host command_readiness=ready");
    for (const [name, runtime] of [["source_runtime", evidence?.source_runtime], ["host_runtime", evidence?.host_runtime]]) {
      for (const key of ["required_node", "package_manager", "lock_owner_format", "selected_runtime", "isolation_method"]) {
        require(!["unknown", "none", "conflict", "blocked"].includes(String(runtime?.[key]).toLowerCase()), `runtime pass requires resolved ${name}.${key}`);
      }
    }
    require(!(evidence?.dependency_demands || []).some((row) => row?.disposition === "unknown" || row?.decision_status !== "approved"), "runtime pass cannot contain unresolved dependency demands");
    if ((evidence?.approved_runtime_actions || []).length > 0) {
      require((evidence?.restoration_plan || []).length > 0, "approved runtime actions require a restoration_plan");
    }
    const commands = evidence?.verification_commands || [];
    require(commands.some((row) => row?.repository === "source"), "runtime pass requires source verification command evidence");
    require(commands.some((row) => row?.repository === "host"), "runtime pass requires host verification command evidence");
    for (const [index, row] of commands.entries()) {
      const label = `verification_commands[${index}]`;
      require(["source", "host"].includes(row?.repository), `${label}.repository is invalid`);
      for (const key of ["command", "working_directory", "runtime", "timestamp"]) require(nonEmpty(row?.[key]), `${label}.${key} is required`);
      require(nonEmpty(row?.timestamp) && !Number.isNaN(Date.parse(row.timestamp)), `${label}.timestamp must be RFC3339`);
      require(row?.exit_code === 0, `${label}.exit_code must be 0`);
      require(SHA256.test(row?.output_digest ?? ""), `${label}.output_digest must be SHA-256`);
    }
  }
  return errors;
}

function main() {
  const path = process.argv[2];
  if (!path) {
    console.error("Usage: node scripts/validate_runtime_evidence.mjs <runtime-evidence.json> [current-source-revision] [current-host-revision]");
    return 2;
  }
  let evidence;
  try {
    evidence = JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    console.error(`FAIL: cannot read evidence: ${error instanceof Error ? error.message : String(error)}`);
    return 2;
  }
  const errors = validateRuntimeEvidence(evidence, {
    currentSourceRevision: process.argv[3],
    currentHostRevision: process.argv[4],
  });
  if (errors.length) {
    console.error(`FAIL: ${errors.length} runtime evidence contract error(s)`);
    for (const error of errors) console.error(`- ${error}`);
    return 1;
  }
  console.log("PASS: runtime-compatibility-evidence/v1 is complete and pass-claim consistent");
  return 0;
}

if (import.meta.url === pathToFileURL(process.argv[1] || "").href) process.exit(main());
