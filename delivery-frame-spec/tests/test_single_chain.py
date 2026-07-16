#!/usr/bin/env python3
"""P2-1/P2-2 rule-level single chain: one change_id through all four stages using the real
scaffold, hasher, and validators, plus the two coverage gaps from the R3 report:

  A. Standard chain  explore -> frame -> plan -> execute(verified close-out)
     - previous_handoff_id links every hop;
     - invalidation cascade is demonstrable: after design.md lands, the frame-era
       approval (bound to the old artifact_revision) must be REJECTED by the validator.
  B. High execute vertical slice: with only task 1 of 2 checked, --claim-verified must
     FAIL (no partial-slice verified), while the same artifacts support an in-progress
     handoff; self-review close for the High slice must be rejected.

This exercises the machinery end to end in a sandbox. It does not replace an R4 field
test on a real repository (wall-clock and human-gate costs are out of scope here).

Standard library only. Exit 0 = chain holds, 1 = regression.
"""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from delivery_scaffold import build_handoff, now_rfc3339  # noqa: E402
from hash_change_artifacts import hash_change  # noqa: E402
from validate_handoff import validate  # noqa: E402

VALIDATE_DELIVERY_CHANGE = (
    TESTS_DIR.parent.parent / "delivery-execute-verify" / "scripts" / "validate_delivery_change.py"
)
FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"[{'OK ' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        FAILURES.append(name)


def must_pass(name: str, handoff: dict) -> None:
    errors = validate(handoff, profile="hard")
    check(name, not errors, "; ".join(errors))


def must_fail(name: str, handoff: dict, needle: str) -> None:
    errors = validate(handoff, profile="hard")
    check(name, any(needle in e for e in errors),
          f"expected error containing {needle!r}, got: {errors}")


def revision_of(change_dir: Path) -> str:
    digest, _ = hash_change(change_dir)
    return f"sha256:{digest}"


def approve(handoff: dict, approver: str = "user") -> None:
    handoff["gate_status"].update({
        "status": "pass",
        "summary": "闸门通过（单链测试）",
        "approved_by": approver,
        "approved_at": now_rfc3339(),
        "binds_to_revision": handoff["source_revision"]["artifact_revision"],
    })
    handoff["stop_condition"] = ""


TASK_BLOCK = """- [{mark}] 任务 {n}：{title}
  - 对应需求/场景：export-notes / 基本行为
  - 前置依赖：{dep}
  - 目标文件/符号：src/export.py::{symbol}
  - 验证命令/动作：pytest tests/test_export.py::test_{symbol} -q
  - 预期结果：exit 0，测试通过
"""


def write_change(change_dir: Path, *, with_design: bool, tasks: list[tuple[str, int, str, str, str]]) -> None:
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "proposal.md").write_text(
        "## Why\n导出笔记为纯文本。\n\n## What Changes\n新增导出入口。\n\n"
        "## Capabilities\n- export-notes\n\n## Impact\n- src/export.py\n",
        encoding="utf-8",
    )
    spec_dir = change_dir / "specs" / "export-notes"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "spec.md").write_text(
        "## ADDED Requirements\n\n### Requirement: 导出纯文本\n\n系统必须支持导出笔记为纯文本。\n\n"
        "#### Scenario: 基本行为\n\n- **WHEN** 用户点击导出\n- **THEN** 生成 .txt 文件\n",
        encoding="utf-8",
    )
    if with_design:
        (change_dir / "design.md").write_text("# 技术设计\n\n单模块新增导出函数。\n", encoding="utf-8")
    body = "\n".join(TASK_BLOCK.format(mark=m, n=n, title=t, dep=d, symbol=s) for m, n, t, d, s in tasks)
    (change_dir / "tasks.md").write_text(f"# 实施任务清单\n\n## 任务\n\n{body}\n", encoding="utf-8")


