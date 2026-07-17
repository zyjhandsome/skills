#!/usr/bin/env node
// @ts-check
/**
 * Validate a Delivery Family handoff JSON object. Zero dependencies (Node >= 18).
 *
 * Usage:
 *   node validate_handoff.mjs <handoff.json>        # file
 *   node validate_handoff.mjs -                     # stdin
 *   node validate_handoff.mjs <file> --profile legacy
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

// Compatibility is major-based: any delivery-family/<SUPPORTED_FAMILY_MAJOR>.x is accepted
// so additive minor bumps do not require editing this validator. CURRENT_FAMILY_VERSION is
// the version the templates currently emit; it is informational only.
export const SUPPORTED_FAMILY_MAJOR = 1;
export const CURRENT_FAMILY_VERSION = "delivery-family/1.3";
const SCHEMA_VERSION = "delivery-handoff/v1";
const STAGES = new Set([
  "delivery-explore",
  "delivery-frame-spec",
  "delivery-plan-tasks",
  "delivery-execute-verify",
]);
const TOP_LEVEL = new Set([
  "schema_version",
  "family_version",
  "type",
  "handoff_id",
  "generated_at",
  "stage",
  "source_revision",
  "state_source",
  "capability_snapshot",
  "capability_bindings",
  "presentation_capability",
  "gate_status",
  "evidence_mode",
  "next_skill",
  "next_action",
  "required_inputs",
  "stop_condition",
  "stage_payload",
  "presentation",
]);
// Optional additive keys (delivery-family/1.3): accepted when present, never required.
const OPTIONAL_TOP_LEVEL = new Set(["previous_handoff_id"]);
// Hard-prerequisite profile (delivery-family/1.3 default): OpenSpec, Codebase Memory MCP,
// Superpowers, and SubAgents are assumed installed and nominal. A non-nominal snapshot may
// still be reported, but it must not carry a stage transition, and degraded evidence does
// not exist. Use --profile legacy to validate pre-1.2 handoffs.
const NOMINAL_SNAPSHOT = { memory: "ok", openspec: "initialized", superpowers: "loaded" };
const STAGE_PAYLOAD_KEYS = {
  "delivery-explore": new Set([
    "direction_alignment",
    "chosen_direction",
    "non_goals",
    "code_anchors",
    "risk_signal",
    "unknowns",
  ]),
  "delivery-frame-spec": new Set([
    "route",
    "risk",
    "confirmed_artifacts",
    "forbidden_scope",
    "open_questions",
  ]),
  "delivery-plan-tasks": new Set([
    "plan_tasks",
    "plan_decisions",
    "traceability",
    "readiness_result",
    "validation_plan",
    "risk_gates",
    "parallel_ownership",
  ]),
  "delivery-execute-verify": new Set([
    "overall_status",
    "task_status",
    "current_failures_or_blocks",
    "artifact_backflow",
    "alignment_backflow",
    "fresh_verification_evidence",
    "spec_coherence",
    "code_review",
    "archive",
    "asset_writeback",
  ]),
};

/** @param {unknown} value */
function isPlainObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** @param {unknown} value @returns {number | null} */
export function familyMajor(value) {
  if (typeof value !== "string" || !value.startsWith("delivery-family/")) return null;
  const tail = value.split("/", 2)[1];
  const major = tail.split(".", 1)[0];
  if (!/^\d+$/.test(major)) return null;
  return Number.parseInt(major, 10);
}

// Mirrors Python datetime.fromisoformat (with Z -> +00:00): ISO date, optional time,
// optional fractional seconds, optional UTC offset.
const RFC3339_RE =
  /^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?(Z|[+-]\d{2}:\d{2}(:\d{2})?)?)?$/;

/** @param {unknown} value */
export function isRfc3339(value) {
  if (typeof value !== "string" || !value) return false;
  if (!RFC3339_RE.test(value)) return false;
  const normalized = value.replace(" ", "T").replace(/([+-]\d{2}:\d{2}):\d{2}$/, "$1");
  return !Number.isNaN(Date.parse(normalized));
}

/**
 * @param {unknown} value @param {string} path @param {string[]} errors
 * @returns {Record<string, any>}
 */
function requireObject(value, path, errors) {
  if (!isPlainObject(value)) {
    errors.push(`${path} must be an object`);
    return {};
  }
  return /** @type {Record<string, any>} */ (value);
}

/**
 * @param {unknown} value @param {string} path @param {string[]} errors
 * @returns {any[]}
 */
function requireArray(value, path, errors) {
  if (!Array.isArray(value)) {
    errors.push(`${path} must be an array`);
    return [];
  }
  return value;
}

/**
 * @param {Record<string, any>} obj @param {Iterable<string>} keys
 * @param {string} path @param {string[]} errors
 */
