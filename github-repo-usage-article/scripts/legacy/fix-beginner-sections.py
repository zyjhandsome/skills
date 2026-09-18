#!/usr/bin/env python3
"""存量修稿脚本:清理已废弃「新手专区」里的 MCP 模板污染。

新文章不需要它——现行规则已不写「新手专区」(安装与首次验收写进案例 A)。
仅在批量修早期成稿时使用,用完即弃。

用法:
    python fix-beginner-sections.py <文章目录> [--dry-run]
    python fix-beginner-sections.py <文章目录> --type cli      # 强制按某类型修
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CONTAMINATED_WHY = (
    "**为什么要用它？** 没有本地图谱时，AI 只能反复打开文件「翻书」——慢、费 Token。"
    "接上 MCP 后先建地图，结构题直接查图。"
)

MCP_ROW = "| **MCP** | 给 AI 装「标准插座」的插件协议 | 手机 USB 接口 |"
INDEX_ROW = "| **索引** | 把项目扫描一遍、建本地「地图」 | 图书馆编目 |"
TOKEN_ROW = "| **Token** | 发给 AI 的「字数额度」，读文件越多越贵 | 手机流量 |"

TOOL_CONFIG: dict[str, dict[str, str]] = {
    "mcp": {
        "extra_terms": "",
        "why": "**为什么要用它？** 见文首电梯简介；本工具通过 MCP 给 Agent 装「项目地图」，结构题直接查图而不是反复翻文件。",
        "step3": "对 Agent 说「请索引这个项目」或按正文 **案例 A** 操作。",
        "step4": "- Settings → MCP 里能看到对应 server 和 tools 数量。\n- 对照正文 **案例 A** 的「验收方式」逐项打勾。",
        "stuck2": "| Agent 不按 Skill/MCP 走 | 未触发或与其它规则冲突 | 点名正文示例提示词；一次只让一套流程主导 |",
    },
    "skills": {
        "extra_terms": "| **Skill** | 写给 Agent 的「专项工作手册」，按场景触发 | 厨师菜谱 |\n",
        "why": "**为什么要用它？** 没有流程 Skills 时，Agent 容易「一句 prompt 直接写代码」——跳澄清、跳计划、跳测试。装上后会在动手前先对齐目标与验收。",
        "step3": "对 Agent 说正文 **案例 A** 里的「怎么用」示例话，或显式点名对应 Skill/斜杠命令。",
        "step4": "- Agent 对话里输入 `/` 或 `@` 能补全到本仓库相关 Skill/命令。\n- 对照正文 **案例 A** 的「验收方式」逐项打勾。",
        "stuck2": "| Agent 不按 Skill 走 | 未触发或与其它规则冲突 | 点名正文示例提示词；一次只让一套流程主导 |",
    },
    "cli": {
        "extra_terms": "| **CLI** | 在终端里运行的命令行工具 | 遥控器上的实体按钮 |\n",
        "why": "**为什么要用它？** 见文首电梯简介；本工具通过 CLI/脚本把重复操作变成可复制命令，Agent 也可代为调用。",
        "step3": "在终端运行正文 **案例 A** 的安装/启动命令，或把案例里的示例话发给 Agent。",
        "step4": "- 终端命令无报错，且产出与 **案例 A**「你会看到什么」一致。\n- 对照正文 **案例 A** 的「验收方式」逐项打勾。",
        "stuck2": "| 命令找不到 | PATH 未刷新或未重装 | 重启终端；按「常见坑」检查安装路径 |",
    },
    "rules": {
        "extra_terms": "| **Rules** | 写进项目的持久约束，每次对话自动加载 | 员工手册 |\n",
        "why": "**为什么要用它？** 没有项目规则时，Agent 每次会话都「失忆」，风格与约束不一致。规则文件让行为可复用、可版本管理。",
        "step3": "把规则文件复制到项目 `.cursor/rules/`（或宿主对应目录），新开 Agent 对话测试。",
        "step4": "- 新对话中 Agent 行为符合规则描述（见 **案例 A** 验收项）。\n- 对照正文 **案例 A** 的「验收方式」逐项打勾。",
        "stuck2": "| 规则不生效 | 路径错误或 glob 未匹配 | 查宿主文档中 rules 目录与 `alwaysApply` 设置 |",
    },
}

# 按正文关键词推断仓库类型;命中不了就报错要求显式 --type,不再默默回退。
TYPE_HINTS: dict[str, tuple[str, ...]] = {
    "mcp": ("MCP Server", "mcpServers", "Settings → MCP", "MCP 工具清单"),
    "skills": ("npx skills add", "SKILL.md", "斜杠命令", "Skills 一览"),
    "rules": (".cursor/rules", "alwaysApply", "Rules 文件"),
    "cli": ("--help", "npm install -g", "pip install", "终端运行"),
}


def detect_type(content: str) -> str | None:
    scores = {t: sum(content.count(k) for k in keys) for t, keys in TYPE_HINTS.items()}
    best = max(scores, key=lambda t: scores[t])
    return best if scores[best] else None


def fix_terms_table(text: str, cfg: dict[str, str]) -> str:
    """非 MCP 类文章:删掉 MCP/索引/Token 这些通用样板行。"""
    text = text.replace(MCP_ROW + "\n", cfg["extra_terms"])
    text = text.replace(INDEX_ROW + "\n", "")
    return text.replace(TOKEN_ROW + "\n", "")


def fix_content(content: str, forced_type: str | None) -> tuple[str, bool, str]:
    if CONTAMINATED_WHY not in content:
        return content, False, "clean"

    kind = forced_type or detect_type(content)
    if kind is None:
        return content, False, "type-unknown"

    cfg = TOOL_CONFIG[kind]
    updated = content.replace(CONTAMINATED_WHY, cfg["why"])
    updated = re.sub(
        r"### 第 3 步：第一次使用\n\n对 Agent 说「请索引这个项目」或按正文案例 [AB] 操作。",
        f"### 第 3 步：第一次使用\n\n{cfg['step3']}",
        updated,
    )
    updated = re.sub(
        r"### 第 4 步：确认成功 ✅\n\n- Settings → MCP 里能看到对应 server 和 tools 数量。\n"
        r"- 对照正文 \*\*案例 A\*\* 的「验收方式」逐项打勾。",
        f"### 第 4 步：确认成功 ✅\n\n{cfg['step4']}",
        updated,
    )
    updated = updated.replace(
        "| Agent 不按 Skill/MCP 走 | 未触发或与其它规则冲突 | 点名正文示例提示词；一次只让一套流程主导 |",
        cfg["stuck2"],
    )
    if kind != "mcp":
        updated = fix_terms_table(updated, cfg)

    return updated, updated != content, kind


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("directory", type=Path, help="存量文章所在目录")
    parser.add_argument("--glob", default="*使用示例*.md", help="文件匹配模式(默认 *使用示例*.md)")
    parser.add_argument("--type", choices=sorted(TOOL_CONFIG), help="强制指定仓库类型,跳过自动推断")
    parser.add_argument("--dry-run", action="store_true", help="只报告,不写盘")
    args = parser.parse_args()

    if not args.directory.is_dir():
        print(f"error: 目录不存在: {args.directory}", file=sys.stderr)
        return 2

    changed, skipped = [], []
    for path in sorted(args.directory.glob(args.glob)):
        text = path.read_text(encoding="utf-8")
        new_text, did, kind = fix_content(text, args.type)
        if did:
            if not args.dry_run:
                path.write_text(new_text, encoding="utf-8")
            changed.append((path.name, kind))
        elif kind == "type-unknown":
            skipped.append(path.name)

    verb = "would fix" if args.dry_run else "fixed"
    print(f"{verb} {len(changed)} file(s):")
    for name, kind in changed:
        print(f"  - [{kind}] {name}")
    if skipped:
        print(f"skipped {len(skipped)} file(s) — 类型无法推断,请加 --type 重跑:", file=sys.stderr)
        for name in skipped:
            print(f"  - {name}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
