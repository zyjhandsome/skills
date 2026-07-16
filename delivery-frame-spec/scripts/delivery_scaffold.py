#!/usr/bin/env python3
"""Delivery Family scaffold (R3 backlog P1-1/P1-2/P1-3): cut the hand-written JSON and
machine-anchor cost that dominated Quick-lane wall-clock time.

Subcommands
-----------
new-handoff   Generate a valid delivery-handoff/v1 skeleton for any stage. Nominal
              capability snapshot, timestamps, per-stage stage_payload skeleton, and
              artifact_revision computed from the change dir when given. The skeleton
              validates as a non-transition (pending/blocked) handoff out of the box;
              the agent only edits business fields and the gate before transition.

quick-pack    Scaffold a Quick/Debug-Low lightweight change: proposal.md (OpenSpec
              skeleton + Chinese lightweight contract with Explore-consume N/A),
              minimal delta spec (one Requirement + Scenario), and tasks.md whose task
              blocks carry the exact machine anchors validate_delivery_change.py reads.
              Never overwrites existing files.

close-out     Execute verified close-out wizard: runs validate_delivery_change
              --claim-verified, computes artifact_revision, generates the verified
              execute handoff, validates it (hard profile), writes <change>/handoff.json,
              and prints the deferred archive next step. It never runs archive/git.

All output artifacts remain drafts owned by the agent: gates, reviews, and approvals
still follow the family contracts. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from hash_change_artifacts import hash_change  # noqa: E402
from validate_handoff import validate  # noqa: E402

# Windows consoles often default to a legacy code page; the JSON we emit is Chinese-heavy.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

VALIDATE_DELIVERY_CHANGE = (
    SCRIPTS_DIR.parent.parent / "delivery-execute-verify" / "scripts" / "validate_delivery_change.py"
)

STAGES = ("delivery-explore", "delivery-frame-spec", "delivery-plan-tasks", "delivery-execute-verify")

STAGE_PAYLOAD_SKELETONS = {
    "delivery-explore": {
        "direction_alignment": "needs_choice",
        "chosen_direction": "",
        "non_goals": [],
        "code_anchors": [],
        "risk_signal": "none",
        "unknowns": [],
    },
    "delivery-frame-spec": {
        "route": "Standard",
        "risk": "medium",
        "confirmed_artifacts": [],
        "forbidden_scope": [],
        "open_questions": [],
    },
    "delivery-plan-tasks": {
        "plan_tasks": [],
        "plan_decisions": {
            "agent_decided": [],
            "user_decided": [],
            "returned_to_frame": [],
            "remaining_blockers": [],
        },
        "traceability": [],
        "readiness_result": {"blockers": [], "warnings": [], "suggestions": []},
        "validation_plan": [],
        "risk_gates": [],
        "parallel_ownership": [],
    },
    "delivery-execute-verify": {
        "overall_status": "in_progress",
        "task_status": [],
        "current_failures_or_blocks": [],
        "artifact_backflow": "none",
        "alignment_backflow": None,
        "fresh_verification_evidence": [],
        "spec_coherence": "pass",
        "code_review": {
            "status": "pass",
            "mode": "independent",
            "independent_review": "required_pass",
            "reviewer": None,
            "findings": [],
        },
        "archive": {"status": "deferred_to_openspec", "reason": "execute-verify must not sync/archive"},
        "asset_writeback": [],
    },
}

STAGE_PRESENTATION = {
    "delivery-explore": ("探索·方向对齐", "定框·路由与需求边界", "请使用 delivery-frame-spec"),
    "delivery-frame-spec": ("定框", "技术设计与任务拆解", "请使用 delivery-plan-tasks"),
    # Fixed wording (R3 4.3): plan completion != tasks checked; checking belongs to Execute.
    "delivery-plan-tasks": ("计划·就绪审查完成", "实施·按 tasks.md 执行（任务勾选属 Execute 阶段）",
                            "请使用 delivery-execute-verify"),
    "delivery-execute-verify": ("实施·验证", "OpenSpec 归档", "<已解析的 archive_change 操作>"),
}


def now_rfc3339() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head(cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, timeout=15
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None if result.returncode == 0 else None


def compute_revision(change_dir: Path | None) -> str | None:
    if change_dir is None:
        return None
    digest, entries = hash_change(change_dir)
    return f"sha256:{digest}" if entries else None


def change_anchor(change_dir: Path) -> str:
    parts = change_dir.resolve().parts
    if "openspec" in parts:
        return Path(*parts[parts.index("openspec"):]).as_posix()
    return change_dir.as_posix()


def build_handoff(stage: str, change_dir: Path | None, previous: str | None) -> dict:
    ts = now_rfc3339()
    change_id = change_dir.name if change_dir else "<change-id>"
    if stage == "delivery-explore":
        state_source = {"kind": "none", "label": "none（探索非正式）", "anchor": None}
        gate = {"status": "n/a", "summary": "探索非正式，无规格闸门"}
    else:
        state_source = {
            "kind": "openspec_change",
            "label": f"change #{change_id}",
            "anchor": change_anchor(change_dir) if change_dir else None,
        }
        gate = {"status": "pending", "summary": "<闸门未放行；放行时补 status/approved_*/binds_to_revision>"}

    from_task, to_task, continue_prompt = STAGE_PRESENTATION[stage]
    return {
        "schema_version": "delivery-handoff/v1",
        "family_version": "delivery-family/1.2",
        "type": "delivery-handoff",
        "handoff_id": f"{change_id}-{stage.removeprefix('delivery-')}-{ts.replace(':', '').replace('-', '')[:15]}",
        "previous_handoff_id": previous,
        "generated_at": ts,
        "stage": stage,
        "source_revision": {
            "repo_head": git_head(change_dir or Path.cwd()),
            "artifact_revision": compute_revision(change_dir),
            "state_observed_at": ts,
        },
        "state_source": state_source,
        "capability_snapshot": {"memory": "ok", "openspec": "initialized", "superpowers": "loaded"},
        "capability_bindings": {"openspec": {}, "memory": {}, "superpowers": {}, "subagents": {}},
        "presentation_capability": {"mode": "markdown", "source": "unknown"},
        "gate_status": {
            "status": gate["status"],
            "summary": gate["summary"],
            "evidence": [],
            "approved_by": None,
            "approved_at": None,
            "binds_to_revision": None,
            "accepted_warning_ids": [],
        },
        "evidence_mode": "full",
        "next_skill": None,
        "next_action": None,
        "required_inputs": [],
        "stop_condition": "<草稿：填写当前真实停止条件；允许转换时清空并设置 next_skill/next_action>",
        "stage_payload": json.loads(json.dumps(STAGE_PAYLOAD_SKELETONS[stage], ensure_ascii=False)),
        "presentation": {
            "schema": "delivery-presentation/v1",
            "from_task": from_task,
            "to_task": to_task,
            "summary": "<一句话结论>",
            "evidence": [],
            "continue_prompt": continue_prompt,
        },
    }


def emit(obj: dict, out: Path | None) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    if out:
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out}")
    else:
        print(text)


def cmd_new_handoff(args: argparse.Namespace) -> int:
    change_dir = args.change_dir.resolve() if args.change_dir else None
    if change_dir and not change_dir.is_dir():
        print(f"ERROR: change dir does not exist: {change_dir}", file=sys.stderr)
        return 2
    if args.stage != "delivery-explore" and change_dir is None:
        print("ERROR: --change-dir is required for every stage except delivery-explore", file=sys.stderr)
        return 2
    handoff = build_handoff(args.stage, change_dir, args.previous)
    errors = validate(handoff, profile="hard")
    if errors:
        for error in errors:
            print(f"ERROR (skeleton invalid — scaffold bug): {error}", file=sys.stderr)
        return 1
    emit(handoff, args.out)
    print("skeleton validates as a non-transition handoff; fill business fields, then re-validate "
          "before any transition.", file=sys.stderr)
    return 0


QUICK_PROPOSAL = """## Why

