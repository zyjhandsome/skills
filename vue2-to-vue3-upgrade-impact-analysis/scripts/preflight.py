#!/usr/bin/env python3
"""Read-only environment preflight for Vue2→Vue3 upgrade impact analysis.

Exit 0: hard gates passed.
Exit 5: hard gate failed (no report write).
Exit 2: usage error.
Network failures are reported but do not change the exit code.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


def run_probe(command: list[str], cwd: Path, timeout: int) -> dict:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "ok": completed.returncode == 0,
            "stdout": (completed.stdout or "").strip(),
            "stderr": (completed.stderr or "").strip(),
        }
    except (FileNotFoundError, PermissionError) as exc:
        return {
            "command": command,
            "exit_code": None,
            "ok": False,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }
    except subprocess.TimeoutExpired:
        return {
            "command": command,
            "exit_code": None,
            "ok": False,
            "stdout": "",
            "stderr": f"TimeoutExpired after {timeout}s",
        }


def network_probe(url: str, timeout: int) -> dict:
    try:
        request = urllib.request.Request(
            url, method="HEAD", headers={"User-Agent": "vue2-to-vue3-preflight"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            return {"url": url, "ok": 200 <= status < 400, "status": status}
    except Exception as exc:  # noqa: BLE001 — probe must never crash preflight
        return {
            "url": url,
            "ok": False,
            "status": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def detect_package_manager(root: Path) -> dict:
    locks = {
        "pnpm": root / "pnpm-lock.yaml",
        "yarn": root / "yarn.lock",
        "bun": root / "bun.lockb",
        "npm": root / "package-lock.json",
    }
    present = [name for name, path in locks.items() if path.is_file()]
    binaries = {
        name: shutil.which(name) is not None for name in ("npm", "pnpm", "yarn", "bun")
    }
    ok = bool(present) or any(binaries.values())
    return {"lockfiles": present, "binaries": binaries, "ok": ok}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.project_root.resolve()
    if not root.is_dir():
        print(f"project root not found: {root}", file=sys.stderr)
        return 2

    node = run_probe(["node", "-v"], root, args.timeout)
    py = run_probe([sys.executable, "--version"], root, args.timeout)
    pm = detect_package_manager(root)
    network = [
        network_probe("https://registry.npmjs.org/vue", args.timeout),
        network_probe("https://v3-migration.vuejs.org/", args.timeout),
    ]

    hard_ok = bool(node["ok"] and py["ok"] and pm["ok"])
    result = {
        "project_root": str(root),
        "node": node,
        "python": py,
        "package_manager": pm,
        "network": network,
        "hard_gates_ok": hard_ok,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"project_root: {root}")
        print(f"node: {'PASS' if node['ok'] else 'FAIL'} {node.get('stdout') or node.get('stderr')}")
        print(f"python: {'PASS' if py['ok'] else 'FAIL'}")
        print(
            "package_manager: "
            f"{'PASS' if pm['ok'] else 'FAIL'} locks={pm['lockfiles']} bins={pm['binaries']}"
        )
        for item in network:
            print(f"network: {'PASS' if item['ok'] else 'FAIL'} {item['url']}")
        print(f"hard_gates_ok: {hard_ok}")

    return 0 if hard_ok else 5


if __name__ == "__main__":
    raise SystemExit(main())
