#!/usr/bin/env node
// @ts-check
/**
 * P2-1/P2-2 rule-level single chain: one change_id through all four stages using the real
 * scaffold, hasher, and validators, plus the two coverage gaps from the R3 report:
 *
 *   A. Standard chain  explore -> frame -> plan -> execute(verified close-out)
 *      - previous_handoff_id links every hop;
 *      - invalidation cascade is demonstrable: after design.md lands, the frame-era
 *        approval (bound to the old artifact_revision) must be REJECTED by the validator.
 *   B. High execute vertical slice: with only task 1 of 2 checked, --claim-verified must
 *      FAIL (no partial-slice verified), while the same artifacts support an in-progress
 *      handoff; self-review close for the High slice must be rejected.
 *
 * This exercises the machinery end to end in a sandbox. It does not replace an R4 field
 * test on a real repository (wall-clock and human-gate costs are out of scope here).
 *
 * Zero dependencies (Node >= 18). Exit 0 = chain holds, 1 = regression.
 */

import { spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

import { buildHandoff, nowRfc3339 } from "../scripts/delivery_scaffold.mjs";
import { hashChange } from "../scripts/hash_change_artifacts.mjs";
import { validate } from "../scripts/validate_handoff.mjs";

const TESTS_DIR = dirname(fileURLToPath(import.meta.url));
const SCRIPTS_DIR = resolve(TESTS_DIR, "..", "scripts");
const VALIDATE_DELIVERY_CHANGE = resolve(
  TESTS_DIR,
  "..",
  "..",
  "delivery-execute-verify",
  "scripts",
  "validate_delivery_change.mjs"
);
/** @type {string[]} */
const FAILURES = [];

/** @param {string} name @param {boolean} ok @param {string} [detail] */
function check(name, ok, detail = "") {
  console.log(`[${ok ? "OK " : "FAIL"}] ${name}` + (detail && !ok ? ` — ${detail}` : ""));
  if (!ok) FAILURES.push(name);
}

/** @param {string} name @param {Record<string, any>} handoff */
function mustPass(name, handoff) {
  const errors = validate(handoff, "hard");
  check(name, errors.length === 0, errors.join("; "));
}

/** @param {string} name @param {Record<string, any>} handoff @param {string} needle */
function mustFail(name, handoff, needle) {
  const errors = validate(handoff, "hard");
  check(
    name,
    errors.some((e) => e.includes(needle)),
    `expected error containing '${needle}', got: ${JSON.stringify(errors)}`
  );
}

/** @param {string} changeDir */
function revisionOf(changeDir) {
  return `sha256:${hashChange(changeDir).digest}`;
}

/** @param {Record<string, any>} handoff @param {string} [approver] */
function approve(handoff, approver = "user") {
  Object.assign(handoff.gate_status, {
    status: "pass",
    summary: "闸门通过（单链测试）",
    approved_by: approver,
    approved_at: nowRfc3339(),
    binds_to_revision: handoff.source_revision.artifact_revision,
  });
  handoff.stop_condition = "";
}

/**
 * @param {{mark: string, n: number, title: string, dep: string, symbol: string}} t
 */
const taskBlock = (t) => `- [${t.mark}] 任务 ${t.n}：${t.title}
  - 对应需求/场景：export-notes / 基本行为
  - 前置依赖：${t.dep}
  - 目标文件/符号：src/export.py::${t.symbol}
  - 验证命令/动作：pytest tests/test_export.py::test_${t.symbol} -q
  - 预期结果：exit 0，测试通过
`;

/**
 * @param {string} changeDir
 * @param {{withDesign: boolean, tasks: Array<[string, number, string, string, string]>}} opts
 */
function writeChange(changeDir, { withDesign, tasks }) {
  mkdirSync(changeDir, { recursive: true });
  writeFileSync(
    join(changeDir, "proposal.md"),
    "## Why\n导出笔记为纯文本。\n\n## What Changes\n新增导出入口。\n\n" +
      "## Capabilities\n- export-notes\n\n## Impact\n- src/export.py\n",
    "utf-8"
  );
  const specDir = join(changeDir, "specs", "export-notes");
  mkdirSync(specDir, { recursive: true });
  writeFileSync(
    join(specDir, "spec.md"),
    "## ADDED Requirements\n\n### Requirement: 导出纯文本\n\n系统必须支持导出笔记为纯文本。\n\n" +
      "#### Scenario: 基本行为\n\n- **WHEN** 用户点击导出\n- **THEN** 生成 .txt 文件\n",
    "utf-8"
  );
  if (withDesign) {
    writeFileSync(join(changeDir, "design.md"), "# 技术设计\n\n单模块新增导出函数。\n", "utf-8");
  }
  const body = tasks
    .map(([mark, n, title, dep, symbol]) => taskBlock({ mark, n, title, dep, symbol }))
    .join("\n");
  writeFileSync(join(changeDir, "tasks.md"), `# 实施任务清单\n\n## 任务\n\n${body}\n`, "utf-8");
}

/** @param {string} changeDir */
function claimVerified(changeDir) {
  return spawnSync(process.execPath, [VALIDATE_DELIVERY_CHANGE, changeDir, "--claim-verified"], {
    encoding: "utf-8",
  });
}

function main() {
  const root = mkdtempSync(join(tmpdir(), "delivery-single-chain-"));
  try {
    const change = join(root, "openspec", "changes", "add-export-notes");

    // ---- Stage 1: explore ----------------------------------------------------
    const explore = buildHandoff("delivery-explore", null, null);
    Object.assign(explore.stage_payload, {
      direction_alignment: "selected",
      chosen_direction: "导出笔记为纯文本",
      risk_signal: "standard-likely",
      code_anchors: ["src/export.py"],
    });
    explore.next_skill = "delivery-frame-spec";
    explore.stop_condition = "";
    mustPass("explore: selected direction transitions to frame", explore);

    // ---- Stage 2: frame (Standard, no design yet) -----------------------------
    writeChange(change, { withDesign: false, tasks: [[" ", 1, "实现导出函数", "无", "export_txt"]] });
    const frame = buildHandoff("delivery-frame-spec", change, explore.handoff_id);
    const frameRevision = frame.source_revision.artifact_revision;
    check("frame: artifact_revision computed", frameRevision === revisionOf(change));
    approve(frame);
    frame.next_skill = "delivery-plan-tasks";
    Object.assign(frame.stage_payload, {
      route: "Standard",
      risk: "medium",
      confirmed_artifacts: ["proposal.md", "specs/export-notes/spec.md"],
    });
    mustPass("frame: approved Standard transition to plan", frame);
    check("chain: frame.previous == explore.handoff_id", frame.previous_handoff_id === explore.handoff_id);

    // ---- Stage 3: plan — design lands, revision moves, old approval must die --
    writeChange(change, {
      withDesign: true,
      tasks: [
        [" ", 1, "实现导出函数", "无", "export_txt"],
        [" ", 2, "接入导出菜单", "任务 1", "export_menu"],
      ],
    });
    const plan = buildHandoff("delivery-plan-tasks", change, frame.handoff_id);
    const newRevision = plan.source_revision.artifact_revision;
    check("cascade: design.md changed the artifact_revision", newRevision !== frameRevision);

    const stale = structuredClone(plan);
    Object.assign(stale.gate_status, {
      status: "pass",
      summary: "复用旧批准（应被拒绝）",
      approved_by: "user",
      approved_at: nowRfc3339(),
      binds_to_revision: frameRevision,
    });
    stale.next_skill = "delivery-execute-verify";
    stale.stop_condition = "";
    mustFail(
      "cascade: stale frame-era approval is rejected",
      stale,
      "gate approval must bind source_revision.artifact_revision"
    );

    approve(plan);
    plan.next_skill = "delivery-execute-verify";
    mustPass("plan: freshly re-bound implementation gate transitions", plan);

    // ---- Stage 4: execute — verified close-out via the real wizard ------------
    writeChange(change, {
      withDesign: true,
      tasks: [
        ["x", 1, "实现导出函数", "无", "export_txt"],
        ["x", 2, "接入导出菜单", "任务 1", "export_menu"],
      ],
    });
    writeFileSync(
      join(change, "verification.md"),
      "# 验证记录\n\n### 主验证证据\n- 命令：pytest tests/test_export.py -q\n" +
        `- 时间：${nowRfc3339()}\n- 结果：exit 0 / 2 passed / 通过\n`,
      "utf-8"
    );
    const close = spawnSync(
      process.execPath,
      [
        join(SCRIPTS_DIR, "delivery_scaffold.mjs"),
        "close-out",
        "--change-dir",
        change,
        "--review-status",
        "pass",
        "--reviewer",
        "subagent-review-1",
        "--evidence",
        "pytest tests/test_export.py -q: 2 passed",
        "--approved-by",
        "user",
        "--previous",
        plan.handoff_id,
      ],
      { encoding: "utf-8" }
    );
    check("execute: close-out wizard exits 0", close.status === 0, (close.stdout ?? "") + (close.stderr ?? ""));
    const persisted = JSON.parse(readFileSync(join(change, "handoff.json"), "utf-8"));
    mustPass("execute: persisted handoff.json validates", persisted);
    check(
      "execute: verified + archive deferred",
      persisted.stage_payload.overall_status === "verified" &&
        persisted.stage_payload.archive.status === "deferred_to_openspec"
    );
    check("chain: execute.previous == plan.handoff_id", persisted.previous_handoff_id === plan.handoff_id);
    check(
      "chain: one change_id across frame/plan/execute",
      [frame, plan, persisted].every((h) => h.state_source.anchor === frame.state_source.anchor)
    );

    // ---- B. High execute vertical slice ---------------------------------------
    const high = join(root, "openspec", "changes", "high-slice");
    writeChange(high, {
      withDesign: true,
      tasks: [
        ["x", 1, "垂直切片：核心路径", "无", "core_path"],
        [" ", 2, "垂直切片：次级路径", "任务 1", "secondary"],
      ],
    });
    writeFileSync(
      join(high, "verification.md"),
      "# 验证记录\n\n### 主验证证据\n- 命令：pytest tests/test_core.py -q\n" +
        `- 时间：${nowRfc3339()}\n- 结果：exit 0 / 通过\n`,
      "utf-8"
    );
    const partial = claimVerified(high);
    check(
      "high slice: partial tasks cannot --claim-verified",
      partial.status !== 0 && (partial.stderr ?? "").includes("incomplete tasks"),
      partial.stderr ?? ""
    );

    const inProgress = buildHandoff("delivery-execute-verify", high, null);
    inProgress.stage_payload.task_status = [
      { task: 1, status: "verified-slice" },
      { task: 2, status: "pending" },
    ];
    mustPass("high slice: in-progress handoff (slice done, chain open) validates", inProgress);

    const selfReview = buildHandoff("delivery-execute-verify", high, null);
    selfReview.stage_payload.overall_status = "verified";
    Object.assign(selfReview.stage_payload.code_review, { mode: "self_fresh_context", reviewer: null });
    selfReview.next_action = "openspec archive high-slice";
    selfReview.stop_condition = "";
    mustFail("high slice: self-review verified close is rejected", selfReview, "self_fresh_context");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }

  if (FAILURES.length) {
    console.error(`\nRESULT: ${FAILURES.length} failure(s): ${FAILURES.join(", ")}`);
    return 1;
  }
  console.log("\nRESULT: single-chain (Standard full chain + High slice) holds");
  return 0;
}

process.exit(main());
