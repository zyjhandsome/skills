"""validate.py 的机械规则回归(仅标准库)。

用最小夹具驱动 CLI,确认缺区块 / 序数标题 / 六件套缺口 / 模板污染
等会报 ERROR,合规稿与黄金范例能 PASS。
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "validate.py"
EXAMPLE = Path(__file__).resolve().parents[2] / "EXAMPLE.md"

_spec = importlib.util.spec_from_file_location("gru_validate", SCRIPT)
assert _spec and _spec.loader
validate_mod = importlib.util.module_from_spec(_spec)
sys.modules["gru_validate"] = validate_mod
_spec.loader.exec_module(validate_mod)

MINIMAL = """\
# 示例工具 使用示例:一句话价值

> 电梯简介:机制 → 价值。

[![GitHub stars](https://img.shields.io/github/stars/acme/demo?style=social)](https://github.com/acme/demo)

## 仓库能力入口一览

### 整仓作用与原理

本地 CLI,不经 LLM。

```mermaid
flowchart LR
    U["用户"] --> C["cli"]
```

## 0. 案例背景

接手一个 demo 仓。

## 0.2 要不要一上来全量使用?

**适合**:要命令行自检。 **不适合**:只要 GUI。

## 0.3 功能覆盖索引

| 功能 / 能力 | 本文位置 | 第一天需要吗 | 主要风险 |
|---|---|---:|---|
| 安装 | 案例 A | 是 | PATH |

## 案例 A · 安装

> **场景**:要把工具装进终端。

**角色**:Windows 11,已装 Python。

**怎么用**:

```text
pip install demo-cli
```

**你会看到什么(示例输出)**:

```text
Successfully installed demo-cli
```

**效果(用了 vs 没用)**:

| | 不用 | 用了 |
|---|---|---|
| 安装 | 手拷二进制 | 一条 pip |

**实操卡**

```text
前置条件: Python 3.11+
可执行步骤: 1) pip install demo-cli
验收方式: demo-cli --help 无报错
失败处理: 命令找不到 → 刷新 PATH
风险边界: 可卸载
```

## 关键收益总结(用了 vs 没用)

| 环节 | 不用本工具 | 用了之后 | 怎么自检 |
|---|---|---|---|
| 安装 | 手拷 | pip | --help |

## 常见坑

| 坑 | 原因 | 规避 |
|---|---|---|
| 命令找不到 | PATH | 重开终端 |

## 实操检查清单

- [ ] demo-cli --help 能跑

## 底层逻辑

1. **本地优先**:不把源码送云端。

## 参考链接

- 官方仓库:https://github.com/acme/demo

| **本文校验** | 2026-09-18,对照 README |
"""


def _report(text: str, repo_type: str | None = None) -> validate_mod.Report:
    with tempfile.TemporaryDirectory() as tmp:
        article = Path(tmp) / "示例工具 使用示例.md"
        article.write_text(text, encoding="utf-8")
        return validate_mod.validate(article, repo_type)


def _joined(rep: validate_mod.Report) -> str:
    return "\n".join(rep.errors + rep.warns)


class ValidateCliTests(unittest.TestCase):
    def test_minimal_article_passes(self) -> None:
        rep = _report(MINIMAL)
        self.assertFalse(rep.errors, _joined(rep))

    def test_flags_missing_required_block(self) -> None:
        rep = _report(MINIMAL.replace("## 常见坑\n", "## 已改名的坑\n"))
        self.assertTrue(any("缺少必需区块「常见坑」" in e for e in rep.errors), _joined(rep))

    def test_flags_ordinal_heading(self) -> None:
        rep = _report(MINIMAL.replace("## 案例 A · 安装", "## 一、案例 A · 安装"))
        self.assertTrue(any("中文序数" in e for e in rep.errors), _joined(rep))

    def test_flags_beginner_section(self) -> None:
        rep = _report(MINIMAL.replace("## 仓库能力入口一览", "## 新手专区：从 0 到 1\n\n## 仓库能力入口一览"))
        self.assertTrue(any("新手专区" in e for e in rep.errors), _joined(rep))

    def test_flags_leaked_h1(self) -> None:
        rep = _report(MINIMAL.replace("## 案例 A · 安装", "# 带 UI:\n\n## 案例 A · 安装"))
        self.assertTrue(any("额外 H1" in e for e in rep.errors), _joined(rep))

    def test_flags_missing_six_pack_field(self) -> None:
        rep = _report(MINIMAL.replace("**角色**:Windows 11,已装 Python。\n\n", ""))
        self.assertTrue(any("六件套字段「角色」" in e for e in rep.errors), _joined(rep))

    def test_flags_scene_equals_role(self) -> None:
        rep = _report(MINIMAL.replace("**角色**:Windows 11,已装 Python。", "**角色**:要把工具装进终端。"))
        self.assertTrue(any("角色」与「场景」逐字雷同" in e for e in rep.errors), _joined(rep))

    def test_flags_wikilink(self) -> None:
        rep = _report(MINIMAL.replace("## 常见坑", "见 [[其它文章]]\n\n## 常见坑"))
        self.assertTrue(any("双链" in e for e in rep.errors), _joined(rep))

    def test_flags_mcp_contamination_when_type_cli(self) -> None:
        rep = _report(MINIMAL.replace("刷新 PATH", "刷新 PATH。请索引这个项目"), repo_type="cli")
        self.assertTrue(any("MCP 专属表述" in e for e in rep.errors), _joined(rep))

    def test_flags_handwritten_stars(self) -> None:
        rep = _report(MINIMAL.replace("机制 → 价值。", "机制 → 价值。已有 79k+ Stars。"))
        self.assertTrue(any("Star" in e for e in rep.errors), _joined(rep))

    def test_flags_missing_card_field(self) -> None:
        rep = _report(MINIMAL.replace("失败处理: 命令找不到 → 刷新 PATH\n", ""))
        self.assertTrue(any("实操卡缺字段" in e for e in rep.errors), _joined(rep))

    def test_gold_example_passes_as_mcp(self) -> None:
        self.assertTrue(EXAMPLE.exists(), "EXAMPLE.md missing")
        rep = validate_mod.validate(EXAMPLE, "mcp")
        self.assertFalse(rep.errors, _joined(rep))


if __name__ == "__main__":
    unittest.main()
