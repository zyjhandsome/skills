#!/usr/bin/env python3
"""Deterministic, read-only environment preflight for Java dependency analysis.

Exit 0 means hard tool gates passed.
Exit 5 means one or more hard gates failed.
Exit 6 means dual Maven+Gradle roots need an explicit --build-tool choice
(not a hard tool failure — ask the human, then re-run).
Network failures are reported but do not change the exit code.
``--skip-network`` is for unit tests only; analysis must not pass it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

GRADLE_MARKERS = (
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
)
WRAPPER_NAMES = {
    "maven": ("mvnw.cmd", "mvnw") if os.name == "nt" else ("mvnw", "mvnw.cmd"),
    "gradle": ("gradlew.bat", "gradlew") if os.name == "nt" else ("gradlew", "gradlew.bat"),
}
NETWORK_URLS = (
    "https://repo1.maven.org/maven2/",
    "https://api.github.com/",
)
_JAVA_VERSION = re.compile(r'version "([^"]+)"')
_POM_JAVA = re.compile(
    r"<(?:java\.version|maven\.compiler\.(?:release|target|source)|release)>\s*([0-9][0-9.]*)"
)
_GRADLE_JAVA = re.compile(
    r"(?i)(?:sourceCompatibility|targetCompatibility|languageVersion|jvmTarget)\D{0,40}([0-9][0-9.]*)"
)


def _kill_process_tree(proc: subprocess.Popen) -> None:
    """Stop the probe and every child it spawned.

    On Windows, ``Popen.kill`` leaves grandchildren holding the pipes, so a
    wrapper that outlives ``timeout`` blocks until that grandchild exits.
    """
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            check=False,
            creationflags=flags,
        )
        return
    proc.kill()


def run_probe(command: list[str], cwd: Path, timeout: int, env: dict[str, str]) -> dict:
    try:
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
        )
    except OSError as exc:
        return {
            "command": command,
            "exit_code": None,
            "ok": False,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc)
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        return {
            "command": command,
            "exit_code": None,
            "ok": False,
            "stdout": "",
            "stderr": f"TimeoutExpired after {timeout}s",
        }
    return {
        "command": command,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout": (stdout or "").strip(),
        "stderr": (stderr or "").strip(),
    }


def major_from_token(token: str) -> int | None:
    head = token.strip().split()[0] if token else ""
    if head.startswith("1."):
        pieces = head.split(".")
        return int(pieces[1]) if len(pieces) > 1 and pieces[1].isdigit() else None
    digits = re.match(r"(\d+)", head)
    return int(digits.group(1)) if digits else None


def parse_java_version(text: str) -> dict:
    """Extract major/vendor/EA from ``java -version`` output. Missing fields stay empty."""
    match = _JAVA_VERSION.search(text)
    version = match.group(1) if match else ""
    lowered = text.lower()
    vendor = ""
    for name in ("temurin", "adoptium", "corretto", "zulu", "microsoft", "graal", "oracle", "openjdk"):
        if name in lowered:
            vendor = name
            break
    return {
        "version": version,
        "major": major_from_token(version),
        "vendor": vendor,
        "is_ea": bool(re.search(r"(?i)(?:^|[.\-])(?:ea|eap)(?:[.\-+]|$)", version)),
    }


def declared_java_major(root: Path) -> int | None:
    """Best-effort project JDK major. Used only to rank discovered JDKs, never to block."""
    version_file = root / ".java-version"
    if version_file.is_file():
        major = major_from_token(version_file.read_text(encoding="utf-8", errors="replace"))
        if major is not None:
            return major
    pom = root / "pom.xml"
    if pom.is_file():
        text = pom.read_text(encoding="utf-8", errors="replace")[:200_000]
        found = _POM_JAVA.search(text)
        if found:
            return major_from_token(found.group(1))
    for name in ("build.gradle.kts", "build.gradle"):
        path = root / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")[:200_000]
        found = _GRADLE_JAVA.search(text)
        if found:
            return major_from_token(found.group(1))
    return None


def _java_executable_under(directory: Path) -> Path | None:
    executable = "java.exe" if os.name == "nt" else "java"
    for relative in (
        Path("bin") / executable,
        Path("Contents") / "Home" / "bin" / executable,
    ):
        candidate = directory / relative
        if candidate.is_file():
            return candidate
    return None


def java_candidates() -> list[Path]:
    candidates: list[Path] = []
    roots = [Path.home() / ".jdks"]
    if os.name == "nt":
        roots.extend(
            [
                Path("C:/Program Files/Java"),
                Path("C:/Program Files/Microsoft"),
                Path("C:/Program Files/Eclipse Adoptium"),
                Path("C:/Program Files/Amazon Corretto"),
            ]
        )
    else:
        roots.extend(
            [
                Path("/usr/lib/jvm"),
                Path("/Library/Java/JavaVirtualMachines"),
                Path.home() / ".sdkman" / "candidates" / "java",
            ]
        )
    if os.environ.get("JAVA_HOME"):
        roots.insert(0, Path(os.environ["JAVA_HOME"]))
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        directories = [root]
        try:
            directories.extend(child for child in root.iterdir() if child.is_dir())
        except OSError:
            continue
        for directory in directories:
            found = _java_executable_under(directory)
            if found is None:
                continue
            resolved = found.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(found)
    return candidates


def rank_java_candidates(
    candidates: list[Path],
    wanted_major: int | None,
    cwd: Path,
    timeout: int,
    env: dict[str, str],
) -> list[Path]:
    """Put JDKs matching the project declaration first. Do not prefer the newest."""
    if wanted_major is None or len(candidates) < 2:
        return candidates
    matched: list[Path] = []
    rest: list[Path] = []
    for candidate in candidates:
        probe = run_probe([str(candidate), "-version"], cwd, min(timeout, 10), env)
        parsed = parse_java_version(f"{probe['stderr']}\n{probe['stdout']}")
        if parsed["major"] == wanted_major:
            matched.append(candidate)
        else:
            rest.append(candidate)
    return matched + rest


def detect_build_tool(root: Path, requested: str) -> tuple[str | None, list[str], bool]:
    detected: list[str] = []
    if (root / "pom.xml").is_file():
        detected.append("maven")
    if any((root / name).is_file() for name in GRADLE_MARKERS):
        detected.append("gradle")
    if requested != "auto":
        return requested, detected, False
    if len(detected) == 1:
        return detected[0], detected, False
    if len(detected) > 1:
        return None, detected, True
    return None, detected, False


def find_wrapper(root: Path, tool: str) -> Path | None:
    """Wrapper at ``root`` or an ancestor (submodule analysis). At most 8 levels."""
    current = root.resolve()
    for _ in range(8):
        for name in WRAPPER_NAMES[tool]:
            candidate = current / name
            if candidate.is_file():
                return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


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
    """Maven tries the system CLI first. Gradle tries the wrapper first when it exists.

    A failing PATH entry falls through to the other candidate instead of blocking.
    """
    system_name = "mvn" if tool == "maven" else "gradle"
    system = shutil.which(system_name)
    wrapper = find_wrapper(root, tool)
    ordered: list[tuple[str, list[str]]] = []
    system_command = [system, "-v"] if system else None
    wrapper_command = [str(wrapper), "-v"] if wrapper is not None else None
    if tool == "gradle" and wrapper_command is not None:
        ordered.append(("wrapper", wrapper_command))
        if system_command is not None:
            ordered.append(("system", system_command))
    else:
        if system_command is not None:
            ordered.append(("system", system_command))
        if wrapper_command is not None:
            ordered.append(("wrapper", wrapper_command))
    last: dict | None = None
    for source, command in ordered:
        result = run_probe(command, root, timeout, env)
        result["source"] = source
        if result["ok"]:
            return result
        last = result
    if last is not None:
        return last
    return {
        "command": [],
        "exit_code": None,
        "ok": False,
        "stdout": "",
        "stderr": "system CLI and wrapper both missing",
        "source": "missing",
    }


def python_probe(cwd: Path, timeout: int, env: dict[str, str]) -> dict:
    for name in ("python", "python3"):
        executable = shutil.which(name)
        if not executable:
            continue
        result = run_probe([executable, "--version"], cwd, timeout, env)
        if result["ok"]:
            result["executable"] = executable
            result["source"] = "path"
            version_text = result["stdout"] or result["stderr"]
            result["version"] = version_text.split()[-1] if version_text else ""
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
    parser.add_argument(
        "--skip-network",
        action="store_true",
        help="unit tests only; analysis must not pass this flag",
    )
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    if not root.is_dir():
        parser.error(f"project root is not a directory: {root}")

    env = os.environ.copy()
    java_command = shutil.which("java")
    java_source = "path"
    java_home = env.get("JAVA_HOME")
    if not java_command:
        candidates = rank_java_candidates(
            java_candidates(), declared_java_major(root), root, args.timeout, env
        )
        if candidates:
            java_command = str(candidates[0])
            java_home = str(candidates[0].parent.parent)
            # macOS layouts nest the real home under Contents/Home.
            if candidates[0].parent.name == "bin" and candidates[0].parent.parent.name == "Home":
                java_home = str(candidates[0].parent.parent)
            env["JAVA_HOME"] = java_home
            env["PATH"] = str(Path(java_home) / "bin") + os.pathsep + env.get("PATH", "")
            java_source = "discovered"
    java = run_probe([java_command or "java", "-version"], root, args.timeout, env)
    java["source"] = java_source if java["ok"] else "missing"
    java["executable"] = java_command
    java["java_home"] = java_home if java["ok"] else None
    java.update(parse_java_version(f"{java.get('stderr', '')}\n{java.get('stdout', '')}"))

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
    if args.skip_network:
        network = [
            {"url": url, "ok": None, "status": None, "skipped": True} for url in NETWORK_URLS
        ]
    else:
        network = [network_probe(url, args.timeout) for url in NETWORK_URLS]
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
