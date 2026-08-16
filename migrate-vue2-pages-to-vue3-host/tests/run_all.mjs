#!/usr/bin/env node
// @ts-check

import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { validateVisualEvidence } from "../scripts/validate_visual_evidence.mjs";
import { canonicalPacketDigest, validateDomainPacket } from "../scripts/validate_domain_packet.mjs";
import { validateRuntimeEvidence } from "../scripts/validate_runtime_evidence.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const SKILL = join(ROOT, "SKILL.md");
const REFERENCES = join(ROOT, "references");
const AGENT_YAML = join(ROOT, "agents", "openai.yaml");
const SCENARIOS = JSON.parse(
  readFileSync(join(HERE, "fixtures", "scenarios.json"), "utf8")
);
const VALID_VISUAL_EVIDENCE = join(HERE, "fixtures", "visual-evidence-valid.json");
const INVALID_VISUAL_EVIDENCE = join(HERE, "fixtures", "visual-evidence-invalid-wrong-page.json");

const REQUIRED_REFERENCES = [
  "discovery-and-page-closure.md",
  "vue2-to-vue3-transformations.md",
  "host-integration-slicing-and-iframe-exit.md",
  "visual-parity-validation.md",
  "runtime-and-dependency-compatibility.md",
  "domain-packet-and-lifecycle-interoperability.md",
];

const DOC_FILES = [
  SKILL,
  AGENT_YAML,
  ...REQUIRED_REFERENCES.map((name) => join(REFERENCES, name)),
];

/** @param {string} path */
const read = (path) => readFileSync(path, "utf8");
/** @param {string} value */
const lower = (value) => value.toLowerCase().replace(/\s+/g, " ").trim();

function checkStructure() {
  for (const path of DOC_FILES) {
    assert.ok(existsSync(path), `missing required file: ${relative(ROOT, path)}`);
    assert.ok(!read(path).includes("TODO"), `TODO placeholder remains: ${relative(ROOT, path)}`);
  }

  const skill = read(SKILL);
  assert.ok(skill.split(/\r?\n/).length < 500, "SKILL.md must stay under 500 lines");
  const frontmatter = skill.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  assert.ok(frontmatter, "SKILL.md frontmatter is missing");
  const topLevelKeys = frontmatter[1]
    .split(/\r?\n/)
    .filter((line) => /^[a-z][a-z0-9_-]*:/.test(line))
    .map((line) => line.slice(0, line.indexOf(":")));
  assert.deepEqual(topLevelKeys, ["name", "description"], "frontmatter may contain only name and description");

  for (const name of REQUIRED_REFERENCES) {
    assert.ok(skill.includes(`references/${name}`), `SKILL.md does not route to ${name}`);
  }
  assert.deepEqual(
    readdirSync(REFERENCES).sort(),
    REQUIRED_REFERENCES.slice().sort(),
    "unexpected or missing reference files"
  );

  const yaml = read(AGENT_YAML);
  assert.ok(
    yaml.includes("$migrate-vue2-pages-to-vue3-host"),
    "default_prompt must contain the exact skill token"
  );
  assert.ok(
    existsSync(join(ROOT, "scripts", "validate_visual_evidence.mjs")),
    "visual evidence validator is missing"
  );
  assert.ok(existsSync(join(ROOT, "scripts", "validate_domain_packet.mjs")), "domain packet validator is missing");
  assert.ok(existsSync(join(ROOT, "scripts", "validate_runtime_evidence.mjs")), "runtime evidence validator is missing");
}

function checkIndependence() {
  const corpus = DOC_FILES.map(read).join("\n");
  const forbiddenCouplings = [
    "delivery-",
    "OpenSpec",
    "frontend-dependency-upgrade-impact-analysis",
    "Delivery G9",
    "quality_profiles.visual",
  ];
  for (const token of forbiddenCouplings) {
    assert.ok(!corpus.includes(token), `hard coupling remains in Skill docs: ${token}`);
  }

  for (const required of [
    "vue-migration-domain/v1",
    "visual-parity-evidence/v1",
    "runtime-compatibility-evidence/v1",
    "implementation_authorization",
    "source_revision",
    "host_revision",
    "packet_digest",
    "no `execute` mode",
    "Never mutate",
  ]) {
    assert.ok(corpus.includes(required), `standalone contract is missing: ${required}`);
  }

  assert.ok(!/^\|\s*`execute`\s*\|/m.test(corpus), "execute mode row must be removed from Skill docs");
  assert.ok(
    !corpus.includes("mode: assess | design | execute | verify"),
    "domain packet schema must not list execute as a mode"
  );
}