function requireKeys(obj, keys, path, errors) {
  const missing = [...keys].filter((k) => !(k in obj)).sort();
  if (missing.length) errors.push(`${path} missing keys: ${missing.join(", ")}`);
}

/** @param {unknown} value */
function reprish(value) {
  return value === null || value === undefined ? "None" : JSON.stringify(value);
}

/**
 * @param {unknown} data
 * @param {"hard" | "legacy"} [profile]
 * @returns {string[]}
 */
export function validate(data, profile = "hard") {
  /** @type {string[]} */
  const errors = [];
  const root = requireObject(data, "$", errors);
  requireKeys(root, TOP_LEVEL, "$", errors);
  // Forward-compatible extension: keys prefixed with "x_" are reserved for additive,
  // non-authoritative extensions and are ignored by this validator.
  const extras = Object.keys(root)
    .filter((k) => !TOP_LEVEL.has(k) && !OPTIONAL_TOP_LEVEL.has(k) && !k.startsWith("x_"))
    .sort();
  if (extras.length) errors.push(`$ has unsupported top-level keys: ${extras.join(", ")}`);
  if ("previous_handoff_id" in root) {
    const prev = root.previous_handoff_id;
    if (prev !== null && (typeof prev !== "string" || !prev)) {
      errors.push("previous_handoff_id must be a non-empty string or null");
    }
  }

  if (root.schema_version !== SCHEMA_VERSION) {
    errors.push(`schema_version must be ${SCHEMA_VERSION}`);
  }
  if (familyMajor(root.family_version) !== SUPPORTED_FAMILY_MAJOR) {
    errors.push(
      `family_version major must be ${SUPPORTED_FAMILY_MAJOR} ` +
        `(e.g. ${CURRENT_FAMILY_VERSION}); got ${reprish(root.family_version)}`
    );
  }
  if (root.type !== "delivery-handoff") errors.push("type must be delivery-handoff");
  if (typeof root.handoff_id !== "string" || !root.handoff_id) {
    errors.push("handoff_id must be a non-empty string");
  }
  if (!isRfc3339(root.generated_at)) errors.push("generated_at must be an RFC3339 timestamp");

  const stage = root.stage;
  if (!STAGES.has(stage)) {
    errors.push(`stage must be one of: ${[...STAGES].sort().join(", ")}`);
  }

  const revision = requireObject(root.source_revision, "source_revision", errors);
  requireKeys(revision, ["repo_head", "artifact_revision", "state_observed_at"], "source_revision", errors);
  if (revision.repo_head !== null && revision.repo_head !== undefined && typeof revision.repo_head !== "string") {
    errors.push("source_revision.repo_head must be a string or null");
  }
  if (
    revision.artifact_revision !== null &&
    revision.artifact_revision !== undefined &&
    typeof revision.artifact_revision !== "string"
  ) {
    errors.push("source_revision.artifact_revision must be a string or null");
  }
  if (!isRfc3339(revision.state_observed_at)) {
    errors.push("source_revision.state_observed_at must be RFC3339");
  }

  const state = requireObject(root.state_source, "state_source", errors);
  requireKeys(state, ["kind", "label", "anchor"], "state_source", errors);
  if (!["none", "openspec_change"].includes(state.kind)) {
    errors.push("state_source.kind must be none or openspec_change");
  }
  if (state.kind === "openspec_change" && !state.anchor) {
    errors.push("state_source.anchor is required for openspec_change");
  }
  if (state.kind === "none" && state.anchor !== null && state.anchor !== undefined) {
    errors.push("state_source.anchor must be null when kind is none");
  }

  const snapshot = requireObject(root.capability_snapshot, "capability_snapshot", errors);
  requireKeys(snapshot, ["memory", "openspec", "superpowers"], "capability_snapshot", errors);
  if (!["ok", "stale-index", "down"].includes(snapshot.memory)) {
    errors.push("capability_snapshot.memory has an invalid value");
  }
  if (!["initialized", "cli-only", "unavailable"].includes(snapshot.openspec)) {
    errors.push("capability_snapshot.openspec has an invalid value");
  }
  const superpowers = snapshot.superpowers;
  if (
    !(
      ["loaded", "missing"].includes(superpowers) ||
      (typeof superpowers === "string" && superpowers.startsWith("partial("))
    )
  ) {
    errors.push("capability_snapshot.superpowers has an invalid value");
  }

  const bindings = requireObject(root.capability_bindings, "capability_bindings", errors);
  requireKeys(bindings, ["openspec", "memory", "superpowers", "subagents"], "capability_bindings", errors);

  const presentationCap = requireObject(root.presentation_capability, "presentation_capability", errors);
  requireKeys(presentationCap, ["mode", "source"], "presentation_capability", errors);
  if (!["delivery-ui/v1", "legacy-v0", "markdown"].includes(presentationCap.mode)) {
    errors.push("presentation_capability.mode has an invalid value");
  }
  if (!["host-declared", "detected", "unknown"].includes(presentationCap.source)) {
    errors.push("presentation_capability.source has an invalid value");
  }

  const gate = requireObject(root.gate_status, "gate_status", errors);
  requireKeys(
    gate,
    [
      "status",
      "summary",
      "evidence",
      "approved_by",
      "approved_at",
      "binds_to_revision",
      "accepted_warning_ids",
    ],
    "gate_status",
    errors
  );
  if (!["n/a", "pending", "pass", "warn", "block"].includes(gate.status)) {
    errors.push("gate_status.status has an invalid value");
  }
  requireArray(gate.evidence, "gate_status.evidence", errors);
  const warnings = requireArray(gate.accepted_warning_ids, "gate_status.accepted_warning_ids", errors);
  if (warnings.some((w) => typeof w !== "string" || !w)) {
    errors.push("gate_status.accepted_warning_ids must contain non-empty strings");
  }
  const approvalValues = [gate.approved_by, gate.approved_at, gate.binds_to_revision];
  const isNullish = (/** @type {unknown} */ v) => v === null || v === undefined;
  if (approvalValues.some((v) => !isNullish(v))) {
    if (approvalValues.some(isNullish)) {
      errors.push("gate approval requires approved_by, approved_at, and binds_to_revision together");
    }
    if (!isRfc3339(gate.approved_at)) {
      errors.push("gate_status.approved_at must be RFC3339 when approval exists");
    }
    if (gate.binds_to_revision !== revision.artifact_revision) {
      errors.push("gate approval must bind source_revision.artifact_revision");
    }
  }
  if (gate.status === "warn" && (root.next_skill || root.next_action) && warnings.length === 0) {
    errors.push("a continuing warn gate requires accepted_warning_ids");
  }
  const visibleGate = JSON.stringify({ summary: gate.summary ?? null, evidence: gate.evidence ?? null });
  for (const warning of warnings) {
    if (typeof warning === "string" && warning && !visibleGate.includes(warning)) {
      errors.push(`accepted warning id is not visible in gate summary/evidence: ${warning}`);
    }
  }

  if (!["full", "degraded"].includes(root.evidence_mode)) {
    errors.push("evidence_mode must be full or degraded");
  }
  const nextSkill = root.next_skill ?? null;
  const nextAction = root.next_action ?? null;
  if (nextSkill !== null && nextAction !== null) {
    errors.push("next_skill and next_action cannot both be non-null");
  }

  if (profile === "hard") {
    if (root.evidence_mode !== "full") {
      errors.push("hard profile: evidence_mode must be full (no degraded evidence mode)");
    }
    const hasTransition = nextSkill !== null || nextAction !== null;
    const nonNominal = Object.entries(NOMINAL_SNAPSHOT)
      .filter(([key, nominal]) => snapshot[key] !== nominal)
      .map(([key]) => `${key}=${reprish(snapshot[key])}`)
      .sort();
    if (hasTransition && nonNominal.length) {
      errors.push(
        "hard profile: a non-nominal capability_snapshot cannot carry a stage " +
          `transition (${nonNominal.join(", ")}); report the failure with ` +
          "next_skill/next_action null and a stop_condition instead"
      );
    }
  }
  requireArray(root.required_inputs, "required_inputs", errors);
  if (typeof root.stop_condition !== "string") {
    errors.push("stop_condition must be a string");
  }

  const payload = requireObject(root.stage_payload, "stage_payload", errors);
  if (stage in STAGE_PAYLOAD_KEYS) {
    requireKeys(payload, STAGE_PAYLOAD_KEYS[/** @type {keyof typeof STAGE_PAYLOAD_KEYS} */ (stage)], "stage_payload", errors);
  }

  const presentation = requireObject(root.presentation, "presentation", errors);
  requireKeys(
    presentation,
    ["schema", "from_task", "to_task", "summary", "evidence", "continue_prompt"],
    "presentation",
    errors
  );
  if (presentation.schema !== "delivery-presentation/v1") {
    errors.push("presentation.schema must be delivery-presentation/v1");
  }
  requireArray(presentation.evidence, "presentation.evidence", errors);

  if (stage === "delivery-explore") {
    if (!["selected", "needs_choice"].includes(payload.direction_alignment)) {
      errors.push("Explore direction_alignment must be selected or needs_choice");
    }
    if (state.kind !== "none") errors.push("Explore must use state_source.kind none");
    if (![null, "delivery-frame-spec"].includes(nextSkill)) {
      errors.push("Explore next_skill may only be delivery-frame-spec or null");
    }
    if (payload.direction_alignment === "selected" && nextSkill !== "delivery-frame-spec") {
      errors.push("selected Explore direction must transition to delivery-frame-spec");
    }
    if (payload.direction_alignment === "needs_choice" && nextSkill !== null) {
      errors.push("needs_choice Explore state cannot transition");
    }
  } else if (stage === "delivery-frame-spec") {
    if (![null, "delivery-explore", "delivery-plan-tasks", "delivery-execute-verify"].includes(nextSkill)) {
      errors.push("Frame next_skill is invalid");
    }
    if (["delivery-plan-tasks", "delivery-execute-verify"].includes(nextSkill)) {
      if (state.kind !== "openspec_change") {
        errors.push("Frame mutation transition requires openspec_change state");
      }
      if (!["pass", "warn"].includes(gate.status)) {
        errors.push("Frame mutation transition requires a pass or accepted warn gate");
      }
      if (isNullish(gate.binds_to_revision)) {
        errors.push("Frame mutation transition requires revision-bound approval");
      }
      if (!revision.artifact_revision) {
        errors.push("Frame mutation transition requires artifact_revision");
      }
    }
  } else if (stage === "delivery-plan-tasks") {
    if (state.kind !== "openspec_change") errors.push("Plan must use openspec_change state");
    if (![null, "delivery-execute-verify"].includes(nextSkill)) {
      errors.push("Plan next_skill may only be delivery-execute-verify or null");
    }
    if (nextSkill === "delivery-execute-verify") {
      if (!["pass", "warn"].includes(gate.status)) {
        errors.push("Plan execution transition requires a pass or accepted warn gate");
      }
      if (isNullish(gate.binds_to_revision)) {
        errors.push("Plan execution transition requires revision-bound approval");
      }
      if (!revision.artifact_revision) {
        errors.push("Plan execution transition requires artifact_revision");
      }
    }
  } else if (stage === "delivery-execute-verify") {
    if (state.kind !== "openspec_change") errors.push("Execute must use openspec_change state");
    if (nextSkill !== null) errors.push("Execute must use next_action, not next_skill");
    const archive = requireObject(payload.archive, "stage_payload.archive", errors);
    const review = requireObject(payload.code_review, "stage_payload.code_review", errors);
    if (payload.overall_status === "verified") {
      if (archive.status !== "deferred_to_openspec") {
        errors.push("verified Execute handoff must defer archive to OpenSpec");
      }
      if (nextAction === null) {
        errors.push("verified Execute handoff requires the resolved archive next_action");
      }
      // G7: Medium/High cannot close on self_fresh_context.
      // Risk is not always in stage_payload for execute; infer from review fields.
      const mode = review.mode ?? null;
      const indep = review.independent_review ?? null;
      if (mode === null || indep === null) {
        errors.push(
          "verified Execute handoff requires code_review.mode and code_review.independent_review"
        );
      } else if (mode === "self_fresh_context" && indep !== "low_accepted") {
        errors.push("verified Execute handoff cannot use self_fresh_context except low_accepted");
      } else if (mode === "independent" && !["required_pass", "required_warn_accepted"].includes(indep)) {
        errors.push(
          "independent code_review.independent_review must be required_pass or required_warn_accepted"
        );
      } else if (!["independent", "self_fresh_context"].includes(mode)) {
        errors.push("code_review.mode must be independent or self_fresh_context");
      }
      if (!["pass", "warn"].includes(review.status)) {
        errors.push("verified Execute handoff requires code_review.status pass or warn");
      }
    }
  }

  return errors;
}

function main() {
  const args = process.argv.slice(2);
  /** @type {"hard" | "legacy"} */
  let profile = "hard";
  /** @type {string[]} */
  const positional = [];
  for (let i = 0; i < args.length; i += 1) {
    if (args[i] === "--profile") {
      const value = args[i + 1];
      if (value !== "hard" && value !== "legacy") {
        console.error("ERROR: --profile must be hard or legacy");
        return 2;
      }
      profile = value;
      i += 1;
    } else {
      positional.push(args[i]);
    }
  }
  if (positional.length !== 1) {
    console.error("usage: node validate_handoff.mjs <handoff.json | -> [--profile hard|legacy]");
    return 2;
  }

  let data;
  try {
    const raw = positional[0] === "-" ? readFileSync(0, "utf-8") : readFileSync(positional[0], "utf-8");
    data = JSON.parse(raw);
  } catch (exc) {
    console.error(`INVALID JSON: ${exc instanceof Error ? exc.message : exc}`);
    return 2;
  }

  const errors = validate(data, profile);
  if (errors.length) {
    for (const error of errors) console.error(`ERROR: ${error}`);
    return 1;
  }
  console.log(`PASS: valid delivery-handoff/v1 (${profile} profile)`);
  return 0;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exit(main());
}
