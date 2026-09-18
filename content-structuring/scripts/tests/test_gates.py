#!/usr/bin/env python3
"""Gate regression tests for content-structuring scripts (v5.34)."""

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


def test_fixture_adversarial_4d_ok() -> None:
    cp = run([sys.executable, str(NORM), str(FIX / "adversarial-interview.md"), "--check"])
    out = (cp.stdout or b"").decode("utf-8", errors="replace")
    err = (cp.stderr or b"").decode("utf-8", errors="replace")
    assert cp.returncode == 0, out + err


def test_fixture_longform_4d_ok() -> None:
    """Generic template keeps --- before 关键语录与交锋时刻 (structural, spec v5.32)."""
    cp = run([sys.executable, str(NORM), str(FIX / "longform-generic.md"), "--check"])
    out = (cp.stdout or b"").decode("utf-8", errors="replace")
    err = (cp.stderr or b"").decode("utf-8", errors="replace")
    assert cp.returncode == 0, out + err


def test_fixture_multisource_4d_ok() -> None:
    cp = run([sys.executable, str(NORM), str(FIX / "multisource-conflict.md"), "--check"])
    out = (cp.stdout or b"").decode("utf-8", errors="replace")
    err = (cp.stderr or b"").decode("utf-8", errors="replace")
    assert cp.returncode == 0, out + err


def test_fixture_longform_4c_ok() -> None:
    cp = run([sys.executable, str(CHECK4C), str(FIX / "longform-generic.md")])
    out = (cp.stdout or b"").decode("utf-8", errors="replace")
    err = (cp.stderr or b"").decode("utf-8", errors="replace")
    assert cp.returncode == 0, out + err


def test_fixture_multisource_4c_ok() -> None:
    cp = run([sys.executable, str(CHECK4C), str(FIX / "multisource-conflict.md")])
    out = (cp.stdout or b"").decode("utf-8", errors="replace")
    err = (cp.stderr or b"").decode("utf-8", errors="replace")
    assert cp.returncode == 0, out + err


def test_4c_inline_lexicon_comments_do_not_break_patterns() -> None:
    """Gloss comments after a pattern must not become part of the regex."""
    text = """# T

## 第一节

灰度 rollout 之后再看 PIP。
"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = Path(f.name)
    try:
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        err = (cp.stderr or b"").decode("utf-8", errors="replace")
        assert cp.returncode == 0, out + err
        assert "CONTEXTUAL_ENGLISH_REVIEW" in out, out
        assert "rollout" in out.lower() or "PIP" in out, out
    finally:
        path.unlink(missing_ok=True)


def test_4c_full_lexicon_loaded_from_file() -> None:
    """Words beyond the old 5 hard-coded stems must block (lexicon.txt is the source)."""
    text = """# T

## 第一节

这家公司的 flywheel 很强，incumbent 压力大，团队仍在 pontificate。
"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = Path(f.name)
    try:
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        err = (cp.stderr or b"").decode("utf-8", errors="replace")
        assert cp.returncode != 0, out + err
        assert "flywheel" in out and "incumbent" in out and "pontificate" in out, out
    finally:
        path.unlink(missing_ok=True)


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


def test_4c_allows_rag_and_technical_harness() -> None:
    text = """# T

## 第一节

检索增强生成（RAG）用于召回。Harness 是产品名，harness 也是常见技术层标签。
"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = Path(f.name)
    try:
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        err = (cp.stderr or b"").decode("utf-8", errors="replace")
        assert cp.returncode == 0, out + err
        assert "RAG" not in out, out
    finally:
        path.unlink(missing_ok=True)


def test_4c_allows_field_native_concept_labels() -> None:
    text = """# T

## 第一节

他把自己定义为 Builder。技术演化线是 Agent → Loop → Graph，核心是 Agent Loop。
"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = Path(f.name)
    try:
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        err = (cp.stderr or b"").decode("utf-8", errors="replace")
        assert cp.returncode == 0, out + err
        assert "ACTIONABLE_HITS" not in out, out
    finally:
        path.unlink(missing_ok=True)


def test_4c_reports_likely_over_translation_without_failing() -> None:
    text = """# T

## 第一节

现场先问：先是代理，然后循环，然后图。讲者说自己爱的是建造，编程只是手段。
"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = Path(f.name)
    try:
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        err = (cp.stderr or b"").decode("utf-8", errors="replace")
        assert cp.returncode == 0, out + err
        assert "OVER_TRANSLATION_REVIEW" in out, out
    finally:
        path.unlink(missing_ok=True)


def test_4c_consecutive_english_is_review_not_fail() -> None:
    """4c-2: out-of-lexicon leftover phrases must surface as review, not exit 0 silence."""
    text = """# T