/**
 * Deterministic state-machine stress model for the domain gates.
 * @param {any} scenario
 */
function simulate(scenario) {
  const trace = ["recover"];
  if (scenario.unit_complete === false) {
    return { terminal: "blocked:inputs", trace };
  }
  if (!scenario.revision_fresh) return { terminal: "stale:refresh-required", trace };
  trace.push("discover", "contract");
  if (scenario.visual_chain === "unavailable") {
    return { terminal: "blocked:visual-chain", trace };
  }
  if (scenario.visual_baseline === "missing") {
    return { terminal: "blocked:visual-baseline", trace };
  }
  if (scenario.visual_baseline === "approved_substitute" && scenario.claims_exact_parity) {
    return { terminal: "blocked:visual-policy", trace };
  }
  trace.push("runtime-dependency");
  if (scenario.runtime !== "ready") return { terminal: "blocked:runtime", trace };
  if (scenario.dependency !== "ready") return { terminal: "blocked:dependency", trace };
  trace.push("design");
  if (scenario.requested_mode === "execute" || scenario.requested_mutation === true) {
    return { terminal: "blocked:no-execute-mode", trace };
  }
  trace.push("verify");
  if (scenario.verification === "fail") return { terminal: "rollback-required", trace };
  if (scenario.verification === "pass") return { terminal: "verified", trace };
  return { terminal: "verification-pending", trace };
}

function checkScenarios() {
  assert.ok(SCENARIOS.length >= 11, "stress suite must contain at least eleven scenarios");
  for (const scenario of SCENARIOS) {
    const actual = simulate(scenario);
    assert.equal(
      actual.terminal,
      scenario.expected_terminal,
      `${scenario.id}: terminal mismatch; trace=${actual.trace.join(" -> ")}`
    );

    for (const [relativePath, terms] of Object.entries(scenario.required_files)) {
      const path = join(ROOT, relativePath);
      assert.ok(existsSync(path), `${scenario.id}: missing referenced file ${relativePath}`);
      const content = lower(read(path));
      for (const term of /** @type {string[]} */ (terms)) {
        assert.ok(
          content.includes(lower(term)),
          `${scenario.id}: ${relativePath} lacks contract term '${term}'`
        );
      }
    }
    console.log(`[PASS] ${scenario.id}: ${actual.trace.join(" -> ")} -> ${actual.terminal}`);
  }
}