{goal}

## What Changes

<一句话：可观察行为变化>

## Capabilities

- {capability}

## Impact

- {impact}

---

# 轻量契约（Quick / Debug-Low）

目标：{goal}
非目标：<不做什么>
影响文件/符号：{impact}
可观察行为：<用户/系统可见的变化>
最小验证：<命令与预期>
禁止范围：<不得触碰的路径/行为>
风险/未知项：<一句话>
澄清完整性扫描：已检查适用维度；无实质阻塞项（有则列出）

### Explore 交接消费
N/A — 无 explore handoff

### 状态源与工件位置
- 后端：OpenSpec change
- 路径：{anchor}
- 闸门记录：实施批准：待批准

> Quick 车道无 `design.md` 属预期：`openspec status` 显示 design 未完成不代表变更不完整，
> 向用户解释时引用本行即可；不要为凑 status 写假 design。
"""

QUICK_SPEC = """## ADDED Requirements

### Requirement: {requirement}

系统必须 {goal}。

#### Scenario: 基本行为

- **WHEN** <执行动作>
- **THEN** <可观察结果>
"""

QUICK_TASKS = """# {change_id}：实施任务清单

## 执行规则
- 权威状态源：{anchor}
- 风险/闸门：Quick / low；实施前须用户明确批准轻量契约
- 禁止范围：<同契约>
- 必须执行的最终验证：<命令>

