import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { hashChange, normalizeRevision } from "../scripts/hash_change_artifacts.mjs";
import {
  GATE_END,
  GATE_START,
  emptyGateBlock,
  formatGateLine,
  parseGateRecord,
  upsertGateLine,
} from "../scripts/gate_record.mjs";

const scratch = mkdtempSync(join(tmpdir(), "rev-stability-"));
const dir = join(scratch, "change");
mkdirSync(join(dir, "specs", "cap"), { recursive: true });

const yaml = "schema: spec-driven\ncreated: 2026-11-24\n";
const specText = "## ADDED Requirements\n\n### Requirement: 导出纯文本\n系统 MUST 导出纯文本。\n";
const tasksText = "- [ ] 任务 1\n- [ ] 任务 2\n  - [ ] 1.1\n";
const proposalText = `### 状态源与工件位置\n${emptyGateBlock()}`;

/** @param {string} name @param {string} text */
function write(name, text) {
  writeFileSync(join(dir, name), text);
}

/** @param {string} name */
function read(name) {
  return readFileSync(join(dir, name), "utf8");
}

/** @param {string} name @param {string} text */
function append(name, text) {
  write(name, read(name) + text);
}

function writeBaseFiles() {
  write(".openspec.yaml", yaml);
  write("proposal.md", proposalText);
  write("tasks.md", tasksText);
  write("specs/cap/spec.md", specText);
}

/** Each revision-changing edit starts from the bytes that produced `base`. */
function restoreBase() {
  writeBaseFiles();
  rmSync(join(dir, "design.md"), { force: true });
}

writeBaseFiles();

/** @param {string} revision */
function approved(revision) {
  return {
    status: "approved",
    approvedBy: "user",
    approvedAt: "2026-11-24T10:00:00+08:00",
    revision,
    acceptedWarnings: [],
    note: null,
  };
}

/** @param {string} from @param {string} to */
function tick(from, to) {
  const current = read("tasks.md");
  assert.ok(current.includes(from), `tasks.md missing ${from}`);
  write("tasks.md", current.replace(from, to));
}

function rewriteAllWithCRLF() {
  for (const name of [".openspec.yaml", "proposal.md", "tasks.md", "specs/cap/spec.md", "verification.md", "handoff.json"]) {
    let text;
    try {
      text = read(name);
    } catch {
      continue;
    }
    write(name, text.replace(/\r\n/g, "\n").replace(/\n/g, "\r\n"));
  }
}

function editSpecText() {
  write("specs/cap/spec.md", read("specs/cap/spec.md").replace("导出纯文本。", "导出纯文本并带标题。"));
}

function editTaskTitleText() {
  write("tasks.md", read("tasks.md").replace("- [ ] 任务 2", "- [ ] 任务 2 改标题"));
}

/** @param {string} line */
function injectIntoGateBlock(line) {
  write("proposal.md", read("proposal.md").replace(GATE_END, `${line}\n${GATE_END}`));
}

function removeGateEndMarker() {
  write("proposal.md", read("proposal.md").replaceAll(GATE_END, ""));
}

try {
  const base = hashChange(dir).revision;
  assert.match(base, /^sha256:[0-9a-f]{64}$/);

  tick("- [ ] 任务 1", "- [x] 任务 1");
  assert.equal(hashChange(dir).revision, base);
  tick("  - [ ] 1.1", "  - [~] 1.1");
  assert.equal(hashChange(dir).revision, base);
  write("verification.md", "# v\n");
  assert.equal(hashChange(dir).revision, base);
  write("handoff.json", "{}\n");
  assert.equal(hashChange(dir).revision, base);
  write("proposal.md", upsertGateLine(read("proposal.md"), "impl", approved(base)));
  assert.equal(hashChange(dir).revision, base);
  rewriteAllWithCRLF();
  assert.equal(hashChange(dir).revision, base);

  restoreBase();
  editSpecText();
  assert.notEqual(hashChange(dir).revision, base);
  restoreBase();
  editTaskTitleText();
  assert.notEqual(hashChange(dir).revision, base);
  restoreBase();
  write("design.md", "# d\n");
  assert.notEqual(hashChange(dir).revision, base);
  restoreBase();
  append(".openspec.yaml", "skip_specs: true\n");
  assert.notEqual(hashChange(dir).revision, base);

  restoreBase();
  injectIntoGateBlock("### Requirement: 偷偷加的需求");
  assert.throws(() => hashChange(dir), /gate-record/);
  removeGateEndMarker();
  assert.throws(() => hashChange(dir), /gate-record/);

  assert.equal(normalizeRevision("AB".repeat(32)), "sha256:" + "ab".repeat(32));
  assert.equal(normalizeRevision("sha256:" + "ab".repeat(32)), "sha256:" + "ab".repeat(32));
  assert.equal(normalizeRevision("sha256:aaa"), null);
  assert.equal(normalizeRevision(123), null);

  const line = formatGateLine("impl", approved(base));
  assert.deepEqual(parseGateRecord(`${GATE_START}\n${line}\n${GATE_END}\n`).impl.revision, base);
  console.log("PASS: revision v2 ignores ticks, approvals, and newlines");
} finally {
  rmSync(scratch, { recursive: true, force: true });
}
