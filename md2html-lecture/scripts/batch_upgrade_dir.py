#!/usr/bin/env python3
"""Batch-upgrade lecture HTML with the latest md2html-lecture template.

For each *_整理文档.html that has a sibling .md:
  1. Extract hand-added Mermaid <figure class="diagram"> blocks (keyed by preceding h2)
  2. Re-run build_html.py
  3. Re-inject diagrams + generic speaker tags + light bio italic fix
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_BUILD = Path(__file__).resolve().with_name("build_html.py")
DEFAULT_GLOB = "*_整理文档.html"

FIGURE_RE = re.compile(
    r'(<h2\s+id="([^"]+)"[^>]*>.*?</h2>)\s*'
    r'(<figure\s+class="diagram">.*?</figure>)',
    re.DOTALL | re.IGNORECASE,
)
BIO_ITALIC_RE = re.compile(r"(?<![</\w])\*([^*\n]{2,80})\*(?!\*)")


def extract_diagrams(html: str) -> dict[str, str]:
    """Map h2 id -> figure HTML (first diagram after that h2 only)."""
    found: dict[str, str] = {}
    for m in FIGURE_RE.finditer(html):
        hid = m.group(2)
        fig = m.group(3).strip()
        if hid not in found:
            found[hid] = fig
    return found


def inject_diagrams(html: str, diagrams: dict[str, str]) -> tuple[int, str]:
    """Re-insert saved diagrams after matching h2 ids. Returns (added, html)."""
    added = 0
    for hid, fig in diagrams.items():
        pat = re.compile(
            rf'(<h2\s+id="{re.escape(hid)}"[^>]*>.*?</h2>)\s*',
            re.DOTALL | re.IGNORECASE,
        )
        m = pat.search(html)
        if not m:
            continue
        start = m.end()
        window = html[start : start + 400]
        if 'class="diagram"' in window:
            continue
        html = html[: start] + fig + "\n\n" + html[start:]
        added += 1
    return added, html


def patch_speakers(html: str) -> str:
    """Replace Harrison/Andrew hardcode with generic first/second speaker + common names."""
    old = """    function tagSpeakers() {
      document.querySelectorAll(".timeline .step-body h3").forEach(h3 => {
        const step = h3.closest(".step");
        if (!step) return;
        const name = h3.textContent.trim();
        if (/Harrison/i.test(name)) step.classList.add("speaker-host");
        else if (/Andrew/i.test(name)) step.classList.add("speaker-guest");
      });
    }"""
    new = """    function tagSpeakers() {
      const names = [];
      document.querySelectorAll(".timeline .step-body h3").forEach(h3 => {
        const n = h3.textContent.trim();
        if (n && !names.includes(n)) names.push(n);
      });
      const host = names[0] || "";
      const guest = names[1] || "";
      document.querySelectorAll(".timeline .step-body h3").forEach(h3 => {
        const step = h3.closest(".step");
        if (!step) return;
        const name = h3.textContent.trim();
        if (/Patrick|Lenny|主持|Nilay|Emily Chang|Host/i.test(name) || (host && name === host)) {
          step.classList.add("speaker-host");
        } else if (/Sam Altman|Boris|Altman|Guest/i.test(name) || (guest && name === guest)) {
          step.classList.add("speaker-guest");
        } else if (host && name === host) {
          step.classList.add("speaker-host");
        } else if (guest && name === guest) {
          step.classList.add("speaker-guest");
        }
      });
    }"""
    # Also match already-patched Patrick/Sam version
    alt_old = """    function tagSpeakers() {
      document.querySelectorAll(".timeline .step-body h3").forEach(h3 => {
        const step = h3.closest(".step");
        if (!step) return;
        const name = h3.textContent.trim();
        if (/Patrick/i.test(name)) step.classList.add("speaker-host");
        else if (/Sam Altman|Altman/i.test(name)) step.classList.add("speaker-guest");
      });
    }"""
    if old in html:
        return html.replace(old, new, 1)
    if alt_old in html:
        return html.replace(alt_old, new, 1)
    if "function tagSpeakers()" in html and "names.includes" not in html:
        # Fallback: regex replace the whole function body
        return re.sub(
            r"    function tagSpeakers\(\) \{.*?\n    \}",
            new,
            html,
            count=1,
            flags=re.DOTALL,
        )
    return html


def fix_bio_italics(html: str) -> str:
    """Convert leftover *markdown italics* inside speaker-bio to <em>."""
    def repl_bio(m: re.Match) -> str:
        block = m.group(0)
        block2 = BIO_ITALIC_RE.sub(r"<em>\1</em>", block)
        return block2

    return re.sub(
        r'(<aside class="callout callout-info speaker-bio"[^>]*>.*?</aside>)',
        repl_bio,
        html,
        count=1,
        flags=re.DOTALL,
    )


def shorten_meta_if_long(html: str) -> str:
    """If meta source line is very long, keep text after last ' · ' segment pair lightly trimmed.
    Only touch lines that look like full English titles with duplicate names."""
    # Soften: leave as-is unless > 120 chars — prefer Invest/Lenny-style short form already handled per-file.
    return html


def process_one(md: Path, root: Path, build: Path) -> dict:
    html_path = md.with_suffix(".html")
    result = {
        "md": str(md.relative_to(root)),
        "ok": False,
        "diagrams_saved": 0,
        "diagrams_restored": 0,
        "error": "",
    }
    if not html_path.exists():
        result["error"] = "no-html"
        return result

    old_html = html_path.read_text(encoding="utf-8")
    diagrams = extract_diagrams(old_html)
    result["diagrams_saved"] = len(diagrams)

    proc = subprocess.run(
        [sys.executable, str(build), str(md), str(html_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        result["error"] = (proc.stderr or proc.stdout or "build failed")[:300]
        return result

    new_html = html_path.read_text(encoding="utf-8")
    restored, new_html = inject_diagrams(new_html, diagrams)
    result["diagrams_restored"] = restored
    new_html = patch_speakers(new_html)
    new_html = fix_bio_italics(new_html)
    new_html = shorten_meta_if_long(new_html)
    html_path.write_text(new_html, encoding="utf-8")
    result["ok"] = True
    if "Wrote" in (proc.stdout or ""):
        # capture sections line
        for line in (proc.stdout or "").splitlines():
            if "sections=" in line or "Wrote" in line:
                result["build"] = line.strip()
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-build lecture HTML in place, preserving hand-added Mermaid diagrams."
    )
    parser.add_argument("root", type=Path, help="directory scanned recursively for lecture HTML")
    parser.add_argument(
        "--build",
        type=Path,
        default=DEFAULT_BUILD,
        help="path to build_html.py (default: alongside this script)",
    )
    parser.add_argument(
        "--glob",
        default=DEFAULT_GLOB,
        help=f"HTML filename pattern to upgrade (default: {DEFAULT_GLOB})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    # Note titles and progress arrows can fall outside a legacy console codepage
    # (cp936 has no U+2194); degrade those characters instead of aborting.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    args = parse_args(argv)
    root = args.root.expanduser().resolve()
    build = args.build.expanduser().resolve()
    if not root.is_dir():
        print(f"error: root is not a directory: {root}", file=sys.stderr)
        return 2
    if not build.is_file():
        print(f"error: build script not found: {build}", file=sys.stderr)
        return 2

    targets = []
    for h in sorted(root.rglob(args.glob)):
        md = h.with_suffix(".md")
        if md.exists():
            targets.append(md)

    print(f"Found {len(targets)} HTML↔MD pairs under {root}")
    ok = fail = 0
    total_restored = 0
    for i, md in enumerate(targets, 1):
        r = process_one(md, root, build)
        status = "OK" if r["ok"] else "FAIL"
        if r["ok"]:
            ok += 1
            total_restored += r["diagrams_restored"]
        else:
            fail += 1
        extra = r.get("build", r.get("error", ""))
        print(
            f"[{i}/{len(targets)}] {status} "
            f"diag {r['diagrams_saved']}→{r['diagrams_restored']}  "
            f"{r['md']}"
            + (f"  | {extra}" if extra else "")
        )

    print(f"\nDone: ok={ok} fail={fail} diagrams_restored={total_restored}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
