#!/usr/bin/env python3
"""Catch judgment rows marked pass without the evidence the skill requires.

Machine rows (4c/4d/4e) can be green while 声纹, 遮名, 信息覆盖抽样, or 原文图 are
rubber-stamped ✅. This check fires when:
  - A judgment row claims ✅ without valid evidence (voice quotes, blind-test 3
    distinct non-reused quotes, 3 coverage anchors, or verified 原文图 counts/captions)
  - Body retains a raw WebFetch `Page image` placeholder
  - An adversarial draft (`争辩型访谈` / `核心冲突` / `原声交锋`) states a false consensus

Usage:
  python check_judgment.py path/to/doc.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FALSE_CONSENSUS = re.compile(r"共识点|达成共识|双方一致|全文共识")
NEGATION = re.compile(r"没有|未|不写|并非|不要|未决")
QUOTE = re.compile(r"「([^」]+)」")
NUMBERED = re.compile(r"^\s*\d+\.\s+\S")
SEPARATOR = re.compile(r"^:?-{3,}:?$")

_BALANCED_PARENS = r"\((?:[^()\n]|\([^()\n]*\))*\)"
_STANDALONE_IMG_RE = re.compile(rf"^!\[[^\]\n]*\]{_BALANCED_PARENS}\s*$")
_STANDALONE_MEDIA_HTML_RE = re.compile(
    r"^<(?:video|img|figure)\b[^>]*>.*$",
    flags=re.IGNORECASE,
)
_INLINE_MD_IMG_RE = re.compile(rf"!\[[^\]\n]*\]{_BALANCED_PARENS}")
_INLINE_HTML_MEDIA_RE = re.compile(r"<(?:video|img)\b[^>]*\bsrc=", flags=re.IGNORECASE)
_CAPTION_BLOCK_RE = re.compile(r"^\*[^*\n]+.*\*\s*$")


def _split_self_check(text: str) -> tuple[str, str]:
    marker = "## 自检报告"
    if marker not in text:
        return text, ""
    body, section = text.split(marker, 1)
    return body, section


def _strip_fences(text: str) -> str:
    out: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        if fence is not None:
            closer = rf"^\s*{re.escape(fence[0])}{{{len(fence)},}}\s*$"
            if re.match(closer, line):
                fence = None
            continue
        m = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
            fence = m.group(1)
            continue
        out.append(line)
    return "\n".join(out)


def _is_adversarial(body: str, section: str) -> bool:
    """False-consensus prohibition applies only to 争辩型访谈 / 原声增强 drafts."""
    return bool(
        "争辩型" in body
        or "争辩结构" in section
        or re.search(r">\s*\*\*核心冲突\*\*", body)
        or "### 原声交锋" in body
    )


def _outside_quotes(text: str) -> str:
    return re.sub(r"「[^」]*」", "", text)


def _consensus_hits(text: str) -> list[str]:
    hits: list[str] = []
    cleaned = _outside_quotes(_strip_fences(text))
    for sent in re.split(r"[。！？\n；;]", cleaned):
        snippet = sent.strip()
        if snippet and FALSE_CONSENSUS.search(snippet) and not NEGATION.search(snippet):
            hits.append(snippet[:40])
    return hits


def _table_rows(section: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    started = False
    for line in section.splitlines():
        if not line.startswith("|"):
            if started:
                break
            continue
        started = True
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0] in {"检查项", "a"} or SEPARATOR.match(cells[0]):
            continue
        note = cells[2] if len(cells) > 2 else ""
        rows.append((cells[0], cells[1], note))
    return rows


def _passed(result: str) -> bool:
    return "✅" in result and "不适用" not in result


def _subsection(section: str, heading: str) -> str:
    match = re.search(rf"###[^\n]*{re.escape(heading)}[^\n]*\n", section)
    if not match:
        return ""
    rest = section[match.end() :]
    nxt = re.search(r"\n### |\n\*文档生成时间", rest)
    return rest if nxt is None else rest[: nxt.start()]


def _norm_quote(s: str) -> str:
    """Normalize inline Markdown emphasis so bolded body quotes match plain citations."""
    return re.sub(r"\*\*|\*|`", "", s).strip()


def _quotes_missing_from_body(quotes: list[str], norm_body: str) -> list[str]:
    missing: list[str] = []
    for quote in quotes:
        nq = _norm_quote(quote)
        if nq and nq not in norm_body:
            missing.append(nq[:24])
    return missing


def count_body_media(body: str) -> tuple[int, int]:
    """Return (embedded_media_count, uncaptioned_standalone_count) in unfenced body."""
    unfenced = _strip_fences(body)
    # Strip metadata / TOC preamble if 目录 exists so only article body is counted
    content = unfenced.split("## 目录", 1)[1] if "## 目录" in unfenced else unfenced
    content = content.split("## 延伸术语表", 1)[0]

    blocks = [b.strip() for b in content.split("\n\n") if b.strip()]
    standalone_count = 0
    uncaptioned = 0
    inline_extra = 0
    for idx, blk in enumerate(blocks):
        lines = [ln.strip() for ln in blk.splitlines() if ln.strip()]
        if len(lines) == 1 and (
            _STANDALONE_IMG_RE.match(lines[0])
            or _STANDALONE_MEDIA_HTML_RE.match(lines[0])
        ):
            standalone_count += 1
            has_inline_figcaption = "<figcaption" in lines[0].lower()
            nxt = blocks[idx + 1] if idx + 1 < len(blocks) else ""
            nxt_lines = [ln.strip() for ln in nxt.splitlines() if ln.strip()]
            has_next_caption = (
                len(nxt_lines) == 1 and bool(_CAPTION_BLOCK_RE.match(nxt_lines[0]))
            )
            if not (has_inline_figcaption or has_next_caption):
                uncaptioned += 1
        else:
            inline_extra += len(_INLINE_MD_IMG_RE.findall(blk))
            inline_extra += len(_INLINE_HTML_MEDIA_RE.findall(blk))
    return standalone_count + inline_extra, uncaptioned


def _check_media_row(note: str, actual_media: int, uncaptioned: int) -> list[str]:
    errs: list[str] = []
    clean_note = note.strip()
    if "不适用" in clean_note:
        return errs
    if not clean_note:
        return ["原文图标了通过，但备注为空（须写明源页/候选张数与稿内张数）"]
    if re.search(r"(?:^|[；;，,\s])(?:无统计图|没有统计图)(?:[。；;，,\s]|$)", clean_note):
        errs.append("原文图只写「无统计图」不能算通过（须核对示意图、插画与视频关键画面）")

    matched_schema = False
    # Schema 1: 源页(正文) N 张，稿内 K 张
    m_pair = re.search(
        r"源页(?:正文)?\s*(\d+)\s*张[，,、;；\s]*稿内\s*(\d+)\s*张",
        clean_note,
    )
    if m_pair:
        matched_schema = True
        src_n, draft_n = int(m_pair.group(1)), int(m_pair.group(2))
        if src_n != draft_n and "剔除" not in clean_note and "未取得" not in clean_note:
            errs.append(
                f"原文图标了通过，但源页 {src_n} 张与稿内 {draft_n} 张不一致"
            )
        if draft_n != actual_media:
            errs.append(
                f"原文图声称稿内 {draft_n} 张，但正文实际检出 {actual_media} 处媒体嵌入"
            )

    # Schema 2: 候选 M 处：外链保留 K 张 + 剔除装饰噪音 D 处
    m_cand = re.search(
        r"候选\s*(\d+)\s*[处张].*?(?:外链)?保留\s*(\d+)\s*张.*?剔除[^\d]*(\d+)\s*[处张]",
        clean_note,
    )
    if m_cand:
        matched_schema = True
        total_m, keep_k, drop_d = (
            int(m_cand.group(1)),
            int(m_cand.group(2)),
            int(m_cand.group(3)),
        )
        if total_m != keep_k + drop_d:
            errs.append(
                f"原文图候选清点相加不一致（候选 {total_m} != 保留 {keep_k} + 剔除 {drop_d}）"
            )
        if keep_k != actual_media:
            errs.append(
                f"原文图声称保留 {keep_k} 张，但正文实际检出 {actual_media} 处媒体嵌入"
            )

    # Schema 3: 关键画面 M 处：同源外链 K1 张 + 内联重构 K2 处 + 视觉盲区 K3 处
    m_video = re.search(
        r"关键画面\s*(\d+)\s*处.*?外链\s*(\d+)\s*张.*?内联重构\s*(\d+)\s*处.*?视觉盲区\s*(\d+)\s*处",
        clean_note,
    )
    if m_video:
        matched_schema = True
        total_m, k1, k2, k3 = (
            int(m_video.group(1)),
            int(m_video.group(2)),
            int(m_video.group(3)),
            int(m_video.group(4)),
        )
        if total_m != k1 + k2 + k3:
            errs.append(
                f"原文图关键画面清点相加不一致（{total_m} != {k1}+{k2}+{k3}）"
            )
        if k1 != actual_media:
            errs.append(
                f"原文图声称同源外链 {k1} 张，但正文实际检出 {actual_media} 处媒体嵌入"
            )

    if not matched_schema:
        m_fallback = re.search(r"(?:稿内|外链(?:保留)?)\s*(\d+)\s*张", clean_note)
        if m_fallback:
            claimed = int(m_fallback.group(1))
            if claimed != actual_media:
                errs.append(
                    f"原文图声称 {claimed} 张，但正文实际检出 {actual_media} 处媒体嵌入"
                )
        else:
            errs.append(
                "原文图标了通过，但备注未按规范写出「源页 N 张，稿内 N 张」或候选/关键画面清点数"
            )

    if actual_media > 0 and uncaptioned > 0:
        errs.append(
            f"原文图标了通过，但正文有 {uncaptioned} 处独立图片/视频缺少紧邻斜体图注"
        )
    return errs


def issues(text: str) -> list[str]:
    body, section = _split_self_check(text)
    found: list[str] = []

    if re.search(r"^\s*Page image\s*$", _strip_fences(body), flags=re.M):
        found.append("正文残留 WebFetch 的 Page image 占位行，图片清单未完成")

    adversarial = _is_adversarial(body, section)
    if adversarial:
        for snippet in _consensus_hits(body):
            found.append(f"正文写出假共识「{snippet}」")

    if not section:
        return found

    rows = _table_rows(section)
    norm_body = _norm_quote(body)
    actual_media, uncaptioned = count_body_media(body)

    voice_passed = any(_passed(result) and "声纹" in name for name, result, _ in rows)
    blind_passed = any(_passed(result) and "遮名" in name for name, result, _ in rows)
    coverage_passed = any(
        _passed(result) and "覆盖抽样" in name for name, result, _ in rows
    )

    for name, result, note in rows:
        if not _passed(result):
            continue
        if adversarial:
            for snippet in _consensus_hits(f"{name} {note}"):
                found.append(f"自检通过项写出假共识「{snippet}」")
        if "原文图" in name or "视觉资产" in name:
            found.extend(_check_media_row(note, actual_media, uncaptioned))

    voice_block = _subsection(section, "人物声纹")
    voice_quotes_raw = QUOTE.findall(voice_block)
    voice_quotes_norm = {_norm_quote(q) for q in voice_quotes_raw if _norm_quote(q)}

    if voice_passed:
        if not voice_quotes_raw:
            found.append("人物声纹标了通过，但没有「成稿原句」")
        else:
            missing = _quotes_missing_from_body(voice_quotes_raw, norm_body)
            if missing:
                found.append("人物声纹的原句不在正文：" + "、".join(missing))

    if voice_passed or blind_passed:
        blind_block = _subsection(section, "遮名检验")
        lines = [line for line in blind_block.splitlines() if "「" in line and "→" in line]
        if len(lines) < 3:
            found.append(
                f"遮名检验只有 {len(lines)} 句（声纹或遮名已标通过，需要前/中/后 3 句）"
            )
        else:
            blind_quotes_raw = [q for ln in lines for q in QUOTE.findall(ln)]
            missing = _quotes_missing_from_body(blind_quotes_raw, norm_body)
            if missing:
                found.append("遮名原句不在正文：" + "、".join(missing))
            blind_norm = [_norm_quote(q) for q in blind_quotes_raw if _norm_quote(q)]
            if len(set(blind_norm)) < 3:
                found.append("遮名检验存在重复原句（须从前/中/后抽 3 句互不相同的原句）")
            reused = sorted(set(blind_norm) & voice_quotes_norm)
            if reused:
                found.append(
                    "遮名检验复用了人物声纹证据句（须避开已用作声纹的句子）："
                    + "、".join(q[:20] for q in reused)
                )

    if coverage_passed:
        cov_block = _subsection(section, "信息覆盖抽样")
        anchors = [line for line in cov_block.splitlines() if NUMBERED.match(line)]
        if len(anchors) < 3:
            found.append(f"信息覆盖抽样标了通过，但只有 {len(anchors)} 个锚点")
    return found


def format_row(found: list[str]) -> str:
    if not found:
        return "| 判断行证据 | ✅ | 声纹、遮名、覆盖抽样、原文图的通过标记有证据；无假共识 |"
    return "| 判断行证据 | ⚠️ | " + "；".join(found) + " |"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Check rubber-stamped judgment rows")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    found = issues(args.path.read_text(encoding="utf-8"))
    print(format_row(found))
    for item in found:
        print(f"  - {item}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
