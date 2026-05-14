#!/usr/bin/env python3
"""
Fix OxivaFlow MX HTML: MXN amounts on one line (nbsp), spacing around bold.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FILES = [
    REPO / "OxivaFlow/MX/mexico.html",
    REPO / "OxivaFlow/MX/mexico2.html",
]


def fix_mxn_linebreaks(html: str) -> str:
    # $12,345.67 + whitespace/newlines + MXN -> prevent line break inside amount+currency
    html = re.sub(
        r"(\$\d{1,3}(?:,\d{3})*\.\d{2})\s+MXN",
        r"\1&nbsp;MXN",
        html,
    )
    # Rare stray amounts without $
    html = re.sub(
        r"(?<![\$0-9a-zA-Z])(\d{1,3}(?:,\d{3})*\.\d{2})\s+MXN(?![\$0-9a-zA-Z])",
        r"$\1&nbsp;MXN",
        html,
    )
    html = re.sub(r"&nbsp;\s+MXN", "&nbsp;MXN", html)
    return html


def _space_after_strong(m: re.Match[str]) -> str:
    ch = m.group(1)
    if ch == "<":
        return ch
    if ch in ',.;:!?)]}»„"\'':
        return ch
    return " " + ch


def fix_strong_spacing(html: str) -> str:
    html = re.sub(r"</strong>(<strong\b)", r"</strong> \1", html)
    html = re.sub(r"</strong>(<em\b)", r"</strong> \1", html)
    html = re.sub(r"(?<=</strong>)(\S)", _space_after_strong, html)

    before = (
        r"([\wªºÀ-ÖØ-öø-ÿ\u2122])(<strong\b)"  # letter/digit/word + immediately <strong>
    )
    html = re.sub(before, r"\1 \2", html, flags=re.UNICODE)

    html = re.sub(r",(\s*)(<strong\b)", r", \2", html)
    html = re.sub(r"(?<=[a-zA-ZÀ-ÖØ-öø-ÿ])(\.)(\s*)(<strong\b)", r". \g<3>", html)
    html = re.sub(r"\?(\s*)(<strong\b)", r"? \2", html)
    html = re.sub(r"!(\s*)(<strong\b)", r"! \2", html)

    html = re.sub(r" {2,}</strong>", "</strong>", html)
    html = re.sub(r"</strong> {2,}", "</strong> ", html)
    html = re.sub(r"</strong>\s+,", "</strong>,", html)
    html = re.sub(r"</strong>\s+\.", "</strong>.", html)
    return html


def process(path: Path) -> None:
    html = path.read_text(encoding="utf-8")
    html = fix_mxn_linebreaks(html)
    html = fix_strong_spacing(html)
    path.write_text(html, encoding="utf-8")


def main() -> None:
    for p in FILES:
        if p.exists():
            process(p)
            print("Wrote", p)
        else:
            print("Missing:", p)


if __name__ == "__main__":
    main()