def claim_verified(change_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATE_DELIVERY_CHANGE), str(change_dir), "--claim-verified"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="delivery-single-chain-"))
    try:
        change = root / "openspec" / "changes" / "add-export-notes"

        # ---- Stage 1: explore ----------------------------------------------------
        explore = build_handoff("delivery-explore", None, None)
        explore["stage_payload"].update(
            {"direction_alignment": "selected", "chosen_direction": "导出笔记为纯文本",
             "risk_signal": "standard-likely", "code_anchors": ["src/export.py"]})
        explore["next_skill"] = "delivery-frame-spec"
        explore["stop_condition"] = ""
        must_pass("explore: selected direction transitions to frame", explore)

        # ---- Stage 2: frame (Standard, no design yet) -----------------------------
        write_change(change, with_design=False,
                     tasks=[(" ", 1, "实现导出函数", "无", "export_txt")])
        frame = build_handoff("delivery-frame-spec", change, explore["handoff_id"])
        frame_revision = frame["source_revision"]["artifact_revision"]
        check("frame: artifact_revision computed", frame_revision == revision_of(change))
        approve(frame)
        frame["next_skill"] = "delivery-plan-tasks"
        frame["stage_payload"].update({"route": "Standard", "risk": "medium",
                                       "confirmed_artifacts": ["proposal.md", "specs/export-notes/spec.md"]})
        must_pass("frame: approved Standard transition to plan", frame)
        check("chain: frame.previous == explore.handoff_id",
              frame["previous_handoff_id"] == explore["handoff_id"])

        # ---- Stage 3: plan — design lands, revision moves, old approval must die --
        write_change(change, with_design=True,
                     tasks=[(" ", 1, "实现导出函数", "无", "export_txt"),
                            (" ", 2, "接入导出菜单", "任务 1", "export_menu")])
        plan = build_handoff("delivery-plan-tasks", change, frame["handoff_id"])
        new_revision = plan["source_revision"]["artifact_revision"]
        check("cascade: design.md changed the artifact_revision", new_revision != frame_revision)

        stale = copy.deepcopy(plan)
        stale["gate_status"].update({"status": "pass", "summary": "复用旧批准（应被拒绝）",
                                     "approved_by": "user", "approved_at": now_rfc3339(),
                                     "binds_to_revision": frame_revision})
        stale["next_skill"] = "delivery-execute-verify"
        stale["stop_condition"] = ""
        must_fail("cascade: stale frame-era approval is rejected", stale,
                  "gate approval must bind source_revision.artifact_revision")

        approve(plan)
        plan["next_skill"] = "delivery-execute-verify"
        must_pass("plan: freshly re-bound implementation gate transitions", plan)

        # ---- Stage 4: execute — verified close-out via the real wizard ------------
        write_change(change, with_design=True,
                     tasks=[("x", 1, "实现导出函数", "无", "export_txt"),
                            ("x", 2, "接入导出菜单", "任务 1", "export_menu")])
        (change / "verification.md").write_text(
            "# 验证记录\n\n### 主验证证据\n- 命令：pytest tests/test_export.py -q\n"
            f"- 时间：{now_rfc3339()}\n- 结果：exit 0 / 2 passed / 通过\n",
            encoding="utf-8",
        )
        close = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "delivery_scaffold.py"), "close-out",
             "--change-dir", str(change), "--review-status", "pass",
             "--reviewer", "subagent-review-1", "--evidence", "pytest tests/test_export.py -q: 2 passed",
             "--approved-by", "user", "--previous", plan["handoff_id"]],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        check("execute: close-out wizard exits 0", close.returncode == 0,
              close.stdout + close.stderr)
        persisted = json.loads((change / "handoff.json").read_text(encoding="utf-8"))
        must_pass("execute: persisted handoff.json validates", persisted)
        check("execute: verified + archive deferred",
              persisted["stage_payload"]["overall_status"] == "verified"
              and persisted["stage_payload"]["archive"]["status"] == "deferred_to_openspec")
        check("chain: execute.previous == plan.handoff_id",
              persisted["previous_handoff_id"] == plan["handoff_id"])
        check("chain: one change_id across frame/plan/execute",
              all(h["state_source"]["anchor"] == frame["state_source"]["anchor"]
                  for h in (frame, plan, persisted)))

        # ---- B. High execute vertical slice ---------------------------------------
        high = root / "openspec" / "changes" / "high-slice"
        write_change(high, with_design=True,
                     tasks=[("x", 1, "垂直切片：核心路径", "无", "core_path"),
                            (" ", 2, "垂直切片：次级路径", "任务 1", "secondary")])
        (high / "verification.md").write_text(
            "# 验证记录\n\n### 主验证证据\n- 命令：pytest tests/test_core.py -q\n"
            f"- 时间：{now_rfc3339()}\n- 结果：exit 0 / 通过\n",
            encoding="utf-8",
        )
        partial = claim_verified(high)
        check("high slice: partial tasks cannot --claim-verified",
              partial.returncode != 0 and "incomplete tasks" in partial.stderr, partial.stderr)

        in_progress = build_handoff("delivery-execute-verify", high, None)
        in_progress["stage_payload"]["task_status"] = [
            {"task": 1, "status": "verified-slice"}, {"task": 2, "status": "pending"}]
        must_pass("high slice: in-progress handoff (slice done, chain open) validates", in_progress)

        self_review = build_handoff("delivery-execute-verify", high, None)
        self_review["stage_payload"]["overall_status"] = "verified"
        self_review["stage_payload"]["code_review"].update(
            {"mode": "self_fresh_context", "reviewer": None})
        self_review["next_action"] = "openspec archive high-slice"
        self_review["stop_condition"] = ""
        must_fail("high slice: self-review verified close is rejected", self_review,
                  "self_fresh_context")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if FAILURES:
        print(f"\nRESULT: {len(FAILURES)} failure(s): {', '.join(FAILURES)}", file=sys.stderr)
        return 1
    print("\nRESULT: single-chain (Standard full chain + High slice) holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
