#!/usr/bin/env python3
"""Run explicitly approved project commands under an installed Node and verify restoration."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


VERSION_RE = re.compile(r"(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)")
PIN_FILES = (".nvmrc", ".node-version", ".tool-versions")
CI_FILES = (".gitlab-ci.yml", "azure-pipelines.yml", "azure-pipelines.yaml")
INSTALL_RE = re.compile(
    r"(?:^|&&|\|\||;)\s*(?:"
    r"npm\s+(?:ci|i|install|add|update|uninstall|remove|rm|un)\b|"
    r"pnpm\s+(?:i|install|add|up|update|remove|rm|dlx)\b|"
    r"yarn\s*$|yarn\s+(?:install|add|up|upgrade|remove|dlx)\b|"
    r"bun\s+(?:i|install|add|update|remove)\b|bunx\b|npx\b)",
    re.I,
)
NODE_INSTALL_RE = re.compile(
    r"(?:^|&&|\|\||;)\s*(?:nvm|fnm)\s+install\b|"
    r"(?:^|&&|\|\||;)\s*volta\s+install\s+node@|"
    r"(?:^|&&|\|\||;)\s*asdf\s+install\s+nodejs\b",
    re.I,
)
RUNTIME_MUTATION_RE = re.compile(
    r"(?:^|&&|\|\||;)\s*(?:nvm\s+(?:use|alias)|fnm\s+(?:use|default)|"
    r"volta\s+pin\s+node|asdf\s+(?:local|global)\s+nodejs)\b",
    re.I,
)


def normalize_version(value: str) -> str:
    match = VERSION_RE.search(str(value or ""))
    return match.group(1) if match else ""


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def snapshot_node_constraints(project_root: Path) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for relative in PIN_FILES:
        path = project_root / relative
        snapshot[relative] = file_hash(path)
    package_json = project_root / "package.json"
    if package_json.is_file():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            snapshot["package.json#engines.node"] = str((data.get("engines") or {}).get("node") or "")
            snapshot["package.json#volta.node"] = str((data.get("volta") or {}).get("node") or "")
        except (OSError, json.JSONDecodeError):
            snapshot["package.json#runtime-fields-unreadable"] = file_hash(package_json)
    for relative in CI_FILES:
        path = project_root / relative
        snapshot[relative] = file_hash(path)
    workflows = project_root / ".github" / "workflows"
    if workflows.is_dir():
        for path in sorted([*workflows.glob("*.yml"), *workflows.glob("*.yaml")]):
            relative = str(path.relative_to(project_root)).replace("\\", "/")
            snapshot[relative] = file_hash(path)
    return snapshot


def current_node(env: dict[str, str] | None = None) -> tuple[str, str]:
    path_value = (env or os.environ).get("PATH", "")
    executable = shutil.which("node", path=path_value) or ""
    if not executable:
        return "", ""
    result = subprocess.run(
        [executable, "--version"],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return normalize_version(result.stdout or result.stderr), executable


def runtime_directory_candidates(manager: str, version: str) -> list[Path]:
    home = Path.home()
    candidates: list[Path] = []
    if manager == "nvm-windows":
        if os.environ.get("NVM_HOME"):
            root = Path(os.environ["NVM_HOME"])
            candidates.extend([root / f"v{version}", root / version])
    elif manager == "nvm":
        root = Path(os.environ.get("NVM_DIR") or home / ".nvm")
        candidates.extend([root / "versions" / "node" / f"v{version}" / "bin"])
    elif manager == "fnm":
        roots = [
            Path(os.environ["FNM_DIR"]) if os.environ.get("FNM_DIR") else None,
            home / ".local" / "share" / "fnm",
            Path(os.environ["APPDATA"]) / "fnm" if os.environ.get("APPDATA") else None,
        ]
        for root in (item for item in roots if item):
            candidates.extend([
                root / "node-versions" / f"v{version}" / "installation" / "bin",
                root / "node-versions" / f"v{version}" / "installation",
            ])
    elif manager == "volta":
        root = Path(os.environ.get("VOLTA_HOME") or home / ".volta")
        candidates.append(root / "tools" / "image" / "node" / version / "bin")
        candidates.append(root / "tools" / "image" / "node" / version)
    elif manager == "asdf":
        root = Path(os.environ.get("ASDF_DATA_DIR") or home / ".asdf")
        candidates.append(root / "installs" / "nodejs" / version / "bin")
    return candidates


def directory_has_node(path: Path) -> bool:
    return (path / ("node.exe" if os.name == "nt" else "node")).is_file()


def resolve_runtime_directory(manager: str, version: str) -> Path | None:
    return next(
        (path for path in runtime_directory_candidates(manager, version) if directory_has_node(path)),
        None,
    )


def select_manager(requested: str, version: str) -> tuple[str, Path | None]:
    managers = ["nvm-windows", "nvm", "fnm", "volta", "asdf"]
    if requested != "auto":
        return requested, resolve_runtime_directory(requested, version)
    for manager in managers:
        runtime_dir = resolve_runtime_directory(manager, version)
        if runtime_dir:
            return manager, runtime_dir
    if os.name == "nt" and shutil.which("nvm"):
        return "nvm-windows", None
    return "", None


def isolated_environment(runtime_dir: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PATH"] = str(runtime_dir) + os.pathsep + env.get("PATH", "")
    env["FRONTEND_UPGRADE_NODE_ISOLATED"] = "1"
    return env


def classify_command(command: str) -> str:
    return "dependency-install-or-upgrade" if INSTALL_RE.search(command) else "project-scripts"


def verify_approvals(args: argparse.Namespace) -> None:
    if not args.execute:
        return
    if not args.approve_runtime_switch:
        raise ValueError("执行模式需要 --approve-runtime-switch；该参数只能在用户明确批准后传入")
    for command in args.command:
        if NODE_INSTALL_RE.search(command):
            raise ValueError(
                f"受控执行器不会安装 Node：{command}。请先单独获得 node-install 批准并在外部安装，然后重新预检。"
            )
        if RUNTIME_MUTATION_RE.search(command):
            raise ValueError(f"命令会绕过受控切换或写入运行时状态，已拒绝：{command}")
        scope = classify_command(command)
        if scope == "dependency-install-or-upgrade" and not args.approve_dependency_install:
            raise ValueError(f"命令需要 --approve-dependency-install：{command}")
        if scope == "project-scripts" and not args.approve_project_scripts:
            raise ValueError(f"命令需要 --approve-project-scripts：{command}")


def run_shell_command(command: str, project_root: Path, env: dict[str, str]) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    node_version, node_path = current_node(env)
    result = subprocess.run(command, cwd=project_root, env=env, shell=True, check=False)
    return {
        "command": command,
        "scope": classify_command(command),
        "started": started,
        "node_version": node_version,
        "node_path": node_path,
        "exit_code": result.returncode,
    }


def execute(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    project_root = Path(args.project_root).resolve()
    if not project_root.is_dir():
        raise ValueError(f"项目目录不存在：{project_root}")
    target = normalize_version(args.node_version)
    if target != args.node_version.strip().lstrip("v"):
        raise ValueError("--node-version 必须是精确 semver")
    verify_approvals(args)
    original_version, original_path = current_node()
    if original_version == target and original_path:
        manager, runtime_dir = "current", Path(original_path).parent
    else:
        manager, runtime_dir = select_manager(args.manager, target)
    plan: dict[str, Any] = {
        "project_root": str(project_root),
        "target_node": target,
        "manager": manager or "not-found",
        "mode": "isolated-child-process" if runtime_dir else "guarded-global-switch",
        "execute": bool(args.execute),
        "commands": [
            {"command": command, "scope": classify_command(command)}
            for command in args.command
        ],
        "original_node": original_version,
        "original_node_path": original_path,
        "results": [],
        "restoration": "not-required",
        "constraint_integrity": "not-checked",
    }
    if not runtime_dir and not (manager == "nvm-windows" and shutil.which("nvm")):
        raise RuntimeError(
            f"未找到已安装的 Node {target}。请先经单独批准执行对应版本管理器的 install 命令，再重新预检；本脚本不会自动安装。"
        )
    if not runtime_dir and not original_version:
        raise RuntimeError("无法确定原 Node 精确版本；为避免无法恢复，拒绝使用全局 nvm 切换")
    if not args.execute:
        plan["constraint_integrity"] = "dry-run"
        return 0, plan

    before_constraints = snapshot_node_constraints(project_root)
    switched_globally = False
    command_env = dict(os.environ)
    failure_code = 0
    try:
        if runtime_dir:
            command_env = isolated_environment(runtime_dir)
        else:
            switch = subprocess.run(
                ["nvm", "use", target],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if switch.returncode != 0:
                raise RuntimeError(f"nvm use {target} 失败：{switch.stderr or switch.stdout}")
            switched_globally = True
            plan["restoration"] = "pending"
        actual_version, actual_path = current_node(command_env)
        if actual_version != target:
            raise RuntimeError(
                f"目标运行时验证失败：期望 {target}，实际 {actual_version or '未检测到'}（{actual_path or '无路径'}）"
            )
        for command in args.command:
            result = run_shell_command(command, project_root, command_env)
            plan["results"].append(result)
            if result["exit_code"] != 0:
                failure_code = int(result["exit_code"]) or 1
                break
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        plan["execution_error"] = str(exc)
        failure_code = 2
    finally:
        if switched_globally:
            if not original_version:
                plan["restoration"] = "failed-original-node-unknown"
            else:
                restore = subprocess.run(
                    ["nvm", "use", original_version],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                restored_version, restored_path = current_node()
                if restore.returncode == 0 and restored_version == original_version:
                    plan["restoration"] = "verified"
                    plan["restored_node_path"] = restored_path
                else:
                    plan["restoration"] = "failed"
                    plan["restoration_error"] = restore.stderr or restore.stdout
        else:
            restored_version, restored_path = current_node()
            if restored_version == original_version and restored_path == original_path:
                plan["restoration"] = "verified-isolated"
            else:
                plan["restoration"] = "failed-unexpected-host-change"
        after_constraints = snapshot_node_constraints(project_root)
        if after_constraints == before_constraints:
            plan["constraint_integrity"] = "verified-unchanged"
        else:
            plan["constraint_integrity"] = "changed"
            plan["constraint_changes"] = {
                key: {"before": before_constraints.get(key), "after": after_constraints.get(key)}
                for key in sorted(set(before_constraints) | set(after_constraints))
                if before_constraints.get(key) != after_constraints.get(key)
            }

    if not str(plan["restoration"]).startswith("verified"):
        return 5, plan
    if plan["constraint_integrity"] != "verified-unchanged":
        return 6, plan
    return failure_code, plan


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root")
    parser.add_argument("--node-version", required=True, help="Exact already-installed Node semver selected by the analysis report.")
    parser.add_argument("--manager", choices=("auto", "nvm-windows", "nvm", "fnm", "volta", "asdf"), default="auto")
    parser.add_argument("--command", action="append", default=[], help="Explicit project command; repeatable.")
    parser.add_argument("--execute", action="store_true", help="Execute instead of printing a dry-run plan.")
    parser.add_argument("--approve-runtime-switch", action="store_true")
    parser.add_argument("--approve-dependency-install", action="store_true")
    parser.add_argument("--approve-project-scripts", action="store_true")
    parser.add_argument("--log-json", help="Optional execution log path. Written only in --execute mode.")
    args = parser.parse_args(argv)
    if not args.command:
        parser.error("至少提供一个 --command")
    return args


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        code, plan = execute(args)
        rendered = json.dumps(plan, ensure_ascii=False, indent=2)
        print(rendered)
        if args.execute and args.log_json:
            log_path = Path(args.log_json).resolve()
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(rendered + "\n", encoding="utf-8")
        return code
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
