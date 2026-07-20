#!/usr/bin/env python3
"""Patch md2html-lecture HTML/CSS for key-info emphasis hierarchy.

Idempotent: skips files that already contain the Key-info mark comment.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "Key-info mark: soft accent chip"

OLD_STRONG = """    .content strong { color: var(--text); font-weight: 600; }
    .content em { color: var(--text-muted); }
    .content hr { border: none; border-top: 1px solid var(--border); margin: 40px 0; }"""

NEW_STRONG = """    /* Key-info mark: soft accent chip — not link-blue, keeps hierarchy with tip/highlight */
    .content strong {
      color: var(--accent-strong);
      font-weight: 700;
      background: var(--accent-soft);
      padding: 0.08em 0.32em;
      margin: 0 0.04em;
      border-radius: 4px;
      border: 1px solid transparent;
      box-decoration-break: clone;
      -webkit-box-decoration-break: clone;
    }
    /* Keep names / dialogue quotes calm — emphasis belongs to thesis & analysis */
    .speaker-bio strong,
    .timeline strong,
    .callout-info strong {
      color: var(--text);
      font-weight: 600;
      background: transparent;
      padding: 0;
      margin: 0;
      border: none;
    }
    .content em { color: var(--text-muted); }
    .content hr { border: none; border-top: 1px solid var(--border); margin: 40px 0; }"""

OLD_HIGHLIGHT = """    .highlight {
      background: linear-gradient(135deg, var(--accent-soft), var(--surface-2));
      border-left: 4px solid var(--accent);
      padding: 18px 22px;
      border-radius: 0 var(--radius) var(--radius) 0;
      margin: 24px 0;
      font-size: 16px;
      line-height: 1.65;
      max-width: var(--measure);
    }
    .highlight-label {
      display: inline-block;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--accent-strong);
      margin-bottom: 6px;
    }"""

NEW_HIGHLIGHT = """    .highlight {
      position: relative;
      background: linear-gradient(135deg, var(--accent-soft) 0%, var(--surface) 55%, var(--surface-2) 100%);
      border: 1px solid var(--accent-border);
      border-left: 5px solid var(--accent);
      padding: 20px 24px 20px 22px;
      border-radius: 0 var(--radius) var(--radius) 0;
      margin: 24px 0;
      font-size: 17px;
      font-weight: 500;
      line-height: 1.65;
      max-width: var(--measure);
      box-shadow: 0 1px 0 rgba(217, 119, 87, 0.08), var(--shadow);
      color: var(--text);
    }
    .highlight::before {
      content: "全文论点";
      display: inline-block;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--accent-strong);
      background: var(--surface);
      border: 1px solid var(--accent-border);
      border-radius: 999px;
      padding: 2px 10px;
      margin: 0 0 10px;
    }
    .highlight p { margin: 0; }
    .highlight strong {
      color: var(--accent-strong);
      font-weight: 700;
      background: color-mix(in srgb, var(--accent-soft) 70%, var(--surface));
      border: 1px solid var(--accent-border);
    }
    .highlight-label {
      display: inline-block;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--accent-strong);
      margin-bottom: 6px;
    }"""

OLD_INSIGHT = """    .section-insight { margin-top: 12px; margin-bottom: 20px; }
    .section-insight .callout-body p { margin: 0; }"""

NEW_INSIGHT = """    .section-insight {
      margin-top: 12px;
      margin-bottom: 20px;
      border-left: 4px solid var(--accent);
      box-shadow: 0 1px 0 rgba(217, 119, 87, 0.06), var(--shadow-sm);
      padding: 16px 18px 16px 16px;
      font-size: 15.5px;
      font-weight: 500;
    }
    .section-insight .callout-body p { margin: 0; }
    .section-insight .callout-icon {
      color: var(--accent);
      width: 22px;
      height: 22px;
    }
    .section-insight .callout-body {
      color: var(--text);
    }
    .section-insight strong {
      color: var(--accent-strong);
      font-weight: 700;
      background: color-mix(in srgb, var(--surface) 55%, var(--accent-soft));
      border: 1px solid var(--accent-border);
    }
    [data-theme="dark"] .highlight {
      box-shadow: 0 1px 0 rgba(232, 149, 114, 0.12), var(--shadow);
    }
    [data-theme="dark"] .section-insight {
      box-shadow: 0 1px 0 rgba(232, 149, 114, 0.10), var(--shadow-sm);
    }"""


def patch_text(text: str) -> tuple[str, list[str]]:
    applied: list[str] = []
    if MARKER in text:
        return text, ["already-patched"]
    for name, old, new in (
        ("strong", OLD_STRONG, NEW_STRONG),
        ("highlight", OLD_HIGHLIGHT, NEW_HIGHLIGHT),
        ("insight", OLD_INSIGHT, NEW_INSIGHT),
    ):
        if old not in text:
            applied.append(f"missing-{name}")
            continue
        text = text.replace(old, new, 1)
        applied.append(f"ok-{name}")
    return text, applied


def patch_file(path: Path) -> str:
    original = path.read_text(encoding="utf-8")
    updated, status = patch_text(original)
    if status == ["already-patched"]:
        return f"SKIP  {path}"
    if updated == original:
        return f"FAIL  {path} ({', '.join(status)})"
    if not any(s.startswith("ok-") for s in status):
        return f"FAIL  {path} ({', '.join(status)})"
    path.write_text(updated, encoding="utf-8", newline="\n")
    return f"OK    {path} ({', '.join(status)})"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: patch_key_emphasis.py <file-or-dir> [<file-or-dir> ...]")
        return 2
    paths: list[Path] = []
    for arg in argv[1:]:
        p = Path(arg)
        if p.is_dir():
            paths.extend(sorted(p.rglob("*.html")))
        elif p.is_file():
            paths.append(p)
        else:
            print(f"MISS  {p}")
    ok = fail = skip = 0
    for path in paths:
        line = patch_file(path)
        print(line)
        if line.startswith("OK"):
            ok += 1
        elif line.startswith("SKIP"):
            skip += 1
        else:
            fail += 1
    print(f"\nDone: ok={ok} skip={skip} fail={fail} total={len(paths)}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