## 任务

- [ ] 任务 1：{goal}
  - 对应需求/场景：{requirement} / 基本行为
  - 前置依赖：无
  - 目标文件/符号：{impact}
  - 允许修改：{impact}
  - 禁止修改：<路径>
  - 实施步骤：<1-2 步>
  - 失败测试或已批准替代验证：<测试文件/断言>
  - 验证命令/动作：<命令>
  - 预期结果：<如 exit 0，N passed>
  - 迁移/回滚：不适用（可逆小改动）
  - 完成定义：验证命令通过且行为可观察
  - 负责人/冲突说明：单人无冲突

## 集成顺序

单任务，无集成顺序。

## 最终验证
| 命令/动作 | 覆盖范围 | 预期结果 |
|---|---|---|
| <命令> | 本任务行为 + 相邻回归 | exit 0 |
"""


def cmd_quick_pack(args: argparse.Namespace) -> int:
    change_dir = args.change_dir.resolve()
    if change_dir.exists() and any(change_dir.iterdir()):
        existing = [p.name for p in change_dir.iterdir()]
        print(f"ERROR: change dir not empty ({', '.join(existing[:5])}…) — quick-pack never overwrites",
              file=sys.stderr)
        return 2
    change_dir.mkdir(parents=True, exist_ok=True)
    anchor = change_anchor(change_dir)
    fields = {
        "goal": args.goal,
        "capability": args.capability,
        "impact": args.impact,
        "anchor": anchor,
        "change_id": change_dir.name,
        "requirement": args.requirement or args.goal,
    }

    (change_dir / "proposal.md").write_text(QUICK_PROPOSAL.format(**fields), encoding="utf-8")
    spec_dir = change_dir / "specs" / args.capability
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "spec.md").write_text(QUICK_SPEC.format(**fields), encoding="utf-8")
    (change_dir / "tasks.md").write_text(QUICK_TASKS.format(**fields), encoding="utf-8")

    digest, _ = hash_change(change_dir)
    print(f"scaffolded Quick change at {change_dir}")
    print(f"artifact_revision (pre-edit): sha256:{digest}")
    print("next: fill the <placeholders>, run `openspec validate`, present the contract, and record "
          "the user go bound to the post-edit artifact_revision (re-run hash_change_artifacts.py).")
    return 0


def cmd_close_out(args: argparse.Namespace) -> int:
    change_dir = args.change_dir.resolve()
    if not change_dir.is_dir():
        print(f"ERROR: change dir does not exist: {change_dir}", file=sys.stderr)
        return 2

    # 1. Machine checks on tasks/verification (the R3 rework hotspot).
    claim = subprocess.run(
        [sys.executable, str(VALIDATE_DELIVERY_CHANGE), str(change_dir), "--claim-verified"],
        capture_output=True, text=True,
    )
    sys.stderr.write(claim.stderr)
    print(claim.stdout.strip())
    if claim.returncode != 0:
        print("close-out blocked: fix tasks/verification anchors above, then re-run.", file=sys.stderr)
        return 1

    # 2. Verified execute handoff draft.
    handoff = build_handoff("delivery-execute-verify", change_dir, args.previous)
    revision = handoff["source_revision"]["artifact_revision"]
    payload = handoff["stage_payload"]
    payload["overall_status"] = "verified"
    payload["fresh_verification_evidence"] = args.evidence or []
    payload["spec_coherence"] = args.spec_coherence
    payload["code_review"].update({
        "status": args.review_status,
        "reviewer": args.reviewer,
    })
    handoff["gate_status"].update({
        "status": "pass",
        "summary": f"新鲜验证 + 独立审查（{args.reviewer or 'independent reviewer'}）通过；归档移交 OpenSpec",
        "evidence": list(args.evidence or []),
        "approved_by": args.approved_by,
        "approved_at": now_rfc3339() if args.approved_by else None,
        "binds_to_revision": revision if args.approved_by else None,
    })
    next_action = args.next_action or f"openspec archive {change_dir.name}"
    handoff["next_action"] = next_action
    handoff["stop_condition"] = ""
    handoff["presentation"]["summary"] = "verified；归档移交 OpenSpec（本技能不执行 archive）"
    handoff["presentation"]["continue_prompt"] = next_action

    errors = validate(handoff, profile="hard")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("close-out blocked: handoff draft invalid — usually missing --review-status/--evidence "
              "or an approval field combination.", file=sys.stderr)
        return 1

    out = args.out or (change_dir / "handoff.json")
    emit(handoff, out)
    print("\nverified close-out ready:")
    print(f"  1. archive is DEFERRED — run the resolved archive operation yourself: {next_action}")
    print("  2. commit / push / PR remain user-gated; ask before any git mutation.")
    print("  3. confirm the resolved archive binding in capability_bindings.openspec before running it.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new-handoff", help="generate a delivery-handoff/v1 skeleton")
    p_new.add_argument("stage", choices=STAGES)
    p_new.add_argument("--change-dir", type=Path, help="OpenSpec change dir (required except explore)")
    p_new.add_argument("--previous", help="previous_handoff_id for chain tracing")
    p_new.add_argument("--out", type=Path, help="write to file instead of stdout")
    p_new.set_defaults(func=cmd_new_handoff)

    p_quick = sub.add_parser("quick-pack", help="scaffold a Quick/Debug-Low lightweight change")
    p_quick.add_argument("--change-dir", type=Path, required=True, help="openspec/changes/<id> to create")
    p_quick.add_argument("--capability", required=True, help="kebab-case capability name for the delta spec")
    p_quick.add_argument("--goal", required=True, help="one-sentence goal (fills contract and spec)")
    p_quick.add_argument("--impact", required=True, help="affected file/symbol, e.g. src/ui/tray.py::tooltip")
    p_quick.add_argument("--requirement", help="requirement name; defaults to goal")
    p_quick.set_defaults(func=cmd_quick_pack)

    p_close = sub.add_parser("close-out", help="verified close-out wizard for execute")
    p_close.add_argument("--change-dir", type=Path, required=True)
    p_close.add_argument("--review-status", choices=("pass", "warn"), required=True,
                         help="independent review outcome (must have actually happened)")
    p_close.add_argument("--reviewer", help="independent reviewer id (subagent id or human)")
    p_close.add_argument("--evidence", action="append",
                         help="fresh verification evidence line, repeatable, e.g. 'pytest -q: 24 passed'")
    p_close.add_argument("--spec-coherence", choices=("pass", "warn"), default="pass")
    p_close.add_argument("--approved-by", help="implementation-go approver to bind to the current revision")
    p_close.add_argument("--previous", help="previous_handoff_id")
    p_close.add_argument("--next-action", help="resolved archive operation; default 'openspec archive <id>'")
    p_close.add_argument("--out", type=Path, help="handoff output path; default <change-dir>/handoff.json")
    p_close.set_defaults(func=cmd_close_out)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
