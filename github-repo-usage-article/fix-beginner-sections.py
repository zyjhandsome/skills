#!/usr/bin/env python3
"""Fix cross-article MCP template contamination in legacy 新手专区 sections (deprecated section;存量修稿用)."""

from __future__ import annotations

import re
from pathlib import Path

ARTICLE_DIR = Path(r"d:\Hzhao\00 赵一纯 Obsidian\05 AI（人工智能）\13 AI GitHub精选仓库收藏&使用示例&已安装Skills")

# Skip fully rewritten articles
SKIP = {"Spec-Kit 使用示例 · 实时同声传译桌面应用.md", "Codebase Memory MCP 使用示例 · 单二进制本地知识图谱让代理结构查询省 99% Token.md"}

CONTAMINATED_WHY = (
    "**为什么要用它？** 没有本地图谱时，AI 只能反复打开文件「翻书」——慢、费 Token。接上 MCP 后先建地图，结构题直接查图。"
)

MCP_ROW = "| **MCP** | 给 AI 装「标准插座」的插件协议 | 手机 USB 接口 |"
INDEX_ROW = "| **索引** | 把项目扫描一遍、建本地「地图」 | 图书馆编目 |"

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
        "stuck2": "| 命令找不到 | PATH 未刷新或未重装 | 重启终端；按 **§ 九、常见坑** 检查安装路径 |",
    },
    "rules": {
        "extra_terms": "| **Rules** | 写进项目的持久约束，每次对话自动加载 | 员工手册 |\n",
        "why": "**为什么要用它？** 没有项目规则时，Agent 每次会话都「失忆」，风格与约束不一致。规则文件让行为可复用、可版本管理。",
        "step3": "把规则文件复制到项目 `.cursor/rules/`（或宿主对应目录），新开 Agent 对话测试。",
        "step4": "- 新对话中 Agent 行为符合规则描述（见 **案例 A** 验收项）。\n- 对照正文 **案例 A** 的「验收方式」逐项打勾。",
        "stuck2": "| 规则不生效 | 路径错误或 glob 未匹配 | 查宿主文档中 rules 目录与 `alwaysApply` 设置 |",
    },
}

FILE_TYPE: dict[str, str] = {
    "CodeGraph": "mcp",
    "Understand Anything": "mcp",
    "Browser-Harness": "mcp",
    "Ruflo": "mcp",
    "Superpowers": "skills",
    "Karpathy Skills": "skills",
    "Spec-Kit": "skills",
    "Agent Skills": "skills",
    "Matt Pocock": "skills",
    "LJG-Skills": "skills",
    "Taste Skill": "skills",
    "GStack": "skills",
    "md2html": "skills",
    "AnySearch Skill": "skills",
    "Agency Agents": "skills",
    "Everything-Claude-Code": "skills",
    "Awesome-CursorRules": "rules",
    "Awesome DESIGN": "rules",
    "Google DESIGN": "rules",
    "MarkItDown": "cli",
    "TrendRadar": "cli",
    "Multica": "cli",
    "Paseo": "cli",
    "PraisonAI": "cli",
    "CrewAI": "cli",
    "AutoGen": "cli",
    "OpenHuman": "cli",
}


def detect_tool_name(content: str, filename: str) -> str:
    m = re.match(r"# (.+?) 使用示例", content)
    return m.group(1) if m else filename.split(" 使用示例")[0]


def detect_type(tool: str) -> str:
    for key, t in FILE_TYPE.items():
        if key in tool:
            return t
    return "skills"


def fix_terms_table(text: str, cfg: dict[str, str], tool: str) -> str:
    """Replace MCP/index rows when not MCP type."""
    if cfg is TOOL_CONFIG["mcp"]:
        return text

    # Remove generic MCP/index/token boilerplate rows; keep host + tool rows
    text = text.replace(MCP_ROW + "\n", cfg["extra_terms"])
    text = text.replace(INDEX_ROW + "\n", "")
    token_row = "| **Token** | 发给 AI 的「字数额度」，读文件越多越贵 | 手机流量 |"
    if "Token" in text and cfg is not TOOL_CONFIG["mcp"]:
        text = text.replace(token_row + "\n", "")

    # Ensure tool row exists
    tool_row = f"| **{tool.split()[0]}** | 本文主角：见文首电梯简介 | 见案例背景 |"
    if "本文主角" not in text:
        pass  # already has tool-specific row
    return text


def fix_beginner_section(content: str, filename: str) -> tuple[str, bool]:
    if filename in SKIP:
        return content, False
    if CONTAMINATED_WHY not in content:
        return content, False

    tool = detect_tool_name(content, filename)
    t = detect_type(tool)
    cfg = TOOL_CONFIG[t]

    updated = content.replace(CONTAMINATED_WHY, cfg["why"])

    updated = re.sub(
        r"### 第 3 步：第一次使用\n\n对 Agent 说「请索引这个项目」或按正文案例 [AB] 操作。",
        f"### 第 3 步：第一次使用\n\n{cfg['step3']}",
        updated,
    )

    updated = re.sub(
        r"### 第 4 步：确认成功 ✅\n\n- Settings → MCP 里能看到对应 server 和 tools 数量。\n- 对照正文 \*\*案例 A\*\* 的「验收方式」逐项打勾。",
        f"### 第 4 步：确认成功 ✅\n\n{cfg['step4']}",
        updated,
    )

    if cfg["stuck2"]:
        updated = updated.replace(
            "| Agent 不按 Skill/MCP 走 | 未触发或与其它规则冲突 | 点名正文示例提示词；一次只让一套流程主导 |",
            cfg["stuck2"],
        )

    updated = fix_terms_table(updated, cfg, tool)

    # Fix broken anchor: 仓库 Skills 一览 → 仓库能力入口一览 when section missing
    if "## 仓库能力入口一览" not in updated and "## 仓库 Skills 一览" in updated:
        updated = updated.replace(
            "[仓库能力入口一览](#仓库能力入口一览) 或 [仓库 Skills 一览](#仓库-skills-一览)",
            "[仓库 Skills 一览](#仓库-skills-一览)",
        )

    return updated, updated != content


def main() -> None:
    changed = []
    for path in sorted(ARTICLE_DIR.glob("*使用示例*.md")):
        text = path.read_text(encoding="utf-8")
        new_text, did = fix_beginner_section(text, path.name)
        if did:
            path.write_text(new_text, encoding="utf-8")
            changed.append(path.name)
    print(f"Fixed {len(changed)} files:")
    for name in changed:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
