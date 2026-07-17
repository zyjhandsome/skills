#!/usr/bin/env node
// @ts-check
/**
 * Compute artifact_revision for an OpenSpec change directory.
 *
 * Hashes authoritative planning/execution files (proposal, design, tasks, specs/**,
 * verification when present). Ignores _test_harness and dotfiles.
 *
 * Usage:
 *   node hash_change_artifacts.mjs path/to/openspec/changes/<id>
 *   node hash_change_artifacts.mjs path/to/openspec/changes/<id> --json
 *
 * Zero dependencies (Node >= 18).
 */

import { createHash } from "node:crypto";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { resolve, join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

const INCLUDE_NAMES = ["proposal.md", "design.md", "tasks.md", "verification.md"];

/** @param {string} p */
function isFile(p) {
  try {
    return statSync(p).isFile();
  } catch {
    return false;
  }
}

/**
 * Recursively collect *.md files under dir.
 * @param {string} dir
 * @returns {string[]}
 */
function mdFilesUnder(dir) {
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
    if (entry.isDirectory()) out.push(...mdFilesUnder(full));
    else if (entry.isFile() && entry.name.endsWith(".md")) out.push(full);
  }
  return out;
}

/** @param {string} root @param {string} p */
function relPosix(root, p) {
  return relative(root, p).split(sep).join("/");
}

/**
 * List authoritative artifact files sorted by relative posix path.
 * @param {string} changeDir
 * @returns {string[]}
 */
export function iterArtifactFiles(changeDir) {
  const root = resolve(changeDir);
  const files = new Set();
  for (const name of INCLUDE_NAMES) {
    const p = join(root, name);
    if (isFile(p)) files.add(resolve(p));
  }
  for (const p of mdFilesUnder(join(root, "specs"))) files.add(resolve(p));
  return [...files].sort((a, b) => {
    const ra = relPosix(root, a);
    const rb = relPosix(root, b);
    return ra < rb ? -1 : ra > rb ? 1 : 0;
  });
}

/**
 * Hash the change directory's authoritative artifacts.
 * Byte-for-byte compatible with the original Python implementation.
 * @param {string} changeDir
 * @returns {{ digest: string, entries: Array<{path: string, sha256: string}> }}
 */
export function hashChange(changeDir) {
  const root = resolve(changeDir);
  /** @type {Array<{path: string, sha256: string}>} */
  const entries = [];
  const h = createHash("sha256");
  for (const path of iterArtifactFiles(changeDir)) {
    const rel = relPosix(root, path);
    const data = readFileSync(path);
    entries.push({ path: rel, sha256: createHash("sha256").update(data).digest("hex") });
    h.update(Buffer.from(rel, "utf-8"));
    h.update(Buffer.from([0]));
    h.update(data);
    h.update(Buffer.from([0]));
  }
  return { digest: h.digest("hex"), entries };
}

function main() {
  const args = process.argv.slice(2);
  const wantJson = args.includes("--json");
  const positional = args.filter((a) => a !== "--json");
  if (positional.length !== 1) {
    console.error("usage: node hash_change_artifacts.mjs <change_dir> [--json]");
    return 2;
  }
  const changeDir = positional[0];
  let isDir = false;
  try {
    isDir = statSync(changeDir).isDirectory();
  } catch {
    isDir = false;
  }
  if (!isDir) {
    console.error(`ERROR: not a directory: ${changeDir}`);
    return 2;
  }
  const { digest, entries } = hashChange(changeDir);
  if (entries.length === 0) {
    console.error("ERROR: no authoritative artifacts found");
    return 1;
  }
  if (wantJson) {
    console.log(JSON.stringify({ artifact_revision: digest, files: entries }, null, 2));
  } else {
    console.log(digest);
  }
  return 0;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exit(main());
}
