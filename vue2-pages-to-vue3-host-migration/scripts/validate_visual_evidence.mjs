#!/usr/bin/env node
// @ts-check

import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { dirname, isAbsolute, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const PASS = "pass";
const SHA256 = /^[0-9a-f]{64}$/i;
const IDENTITY_KEYS = ["url", "route", "marker", "fixture"];
const CHECK_KEYS = ["screenshot", "computed_style", "semantic", "interaction"];
const TABLE_SURFACES = ["container", "header", "rows_cells", "content", "controls"];
const PAGE_STYLE_SURFACES = ["layout", "typography", "box_model", "interaction"];
const ICON_SURFACES = ["content", "geometry", "paint", "accessibility"];
const IMAGE_EXTENSIONS = /\.(png|jpe?g|webp|ppm)$/i;
const ICON_EXTENSIONS = /\.(svg|png|jpe?g|webp|woff2?|ttf|otf)$/i;

/** @param {unknown} value */
function nonEmpty(value) {
  return typeof value === "string" && value.trim().length > 0;
}

/** @param {string} path */
function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

/** @param {unknown} actual @param {unknown} expected */
function same(actual, expected) {
  return typeof actual === typeof expected && String(actual) === String(expected);
}

/** @param {any} metric */
function metricWithinTolerance(metric) {
  if (typeof metric?.baseline === "number" && typeof metric?.candidate === "number") {
    return typeof metric?.tolerance === "number" &&
      Math.abs(metric.baseline - metric.candidate) <= metric.tolerance;
  }
  return metric?.tolerance === "exact" && same(metric?.baseline, metric?.candidate);
}

/**
 * Validate pass-claim completeness for visual-parity-evidence/v1.
 * This checks metadata, artifact integrity, and declared metric math. Screenshot
 * generation and semantic interpretation remain external evidence producers.
 * @param {any} evidence
 * @param {{ baseDir?: string }} [options]
 */
export function validateVisualEvidence(evidence, options = {}) {
  /** @type {string[]} */
  const errors = [];
  const baseDir = options.baseDir || process.cwd();
  /**
   * @param {unknown} condition
   * @param {string} message
   */
  const require = (condition, message) => {
    if (!condition) errors.push(message);
  };
  /**
   * @param {unknown} pathValue
   * @param {unknown} digestValue
   * @param {string} label
   */
  const validateArtifact = (pathValue, digestValue, label) => {
    require(nonEmpty(pathValue), `${label}.path is required`);
    require(nonEmpty(digestValue), `${label}.digest is required`);
    if (!nonEmpty(pathValue)) return;
    const pathText = String(pathValue);
    const digestText = String(digestValue);
    require(IMAGE_EXTENSIONS.test(pathText), `${label}.path must be an image artifact`);
    const absolute = isAbsolute(pathText) ? pathText : resolve(baseDir, pathText);
    require(existsSync(absolute), `${label}.path does not exist: ${absolute}`);
    if (existsSync(absolute) && nonEmpty(digestValue)) {
      require(sha256(absolute) === digestText.toLowerCase(), `${label}.digest does not match file contents`);
    }
  };
  /**
   * @param {unknown} pathValue
   * @param {unknown} digestValue
   * @param {string} label
   * @param {RegExp} extensions
   */
  const validateFileArtifact = (pathValue, digestValue, label, extensions) => {
    require(nonEmpty(pathValue), `${label}.path is required`);
    require(SHA256.test(String(digestValue ?? "")), `${label}.digest must be a SHA-256 digest`);
    if (!nonEmpty(pathValue)) return null;
    const pathText = String(pathValue);
    require(extensions.test(pathText), `${label}.path has an unsupported extension`);
    const absolute = isAbsolute(pathText) ? pathText : resolve(baseDir, pathText);
    require(existsSync(absolute), `${label}.path does not exist: ${absolute}`);
    if (existsSync(absolute) && SHA256.test(String(digestValue ?? ""))) {
      require(sha256(absolute) === String(digestValue).toLowerCase(), `${label}.digest does not match file contents`);
    }
    return existsSync(absolute) ? absolute : null;
  };
  /**
   * @param {unknown} pathValue
   * @param {unknown} digestValue
   * @param {string} label
   */
  const loadJsonArtifact = (pathValue, digestValue, label) => {
    const absolute = validateFileArtifact(pathValue, digestValue, label, /\.json$/i);
    if (!absolute) return null;
    try {
      return JSON.parse(readFileSync(absolute, "utf8"));
    } catch (error) {
      require(false, `${label} is not valid JSON: ${error instanceof Error ? error.message : String(error)}`);
      return null;
    }
  };

  let migrationContract;
  const contractPathValue = evidence?.migration_contract?.path;
  const contractDigestValue = evidence?.migration_contract?.digest;
  require(nonEmpty(contractPathValue), "migration_contract.path is required");
  require(nonEmpty(contractDigestValue), "migration_contract.digest is required");
  if (nonEmpty(contractPathValue)) {
    const contractPath = isAbsolute(contractPathValue) ? contractPathValue : resolve(baseDir, contractPathValue);
    require(existsSync(contractPath), `migration_contract.path does not exist: ${contractPath}`);
    if (existsSync(contractPath)) {
      require(sha256(contractPath) === String(contractDigestValue).toLowerCase(), "migration_contract.digest does not match file contents");
      try {
        migrationContract = JSON.parse(readFileSync(contractPath, "utf8"));
      } catch (error) {
        require(false, `migration_contract is not valid JSON: ${error instanceof Error ? error.message : String(error)}`);
      }
    }
  }
  require(migrationContract?.schema === "visual-migration-contract/v1", "migration contract schema must be visual-migration-contract/v1");
  require(migrationContract?.source_revision === evidence?.source_revision, "migration contract source_revision must match evidence");
  require(migrationContract?.host_revision === evidence?.host_revision, "migration contract host_revision must match evidence");

  require(evidence?.schema === "visual-parity-evidence/v1", "schema must be visual-parity-evidence/v1");
  require(evidence?.producer === "vue2-pages-to-vue3-host-migration", "producer must be vue2-pages-to-vue3-host-migration");
  require(evidence?.authority === "domain_evidence_only", "authority must be domain_evidence_only");
  require(nonEmpty(evidence?.source_revision), "source_revision is required");
  require(nonEmpty(evidence?.host_revision), "host_revision is required");
  require(["strict_parity", "approved_redesign"].includes(evidence?.assessment_mode), "assessment_mode is invalid");
  require(nonEmpty(evidence?.baseline?.source), "baseline.source is required");
  const baselineManifest = loadJsonArtifact(
    evidence?.baseline?.manifest_path,
    evidence?.baseline?.manifest_digest,
    "baseline.manifest"
  );
  require(baselineManifest?.schema === "visual-baseline-manifest/v1", "baseline manifest schema must be visual-baseline-manifest/v1");
  require(baselineManifest?.source_revision === evidence?.source_revision, "baseline manifest source_revision must match evidence");
  require(baselineManifest?.fixture_id === evidence?.capture?.fixture_id, "baseline manifest fixture_id must match capture");
  if (evidence?.assessment_mode === "approved_redesign") {
    require(nonEmpty(evidence?.baseline?.substitute_approved_by), "approved_redesign requires baseline.substitute_approved_by");
  }
  require(nonEmpty(evidence?.comparison_boundary?.content_root_selector), "comparison_boundary.content_root_selector is required");
  require(
    ["host_native", "strict_parity", "explicitly_accepted"].includes(evidence?.comparison_boundary?.host_shell),
    "comparison_boundary.host_shell is invalid"
  );
  require(
    ["strict_parity", "approved_redesign"].includes(evidence?.comparison_boundary?.migrated_content),
    "comparison_boundary.migrated_content is invalid"
  );
  require(
    evidence?.assessment_mode === evidence?.comparison_boundary?.migrated_content,
    "assessment_mode must match comparison_boundary.migrated_content"
  );

  const capture = evidence?.capture;
  for (const key of ["browser", "viewport", "device_scale_factor", "locale", "timezone", "font_ready_condition", "animation_policy", "fixture_id"]) {
    require(capture?.[key] !== undefined && capture?.[key] !== "", `capture.${key} is required`);
  }
  require(capture?.fixture_id === migrationContract?.fixture_id, "capture.fixture_id must match migration contract");

  const differencePolicy = evidence?.difference_policy;
  for (const key of ["forbidden", "tolerance_bound", "explicitly_accepted"]) {
    require(Array.isArray(differencePolicy?.[key]), `difference_policy.${key} must be an array`);
  }
  require((differencePolicy?.forbidden || []).length === 0, "difference_policy.forbidden must be empty for a pass claim");
  for (const [index, tolerance] of (differencePolicy?.tolerance_bound || []).entries()) {
    const label = `difference_policy.tolerance_bound[${index}]`;
    require(nonEmpty(tolerance?.id), `${label}.id is required`);
    require(nonEmpty(tolerance?.reason), `${label}.reason is required`);
    require(tolerance?.threshold !== undefined, `${label}.threshold is required`);
    require(Array.isArray(tolerance?.affected_states) && tolerance.affected_states.length > 0, `${label}.affected_states is required`);
  }
  for (const [index, accepted] of (differencePolicy?.explicitly_accepted || []).entries()) {
    const label = `difference_policy.explicitly_accepted[${index}]`;
    for (const key of ["id", "reason", "approver", "decision_reference"]) {
      require(nonEmpty(accepted?.[key]), `${label}.${key} is required`);
    }
    require(accepted?.source_revision === evidence?.source_revision, `${label}.source_revision must match evidence`);
    require(accepted?.host_revision === evidence?.host_revision, `${label}.host_revision must match evidence`);
    require(Array.isArray(accepted?.affected_states) && accepted.affected_states.length > 0, `${label}.affected_states is required`);
  }

  const styleRequirements = migrationContract?.style_requirements;
  require(styleRequirements?.style_closure_required === true, "migration contract must require style closure");
  const requiredStyleSurfaces = Array.isArray(styleRequirements?.required_style_surfaces)
    ? styleRequirements.required_style_surfaces : [];
  for (const surface of PAGE_STYLE_SURFACES) {
    require(requiredStyleSurfaces.includes(surface), `migration contract required_style_surfaces must include ${surface}`);
  }
  const requiredStyleProperties = Array.isArray(styleRequirements?.required_style_properties)
    ? styleRequirements.required_style_properties : [];
  for (const property of ["font-family", "font-size", "font-weight", "line-height", "box-sizing"]) {
    require(requiredStyleProperties.includes(property), `migration contract required_style_properties must include ${property}`);
  }
  const requiredColorRoles = Array.isArray(styleRequirements?.required_color_roles)
    ? styleRequirements.required_color_roles : [];
  require(new Set(requiredColorRoles).size >= 3, "migration contract must require at least three semantic color roles");
  const requiredIconIds = Array.isArray(styleRequirements?.required_icon_ids)
    ? styleRequirements.required_icon_ids : [];

  const styleClosure = evidence?.style_closure;
  require(styleClosure?.status === "complete", "style_closure.status must be complete");
  const styleEntries = Array.isArray(styleClosure?.entries) ? styleClosure.entries : [];
  require(styleEntries.length > 0, "style_closure.entries must not be empty");
  for (const [index, dependency] of styleEntries.entries()) {
    const label = `style_closure.entries[${index}]`;
    for (const key of ["id", "kind", "source", "evidence", "disposition", "target"]) {
      require(nonEmpty(dependency?.[key]), `${label}.${key} is required`);
    }
  }
  require(Array.isArray(styleClosure?.unresolved), "style_closure.unresolved must be an array");
  require((styleClosure?.unresolved || []).length === 0, "style_closure.unresolved must be empty");

  const pageStyle = evidence?.page_style_contract;
  require(pageStyle?.result === PASS, "page_style_contract.result must be pass");
  /** @type {any[]} */
  const pageMetrics = Array.isArray(pageStyle?.metrics) ? pageStyle.metrics : [];
  const coveredStyleSurfaces = new Set(pageMetrics.map((metric) => metric?.surface));
  const coveredStyleProperties = new Set(pageMetrics.map((metric) => metric?.property));
  for (const surface of requiredStyleSurfaces) {
    require(coveredStyleSurfaces.has(surface), `page_style_contract.metrics must cover ${surface}`);
  }
  for (const property of requiredStyleProperties) {
    require(coveredStyleProperties.has(property), `page_style_contract.metrics must cover property ${property}`);
  }
  for (const [index, metric] of pageMetrics.entries()) {
    const label = `page_style_contract.metrics[${index}]`;
    for (const key of ["surface", "id", "selector", "state_class", "property"]) {
      require(nonEmpty(metric?.[key]), `${label}.${key} is required`);
    }
    require(metric?.baseline !== undefined, `${label}.baseline is required`);
    require(metric?.candidate !== undefined, `${label}.candidate is required`);
    require(typeof metric?.baseline === typeof metric?.candidate, `${label} baseline/candidate types must match`);
    require(metric?.tolerance !== undefined, `${label}.tolerance is required`);
    require(metricWithinTolerance(metric), `${label} baseline/candidate exceed tolerance`);
    require(metric?.result === PASS, `${label}.result must be pass`);
  }

  const colorContract = evidence?.color_contract;
  require(colorContract?.result === PASS, "color_contract.result must be pass");
  /** @type {any[]} */
  const colorMetrics = Array.isArray(colorContract?.metrics) ? colorContract.metrics : [];
  const coveredColorRoles = new Set(colorMetrics.map((metric) => metric?.role));
  for (const role of requiredColorRoles) {
    require(coveredColorRoles.has(role), `color_contract.metrics must cover role ${role}`);
  }
  for (const [index, metric] of colorMetrics.entries()) {
    const label = `color_contract.metrics[${index}]`;
    for (const key of ["id", "role", "selector", "state_class", "property"]) {
      require(nonEmpty(metric?.[key]), `${label}.${key} is required`);
    }
    require(metric?.baseline !== undefined, `${label}.baseline is required`);
    require(metric?.candidate !== undefined, `${label}.candidate is required`);
    require(typeof metric?.baseline === typeof metric?.candidate, `${label} baseline/candidate types must match`);
    require(metric?.tolerance === "exact", `${label}.tolerance must be exact`);
    require(metricWithinTolerance(metric), `${label} baseline/candidate exceed tolerance`);
    require(metric?.result === PASS, `${label}.result must be pass`);
  }

  require(typeof evidence?.contains_icons === "boolean", "contains_icons must be explicit");
  require(evidence?.contains_icons === (requiredIconIds.length > 0), "contains_icons must match migration contract required_icon_ids");
  if (requiredIconIds.length > 0) {
    const iconContract = evidence?.icon_contract;
    require(iconContract?.result === PASS, "icon_contract.result must be pass");
    /** @type {any[]} */
    const icons = Array.isArray(iconContract?.icons) ? iconContract.icons : [];
    const iconIds = new Set(icons.map((icon) => icon?.id));
    for (const iconId of requiredIconIds) require(iconIds.has(iconId), `icon_contract.icons must cover ${iconId}`);
    for (const [index, icon] of icons.entries()) {
      const label = `icon_contract.icons[${index}]`;
      require(nonEmpty(icon?.id), `${label}.id is required`);
      require(nonEmpty(icon?.selector), `${label}.selector is required`);
      validateFileArtifact(icon?.source?.path, icon?.source?.digest, `${label}.source`, ICON_EXTENSIONS);
      validateFileArtifact(icon?.candidate?.path, icon?.candidate?.digest, `${label}.candidate`, ICON_EXTENSIONS);
      require(nonEmpty(icon?.source?.fingerprint), `${label}.source.fingerprint is required`);
      require(nonEmpty(icon?.candidate?.fingerprint), `${label}.candidate.fingerprint is required`);
      require(icon?.source?.fingerprint === icon?.candidate?.fingerprint, `${label} source/candidate fingerprint mismatch`);
      /** @type {any[]} */
      const iconMetrics = Array.isArray(icon?.metrics) ? icon.metrics : [];
      const iconSurfaces = new Set(iconMetrics.map((metric) => metric?.surface));
      for (const surface of ICON_SURFACES) require(iconSurfaces.has(surface), `${label}.metrics must cover ${surface}`);
      for (const [metricIndex, metric] of iconMetrics.entries()) {
        const metricLabel = `${label}.metrics[${metricIndex}]`;
        require(nonEmpty(metric?.id), `${metricLabel}.id is required`);
        require(metric?.baseline !== undefined, `${metricLabel}.baseline is required`);
        require(metric?.candidate !== undefined, `${metricLabel}.candidate is required`);
        require(typeof metric?.baseline === typeof metric?.candidate, `${metricLabel} baseline/candidate types must match`);
        require(metric?.tolerance !== undefined, `${metricLabel}.tolerance is required`);
        require(metricWithinTolerance(metric), `${metricLabel} baseline/candidate exceed tolerance`);
        require(metric?.result === PASS, `${metricLabel}.result must be pass`);
      }
      require(icon?.result === PASS, `${label}.result must be pass`);
    }
  }

  /** @type {any[]} */
  const states = Array.isArray(evidence?.required_states) ? evidence.required_states : [];
  require(states.length >= 5, "at least five required_states are required");
  const stateIds = states.map((state) => state?.id).filter(nonEmpty);
  require(new Set(stateIds).size === stateIds.length, "required_states ids must be unique");
  const stateClasses = states.map((state) => state?.state_class).filter(nonEmpty);
  require(new Set(stateClasses).size >= Math.min(5, states.length), "required_states must cover at least five distinct state_class values");
  const contractedClasses = Array.isArray(migrationContract?.required_state_classes) ? migrationContract.required_state_classes : [];
  require(contractedClasses.length >= 5, "migration contract must require at least five state classes");
  for (const stateClass of contractedClasses) require(stateClasses.includes(stateClass), `required_states must cover contracted state class '${stateClass}'`);
  const baselineRows = Array.isArray(baselineManifest?.states) ? baselineManifest.states : [];
  require(baselineRows.length === states.length, "baseline manifest must contain exactly one row per required state");
  const baselineById = new Map(baselineRows.map((row) => [row?.id, row]));
  require(baselineById.size === baselineRows.length, "baseline manifest state ids must be unique");
  /** @type {Map<unknown, any[]>} */
  const computedMetricsByStateClass = new Map();

  for (const [index, state] of states.entries()) {
    const label = `required_states[${index}]${nonEmpty(state?.id) ? `(${state.id})` : ""}`;
    require(nonEmpty(state?.id), `${label}.id is required`);
    require(nonEmpty(state?.state_class), `${label}.state_class is required`);
    for (const key of IDENTITY_KEYS) {
      const assertion = state?.identity_assertions?.[key];
      require(assertion?.result === PASS, `${label}.identity_assertions.${key}.result must be pass`);
      require(assertion?.expected !== undefined, `${label}.identity_assertions.${key}.expected is required`);
      require(assertion?.actual !== undefined, `${label}.identity_assertions.${key}.actual is required`);
      if (assertion?.expected !== undefined && assertion?.actual !== undefined) {
        require(same(assertion.actual, assertion.expected), `${label}.identity_assertions.${key} expected/actual mismatch`);
      }
      const contracted = key === "fixture" ? migrationContract?.fixture_id : migrationContract?.native_identity?.[key];
      require(assertion?.expected === contracted, `${label}.identity_assertions.${key}.expected must match migration contract`);
    }
    if (evidence?.legacy_boundary?.detected === true) {
      const mode = state?.identity_assertions?.migration_mode;
      require(mode?.result === PASS, `${label}.identity_assertions.migration_mode.result must be pass`);
      require(mode?.expected !== undefined && same(mode.actual, mode.expected), `${label}.identity_assertions.migration_mode expected/actual mismatch`);
      require(mode?.expected === "native", `${label}.identity_assertions.migration_mode.expected must be native for candidate evidence`);
    }
    const baselineRow = baselineById.get(state?.id);
    require(baselineRow !== undefined, `${label} is missing from baseline manifest`);
    require(baselineRow?.state_class === state?.state_class, `${label} baseline manifest state_class mismatch`);
    require(baselineRow?.path === state?.artifacts?.baseline_path, `${label} baseline path must match baseline manifest`);
    require(baselineRow?.digest === state?.artifacts?.baseline_digest, `${label} baseline digest must match baseline manifest`);
    validateArtifact(state?.artifacts?.baseline_path, state?.artifacts?.baseline_digest, `${label}.artifacts.baseline`);
    validateArtifact(state?.artifacts?.candidate_path, state?.artifacts?.candidate_digest, `${label}.artifacts.candidate`);
    validateArtifact(state?.artifacts?.diff_path, state?.artifacts?.diff_digest, `${label}.artifacts.diff`);
    const computedStyle = loadJsonArtifact(
      state?.artifacts?.computed_style_path,
      state?.artifacts?.computed_style_digest,
      `${label}.artifacts.computed_style`
    );
    require(computedStyle?.schema === "computed-style-evidence/v1", `${label} computed style schema must be computed-style-evidence/v1`);
    require(computedStyle?.state_id === state?.id, `${label} computed style state_id mismatch`);
    require(computedStyle?.fixture_id === evidence?.capture?.fixture_id, `${label} computed style fixture_id mismatch`);
    /** @type {any[]} */
    const computedMetrics = Array.isArray(computedStyle?.metrics) ? computedStyle.metrics : [];
    require(computedMetrics.length > 0, `${label} computed style metrics must not be empty`);
    for (const [metricIndex, metric] of computedMetrics.entries()) {
      const metricLabel = `${label}.artifacts.computed_style.metrics[${metricIndex}]`;
      require(nonEmpty(metric?.selector), `${metricLabel}.selector is required`);
      require(nonEmpty(metric?.property), `${metricLabel}.property is required`);
      require(metric?.value !== undefined, `${metricLabel}.value is required`);
    }
    computedMetricsByStateClass.set(state?.state_class, computedMetrics);
    for (const key of CHECK_KEYS) {
      require(state?.checks?.[key] === PASS, `${label}.checks.${key} must be pass`);
    }
    require(state?.result === PASS, `${label}.result must be pass`);
  }
  /**
   * @param {any[]} contractMetrics
   * @param {string} contractLabel
   */
  const requireComputedStyleBacking = (contractMetrics, contractLabel) => {
    for (const [index, metric] of contractMetrics.entries()) {
      const computedMetrics = computedMetricsByStateClass.get(metric?.state_class) || [];
      require(
        computedMetrics.some((measured) =>
          measured?.selector === metric?.selector &&
          measured?.property === metric?.property &&
          same(measured?.value, metric?.candidate)
        ),
        `${contractLabel}.metrics[${index}] candidate is not backed by its state computed-style artifact`
      );
    }
  };
  requireComputedStyleBacking(pageMetrics, "page_style_contract");
  requireComputedStyleBacking(colorMetrics, "color_contract");
  const candidateDigests = states.map((state) => state?.artifacts?.candidate_digest).filter(nonEmpty);
  const diffDigests = states.map((state) => state?.artifacts?.diff_digest).filter(nonEmpty);
  const baselineDigests = states.map((state) => state?.artifacts?.baseline_digest).filter(nonEmpty);
  const baselinePaths = states.map((state) => state?.artifacts?.baseline_path).filter(nonEmpty);
  require(new Set(candidateDigests).size === candidateDigests.length, "required_states candidate artifacts must be distinct");
  require(new Set(diffDigests).size === diffDigests.length, "required_states diff artifacts must be distinct");
  require(new Set(baselinePaths).size === states.length, "required_states baseline artifact paths must be distinct");
  require(new Set(baselineDigests).size === states.length, "required_states baseline artifact digests must be distinct");
  for (const [index, tolerance] of (differencePolicy?.tolerance_bound || []).entries()) {
    for (const stateId of tolerance?.affected_states || []) {
      require(stateIds.includes(stateId), `difference_policy.tolerance_bound[${index}] references unknown state '${stateId}'`);
    }
  }
  for (const [index, accepted] of (differencePolicy?.explicitly_accepted || []).entries()) {
    for (const stateId of accepted?.affected_states || []) {
      require(stateIds.includes(stateId), `difference_policy.explicitly_accepted[${index}] references unknown state '${stateId}'`);
    }
  }

  if (evidence?.contains_table === true) {
    const table = evidence?.table_contract;
    require(table && typeof table === "object", "table_contract is required when contains_table=true");
    require(table?.result === PASS, "table_contract.result must be pass");
    /** @type {any[]} */
    const metrics = Array.isArray(table?.metrics) ? table.metrics : [];
    const surfaces = new Set(metrics.map((metric) => metric?.surface));
    for (const surface of TABLE_SURFACES) require(surfaces.has(surface), `table_contract.metrics must cover ${surface}`);
    for (const [index, metric] of metrics.entries()) {
      const label = `table_contract.metrics[${index}]`;
      require(nonEmpty(metric?.id), `${label}.id is required`);
      require(metric?.baseline !== undefined, `${label}.baseline is required`);
      require(metric?.candidate !== undefined, `${label}.candidate is required`);
      require(typeof metric?.baseline === typeof metric?.candidate, `${label} baseline/candidate types must match`);
      require(metric?.tolerance !== undefined, `${label}.tolerance is required`);
      require(metricWithinTolerance(metric), `${label} baseline/candidate exceed tolerance`);
      require(metric?.result === PASS, `${label}.result must be pass`);
    }
  }

  const legacy = evidence?.legacy_boundary;
  require(typeof legacy?.detected === "boolean", "legacy_boundary.detected must be explicit");
  require(nonEmpty(legacy?.detection_method), "legacy_boundary.detection_method is required");
  validateArtifact(legacy?.evidence_path, legacy?.evidence_digest, "legacy_boundary.evidence");
  require(evidence?.rollback?.applicable === legacy?.detected, "rollback.applicable must match legacy_boundary.detected");
  require(legacy?.detected === migrationContract?.legacy_boundary_required, "legacy_boundary.detected must match migration contract");
  if (legacy?.detected === true) {
    require(evidence?.rollback?.tested === true, "rollback.tested must be true when a legacy boundary is detected");
    require(evidence?.rollback?.deterministic_fixture === true, "rollback.deterministic_fixture must be true");
    require(evidence?.rollback?.result === PASS, "rollback.result must be pass");
    if (evidence?.rollback?.nested_shell === true) {
      const acceptance = evidence.rollback.nested_shell_acceptance;
      require(acceptance?.disposition === "explicitly_accepted", "rollback nested shell acceptance disposition must be explicitly_accepted");
      require(nonEmpty(acceptance?.approver), "rollback nested shell acceptance requires approver");
      require(nonEmpty(acceptance?.decision_reference), "rollback nested shell acceptance requires decision_reference");
      require(acceptance?.source_revision === evidence?.source_revision, "rollback nested shell acceptance source_revision mismatch");
      require(acceptance?.host_revision === evidence?.host_revision, "rollback nested shell acceptance host_revision mismatch");
      require(Array.isArray(acceptance?.affected_states) && acceptance.affected_states.length > 0, "rollback nested shell acceptance requires affected_states");
      for (const stateId of acceptance?.affected_states || []) require(stateIds.includes(stateId), `rollback nested shell acceptance references unknown state '${stateId}'`);
    }
  }

  require(typeof evidence?.global_style_changed === "boolean", "global_style_changed must be explicit");
  if (evidence?.global_style_changed === true) {
    /** @type {any[]} */
    const collateral = Array.isArray(evidence?.global_collateral) ? evidence.global_collateral : [];
    require(collateral.length >= 3, "global_collateral must contain migrated page and two existing B pages");
    require(collateral.filter((row) => row?.kind === "migrated").length >= 1, "global_collateral must include a migrated page row");
    require(collateral.filter((row) => row?.kind === "existing_host").length >= 2, "global_collateral must include two existing host page rows");
    for (const [index, row] of collateral.entries()) {
      const label = `global_collateral[${index}]`;
      require(nonEmpty(row?.id), `${label}.id is required`);
      require(nonEmpty(row?.route), `${label}.route is required`);
      require(row?.identity_result === PASS, `${label}.identity_result must be pass`);
      validateArtifact(row?.artifacts?.candidate_path, row?.artifacts?.candidate_digest, `${label}.artifacts.candidate`);
      validateArtifact(row?.artifacts?.diff_path, row?.artifacts?.diff_digest, `${label}.artifacts.diff`);
      require(row?.result === PASS, `${label}.result must be pass`);
    }
  }

  require(["independent", "authorized_human"].includes(evidence?.review?.mode), "review.mode is invalid");
  require(nonEmpty(evidence?.review?.reviewer), "review.reviewer is required");
  if (evidence?.final_visual_result === PASS) {
    require(errors.length === 0, "final_visual_result=pass is invalid while required evidence is incomplete");
  } else {
    require(false, "final_visual_result must be pass for completion validation");
  }
  return errors;
}

function main() {
  const path = process.argv[2];
  if (!path) {
    console.error("Usage: node scripts/validate_visual_evidence.mjs <visual-evidence.json>");
    process.exitCode = 2;
    return;
  }
  let evidence;
  try {
    evidence = JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    console.error(`FAIL: cannot read evidence: ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 2;
    return;
  }
  const errors = validateVisualEvidence(evidence, { baseDir: dirname(resolve(path)) });
  if (errors.length) {
    console.error(`FAIL: ${errors.length} visual evidence contract error(s)`);
    for (const error of errors) console.error(`- ${error}`);
    process.exitCode = 1;
    return;
  }
  console.log("PASS: visual-parity-evidence/v1 is complete and pass-claim consistent");
}

if (import.meta.url === pathToFileURL(process.argv[1] || "").href) main();
