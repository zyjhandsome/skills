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

const legacyDigest = hash(readFileSync(join(ART, "legacy-boundary.ppm")));
const contractDigest = hash(readFileSync(join(HERE, "visual-migration-contract.json")));

/** @type {any[]} */
const requiredStates = [];
/** @type {any[]} */
const baselineStates = [];
for (const state of states) {
  const [r, g, b] = state.rgb;
  const baseline = makePpm(`baseline-${state.id}`, r, g, b);
  const candidate = makePpm(`candidate-${state.id}`, r, g, b);
  const diff = makePpm(`diff-${state.id}`, 255 - r, g, b);
  const baselinePath = `artifacts/baseline-${state.id}.ppm`;
  const candidatePath = `artifacts/candidate-${state.id}.ppm`;
  const diffPath = `artifacts/diff-${state.id}.ppm`;
  const computedStylePath = `artifacts/computed-style-${state.id}.json`;
  const computedStyle = Buffer.from(`${JSON.stringify({
    schema: "computed-style-evidence/v1",
    state_id: state.id,
    fixture_id: "orders-v1",
    metrics: [
      { selector: "[data-visual-unit='orders']", property: "width", value: 1200 },
      { selector: "[data-visual-unit='orders']", property: "font-family", value: "Arial, sans-serif" },
      { selector: "[data-visual-unit='orders']", property: "font-size", value: "14px" },
      { selector: "[data-visual-unit='orders']", property: "font-weight", value: "400" },
      { selector: "[data-visual-unit='orders']", property: "line-height", value: "20px" },
      { selector: "[data-visual-unit='orders']", property: "box-sizing", value: "border-box" },
      { selector: "[data-visual-unit='orders']", property: "background-color", value: "rgb(255, 255, 255)" },
      { selector: "[data-visual-unit='orders']", property: "color", value: "rgb(48, 49, 51)" },
      { selector: ".orders-table", property: "border-color", value: "rgb(223, 230, 236)" },
      { selector: "[data-icon='edit']", property: "color", value: "rgb(64, 158, 255)" },
      { selector: "[data-icon='edit']", property: "cursor", value: "pointer" },
      { selector: ".status-success", property: "color", value: "rgb(103, 194, 58)" },
    ],
  }, null, 2)}\n`);
  writeFileSync(join(HERE, baselinePath), baseline);
  writeFileSync(join(HERE, candidatePath), candidate);
  writeFileSync(join(HERE, diffPath), diff);
  writeFileSync(join(HERE, computedStylePath), computedStyle);
  const baselineDigest = hash(baseline);
  baselineStates.push({
    id: state.id,
    state_class: state.id,
    path: baselinePath,
    digest: baselineDigest,
  });
  requiredStates.push({
    id: state.id,
    state_class: state.id,
    identity_assertions: identity,
    artifacts: {
      baseline_path: baselinePath,
      baseline_digest: baselineDigest,
      candidate_path: candidatePath,
      candidate_digest: hash(candidate),
      diff_path: diffPath,
      diff_digest: hash(diff),
      computed_style_path: computedStylePath,
      computed_style_digest: hash(computedStyle),
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

const baselineManifest = Buffer.from(`${JSON.stringify({
  schema: "visual-baseline-manifest/v1",
  source_revision: "source-123",
  fixture_id: "orders-v1",
  states: baselineStates,
}, null, 2)}\n`);
writeFileSync(join(HERE, "visual-baseline-manifest.json"), baselineManifest);

const editIcon = Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75z"/></svg>\n');
const refreshIcon = Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M17.65 6.35A7.95 7.95 0 0 0 12 4V1L7 6l5 5V7a5 5 0 1 1-4.9 6H4.02A8 8 0 1 0 17.65 6.35z"/></svg>\n');
/** @type {[string, Buffer][]} */
const iconAssets = [["edit", editIcon], ["refresh", refreshIcon]];
for (const [name, content] of iconAssets) {
  writeFileSync(join(ART, `${name}-source.svg`), content);
  writeFileSync(join(ART, `${name}-candidate.svg`), content);
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
    manifest_path: "visual-baseline-manifest.json",
    manifest_digest: hash(baselineManifest),
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
  style_closure: {
    status: "complete",
    entries: [
      {
        id: "orders-sfc-style",
        kind: "sfc-style",
        source: "src/views/orders/index.vue",
        evidence: "SFC style block inspected",
        disposition: "adapt-to-B",
        target: "src/views/orders/index.vue",
      },
      {
        id: "orders-theme-vars",
        kind: "scss-variable",
        source: "src/styles/variables.scss",
        evidence: "$primary-color=#409eff",
        disposition: "adapt-to-B",
        target: "src/views/orders/orders-compat.scss",
      },
      {
        id: "orders-edit-icon",
        kind: "icon",
        source: "src/icons/edit.svg",
        evidence: "sha256 fingerprint",
        disposition: "copy-local",
        target: "src/views/orders/icons/edit.svg",
      },
    ],
    unresolved: [],
  },
  page_style_contract: {
    metrics: [
      { surface: "layout", id: "content-width", selector: "[data-visual-unit='orders']", state_class: "loaded", property: "width", baseline: 1200, candidate: 1200, tolerance: 2, result: "pass" },
      { surface: "typography", id: "body-font-family", selector: "[data-visual-unit='orders']", state_class: "loaded", property: "font-family", baseline: "Arial, sans-serif", candidate: "Arial, sans-serif", tolerance: "exact", result: "pass" },
      { surface: "typography", id: "body-font-size", selector: "[data-visual-unit='orders']", state_class: "loaded", property: "font-size", baseline: "14px", candidate: "14px", tolerance: "exact", result: "pass" },
      { surface: "typography", id: "body-font-weight", selector: "[data-visual-unit='orders']", state_class: "loaded", property: "font-weight", baseline: "400", candidate: "400", tolerance: "exact", result: "pass" },
      { surface: "typography", id: "body-line-height", selector: "[data-visual-unit='orders']", state_class: "loaded", property: "line-height", baseline: "20px", candidate: "20px", tolerance: "exact", result: "pass" },
      { surface: "box_model", id: "content-box-sizing", selector: "[data-visual-unit='orders']", state_class: "loaded", property: "box-sizing", baseline: "border-box", candidate: "border-box", tolerance: "exact", result: "pass" },
      { surface: "interaction", id: "edit-cursor", selector: "[data-icon='edit']", state_class: "editing", property: "cursor", baseline: "pointer", candidate: "pointer", tolerance: "exact", result: "pass" },
    ],
    result: "pass",
  },
  color_contract: {
    metrics: [
      { id: "page-background", role: "page-background", selector: "[data-visual-unit='orders']", state_class: "loaded", property: "background-color", baseline: "rgb(255, 255, 255)", candidate: "rgb(255, 255, 255)", tolerance: "exact", result: "pass" },
      { id: "body-text", role: "body-text", selector: "[data-visual-unit='orders']", state_class: "loaded", property: "color", baseline: "rgb(48, 49, 51)", candidate: "rgb(48, 49, 51)", tolerance: "exact", result: "pass" },
      { id: "table-border", role: "border", selector: ".orders-table", state_class: "loaded", property: "border-color", baseline: "rgb(223, 230, 236)", candidate: "rgb(223, 230, 236)", tolerance: "exact", result: "pass" },
      { id: "primary-action", role: "primary-action", selector: "[data-icon='edit']", state_class: "loaded", property: "color", baseline: "rgb(64, 158, 255)", candidate: "rgb(64, 158, 255)", tolerance: "exact", result: "pass" },
      { id: "success-status", role: "status-success", selector: ".status-success", state_class: "loaded", property: "color", baseline: "rgb(103, 194, 58)", candidate: "rgb(103, 194, 58)", tolerance: "exact", result: "pass" },
    ],
    result: "pass",
  },
  contains_icons: true,
  icon_contract: {
    icons: [
      {
        id: "edit",
        selector: "[data-icon='edit']",
        source: { path: "artifacts/edit-source.svg", digest: hash(editIcon), fingerprint: hash(editIcon) },
        candidate: { path: "artifacts/edit-candidate.svg", digest: hash(editIcon), fingerprint: hash(editIcon) },
        metrics: [
          { surface: "content", id: "edit-viewbox-path", baseline: hash(editIcon), candidate: hash(editIcon), tolerance: "exact", result: "pass" },
          { surface: "geometry", id: "edit-size", baseline: 16, candidate: 16, tolerance: 1, result: "pass" },
          { surface: "paint", id: "edit-fill", baseline: "currentColor", candidate: "currentColor", tolerance: "exact", result: "pass" },
          { surface: "accessibility", id: "edit-label", baseline: "Edit", candidate: "Edit", tolerance: "exact", result: "pass" },
        ],
        result: "pass",
      },
      {
        id: "refresh",
        selector: "[data-icon='refresh']",
        source: { path: "artifacts/refresh-source.svg", digest: hash(refreshIcon), fingerprint: hash(refreshIcon) },
        candidate: { path: "artifacts/refresh-candidate.svg", digest: hash(refreshIcon), fingerprint: hash(refreshIcon) },
        metrics: [
          { surface: "content", id: "refresh-viewbox-path", baseline: hash(refreshIcon), candidate: hash(refreshIcon), tolerance: "exact", result: "pass" },
          { surface: "geometry", id: "refresh-size", baseline: 16, candidate: 16, tolerance: 1, result: "pass" },
          { surface: "paint", id: "refresh-fill", baseline: "currentColor", candidate: "currentColor", tolerance: "exact", result: "pass" },
          { surface: "accessibility", id: "refresh-label", baseline: "Refresh", candidate: "Refresh", tolerance: "exact", result: "pass" },
        ],
        result: "pass",
      },
    ],
    result: "pass",
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
