#!/usr/bin/env node
// @ts-check
/**
 * Family integrity self-check: run before shipping the delivery-* skills to other users.
 *
 * 1. Every relative path referenced in the four SKILL.md files and shared references
 *    (references/*.md, scripts/*.mjs, tests/*) resolves to an existing file/dir.
 * 2. family_version strings outside the authoritative family-contract.md match its value.
 * 3. All four skills plus the shared contract/template/adapter files exist (atomic install).
 *
 * Zero dependencies (Node >= 18). Exit 0 = consistent, 1 = broken reference or version drift.
 */

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve, relative, extname } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

const TESTS_DIR = dirname(fileURLToPath(import.meta.url));
const SKILLS_ROOT = resolve(TESTS_DIR, "..", "..");
const FAMILY = ["delivery-explore", "delivery-frame-spec", "delivery-plan-tasks", "delivery-execute-verify"];
const REQUIRED_SHARED = [
  "delivery-frame-spec/references/family-contract.md",
  "delivery-frame-spec/references/handoff-contract.md",
  "delivery-frame-spec/references/handoff-template.md",
  "delivery-frame-spec/references/batch-clarification.md",
  "delivery-frame-spec/references/openspec-adapter.md",
  "delivery-frame-spec/scripts/validate_handoff.mjs",
  "delivery-frame-spec/scripts/hash_change_artifacts.mjs",
  "delivery-frame-spec/scripts/delivery_scaffold.mjs",
  "delivery-execute-verify/scripts/validate_delivery_change.mjs",
];
// Backtick-quoted relative paths that live in the repo, including cross-skill references
// like `../delivery-frame-spec/references/family-contract.md`. Skip templates/placeholders.
const PATH_RE = /`((?:\.\.\/)?(?:delivery-[a-z-]+\/)?(?:references|scripts|tests)\/[A-Za-z0-9_./-]+)`/g;
const VERSION_RE = /delivery-family\/(\d+\.\d+)/g;
const AUTHORITY = join(SKILLS_ROOT, "delivery-frame-spec", "references", "family-contract.md");

/** @param {string} p */
function isFile(p) {
  try {
    return statSync(p).isFile();
  } catch {
    return false;
  }
}

/** @returns {string[]} */
function scanFiles() {
  /** @type {string[]} */
  const files = [];
  for (const skill of FAMILY) {
    const root = join(SKILLS_ROOT, skill);
    files.push(join(root, "SKILL.md"));
    const refsDir = join(root, "references");
    try {
      for (const name of readdirSync(refsDir)) {
        if (name.endsWith(".md")) files.push(join(refsDir, name));
      }
    } catch {
      // no references dir
    }
  }
  return files.filter(isFile);
}

/**
 * Recursively list files under dir.
 * @param {string} dir
 * @returns {string[]}
 */
function walk(dir) {
  /** @type {string[]} */
  const out = [];
  let entries;
  try {
    entries = readdirSync(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const entry of entries) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full));
    else if (entry.isFile()) out.push(full);
  }
  return out;
}

function main() {
  /** @type {string[]} */
  const errors = [];

  for (const rel of REQUIRED_SHARED) {
    if (!isFile(join(SKILLS_ROOT, rel))) {
      errors.push(`atomic-install: required shared file missing: ${rel}`);
    }
  }
  for (const skill of FAMILY) {
    if (!isFile(join(SKILLS_ROOT, skill, "SKILL.md"))) {
      errors.push(`atomic-install: ${skill}/SKILL.md missing`);
    }
  }

  for (const doc of scanFiles()) {
    const base = dirname(doc);
    const text = readFileSync(doc, "utf-8");
    for (const match of text.matchAll(PATH_RE)) {
      const ref = match[1];
      if (ref.includes("<") || ref.endsWith("/")) continue;
      let target = resolve(base, ref);
      if (!existsSync(target) && ref.startsWith("../delivery-")) {
        // Cross-skill form documented for consumption from another skill's root
        // (e.g. the authoritative-path line in batch-clarification.md).
        target = resolve(SKILLS_ROOT, ref.replace(/^\.\.\//, ""));
      }
      if (!existsSync(target)) {
        errors.push(`broken reference in ${relative(SKILLS_ROOT, doc)}: \`${ref}\``);
      }
    }
  }

  const authorityText = readFileSync(AUTHORITY, "utf-8");
  const authoritative = new RegExp(VERSION_RE.source).exec(authorityText);
  if (!authoritative) {
    errors.push("family-contract.md declares no family_version");
  } else {
    const current = authoritative[1];
    for (const skill of FAMILY) {
      for (const path of walk(join(SKILLS_ROOT, skill))) {
        if (![".md", ".mjs", ".json"].includes(extname(path))) continue;
        const relPath = relative(SKILLS_ROOT, path);
        if (resolve(path) === resolve(AUTHORITY) || relPath.split(/[\\/]/).includes("tests")) {
          continue; // tests may pin historical versions with banners
        }
        const text = readFileSync(path, "utf-8");
        for (const versionMatch of text.matchAll(VERSION_RE)) {
          const version = versionMatch[1];
          if (version.split(".")[0] !== current.split(".")[0]) {
            errors.push(
              `family_version major drift in ${relPath}: ${version} vs authoritative ${current}`
            );
          }
        }
      }
    }
  }

  if (errors.length) {
    for (const error of errors) console.error(`ERROR: ${error}`);
    return 1;
  }
  console.log("PASS: family references, atomic-install set, and version majors are consistent");
  return 0;
}

process.exit(main());
