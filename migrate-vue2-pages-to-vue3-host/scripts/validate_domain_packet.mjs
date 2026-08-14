#!/usr/bin/env node
// @ts-check

import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { dirname, isAbsolute, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { validateRuntimeEvidence } from "./validate_runtime_evidence.mjs";
import { validateVisualEvidence } from "./validate_visual_evidence.mjs";

const SHA256 = /^sha256:[0-9a-f]{64}$/i;
const MODES = new Set(["assess", "design", "execute", "verify"]);
const AUTH_STATUSES = new Set(["missing", "stale", "approved"]);
const ROLLBACK_STATUSES = new Set(["missing", "designed", "tested", "retired"]);
const VERIFY_STATUSES = new Set(["not_run", "fail", "pass"]);

/** @param {unknown} value */
function nonEmpty(value) {
  return typeof value === "string" && value.trim().length > 0;
}

/** @param {unknown} value */
function object(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

/**
 * @param {unknown} value
 * @returns {unknown}
 */
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (!object(value)) return value;
  return Object.fromEntries(
    Object.keys(/** @type {Record<string, unknown>} */ (value))
      .sort()
      .map((key) => [key, canonical(/** @type {Record<string, unknown>} */ (value)[key])])
  );
}

/** @param {Record<string, unknown>} packet */
export function canonicalPacketDigest(packet) {
  const copy = structuredClone(packet);
  delete copy.packet_digest;
  return `sha256:${createHash("sha256").update(JSON.stringify(canonical(copy))).digest("hex")}`;
}

/**
 * Validate vue-migration-domain/v1 pass-claim and authorization integrity.
 * @param {any} packet
 * @param {{currentSourceRevision?: string, currentHostRevision?: string, evidenceBaseDir?: string}} [options]
 */
export function validateDomainPacket(packet, options = {}) {
  /** @type {string[]} */
  const errors = [];
  /**
   * @param {unknown} condition
   * @param {string} message
   */
  const require = (condition, message) => { if (!condition) errors.push(message); };

  require(packet?.schema_version === "vue-migration-domain/v1", "schema_version must be vue-migration-domain/v1");
  require(packet?.type === "vue-migration-domain", "type must be vue-migration-domain");
  require(packet?.authority === "domain_evidence_only", "authority must be domain_evidence_only");
  require(nonEmpty(packet?.packet_id), "packet_id is required");
  require(nonEmpty(packet?.generated_at) && !Number.isNaN(Date.parse(packet.generated_at)), "generated_at must be RFC3339");
  require(MODES.has(packet?.mode), "mode is invalid");
  require(nonEmpty(packet?.source?.root), "source.root is required");
  require(nonEmpty(packet?.source?.revision), "source.revision is required");
  require(nonEmpty(packet?.host?.root), "host.root is required");
  require(nonEmpty(packet?.host?.revision), "host.revision is required");
  if (options.currentSourceRevision !== undefined) {
    require(packet?.source?.revision === options.currentSourceRevision, "source revision is stale");
  }
  if (options.currentHostRevision !== undefined) {
    require(packet?.host?.revision === options.currentHostRevision, "host revision is stale");
  }

  for (const key of ["id", "source_entry", "host_entry"]) {
    require(nonEmpty(packet?.migration_unit?.[key]), `migration_unit.${key} is required`);
  }
  require(nonEmpty(packet?.intent?.goal), "intent.goal is required");
  require(Array.isArray(packet?.intent?.non_goals), "intent.non_goals must be an array");
  for (const key of ["facts", "inferences", "decisions"]) {
    require(Array.isArray(packet?.evidence?.[key]), `evidence.${key} must be an array`);
    for (const [index, item] of (packet?.evidence?.[key] || []).entries()) {
      require(nonEmpty(item) || object(item), `evidence.${key}[${index}] must be a non-empty string or object`);
    }
  }
  require(Array.isArray(packet?.closure), "closure must be an array");
  const styleClosure = packet?.style_closure;
  require(object(styleClosure), "style_closure is required");
  require(["pending", "complete", "blocked"].includes(styleClosure?.status), "style_closure.status is invalid");
  require(Array.isArray(styleClosure?.entries), "style_closure.entries must be an array");
  require(Array.isArray(styleClosure?.unresolved), "style_closure.unresolved must be an array");
  for (const [index, entry] of (styleClosure?.entries || []).entries()) {
    const label = `style_closure.entries[${index}]`;
    for (const key of ["id", "kind", "source", "evidence", "disposition", "target"]) {
      require(nonEmpty(entry?.[key]), `${label}.${key} is required`);
    }
  }
  if (["design", "execute", "verify"].includes(packet?.mode)) {
    require(styleClosure?.status === "complete", `${packet.mode} requires style_closure.status=complete`);
    require((styleClosure?.entries || []).length > 0, `${packet.mode} requires evidenced style_closure.entries`);
    require((styleClosure?.unresolved || []).length === 0, `${packet.mode} requires style_closure.unresolved to be empty`);
  }
  require(Array.isArray(packet?.host_protocols), "host_protocols must be an array");
  require(packet?.runtime_evidence?.schema === "runtime-compatibility-evidence/v1", "runtime_evidence.schema is invalid");
  require("path_or_inline" in (packet?.runtime_evidence ?? {}), "runtime_evidence.path_or_inline is required");
  require(packet?.visual_evidence?.schema === "visual-parity-evidence/v1", "visual_evidence.schema is invalid");
  require("path_or_inline" in (packet?.visual_evidence ?? {}), "visual_evidence.path_or_inline is required");
  require(object(packet?.design), "design is required");
  require(packet?.design?.target === null || nonEmpty(packet?.design?.target), "design.target must be null or a non-empty string");
  require(Array.isArray(packet?.design?.slices), "design.slices must be an array");
  require(ROLLBACK_STATUSES.has(packet?.rollback?.status), "rollback.status is invalid");

  const authorization = packet?.implementation_authorization;
  require(AUTH_STATUSES.has(authorization?.status), "implementation_authorization.status is invalid");
  require(["direct_user", "external_lifecycle"].includes(authorization?.source), "implementation_authorization.source is invalid");
  for (const key of ["allowed_scope", "forbidden_scope", "validation_obligations", "rollback_conditions"]) {
    require(Array.isArray(authorization?.[key]), `implementation_authorization.${key} must be an array`);
  }
  if (authorization?.status === "approved") {
    require(nonEmpty(authorization?.approved_by), "approved authorization requires approved_by");
    require(nonEmpty(authorization?.approved_at) && !Number.isNaN(Date.parse(authorization.approved_at)), "approved authorization requires RFC3339 approved_at");
    require(authorization?.binds_to_source_revision === packet?.source?.revision, "authorization source revision binding mismatch");
    require(authorization?.binds_to_host_revision === packet?.host?.revision, "authorization host revision binding mismatch");
    require(authorization.allowed_scope.length > 0, "approved authorization requires allowed_scope");
    require(authorization.validation_obligations.length > 0, "approved authorization requires validation_obligations");
    require(authorization.rollback_conditions.length > 0, "approved authorization requires rollback_conditions");
  }
  if (packet?.mode === "execute") {
    require(authorization?.status === "approved", "execute mode requires approved implementation_authorization");
  }

  require(VERIFY_STATUSES.has(packet?.verification?.status), "verification.status is invalid");
  require(Array.isArray(packet?.verification?.evidence), "verification.evidence must be an array");
  require(Array.isArray(packet?.blockers), "blockers must be an array");
  if (packet?.verification?.status === "pass") {
    require(packet?.mode === "verify", "verification pass requires mode=verify");
    require(packet.verification.evidence.length > 0, "verification pass requires evidence");
    require(packet.blockers.length === 0, "verification pass cannot contain blockers");
    require(["tested", "retired"].includes(packet?.rollback?.status), "verification pass requires tested or retired rollback");
    require(packet?.runtime_evidence?.path_or_inline !== null, "verification pass requires runtime evidence");
    require(packet?.visual_evidence?.path_or_inline !== null, "verification pass requires visual evidence");
    /**
     * @param {any} value
     * @param {string} label
     */
    const loadEvidence = (value, label) => {
      if (!object(value)) {
        errors.push(`${label} must be an inline object or {path,digest} reference`);
        return { value: null, baseDir: options.evidenceBaseDir };
      }
      if (!Object.hasOwn(value, "path")) return { value, baseDir: options.evidenceBaseDir };
      require(nonEmpty(value.path), `${label}.path is required`);
      require(SHA256.test(value.digest ?? ""), `${label}.digest must use sha256:<64-hex>`);
      if (!nonEmpty(value.path)) return { value: null, baseDir: options.evidenceBaseDir };
      const absolute = isAbsolute(value.path) ? value.path : resolve(options.evidenceBaseDir ?? process.cwd(), value.path);
      require(existsSync(absolute), `${label}.path does not exist: ${absolute}`);
      if (!existsSync(absolute)) return { value: null, baseDir: dirname(absolute) };
      const actualDigest = `sha256:${createHash("sha256").update(readFileSync(absolute)).digest("hex")}`;
      require(actualDigest === String(value.digest).toLowerCase(), `${label}.digest does not match file contents`);
      try {
        return { value: JSON.parse(readFileSync(absolute, "utf8")), baseDir: dirname(absolute) };
      } catch (error) {
        errors.push(`${label}.path is not valid JSON: ${error instanceof Error ? error.message : String(error)}`);
        return { value: null, baseDir: dirname(absolute) };
      }
    };
    const runtimeLoaded = loadEvidence(packet?.runtime_evidence?.path_or_inline, "runtime_evidence.path_or_inline");
    const runtimeInline = runtimeLoaded.value;
    if (object(runtimeInline)) {
      for (const error of validateRuntimeEvidence(runtimeInline, {
        currentSourceRevision: packet?.source?.revision,
        currentHostRevision: packet?.host?.revision,
      })) errors.push(`runtime_evidence.path_or_inline: ${error}`);
      require(runtimeInline.final_runtime_result === "pass", "verification pass requires inline runtime final_runtime_result=pass");
    }
    const visualLoaded = loadEvidence(packet?.visual_evidence?.path_or_inline, "visual_evidence.path_or_inline");
    const visualInline = visualLoaded.value;
    if (object(visualInline)) {
      for (const error of validateVisualEvidence(visualInline, { baseDir: visualLoaded.baseDir })) {
        errors.push(`visual_evidence.path_or_inline: ${error}`);
      }
      require(visualInline.final_visual_result === "pass", "verification pass requires inline visual final_visual_result=pass");
      require(visualInline.source_revision === packet?.source?.revision, "inline visual source revision mismatch");
      require(visualInline.host_revision === packet?.host?.revision, "inline visual host revision mismatch");
    }
  }

  require(SHA256.test(packet?.packet_digest ?? ""), "packet_digest must use sha256:<64-hex>");
  if (SHA256.test(packet?.packet_digest ?? "")) {
    require(packet.packet_digest.toLowerCase() === canonicalPacketDigest(packet), "packet_digest does not match canonical packet content");
  }
  return errors;
}

function main() {
  const path = process.argv[2];
  if (!path) {
    console.error("Usage: node scripts/validate_domain_packet.mjs <domain-packet.json> [current-source-revision] [current-host-revision]");
    return 2;
  }
  let packet;
  try {
    packet = JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    console.error(`FAIL: cannot read packet: ${error instanceof Error ? error.message : String(error)}`);
    return 2;
  }
  const errors = validateDomainPacket(packet, {
    currentSourceRevision: process.argv[3],
    currentHostRevision: process.argv[4],
  });
  if (errors.length) {
    console.error(`FAIL: ${errors.length} domain packet contract error(s)`);
    for (const error of errors) console.error(`- ${error}`);
    return 1;
  }
  console.log("PASS: vue-migration-domain/v1 is complete and digest-consistent");
  return 0;
}

if (import.meta.url === pathToFileURL(process.argv[1] || "").href) process.exit(main());
