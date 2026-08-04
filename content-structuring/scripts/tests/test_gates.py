#!/usr/bin/env python3
"""Gate regression tests for content-structuring scripts (v5.28)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NORM = ROOT / "scripts" / "normalize_spacing.py"
CHECK4C = ROOT / "scripts" / "check_4c.py"
FIX = ROOT / "fixtures"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    # Avoid Windows console code-page decoding crashes in captured stdout
    return subprocess.run(cmd, capture_output=True)


def test_4d_detects_hr_with_blank_line() -> None:
    text = """# T

## 文章元数据

| 项目 | 内容 |
|------|------|
| **原标题** | X |

---

## 核心导读

> **全文论点**：A

---

## 目录

1. [一](#1)

---

## 第一节

### 核心洞察

> 一

### 深度解析

内容

---

## 第二节

### 核心洞察

> 二

### 深度解析

内容二

---

## 自检报告

| a | b |
|---|---|
| x | y |
"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = Path(f.name)
    try:
        cp = run([sys.executable, str(NORM), str(path), "--check"])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        err = (cp.stderr or b"").decode("utf-8", errors="replace")
        assert cp.returncode != 0, out + err
        assert "between body sections" in out, out
    finally:
        path.unlink(missing_ok=True)


def test_fixture_dialogue_4d_ok() -> None:
    cp = run([sys.executable, str(NORM), str(FIX / "dialogue-three-layer.md"), "--check"])
    out = (cp.stdout or b"").decode("utf-8", errors="replace")
    err = (cp.stderr or b"").decode("utf-8", errors="replace")
    assert cp.returncode == 0, out + err


def test_fixture_dialogue_4c_ok() -> None:
    cp = run([sys.executable, str(CHECK4C), str(FIX / "dialogue-three-layer.md")])
    out = (cp.stdout or b"").decode("utf-8", errors="replace")
    err = (cp.stderr or b"").decode("utf-8", errors="replace")
    assert cp.returncode == 0, out + err


def test_fixture_stock_4c_hits() -> None:
    cp = run([sys.executable, str(CHECK4C), str(FIX / "stock-english-mix.md")])
    out = (cp.stdout or b"").decode("utf-8", errors="replace").lower()
    err = (cp.stderr or b"").decode("utf-8", errors="replace")
    assert cp.returncode != 0, out + err
    assert "super bullish" in out or "operationalize" in out or "refine" in out


def main() -> int:
    tests = [
        test_4d_detects_hr_with_blank_line,
        test_fixture_dialogue_4d_ok,
        test_fixture_dialogue_4c_ok,
        test_fixture_stock_4c_hits,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
