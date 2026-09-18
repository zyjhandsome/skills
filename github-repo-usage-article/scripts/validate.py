#!/usr/bin/env python3
"""校验一篇「使用示例」成稿是否满足 SKILL.md 的机械可判规则。

用法:
    python validate.py <文章.md> [更多文章.md ...]
    python validate.py <目录>                    # 校验目录下所有 *使用示例*.md
    python validate.py <文章.md> --type cli      # 显式指定仓库类型,加严反污染检查
    python validate.py <文章.md> --quiet         # 只输出 ERROR

退出码: 0 = 无 ERROR(可能有 WARN);1 = 有 ERROR;2 = 用法错误。

只判「机械可判」的规则。风格、覆盖度典型性、角色是否雷同等需人工判断的项,
见 SKILL.md 的「人工判断清单」。
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- 基础设施

FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CASE_RE = re.compile(r"^##\s+案例\s+([A-Z])\b")


@dataclass
class Line:
    no: int
    text: str
    in_fence: bool
    fence_lang: str = ""


@dataclass
class Report:
    path: Path
    errors: list[str] = field(default_factory=list)
    warns: list[str] = field(default_factory=list)

    def error(self, msg: str, lineno: int | None = None) -> None:
        self.errors.append(f"{self.path.name}:{lineno or '-'}: ERROR {msg}")

    def warn(self, msg: str, lineno: int | None = None) -> None:
        self.warns.append(f"{self.path.name}:{lineno or '-'}: WARN  {msg}")


def parse_lines(text: str) -> list[Line]:
    """标注每行是否位于代码围栏内,避免把代码/示例误判成正文。"""
    out: list[Line] = []
    in_fence = False
    lang = ""
    in_comment = False
    for i, raw in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(raw):
            if in_fence:
                in_fence, lang = False, ""
                out.append(Line(i, raw, True))
            else:
                in_fence = True
                lang = raw.strip().lstrip("`~").strip().lower()
                out.append(Line(i, raw, True, lang))
            continue
        # HTML 注释(写作提示)同样不算正文
        if not in_fence and "<!--" in raw:
            in_comment = "-->" not in raw
            out.append(Line(i, raw, True))
            continue
        if in_comment:
            if "-->" in raw:
                in_comment = False
            out.append(Line(i, raw, True))
            continue
        out.append(Line(i, raw, in_fence, lang if in_fence else ""))
    return out


def heading_to_slug(title: str) -> str:
    """与 fix-wikilink-anchors.py 保持一致的 slug 规则。"""
    slug = title.strip().lower()
    slug = slug.replace(" · ", "--").replace(" + ", "--").replace("&", "--")
    for ch in "（）()·:：,，":
        slug = slug.replace(ch, "")
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-{3,}", "--", slug)
    return slug.strip("-")


# ---------------------------------------------------------------- 规则定义

# 骨架必需区块:(展示名, 匹配正则) —— 缺一即 ERROR
REQUIRED_BLOCKS: list[tuple[str, re.Pattern[str]]] = [
    ("文章标题 H1 + 使用示例", re.compile(r"^#\s+.*使用示例")),
    ("仓库能力入口一览", re.compile(r"^##\s+仓库(能力入口|\s*Skills)\s*一览")),
    ("0. 案例背景", re.compile(r"^##\s+0\.\s*案例背景")),
    ("0.2 要不要一上来全量使用", re.compile(r"^##\s+0\.2\s")),
    ("0.3 功能覆盖索引", re.compile(r"^##\s+0\.3\s")),
    ("关键收益总结 master 表", re.compile(r"^##\s+关键收益总结")),
    ("常见坑", re.compile(r"^##\s+常见坑")),
    ("实操检查清单", re.compile(r"^##\s+实操检查清单")),
    ("底层逻辑", re.compile(r"^##\s+底层逻辑")),
    ("参考链接", re.compile(r"^##\s+参考链接")),
]

# 案例六件套:(字段名, 匹配正则)
SIX_PACK: list[tuple[str, re.Pattern[str]]] = [
    ("场景", re.compile(r"^>\s*\*{0,2}场景")),
    ("角色", re.compile(r"^\*\*角色\*\*")),
    ("怎么用", re.compile(r"^\*\*怎么用")),
    ("你会看到什么", re.compile(r"^\*\*你会看到什么")),
    ("效果", re.compile(r"^\*\*效果")),
    ("实操卡", re.compile(r"^\*\*实操卡\*\*")),
]

CARD_FIELDS = ("前置条件", "可执行步骤", "验收方式", "失败处理", "风险边界")

MCP_ONLY_PHRASES = ("请索引这个项目", "Settings → MCP", "接上 MCP 后先建地图", "Index this project")

# 易漂移的精确数字(正文里不该出现,应改徽章或定性词)
VOLATILE_RE = [
    (re.compile(r"⭐"), "手写 Star 标记"),
    (re.compile(r"\d[\d,.]*\s*[kKmM]?\+?\s*Stars?\b"), "手写 Star 数"),
    (re.compile(r"\d[\d,.]*\s*[kKmM]\+?\s*(?:次)?(?:安装|下载)"), "手写安装/下载量"),
    (re.compile(r"\d[\d,.]*\s*Forks?\b"), "手写 Fork 数"),
]

ORDINAL_HEADING_RE = re.compile(r"^#{2,6}\s*[一二三四五六七八九十]+\s*[、·.]")
STALE_XREF_RE = re.compile(r"[§第]\s*[一二三四五六七八九十]+\s*[、·]")
WIKILINK_RE = re.compile(r"\[\[")
ANCHOR_RE = re.compile(r"\]\(#([^)]+)\)")
MERMAID_UNQUOTED_RE = re.compile(r"[A-Za-z_][\w]*\[(?!\")[^\]\"]*[（）()][^\]\"]*\]")
VERSION_RE = re.compile(r"\bv\d+\.\d+(?:\.\d+)?\b")


# ---------------------------------------------------------------- 各项检查


def check_required_blocks(lines: list[Line], rep: Report) -> None:
    body = [ln for ln in lines if not ln.in_fence]
    for name, pattern in REQUIRED_BLOCKS:
        if not any(pattern.match(ln.text) for ln in body):
            rep.error(f"缺少必需区块「{name}」")
    if not any(CASE_RE.match(ln.text) for ln in body):
        rep.error("缺少任何「## 案例 X」小节")


def check_no_ordinal_headings(lines: list[Line], rep: Report) -> None:
    for ln in lines:
        if ln.in_fence:
            continue
        if ORDINAL_HEADING_RE.match(ln.text):
            rep.error(f"正文小节标题带中文序数(应去序数):{ln.text.strip()}", ln.no)
        if re.match(r"^##\s+新手专区", ln.text):
            rep.error("出现已废弃的「新手专区」(安装与首次验收应写进案例 A)", ln.no)
        if ln.text.startswith("# ") and "使用示例" not in ln.text:
            # 正文里的野生 H1(常见:代码块泄漏的 "# 带 UI:")
            rep.error(f"正文出现额外 H1(常见为代码块泄漏):{ln.text.strip()[:60]}", ln.no)


def check_no_wikilinks(lines: list[Line], rep: Report) -> None:
    for ln in lines:
        if ln.in_fence:
            continue
        if WIKILINK_RE.search(ln.text):
            rep.error(f"出现 [[双链]](应改标准 Markdown 链接或纯文本):{ln.text.strip()[:60]}", ln.no)


def check_stale_xrefs(lines: list[Line], rep: Report) -> None:
    for ln in lines:
        if ln.in_fence:
            continue
        m = STALE_XREF_RE.search(ln.text)
        if m:
            rep.error(f"按序数的交叉引用(应改名称/案例字母):{m.group(0)}", ln.no)


def check_anchors(lines: list[Line], rep: Report) -> None:
    slugs = {
        heading_to_slug(m.group(2))
        for ln in lines
        if not ln.in_fence and (m := HEADING_RE.match(ln.text))
    }
    for ln in lines:
        if ln.in_fence:
            continue
        for m in ANCHOR_RE.finditer(ln.text):
            target = m.group(1).strip().lower()
            if target not in slugs:
                rep.error(f"文内锚点跳不到任何标题:#{m.group(1)}", ln.no)


def check_cases(lines: list[Line], rep: Report) -> None:
    body = [ln for ln in lines if not ln.in_fence]
    starts = [(i, m.group(1), ln.no) for i, ln in enumerate(body) if (m := CASE_RE.match(ln.text))]
    for idx, (pos, letter, lineno) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(body)
        chunk = body[pos:end]
        for name, pattern in SIX_PACK:
            if not any(pattern.match(c.text) for c in chunk):
                rep.error(f"案例 {letter} 缺六件套字段「{name}」", lineno)
        # 「你会看到什么」必须标示例/示意
        for c in chunk:
            if c.text.startswith("**你会看到什么") and not re.search(r"示例|示意", c.text):
                rep.error(f"案例 {letter} 的「你会看到什么」未标注「示例/示意」", c.no)
        # 场景与角色不得雷同(去掉标记后逐字比较)
        scene = next((c.text for c in chunk if SIX_PACK[0][1].match(c.text)), "")
        role = next((c.text for c in chunk if SIX_PACK[1][1].match(c.text)), "")
        norm = lambda s: re.sub(r"[>*\s]|场景|角色|[:：]", "", s)
        if scene and role and norm(scene) == norm(role):
            rep.error(f"案例 {letter} 的「角色」与「场景」逐字雷同", lineno)


def check_action_cards(lines: list[Line], rep: Report) -> None:
    """实操卡在 ```text 块里,逐块核对五字段。"""
    blocks: list[tuple[int, list[str]]] = []
    collecting = False
    pending = False
    current: list[str] = []
    start = 0
    for ln in lines:
        if not ln.in_fence and ln.text.startswith("**实操卡**"):
            pending = True
            continue
        if pending and FENCE_RE.match(ln.text):
            collecting, pending = True, False
            start = ln.no
            current = []
            continue
        if collecting:
            if FENCE_RE.match(ln.text):
                blocks.append((start, current))
                collecting = False
            else:
                current.append(ln.text)
    if collecting:
        blocks.append((start, current))

    for start, block in blocks:
        joined = "\n".join(block)
        missing = [f for f in CARD_FIELDS if f not in joined]
        if missing:
            rep.error(f"实操卡缺字段:{'、'.join(missing)}", start)


def check_contamination(lines: list[Line], repo_type: str | None, rep: Report) -> None:
    if repo_type == "mcp":
        return
    text = "\n".join(ln.text for ln in lines)
    hits = [p for p in MCP_ONLY_PHRASES if p in text]
    if not hits:
        return
    if repo_type is None:
        # 未声明类型:若通篇没有 MCP 仓的其它证据,视为模板污染
        looks_mcp = any(k in text for k in ("MCP Server", "mcpServers", "MCP 工具清单", "tools 数量"))
        if looks_mcp:
            return
        rep.warn(f"出现 MCP 专属表述 {hits};若本仓不是 MCP Server 即为模板污染(可用 --type 确认)")
        return
    for ln in lines:
        for phrase in hits:
            if phrase in ln.text:
                rep.error(f"非 MCP 仓({repo_type})出现 MCP 专属表述:{phrase}", ln.no)
                break


def check_volatile_numbers(lines: list[Line], rep: Report) -> None:
    for ln in lines:
        if ln.in_fence:
            continue
        if "img.shields.io" in ln.text or "skills.sh/b/" in ln.text:
            continue  # 徽章行本身允许
        for pattern, label in VOLATILE_RE:
            m = pattern.search(ln.text)
            if m:
                rep.error(f"{label}(应改自动同步徽章或定性词):{m.group(0)}", ln.no)


def check_versions(lines: list[Line], rep: Report) -> None:
    hits = [(ln.no, m.group(0)) for ln in lines for m in [VERSION_RE.search(ln.text)] if m]
    if len(hits) > 2:
        spots = "、".join(f"L{no}:{v}" for no, v in hits)
        rep.warn(f"版本号在 {len(hits)} 处出现(应收敛到案例 A 与校验脚注两处):{spots}")


def check_mermaid(lines: list[Line], rep: Report) -> None:
    in_mermaid = False
    seen = 0
    for ln in lines:
        if FENCE_RE.match(ln.text):
            if ln.fence_lang.startswith("mermaid"):
                in_mermaid = True
                seen += 1
            elif in_mermaid:
                in_mermaid = False
            continue
        if in_mermaid and MERMAID_UNQUOTED_RE.search(ln.text):
            rep.warn(f"mermaid 标签含括号但未加引号,可能渲染失败:{ln.text.strip()[:60]}", ln.no)
    if seen == 0:
        rep.warn("全文没有 mermaid 架构原理图")


def check_footer(lines: list[Line], rep: Report) -> None:
    if not any("本文校验" in ln.text for ln in lines if not ln.in_fence):
        rep.error("文末缺少「本文校验」脚注(日期 + 对照来源)")


def check_badges(lines: list[Line], rep: Report) -> None:
    if not any("img.shields.io" in ln.text or "skills.sh/b/" in ln.text for ln in lines):
        rep.warn("未使用自动同步徽章(Stars/release/安装量),建议在电梯简介后补一行")


# ---------------------------------------------------------------- 入口


def validate(path: Path, repo_type: str | None) -> Report:
    rep = Report(path)
    lines = parse_lines(path.read_text(encoding="utf-8"))
    check_required_blocks(lines, rep)
    check_no_ordinal_headings(lines, rep)
    check_no_wikilinks(lines, rep)
    check_stale_xrefs(lines, rep)
    check_anchors(lines, rep)
    check_cases(lines, rep)
    check_action_cards(lines, rep)
    check_contamination(lines, repo_type, rep)
    check_volatile_numbers(lines, rep)
    check_versions(lines, rep)
    check_mermaid(lines, rep)
    check_footer(lines, rep)
    check_badges(lines, rep)
    return rep


def collect(targets: list[Path]) -> list[Path]:
    out: list[Path] = []
    for t in targets:
        if t.is_dir():
            out.extend(sorted(t.glob("*使用示例*.md")))
        elif t.is_file():
            out.append(t)
        else:
            print(f"error: 找不到 {t}", file=sys.stderr)
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("targets", nargs="+", type=Path, help="文章文件或目录")
    parser.add_argument("--type", choices=("mcp", "cli", "skills", "rules", "flow-cli", "lib"), help="仓库类型,用于加严反污染检查")
    parser.add_argument("--quiet", action="store_true", help="只打印 ERROR")
    args = parser.parse_args()

    files = collect(args.targets)
    if not files:
        print("error: 没有可校验的文件", file=sys.stderr)
        return 2

    total_err = 0
    for path in files:
        rep = validate(path, args.type)
        total_err += len(rep.errors)
        for msg in rep.errors:
            print(msg)
        if not args.quiet:
            for msg in rep.warns:
                print(msg)
        status = "FAIL" if rep.errors else "PASS"
        print(f"{status}  {path.name}  ({len(rep.errors)} error, {len(rep.warns)} warn)\n")

    print(f"共 {len(files)} 篇,{total_err} 个 ERROR。" + ("" if total_err else " 机械项全部通过。"))
    return 1 if total_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