function checkVisualEvidenceValidator() {
  const fixtureDir = dirname(VALID_VISUAL_EVIDENCE);
  /** @type {any} */
  const valid = JSON.parse(read(VALID_VISUAL_EVIDENCE));
  /** @param {any} evidence */
  const validate = (evidence) => validateVisualEvidence(evidence, { baseDir: fixtureDir });
  const validErrors = validate(valid);
  assert.deepEqual(validErrors, [], `valid visual evidence rejected: ${validErrors.join("; ")}`);

  const invalidErrors = validate(JSON.parse(read(INVALID_VISUAL_EVIDENCE)));
  for (const fragment of [
    "at least five required_states",
    "identity_assertions.route.result",
    "identity_assertions.marker.result",
    "table_contract.metrics must cover header",
    "rollback.deterministic_fixture",
    "rollback nested shell acceptance requires approver",
  ]) {
    assert.ok(
      invalidErrors.some((error) => error.includes(fragment)),
      `invalid evidence did not report '${fragment}'`
    );
  }
  console.log(`[PASS] visual evidence validator rejected wrong-page and incomplete table evidence (${invalidErrors.length} errors)`);

  /** @type {{ id: string, mutate: (evidence: any) => void, error: string }[]} */
  const cases = [
    {
      id: "wrong-page-actual",
      mutate: (evidence) => { evidence.required_states[0].identity_assertions.route.actual = "#/dashboard"; },
      error: "expected/actual mismatch",
    },
    {
      id: "nonexistent-artifact",
      mutate: (evidence) => { evidence.required_states[0].artifacts.diff_path = "artifacts/not-generated.png"; },
      error: "path does not exist",
    },
    {
      id: "duplicate-states",
      mutate: (evidence) => {
        evidence.required_states = Array.from({ length: 5 }, () => structuredClone(evidence.required_states[1]));
      },
      error: "ids must be unique",
    },
    {
      id: "numeric-table-mismatch-labeled-pass",
      mutate: (evidence) => { evidence.table_contract.metrics[2].candidate = 46; },
      error: "exceed tolerance",
    },
    {
      id: "numeric-table-value-stringified",
      mutate: (evidence) => { evidence.table_contract.metrics[2].candidate = String(evidence.table_contract.metrics[2].baseline); },
      error: "types must match",
    },
    {
      id: "rollback-applicability-bypass",
      mutate: (evidence) => { evidence.rollback.applicable = false; },
      error: "must match legacy_boundary.detected",
    },
    {
      id: "bare-nested-shell-acceptance",
      mutate: (evidence) => {
        evidence.rollback.nested_shell = true;
        evidence.rollback.nested_shell_acceptance = { disposition: "explicitly_accepted" };
      },
      error: "requires approver",
    },
    {
      id: "wrong-producer",
      mutate: (evidence) => { evidence.producer = "attacker"; },
      error: "producer must be",
    },
    {
      id: "missing-authority",
      mutate: (evidence) => { delete evidence.authority; },
      error: "authority must be",
    },
    {
      id: "invalid-assessment-mode",
      mutate: (evidence) => { evidence.assessment_mode = "nonsense"; },
      error: "assessment_mode is invalid",
    },
    {
      id: "unbound-baseline-metadata",
      mutate: (evidence) => { delete evidence.baseline.source; evidence.baseline.manifest_digest = "not-a-digest"; },
      error: "baseline.source is required",
    },
    {
      id: "legacy-candidate-mode",
      mutate: (evidence) => {
        for (const state of evidence.required_states) {
          state.identity_assertions.migration_mode = { expected: "legacy-iframe", actual: "legacy-iframe", result: "pass" };
        }
      },
      error: "must be native",
    },
    {
      id: "forbidden-difference-present",
      mutate: (evidence) => { evidence.difference_policy.forbidden = [{ id: "missing-action" }]; },
      error: "forbidden must be empty",
    },
    {
      id: "accepted-difference-unknown-state",
      mutate: (evidence) => {
        evidence.difference_policy.explicitly_accepted = [{
          id: "accepted-1", reason: "approved", approver: "owner", decision_reference: "decision-1",
          source_revision: evidence.source_revision, host_revision: evidence.host_revision,
          affected_states: ["does-not-exist"],
        }];
      },
      error: "references unknown state",
    },
    {
      id: "self-attested-global-collateral",
      mutate: (evidence) => {
        evidence.global_style_changed = true;
        evidence.global_collateral = [{ result: "pass" }, { result: "pass" }, { result: "pass" }];
      },
      error: "existing host page",
    },
    {
      id: "missing-style-closure",
      mutate: (evidence) => { delete evidence.style_closure; },
      error: "style_closure.status must be complete",
    },
    {
      id: "wrong-source-color-labeled-pass",
      mutate: (evidence) => { evidence.color_contract.metrics[1].candidate = "rgb(0, 0, 0)"; },
      error: "color_contract.metrics[1] baseline/candidate exceed tolerance",
    },
    {
      id: "font-fallback-labeled-pass",
      mutate: (evidence) => { evidence.page_style_contract.metrics[1].candidate = "system-ui"; },
      error: "page_style_contract.metrics[1] baseline/candidate exceed tolerance",
    },
    {
      id: "replacement-icon-content",
      mutate: (evidence) => { evidence.icon_contract.icons[0].candidate.fingerprint = "different-icon"; },
      error: "source/candidate fingerprint mismatch",
    },
    {
      id: "missing-computed-style-artifact",
      mutate: (evidence) => { evidence.required_states[0].artifacts.computed_style_path = "artifacts/not-generated.json"; },
      error: "path does not exist",
    },
    {
      id: "unbound-computed-style-measurement",
      mutate: (evidence) => { evidence.page_style_contract.metrics[1].selector = "[data-unmeasured='font']"; },
      error: "candidate is not backed by its state computed-style artifact",
    },
    {
      id: "reused-state-baseline",
      mutate: (evidence) => {
        evidence.required_states[1].artifacts.baseline_path = evidence.required_states[0].artifacts.baseline_path;
        evidence.required_states[1].artifacts.baseline_digest = evidence.required_states[0].artifacts.baseline_digest;
      },
      error: "baseline path must match baseline manifest",
    },
  ];
  for (const testCase of cases) {
    const evidence = structuredClone(valid);
    testCase.mutate(evidence);
    const errors = validate(evidence);
    assert.ok(errors.some((error) => error.includes(testCase.error)), `${testCase.id} was not rejected by '${testCase.error}'`);
    console.log(`[PASS] adversarial visual evidence rejected: ${testCase.id}`);
  }
}

