#!/usr/bin/env python3
"""Generate an A→B migration-demand-diff dependency packet (analysis only).

Compares direct dependencies declared (or closure-listed) on source A against
the lock/manifest of implementation host B. Does not install or edit either repo.

Exit codes:
  0 written and queue clear (or all decided via --decision-file)
  2 usage
  3 validation/logic error
  4 path missing
  5 blocked (missing package.json)
  7 written but Human Confirmation Queue still has ready/pending rows
     (Agent must ask now; 「继续/全部放行」never clears the queue)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from upgrade_lockfiles import parse_lock  # noqa: E402


ANALYSIS_MODE = "migration-demand-diff"
DISPOSITIONS = (
    "reuse-B",
    "reuse-B-major-review",
    "add-to-B",
    "replace-as-B-stack",
    "copy-local",
    "unknown",
)
ASKABLE_DISPOSITIONS = {
    "reuse-B-major-review",
    "add-to-B",
    "replace-as-B-stack",
    "copy-local",
    "unknown",
}
REUSE_DISPOSITIONS = {"reuse-B", "reuse-B-major-review"}
UI_REPLACE_PACKAGES = {"element-ui", "ant-design-vue", "vant", "naive-ui", "quasar"}
SCHEMA = "migration-demand-diff-report/v1"
PRODUCER = "frontend-dependency-upgrade-impact-analysis"
BLANKET_REJECT = ("继续", "全部放行", "别再问了", "全部纳入")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_deps(package_json: Path) -> dict[str, tuple[str, str]]:
    """Package name to (spec, manifest field). The first field wins."""
    data = load_json(package_json)
    out: dict[str, tuple[str, str]] = {}
    for field in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        block = data.get(field) or {}
        if isinstance(block, dict):
            for name, spec in block.items():
                out.setdefault(str(name), (str(spec), field))
    return out


def major_of(versionish: str) -> int | None:
    text = versionish.strip().lstrip("v^~>=< ")
    match = re.match(r"(\d+)", text)
    return int(match.group(1)) if match else None


def majors_differ(a_spec: str, b_ver: str) -> bool:
    a_maj = major_of(a_spec)
    b_maj = major_of(b_ver)
    return a_maj is not None and b_maj is not None and a_maj != b_maj


def classify(
    name: str,
    a_spec: str,
    b_manifest: dict[str, str],
    b_lock: dict[str, str],
    stack_map: dict[str, str],
) -> dict[str, str]:
    if name in stack_map:
        return {
            "package": name,
            "a_spec": a_spec,
            "b_status": f"stack-map→{stack_map[name]}",
            "disposition": "replace-as-B-stack",
            "note": f"A 的包映射到宿主技术栈包 {stack_map[name]}",
            "queue": "yes",
        }
    if name in b_manifest:
        b_ver = b_lock.get(name) or b_manifest.get(name) or "?"
        if name == "vue":
            return {
                "package": name,
                "a_spec": a_spec,
                "b_status": f"present@{b_ver}",
                "disposition": "reuse-B",
                "note": "始终使用宿主的 Vue 3 运行时，不要把 Vue 2 或 @vue/compat 加到 B",
                "queue": "no",
            }
        if majors_differ(a_spec, b_ver):
            return {
                "package": name,
                "a_spec": a_spec,
                "b_status": f"present@{b_ver}",
                "disposition": "reuse-B-major-review",
                "note": f"宿主已有该包，但主版本不同（{a_spec} vs {b_ver}），需确认 API 是否可复用",
                "queue": "yes",
            }
        return {
            "package": name,
            "a_spec": a_spec,
            "b_status": f"present@{b_ver}",
            "disposition": "reuse-B",
            "note": "宿主直接依赖已有兼容主版本，直接复用",
            "queue": "no",
        }
    host_ui = None
    for cand in ("element-plus", "vant", "naive-ui", "ant-design-vue", "quasar"):
        if cand in b_manifest:
            host_ui = cand
            break
    host_store = None
    for cand in ("pinia", "vuex"):
        if cand in b_manifest:
            host_store = cand
            break
    replacements = {
        "element-ui": host_ui or "element-plus (confirm host UI; pass --stack-map)",
        "vue-router": "vue-router (host major)",
        "vuex": host_store or "pinia-or-vuex4 (host)",
        "vue-template-compiler": "(drop; host bundler)",
        "@vue/cli-service": "(drop; host Vite)",
    }
    if name in replacements:
        target = replacements[name]
        note = f"按宿主技术栈替换为 {target}"
        if name == "element-ui" and host_ui is None:
            note += "；宿主 UI 不是 Element 时必须传 --stack-map"
        if name == "element-ui":
            note += "；视觉策略 needs_choice（替换 UI 还是对齐 A）"
        return {
            "package": name,
            "a_spec": a_spec,
            "b_status": "absent",
            "disposition": "replace-as-B-stack",
            "note": note,
            "queue": "yes",
        }
    if name == "vue":
        return {
            "package": name,
            "a_spec": a_spec,
            "b_status": "absent",
            "disposition": "add-to-B",
            "note": "宿主没有 vue；若要补齐，只能加入宿主的 Vue 3，不能加入 Vue 2 或 @vue/compat",
            "queue": "yes",
        }
    return {
        "package": name,
        "a_spec": a_spec,
        "b_status": "absent",
        "disposition": "add-to-B",
        "note": "宿主未直接声明该包，加入前需确认",
        "queue": "yes",
    }


def filter_demand(
    a_deps: dict[str, tuple[str, str]], closure_file: Path | None
) -> dict[str, tuple[str, str]]:
    if closure_file is None:
        return a_deps
    names = [
        line.strip()
        for line in closure_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    # Keep every requested name. A name missing from A's manifest is still demand
    # (phantom or local); dropping it hid the gap.
    return {name: a_deps.get(name, ("*", "closure")) for name in sorted(set(names))}


def load_decisions(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    data = load_json(path)
    if isinstance(data, list):
        out: dict[str, str] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            pkg = str(item.get("package") or item.get("unit") or "").removeprefix("demand:")
            answer = str(item.get("answer") or item.get("人工答复") or "").strip()
            if pkg and answer:
                out[pkg] = answer
        return out
    if isinstance(data, dict):
        decisions = data.get("decisions") if isinstance(data.get("decisions"), dict) else data
        return {str(k).removeprefix("demand:"): str(v) for k, v in decisions.items()}
    return {}


def accepted_demand_disposition(answer: str, package: str) -> str | None:
    prefix = f"proceed:demand:{package}:"
    if not answer.startswith(prefix):
        return None
    disposition = answer[len(prefix):]
    return disposition if disposition in DISPOSITIONS else None


def apply_decisions(rows: list[dict[str, str]], decisions: dict[str, str]) -> list[dict[str, str]]:
    updated: list[dict[str, str]] = []
    for row in rows:
        pkg = row["package"]
        answer = decisions.get(pkg, "")
        status = "ready" if row.get("queue") == "yes" else "decided"
        if answer:
            disposition = accepted_demand_disposition(answer, pkg)
            current = row["disposition"]
            stale_reuse = disposition in REUSE_DISPOSITIONS and disposition != current
            stale_add = disposition == "add-to-B" and current in REUSE_DISPOSITIONS
            if stale_reuse or stale_add:
                status = "ready"
                row = {
                    **row, "queue": "yes", "decision_note": answer,
                    "note": f"{row['note']}。原决定 {disposition} 与当前结果 {current} 不符，请重新确认。",
                }
            elif disposition:
                status = "decided"
                row = {**row, "disposition": disposition, "decision_note": answer}
            elif answer == "defer":
                status = "deferred"
                row = {**row, "decision_note": answer}
            elif answer == "other" or any(tok in answer for tok in BLANKET_REJECT):
                status = "ready"
                row = {**row, "decision_note": "unrecognized or blanket answer; ask proceed:demand token"}
            else:
                status = "ready"
                row = {**row, "decision_note": f"unrecognized answer {answer!r}"}
        updated.append({**row, "queue_status": status})
    return updated


def askable_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        r
        for r in rows
        if r.get("queue") == "yes" and r.get("queue_status", "ready") in {"ready", "pending"}
    ]


def batch_outcome(rows: list[dict[str, str]], lockfile_status: str) -> tuple[list[dict[str, str]], str, str, str]:
    queue_rows = askable_rows(rows)
    deferred = any(row.get("queue_status") == "deferred" for row in rows)
    decision = "needs_choice" if queue_rows else "not_needed"
    analysis = "partial" if queue_rows else "complete"
    gate = "frozen" if queue_rows or deferred or lockfile_status != "present" else "ready"
    return queue_rows, decision, analysis, gate


def visual_handoff(rows: list[dict[str, str]]) -> dict[str, Any]:
    ui_rows = [
        r
        for r in rows
        if r["disposition"] == "replace-as-B-stack"
        and (r["package"] in UI_REPLACE_PACKAGES or "element-ui" in r["package"])
    ]
    if not ui_rows:
        return {
            "visual_strategy_hint": "not_needed",
            "ui_replace_packages": [],
            "note": "No UI-kit replace-as-B-stack rows",
        }
    return {
        "visual_strategy_hint": "needs_choice",
        "ui_replace_packages": [r["package"] for r in ui_rows],
        "note": "UI replace vs 样式对齐 A — visual skill must keep strategy_status=needs_choice until human decides",
    }


def render_report(
    *,
    source_root: Path,
    host_root: Path,
    rows: list[dict[str, str]],
    output_dir: Path,
    batch_scope: str,
    lockfile_status: str,
    source_lockfile_status: str,
    queue_rows: list[dict[str, str]],
    handoff: dict[str, Any],
) -> str:
    today = date.today().isoformat()
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["disposition"]] = counts.get(row["disposition"], 0) + 1
    table = "\n".join(
        f"| `{r['package']}` | `{r['a_spec']}` | {r['b_status']} | `{r['disposition']}` | {r['note']} |"
        for r in rows
    )
    queue = "\n".join(
        f"| `demand:{r['package']}` | demand | {r.get('queue_status', 'ready')} | "
        f"是否按 `{r['disposition']}` 处理？ | "
        f"`proceed:demand:{r['package']}:{r['disposition']}` / `defer` / `other` |"
        for r in queue_rows
    ) or "| _(none)_ | demand | decided | 无待确认缺口 | n/a |"
    queue_rows, decision, analysis, gate = batch_outcome(rows, lockfile_status)
    summary_path = output_dir / "dependency-summary.json"
    return f"""# 迁入依赖差分（migration-demand-diff）

