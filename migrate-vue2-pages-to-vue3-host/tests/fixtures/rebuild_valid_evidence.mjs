#!/usr/bin/env node
// @ts-check
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ART = join(HERE, "artifacts");

/** @param {Buffer|string} buf */
function hash(buf) {
  return createHash("sha256").update(buf).digest("hex");
}

/**
 * @param {string} label
 * @param {number} r
 * @param {number} g
 * @param {number} b
 */
function makePpm(label, r, g, b) {
  return Buffer.from(
    `P3\n# ${label}\n2 2\n255\n${r} ${g} ${b}  ${r} ${g} ${b}\n${r} ${g} ${b}  ${r} ${g} ${b}\n`
  );
}

const states = [
  { id: "loading", rgb: [10, 20, 30] },
  { id: "loaded", rgb: [40, 50, 60] },
  { id: "empty", rgb: [70, 80, 90] },
  { id: "editing", rgb: [100, 110, 120] },
  { id: "narrow", rgb: [130, 140, 150] },
];

const identity = {
  url: {
    expected: "http://a.test/#/orders",
    actual: "http://a.test/#/orders",
    result: "pass",
  },
  route: { expected: "#/orders", actual: "#/orders", result: "pass" },
  marker: { expected: "orders", actual: "orders", result: "pass" },
  fixture: { expected: "orders-v1", actual: "orders-v1", result: "pass" },
  migration_mode: { expected: "native", actual: "native", result: "pass" },
};

const baselineDigest = hash(readFileSync(join(ART, "baseline.ppm")));
const legacyDigest = hash(readFileSync(join(ART, "legacy-boundary.ppm")));
const contractDigest = hash(readFileSync(join(HERE, "visual-migration-contract.json")));

/** @type {any[]} */
const requiredStates = [];
for (const state of states) {
  const [r, g, b] = state.rgb;
  const candidate = makePpm(`candidate-${state.id}`, r, g, b);
  const diff = makePpm(`diff-${state.id}`, 255 - r, g, b);
  const candidatePath = `artifacts/candidate-${state.id}.ppm`;
  const diffPath = `artifacts/diff-${state.id}.ppm`;
  writeFileSync(join(HERE, candidatePath), candidate);
  writeFileSync(join(HERE, diffPath), diff);
  requiredStates.push({
    id: state.id,
    state_class: state.id,
    identity_assertions: identity,
    artifacts: {
      baseline_path: "artifacts/baseline.ppm",
      baseline_digest: baselineDigest,
      candidate_path: candidatePath,
      candidate_digest: hash(candidate),
      diff_path: diffPath,
      diff_digest: hash(diff),
    },
    checks: {
      screenshot: "pass",
      computed_style: "pass",
      semantic: "pass",
      interaction: "pass",
    },
    result: "pass",
  });
}

const evidence = {
  schema: "visual-parity-evidence/v1",
  producer: "migrate-vue2-pages-to-vue3-host",
  authority: "domain_evidence_only",
  source_revision: "source-123",
  host_revision: "host-456",
  assessment_mode: "strict_parity",
  migration_contract: {
    path: "visual-migration-contract.json",
    digest: contractDigest,
  },
  baseline: {
    source: "running-a",
    digest: baselineDigest,
  },
  comparison_boundary: {
    host_shell: "host_native",
    migrated_content: "strict_parity",
    content_root_selector: "[data-visual-unit='orders']",
  },
  capture: {
    browser: "Chromium 151",
    viewport: "1440x900",
    device_scale_factor: 1,
    locale: "en-US",
    timezone: "Asia/Shanghai",
    font_ready_condition: "document.fonts.ready",
    animation_policy: "reduced",
    fixture_id: "orders-v1",
  },
  difference_policy: {
    forbidden: [],
    tolerance_bound: [],
    explicitly_accepted: [],
  },
  contains_table: true,
  required_states: requiredStates,
  table_contract: {
    metrics: [
      {
        surface: "container",
        id: "table-border",
        baseline: "#dfe6ec",
        candidate: "#dfe6ec",
        tolerance: "exact",
        result: "pass",
      },
      {
        surface: "header",
        id: "header-height",
        baseline: 44,
        candidate: 44,
        tolerance: 2,
        result: "pass",
      },
      {
        surface: "rows_cells",
        id: "row-height",
        baseline: 54,
        candidate: 54,
        tolerance: 2,
        result: "pass",
      },
      {
        surface: "content",
        id: "importance-wrap",
        baseline: "nowrap",
        candidate: "nowrap",
        tolerance: "exact",
        result: "pass",
      },
      {
        surface: "controls",
        id: "edit-button-height",
        baseline: 33,
        candidate: 33,
        tolerance: 2,
        result: "pass",
      },
    ],
    result: "pass",
  },
  legacy_boundary: {
    detected: true,
    detection_method: "migration registry entry",
    evidence_path: "artifacts/legacy-boundary.ppm",
    evidence_digest: legacyDigest,
  },
  rollback: {
    applicable: true,
    tested: true,
    nested_shell: false,
    deterministic_fixture: true,
    result: "pass",
  },
  global_style_changed: false,
  review: {
    mode: "independent",
    reviewer: "review-agent-2",
  },
  final_visual_result: "pass",
};

writeFileSync(join(HERE, "visual-evidence-valid.json"), `${JSON.stringify(evidence, null, 2)}\n`);
console.log("rebuilt visual-evidence-valid.json");
console.log("contract digest:", contractDigest);
