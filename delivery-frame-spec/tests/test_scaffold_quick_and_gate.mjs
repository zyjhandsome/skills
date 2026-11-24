import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { GATE_START } from "../scripts/gate_record.mjs";
import { hashChange } from "../scripts/hash_change_artifacts.mjs";
import { buildHandoff } from "../scripts/delivery_scaffold.mjs";

const SCAFFOLD = resolve(dirname(fileURLToPath(import.meta.url)), "..", "scripts", "delivery_scaffold.mjs");
const YAML = "schema: spec-driven\ncreated: 2026-11-24\n";
const root = mkdtempSync(join(tmpdir(), "scaffold-quick-"));
const a = join(root, "a");
const b = join(root, "b");
const c = join(root, "c");

/** @param {...string} args */
function scaffold(...args) {
  return spawnSync(process.execPath, [SCAFFOLD, ...args], { encoding: "utf8" });
}

/** @param {string} dir @param {...string} extra */
function quickPack(dir, ...extra) {
  return scaffold(
    "quick-pack",
    "--change-dir",
    dir,
    "--capability",
    "cap",
    "--goal",
    "导出笔记为纯文本",
    "--impact",
    "src/export.py",
    ...extra
  );
}

/** @param {string} path @param {string} text */
function write(path, text) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, text);
}

/** @param {string} path */
function read(path) {
  return readFileSync(path, "utf8");
}

/** @param {string} dir */
function fillPlaceholders(dir) {
  for (const name of ["proposal.md", "tasks.md", "specs/cap/spec.md"]) {
    const path = join(dir, name);
    if (!existsSync(path)) continue;
    write(path, read(path).replaceAll("<命令>", "npm test").replace(/<(?!\!)[^>\n]+>/g, "已填写"));
  }
}

/** @param {string} dir */
function tickAll(dir) {
  const path = join(dir, "tasks.md");
  write(path, read(path).replaceAll("- [ ]", "- [x]"));
}

/** @param {string} dir */
function writeVerification(dir) {
  write(
    join(dir, "verification.md"),
    "# 验证\n\n- 命令：npm test\n- 时间：" + new Date().toISOString() + "\n- 退出码/结果：pass\n"
  );
}

try {
  mkdirSync(a);
  write(join(a, ".openspec.yaml"), YAML);
  const packed = quickPack(a);
  assert.equal(packed.status, 0, packed.stderr);
  assert.equal(read(join(a, ".openspec.yaml")), YAML);
  assert.match(read(join(a, "specs", "cap", "spec.md")), /系统 MUST /);
  assert.ok(read(join(a, "proposal.md")).includes(GATE_START));
  assert.ok(read(join(a, "proposal.md")).includes("### New Capabilities"));

  assert.equal(quickPack(a).status, 2);

  assert.equal(quickPack(b, "--skip-specs").status, 2);
  mkdirSync(c);
  write(join(c, ".openspec.yaml"), YAML);
  assert.equal(quickPack(c, "--skip-specs").status, 0);
  assert.ok(!existsSync(join(c, "specs")));
  assert.equal((read(join(c, ".openspec.yaml")).match(/^skip_specs: true$/gm) ?? []).length, 1);

  fillPlaceholders(a);
  const before = hashChange(a).revision;
  const recorded = scaffold("record-gate", "--change-dir", a, "--gate", "impl", "--approved-by", "user");
  assert.equal(recorded.status, 0, recorded.stderr);
  assert.ok(recorded.stdout.includes(before));
  assert.equal(hashChange(a).revision, before);

  tickAll(a);
  writeVerification(a);
  const close = scaffold(
    "close-out",
    "--change-dir",
    a,
    "--review-status",
    "pass",
    "--reviewer",
    "r",
    "--evidence",
    "npm test: pass"
  );
  assert.equal(close.status, 0, close.stderr);
  const handoff = JSON.parse(read(join(a, "handoff.json")));
  assert.equal(handoff.source_revision.revision_algo, 2);
  assert.equal(handoff.stage_payload.implementation_gate.binds_to_revision, before);

  fillPlaceholders(c);
  tickAll(c);
  writeVerification(c);
  const blocked = scaffold("close-out", "--change-dir", c, "--review-status", "pass");
  assert.equal(blocked.status, 1);
  assert.match(blocked.stderr, /implementation gate missing or stale/);

  // Resume in a fresh process from an old-format proposal on a CRLF checkout.
  const old = join(root, "resume");
  const proposal = join(old, "proposal.md");
  write(proposal, "### 状态源与工件位置\r\n- 原实现批准见签核记录");
  write(join(old, "tasks.md"), read(join(a, "tasks.md")));
  writeVerification(old);
  const approved = hashChange(old).revision;
  const at = "2026-11-23T10:30:00+08:00";
  const restore = (rev) => scaffold("record-gate", "--change-dir", old, "--gate", "impl",
    "--approved-by", "review-owner", "--approved-at", at, "--expected-revision", rev,
    "--accepted-warnings", "W1", "--note", "仅限已批准范围");
  assert.equal(scaffold("record-gate", "--change-dir", old, "--init").status, 0);
  assert.equal(hashChange(old).revision, approved);
  const pending = read(proposal);
  assert.notEqual(restore("cd".repeat(32)).status, 0);
  assert.equal(read(proposal), pending);
  assert.equal(restore(approved).status, 0);
  assert.ok(read(proposal).includes("W1"));
  const resume = scaffold("close-out", "--change-dir", old, "--review-status", "pass", "--reviewer", "independent");
  assert.equal(resume.status, 0, resume.stderr);
  assert.deepEqual(JSON.parse(read(join(old, "handoff.json"))).stage_payload.implementation_gate, {
    approved_by: "review-owner", approved_at: at, binds_to_revision: approved,
  });

  const nested = join(root, "openspec", "repo", "openspec", "changes", "x");
  mkdirSync(nested, { recursive: true });
  write(join(nested, "proposal.md"), "## Why\nx\n");
  assert.equal(buildHandoff("delivery-frame-spec", nested, null).state_source.anchor, "openspec/changes/x");
  console.log("PASS: quick-pack accepts openspec dirs and record-gate keeps the revision");
} finally {
  rmSync(root, { recursive: true, force: true });
}