## 状态

| 字段 | 取值 |
|---|---|
| schema | {SCHEMA} |
| producer | {PRODUCER} |
| analysis_mode | {ANALYSIS_MODE} |
| analysis_status | {analysis} |
| decision_status | {decision} |
| batch_implementation_gate | {gate} |
| behavior_parity_required | yes |
| importer_resolution | confirmed |
| source_root | {source_root} |
| implementation_target | {host_root} |
| forbid_source_mutation | yes |
| batch_scope | {batch_scope} |
| lockfile_status | {lockfile_status} |
| source_lockfile_status | {source_lockfile_status} |
| host_lockfile_status | {lockfile_status} |
| report_path | {output_dir} |
| summary_path | {summary_path} |
| evidence_as_of | {today} |
| visual_strategy_hint | {handoff["visual_strategy_hint"]} |

## Upgrade Summary

- analysis mode: `{ANALYSIS_MODE}`
- source A: `{source_root}` (lock=`{source_lockfile_status}`; informational only)
- host B: `{host_root}` (lock=`{lockfile_status}`; **gate uses B**)
- demand packages: {len(rows)}
- disposition counts: {", ".join(f"{k}={v}" for k, v in counts.items() if v)}
- batch_implementation_gate: `{gate}`
- visual handoff: `{handoff["visual_strategy_hint"]}` — {handoff["note"]}
- never install Vue2 / `@vue/compat` on B as primary path
- 「继续 / 全部放行 / 别再问了 / 全部纳入」≠ proceed；须逐行 `proceed:demand:…`

