#!/usr/bin/env node
// @ts-check
/**
 * Compute artifact_revision for an OpenSpec change directory. Algorithm v2:
 * 1. Hash `.openspec.yaml` (when present), `proposal.md`, `design.md`, `tasks.md`,
 *    and `specs/**\/*.md`. `verification.md`, `handoff.json`, and other files are excluded.
 * 2. Canonicalize each file (`canonicalBytes`): UTF-8, strip BOM, normalize newlines
 *    to `\n`; strip the proposal gate-record block; rewrite `tasks.md` checkbox marks to `[ ]`.
 * 3. Sort by posix relative path, then `update(path) · 0x00 · update(canonical) · 0x00`.
 * 4. Default CLI output is `sha256:<hex>`. `--json` prints
 *    `{ artifact_revision, revision_algo: 2, files }`. No args: usage, exit 2.
 *
 * Usage:
 *   node hash_change_artifacts.mjs path/to/openspec/changes/<id>
 *   node hash_change_artifacts.mjs path/to/openspec/changes/<id> --json
 *
 * Zero dependencies (Node >= 18).
 */

import { createHash } from "node:crypto";
import { readFileSync, readdirSync, realpathSync, statSync } from "node:fs";
import { resolve, join, relative, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import process from "node:process";
import { stripGateRecord } from "./gate_record.mjs";

export const REVISION_ALGO = 2;

/** Prefix is group 1; the mark inside the brackets is group 2. Matches OpenSpec 2.1.1 task lines. */
export const CHECKBOX_LINE = /^(\s*(?:[-*+]|\d{1,9}[.)])\s*)\[(?:\s*([^\]\s]?)\s*\](?![(\[])|\s+\])/;

const ROOT_FILES = [".openspec.yaml", "proposal.md", "design.md", "tasks.md"];

/**
 * @param {unknown} value
 * @returns {string | null}
 */
export function normalizeRevision(value) {
  if (typeof value !== "string") return null;
  const match = value.trim().match(/^(?:sha256:)?([0-9a-fA-F]{64})$/);
  if (!match) return null;
  return `sha256:${match[1].toLowerCase()}`;
}

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

/** @param {string} text */
function neutralizeCheckboxes(text) {
  return text
    .split("\n")
    .map((line) => {
      const match = line.match(CHECKBOX_LINE);
      if (!match) return line;
      return line.replace(CHECKBOX_LINE, `${match[1]}[ ]`);
    })
    .join("\n");
}

/**
 * @param {string} relPath
 * @param {Buffer} data
 * @returns {Buffer}
 */
export function canonicalBytes(relPath, data) {
  let text = data.toString("utf8");
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  text = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const rel = relPath.split(sep).join("/");
  if (rel === "proposal.md") text = stripGateRecord(text);
  if (rel === "tasks.md") text = neutralizeCheckboxes(text);
  return Buffer.from(text, "utf8");
}

/**
 * List authoritative artifact files sorted by relative posix path.
 * @param {string} changeDir
 * @returns {string[]}
 */
export function iterArtifactFiles(changeDir) {
  const root = resolve(changeDir);
  /** @type {string[]} */
  const files = [];
  for (const name of ROOT_FILES) {
    const path = join(root, name);
    if (isFile(path)) files.push(resolve(path));
  }
  for (const path of mdFilesUnder(join(root, "specs"))) files.push(resolve(path));
  return files.sort((a, b) => {
    const left = relPosix(root, a);
    const right = relPosix(root, b);
    return left < right ? -1 : left > right ? 1 : 0;
  });
}

/**
 * Hash the change directory's authoritative artifacts.
 * @param {string} changeDir
 * @returns {{ digest: string, revision: string, algo: 2, entries: Array<{path: string, sha256: string}> }}
 */
export function hashChange(changeDir) {
  const root = resolve(changeDir);
  /** @type {Array<{path: string, sha256: string}>} */
  const entries = [];
  const aggregate = createHash("sha256");
  for (const path of iterArtifactFiles(changeDir)) {
    const rel = relPosix(root, path);
    const canonical = canonicalBytes(rel, readFileSync(path));
    entries.push({ path: rel, sha256: createHash("sha256").update(canonical).digest("hex") });
    aggregate.update(Buffer.from(rel, "utf-8"));
    aggregate.update(Buffer.from([0]));
    aggregate.update(canonical);
    aggregate.update(Buffer.from([0]));
  }
  const digest = aggregate.digest("hex");
  return { digest, revision: `sha256:${digest}`, algo: REVISION_ALGO, entries };
}

function main() {
  const args = process.argv.slice(2);
  const wantJson = args.includes("--json");
  const positional = args.filter((arg) => arg !== "--json");
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
  const { revision, entries } = hashChange(changeDir);
  if (entries.length === 0) {
    console.error("ERROR: no authoritative artifacts found");
    return 1;
  }
  if (wantJson) {
    console.log(JSON.stringify({ artifact_revision: revision, revision_algo: REVISION_ALGO, files: entries }, null, 2));
  } else {
    console.log(revision);
  }
  return 0;
}

if (
  process.argv[1] &&
  pathToFileURL(realpathSync(resolve(process.argv[1]))).href.toLowerCase() ===
    pathToFileURL(realpathSync(fileURLToPath(import.meta.url))).href.toLowerCase()
) {
  process.exit(main());
}