function checkDomainPacketValidator() {
  /** @param {string} repository */
  const command = (repository) => ({
    repository, command: "test", working_directory: repository, runtime: "node", timestamp: "2026-08-12T00:00:00Z",
    exit_code: 0, output_digest: "a".repeat(64),
  });
  const runtimeInline = {
    schema: "runtime-compatibility-evidence/v1", producer: "migrate-vue2-pages-to-vue3-host", authority: "domain_evidence_only",
    source_revision: "source-123", host_revision: "host-456",
    source_runtime: { required_node: "18", evidence: ["package.json"], package_manager: "npm@9", lock_owner_format: "npm-v2", selected_runtime: "node18", isolation_method: "fnm", command_readiness: "ready" },
    host_runtime: { required_node: "22", evidence: ["package.json"], package_manager: "pnpm@11", lock_owner_format: "pnpm-v9", selected_runtime: "node22", isolation_method: "fnm", command_readiness: "ready" },
    dependency_demands: [], approved_runtime_actions: [], restoration_plan: [],
    verification_commands: [command("source"), command("host")], final_runtime_result: "pass",
  };
  /** @type {any} */
  const packet = {
    schema_version: "vue-migration-domain/v1", type: "vue-migration-domain", authority: "domain_evidence_only",
    packet_id: "orders-source-1-host-1", generated_at: "2026-08-12T00:00:00Z", mode: "verify",
    source: { root: "A", revision: "source-123" }, host: { root: "B", revision: "host-456" },
    migration_unit: { id: "orders", source_entry: "/orders", host_entry: "/native/orders" },
    intent: { goal: "preserve orders behavior", non_goals: ["redesign"] },
    evidence: { facts: [], inferences: [], decisions: [] }, closure: [],
    style_closure: {
      status: "complete",
      entries: [{
        id: "orders-style", kind: "sfc-style", source: "src/views/orders.vue",
        evidence: "style block inspected", disposition: "adapt-to-B", target: "src/views/orders.vue",
      }],
      unresolved: [],
    },
    host_protocols: [],
    runtime_evidence: { schema: "runtime-compatibility-evidence/v1", path_or_inline: runtimeInline },
    visual_evidence: {
      schema: "visual-parity-evidence/v1",
      path_or_inline: {
        path: VALID_VISUAL_EVIDENCE,
        digest: `sha256:${createHash("sha256").update(readFileSync(VALID_VISUAL_EVIDENCE)).digest("hex")}`,
      },
    },
    design: { target: "B native", slices: [] }, rollback: { status: "tested" },
    implementation_authorization: {
      status: "approved", source: "external_lifecycle", approved_by: "user", approved_at: "2026-08-12T00:00:00Z",
      binds_to_source_revision: "source-123", binds_to_host_revision: "host-456",
      allowed_scope: ["src/orders"], forbidden_scope: ["A"], validation_obligations: ["visual"], rollback_conditions: ["iframe"],
    },
    verification: { status: "pass", evidence: ["build: pass"] }, blockers: [], packet_digest: "",
  };
  packet.packet_digest = canonicalPacketDigest(packet);
  assert.deepEqual(validateDomainPacket(packet, { currentSourceRevision: "source-123", currentHostRevision: "host-456", evidenceBaseDir: dirname(VALID_VISUAL_EVIDENCE) }), []);
  const stale = structuredClone(packet);
  assert.ok(validateDomainPacket(stale, { currentHostRevision: "host-2" }).some((error) => error.includes("host revision is stale")));
  const tampered = structuredClone(packet);
  tampered.intent.goal = "changed after approval";
  assert.ok(validateDomainPacket(tampered).some((error) => error.includes("packet_digest does not match")));
  const executeMode = structuredClone(packet);
  executeMode.mode = "execute";
  executeMode.verification = { status: "not_run", evidence: [] };
  executeMode.packet_digest = canonicalPacketDigest(executeMode);
  assert.ok(validateDomainPacket(executeMode).some((error) => error.includes("mode is invalid")));
  const readOnlyVerify = structuredClone(packet);
  readOnlyVerify.implementation_authorization.status = "stale";
  readOnlyVerify.packet_digest = canonicalPacketDigest(readOnlyVerify);
  assert.ok(!validateDomainPacket(readOnlyVerify, { evidenceBaseDir: dirname(VALID_VISUAL_EVIDENCE) }).some((error) => error.includes("requires approved implementation_authorization")));
  const nullFact = structuredClone(packet);
  nullFact.evidence.facts = [null];
  nullFact.packet_digest = canonicalPacketDigest(nullFact);
  assert.ok(validateDomainPacket(nullFact).some((error) => error.includes("facts[0]")));
  const objectTarget = structuredClone(packet);
  objectTarget.design.target = { kind: "native" };
  objectTarget.packet_digest = canonicalPacketDigest(objectTarget);
  assert.ok(validateDomainPacket(objectTarget).some((error) => error.includes("design.target")));
  const missingStyleClosure = structuredClone(packet);
  delete missingStyleClosure.style_closure;
  missingStyleClosure.packet_digest = canonicalPacketDigest(missingStyleClosure);
  assert.ok(validateDomainPacket(missingStyleClosure).some((error) => error.includes("style_closure is required")));
  const fakeInline = structuredClone(packet);
  fakeInline.runtime_evidence.path_or_inline = { final_runtime_result: "pass" };
  fakeInline.visual_evidence.path_or_inline = { final_visual_result: "pass" };
  fakeInline.packet_digest = canonicalPacketDigest(fakeInline);
  const fakeErrors = validateDomainPacket(fakeInline);
  assert.ok(fakeErrors.some((error) => error.includes("runtime_evidence.path_or_inline: schema")));
  assert.ok(fakeErrors.some((error) => error.includes("visual_evidence.path_or_inline: schema")));
  const barePaths = structuredClone(packet);
  barePaths.runtime_evidence.path_or_inline = "runtime.json";
  barePaths.visual_evidence.path_or_inline = "visual.json";
  barePaths.packet_digest = canonicalPacketDigest(barePaths);
  const barePathErrors = validateDomainPacket(barePaths);
  assert.ok(barePathErrors.filter((error) => error.includes("inline object or {path,digest}")).length >= 2);
  console.log("[PASS] domain packet validator rejected stale, tampered, execute-mode, malformed, and fake-inline packets");
}