## Demand Diff

| 包名 | A 声明 | B 状态 | disposition | 说明 |
|---|---|---|---|---|
{table}

Disposition 语义：`reuse-B` / `reuse-B-major-review` / `add-to-B` / `replace-as-B-stack` / `copy-local` / `unknown`。

## Human Confirmation Queue

| 单元 | 类型 | 状态 | 问题 | 选项 |
|---|---|---|---|---|
{queue}

## Conclusion

- 只分析不改 A/B。
- 实施阶段仅允许改 B；`add-to-B` / `replace-as-B-stack` / `reuse-B-major-review` 须人工 proceed。
- 与 Vue host-port / 视觉跨仓基线交叉核对时，以本报告 `dependency-summary.json` 路径交接（含 `visual_strategy_hint`）。
"""


def write_summary(
    output_dir: Path,
    *,
    source_root: Path,
    host_root: Path,
    rows: list[dict[str, str]],
    analysis: str,
    decision: str,
    gate: str,
    handoff: dict[str, Any],
    source_lockfile_status: str,
    host_lockfile_status: str,
) -> Path:
    path = output_dir / "dependency-summary.json"
    payload = {
        "schema": "migration-demand-diff-summary/v1",
        "producer": PRODUCER,
        "analysis_mode": ANALYSIS_MODE,
        "analysis_status": analysis,
        "decision_status": decision,
        "batch_implementation_gate": gate,
        "source_root": str(source_root),
        "implementation_target": str(host_root),
        "forbid_source_mutation": "yes",
        "source_lockfile_status": source_lockfile_status,
        "host_lockfile_status": host_lockfile_status,
        "demand_count": len(rows),
        "dispositions": {
            d: [r["package"] for r in rows if r["disposition"] == d] for d in DISPOSITIONS
        },
        "visual_strategy_hint": handoff["visual_strategy_hint"],
        "ui_replace_packages": handoff.get("ui_replace_packages", []),
        "report_path": str(output_dir / "migration-demand-diff-report.md"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root", required=True, help="Vue2 source A (read-only)")
    p.add_argument(
        "--implementation-target",
        required=True,
        help="Vue3 host B (analysis root / implement-on)",
    )
    p.add_argument("--output-dir", required=True, help="Writable report directory")
    p.add_argument(
        "--closure-packages",
        help="Optional text file: one package name per line to limit demand set",
    )
    p.add_argument(
        "--stack-map",
        help="Optional JSON map {aPackage: bPackage} for replace-as-B-stack",
    )
    p.add_argument(
        "--decision-file",
        help="JSON map/list of package → proceed:demand:<pkg>:<disposition>|defer|other",
    )
    p.add_argument("--batch-scope", default=None, help="Defaults to page-closure when a closure file is passed, otherwise full-manifest.")
    p.add_argument("--source-package-json", help="Override A package.json path")
    p.add_argument("--host-package-json", help="Override B package.json path")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    source_root = Path(args.source_root).resolve()
    host_root = Path(args.implementation_target).resolve()
    output_dir = Path(args.output_dir).resolve()
    if not source_root.is_dir():
        print(f"ERROR: source-root missing: {source_root}", file=sys.stderr)
        return 4
    if not host_root.is_dir():
        print(f"ERROR: implementation-target missing: {host_root}", file=sys.stderr)
        return 4
    a_pkg = Path(args.source_package_json) if args.source_package_json else source_root / "package.json"
    b_pkg = Path(args.host_package_json) if args.host_package_json else host_root / "package.json"
    if not a_pkg.is_file() or not b_pkg.is_file():
        print("ERROR: package.json missing on A or B", file=sys.stderr)
        return 5
    a_records = read_deps(a_pkg)
    closure = Path(args.closure_packages) if args.closure_packages else None
    demand = filter_demand(a_records, closure)
    b_manifest = {name: spec for name, (spec, _field) in read_deps(b_pkg).items()}
    host_lock_candidates = [
        host_root / "pnpm-lock.yaml",
        host_root / "package-lock.json",
        host_root / "yarn.lock",
    ]
    source_lock_candidates = [
        source_root / "pnpm-lock.yaml",
        source_root / "package-lock.json",
        source_root / "yarn.lock",
    ]
    lock_path = next((p for p in host_lock_candidates if p.is_file()), None)
    source_lock = next((p for p in source_lock_candidates if p.is_file()), None)
    lockfile_status = "present" if lock_path else "absent"
    source_lockfile_status = "present" if source_lock else "absent"
    declared_demand = [name for name in demand if name in b_manifest]
    b_lock = parse_lock(lock_path, declared_demand, manifest_specs=b_manifest).direct_versions
    stack_map = load_json(Path(args.stack_map)) if args.stack_map else {}
    if not isinstance(stack_map, dict):
        print("ERROR: stack-map must be a JSON object", file=sys.stderr)
        return 3
    rows = []
    for name, (spec, field) in sorted(demand.items()):
        row = classify(name, spec, b_manifest, b_lock, {str(k): str(v) for k, v in stack_map.items()})
        row["a_field"] = field
        rows.append(row)
    decisions = load_decisions(Path(args.decision_file) if args.decision_file else None)
    rows = apply_decisions(rows, decisions)
    queue_rows, decision, analysis, gate = batch_outcome(rows, lockfile_status)
    handoff = visual_handoff(rows)
    batch_scope = args.batch_scope or ("page-closure" if closure else "full-manifest")
    output_dir.mkdir(parents=True, exist_ok=True)
    md = render_report(
        source_root=source_root,
        host_root=host_root,
        rows=rows,
        output_dir=output_dir,
        batch_scope=batch_scope,
        lockfile_status=lockfile_status,
        source_lockfile_status=source_lockfile_status,
        queue_rows=queue_rows,
        handoff=handoff,
    )
    (output_dir / "migration-demand-diff-report.md").write_text(md, encoding="utf-8")
    write_summary(
        output_dir,
        source_root=source_root,
        host_root=host_root,
        rows=rows,
        analysis=analysis,
        decision=decision,
        gate=gate,
        handoff=handoff,
        source_lockfile_status=source_lockfile_status,
        host_lockfile_status=lockfile_status,
    )
    (output_dir / "demand-diff.json").write_text(
        json.dumps({"packages": rows, "visual_handoff": handoff}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"WROTE: {output_dir / 'migration-demand-diff-report.md'}")
    print(f"WROTE: {output_dir / 'dependency-summary.json'}")
    if queue_rows:
        print(
            f"NEEDS_CHOICE: {len(queue_rows)} demand row(s); ask proceed tokens now "
            f"(exit 7). Reject blanket NL: {', '.join(BLANKET_REJECT)}",
            file=sys.stderr,
        )
        return 7
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
