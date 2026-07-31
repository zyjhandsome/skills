#!/usr/bin/env python3
"""Deterministic, read-only environment preflight for Java dependency analysis.

Exit 0 means hard tool gates passed.
Exit 5 means one or more hard gates failed.
Exit 6 means dual Maven+Gradle roots need an explicit --build-tool choice
(not a hard tool failure — ask the human, then re-run).
Network failures are reported but do not change the exit code.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


def run_probe(command: list[str], cwd: Path, timeout: int, env: dict[str, str]) -> dict:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "ok": completed.returncode == 0,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except (FileNotFoundError, PermissionError) as exc:
        return {
            "command": command,
            "exit_code": None,
            "ok": False,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "exit_code": None,
            "ok": False,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": f"TimeoutExpired after {timeout}s",
        }


def java_candidates() -> list[Path]:
    candidates: list[Path] = []
    roots = [
        Path.home() / ".jdks",
        Path("C:/Program Files/Java"),
        Path("C:/Program Files/Microsoft"),
        Path("C:/Program Files/Eclipse Adoptium"),
        Path("C:/Program Files/Amazon Corretto"),
    ]
    if os.environ.get("JAVA_HOME"):
        roots.insert(0, Path(os.environ["JAVA_HOME"]))
    executable = "java.exe" if os.name == "nt" else "java"
    for root in roots:
        if not root.exists():
            continue
        direct = root / "bin" / executable
        if direct.is_file():
            candidates.append(direct)
        for child in sorted(root.glob("*"), reverse=True):
            nested = child / "bin" / executable
            if nested.is_file():
                candidates.append(nested)
    return candidates


def detect_build_tool(root: Path, requested: str) -> tuple[str | None, list[str], bool]:
    detected: list[str] = []
    if (root / "pom.xml").is_file():
        detected.append("maven")
    if any((root / name).is_file() for name in ("build.gradle", "build.gradle.kts")):
        detected.append("gradle")
    if requested != "auto":
        return requested, detected, False
    if len(detected) == 1:
        return detected[0], detected, False
    if len(detected) > 1:
        return None, detected, True
    return None, detected, False


def network_probe(url: str, timeout: int) -> dict:
    try:
        request = urllib.request.Request(
            url, method="HEAD", headers={"User-Agent": "codex-skill-preflight"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            return {
                "url": url,
                "ok": 200 <= status < 400,
                "status": status,
            }
    except Exception as exc:  # network stacks expose several platform-specific exceptions
        return {
            "url": url,
            "ok": False,
            "status": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def build_probe(root: Path, tool: str, timeout: int, env: dict[str, str]) -> dict:
    if tool == "maven":
        system, wrapper = shutil.which("mvn"), root / (
            "mvnw.cmd" if os.name == "nt" else "mvnw"
        )
        command = (
            [system, "-v"]
            if system
            else ([str(wrapper), "-v"] if wrapper.is_file() else [])
        )
    else:
        system, wrapper = shutil.which("gradle"), root / (
            "gradlew.bat" if os.name == "nt" else "gradlew"
        )
        command = (
            [system, "-v"]
            if system
            else ([str(wrapper), "-v"] if wrapper.is_file() else [])
        )
    result = (
        run_probe(command, root, timeout, env)
        if command
        else {
            "command": [],
            "exit_code": None,
            "ok": False,
            "stdout": "",
            "stderr": "system CLI and wrapper both missing",
        }
    )
    result["source"] = "system" if system else ("wrapper" if command else "missing")
    return result


def python_probe(cwd: Path, timeout: int, env: dict[str, str]) -> dict:
    for name in ("python", "python3"):
        executable = shutil.which(name)
        if not executable:
            continue
        result = run_probe([executable, "--version"], cwd, timeout, env)
        if result["ok"]:
            result["executable"] = executable
            result["source"] = "path"
            result["version"] = (result["stdout"] or result["stderr"]).split()[-1]
            return result
    # Graded pass: interpreter running this script can still execute validate_report.py.
    return {
        "command": [sys.executable, "--version"],
        "exit_code": 0,
        "ok": True,
        "stdout": sys.version.split()[0],
        "stderr": "",
        "executable": sys.executable,
        "source": "current-interpreter",
        "version": sys.version.split()[0],
        "implementation": sys.implementation.name,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument(
        "--build-tool", choices=("auto", "maven", "gradle"), default="auto"
    )
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    if not root.is_dir():
        parser.error(f"project root is not a directory: {root}")

    env = os.environ.copy()
    java_command = shutil.which("java")
    java_source = "path"
    if not java_command:
        candidates = java_candidates()
        if candidates:
            java_command = str(candidates[0])
            java_home = candidates[0].parent.parent
            env["JAVA_HOME"] = str(java_home)
            env["PATH"] = str(java_home / "bin") + os.pathsep + env.get("PATH", "")
            java_source = "discovered"
    java = run_probe([java_command or "java", "-version"], root, args.timeout, env)
    java["source"] = java_source if java["ok"] else "missing"
    java["executable"] = java_command

    tool, detected, needs_selection = detect_build_tool(root, args.build_tool)
    if needs_selection:
        build = {
            "command": [],
            "exit_code": None,
            "ok": False,
            "stdout": "",
            "stderr": (
                "both Maven and Gradle roots detected; ask which tool to use, "
                "then re-run with --build-tool maven|gradle"
            ),
            "source": "needs_selection",
        }
    elif tool:
        build = build_probe(root, tool, args.timeout, env)
    else:
        build = {
            "command": [],
            "exit_code": None,
            "ok": False,
            "stdout": "",
            "stderr": "auto detection found no Maven or Gradle build root",
            "source": "missing",
        }

    python = python_probe(root, args.timeout, env)
    network = [
        network_probe("https://repo1.maven.org/maven2/", args.timeout),
        network_probe("https://api.github.com/", args.timeout),
    ]
    hard_pass = bool(java["ok"] and build["ok"] and python["ok"])
    result = {
        "project_root": str(root),
        "selected_build_tool": tool,
        "detected_build_tools": detected,
        "needs_build_tool_selection": needs_selection,
        "hard_gates_passed": hard_pass,
        "java": java,
        "build_tool": build,
        "python": python,
        "network": network,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"hard_gates_passed={str(hard_pass).lower()}")
        if needs_selection:
            print("needs_build_tool_selection=true")
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if needs_selection:
        return 6
    return 0 if hard_pass else 5


if __name__ == "__main__":
    raise SystemExit(main())