## 第一节

这套 go to market motion 很强，团队靠 land and expand 打开客户。
真正的瓶颈是 organizational readiness，而不是 technical debt；管理层 still hesitant。
"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = Path(f.name)
    try:
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        err = (cp.stderr or b"").decode("utf-8", errors="replace")
        assert cp.returncode == 0, out + err
        assert "CONSECUTIVE_ENGLISH_4C2" in out, out
        lowered = out.lower()
        assert "go to market" in lowered or "land and expand" in lowered, out
        assert "ACTIONABLE_HITS" not in out, out
    finally:
        path.unlink(missing_ok=True)


def test_4c_lowercase_generic_labels_not_masked() -> None:
    """Title-case product labels stay allowed; lowercase leftovers stay visible to 4c-2."""
    text = """# T

## 第一节

正文把 agent loop 当普通夹写留下，后又写 workflow change。
"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = Path(f.name)
    try:
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        err = (cp.stderr or b"").decode("utf-8", errors="replace")
        assert cp.returncode == 0, out + err
        assert "CONSECUTIVE_ENGLISH_4C2" in out, out
        lowered = out.lower()
        assert "agent loop" in lowered or "workflow change" in lowered, out
    finally:
        path.unlink(missing_ok=True)


def test_selfcheck_emits_machine_rows() -> None:
    """selfcheck.py must print 4c/4d rows from real script counts, not agent prose."""
    selfcheck = ROOT / "scripts" / "selfcheck.py"
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

团队对路线图仍然 super bullish，并靠 land and expand 扩张。

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
        cp = run([sys.executable, str(selfcheck), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        err = (cp.stderr or b"").decode("utf-8", errors="replace")
        assert selfcheck.is_file(), "scripts/selfcheck.py missing"
        assert cp.returncode != 0, out + err
        assert "正文中文叙事" in out and "纯净排版" in out, out
        assert "4c-1" in out and "4c-2" in out, out
        assert "super bullish" in out.lower() or "actionable" in out.lower(), out
    finally:
        path.unlink(missing_ok=True)


def test_selfcheck_warns_when_only_4c2_remains() -> None:
    """4c-1 clean but leftover phrases still block a ✅ 正文中文叙事 row."""
    selfcheck = ROOT / "scripts" / "selfcheck.py"
    text = """# T

## 第一节

这套 go to market motion 很强。
"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = Path(f.name)
    try:
        cp = run([sys.executable, str(selfcheck), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        err = (cp.stderr or b"").decode("utf-8", errors="replace")
        assert cp.returncode == 0, out + err
        assert "| 正文中文叙事 | ⚠️ |" in out, out
        assert "4c-2" in out and "go to market" in out.lower(), out
    finally:
        path.unlink(missing_ok=True)


def test_4c_ignores_code_fences_links_and_urls() -> None:
    text = """# T

[Towards infinite context windows](https://example.com/context)

```text
tokens of context
```

正文已中文化。
"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = Path(f.name)
    try:
        cp = run([sys.executable, str(CHECK4C), str(path)])
        out = (cp.stdout or b"").decode("utf-8", errors="replace")
        err = (cp.stderr or b"").decode("utf-8", errors="replace")
        assert cp.returncode == 0, out + err
    finally:
        path.unlink(missing_ok=True)


def main() -> int:
    tests = [
        test_4d_detects_hr_with_blank_line,
        test_fixture_dialogue_4d_ok,
        test_fixture_adversarial_4d_ok,
        test_fixture_longform_4d_ok,
        test_fixture_multisource_4d_ok,
        test_fixture_longform_4c_ok,
        test_fixture_multisource_4c_ok,
        test_4c_inline_lexicon_comments_do_not_break_patterns,
        test_4c_full_lexicon_loaded_from_file,
        test_fixture_dialogue_4c_ok,
        test_fixture_stock_4c_hits,
        test_4c_allows_rag_and_technical_harness,
        test_4c_allows_field_native_concept_labels,
        test_4c_reports_likely_over_translation_without_failing,
        test_4c_consecutive_english_is_review_not_fail,
        test_4c_lowercase_generic_labels_not_masked,
        test_selfcheck_emits_machine_rows,
        test_selfcheck_warns_when_only_4c2_remains,
        test_4c_ignores_code_fences_links_and_urls,
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