function checkRuntimeEvidenceValidator() {
  /** @param {string} repository */
  const command = (repository) => ({
    repository, command: "test", working_directory: repository, runtime: "node", timestamp: "2026-08-12T00:00:00Z",
    exit_code: 0, output_digest: "a".repeat(64),
  });
  /** @type {any} */
  const runtime = {
    schema: "runtime-compatibility-evidence/v1", producer: "migrate-vue2-pages-to-vue3-host", authority: "domain_evidence_only",
    source_revision: "source-1", host_revision: "host-1",
    source_runtime: { required_node: "18", evidence: ["package.json"], package_manager: "npm@9", lock_owner_format: "npm-v2", selected_runtime: "node18", isolation_method: "fnm", command_readiness: "ready" },
    host_runtime: { required_node: "22", evidence: ["package.json"], package_manager: "pnpm@11", lock_owner_format: "pnpm-v9", selected_runtime: "node22", isolation_method: "fnm", command_readiness: "ready" },
    dependency_demands: [{ package: "element-plus", source_exact_version: "2.13.2", license: "MIT", disposition: "reuse-B", decision_status: "approved" }],
    approved_runtime_actions: [], restoration_plan: [], verification_commands: [command("source"), command("host")], final_runtime_result: "pass",
  };
  assert.deepEqual(validateRuntimeEvidence(runtime, { currentSourceRevision: "source-1", currentHostRevision: "host-1" }), []);
  const unresolved = structuredClone(runtime);
  unresolved.dependency_demands[0].disposition = "unknown";
  assert.ok(validateRuntimeEvidence(unresolved).some((error) => error.includes("unresolved dependency demands")));
  const missingHost = structuredClone(runtime);
  missingHost.verification_commands = [command("source")];
  assert.ok(validateRuntimeEvidence(missingHost).some((error) => error.includes("host verification")));
  console.log("[PASS] runtime evidence validator rejected unresolved dependencies and one-sided verification");
}

checkStructure();
checkIndependence();
checkScenarios();
checkVisualEvidenceValidator();
checkDomainPacketValidator();
checkRuntimeEvidenceValidator();
console.log(`PASS: ${SCENARIOS.length} migration stress scenarios and all standalone contracts`);
