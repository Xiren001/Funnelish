#!/usr/bin/env python3
"""Normalize spaces around <strong> and keep '549.99 MXN' prices on one line (nbsp)."""
from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

REPO = Path(__file__).resolve().parents[1]
FILES = [
    REPO / "PainCare/MX/mexico.html",
    REPO / "PainCare/MX/mexico2.html",
]

# Prices: 549.99 or 1,099.99 before MXN
PRICE_MXN = re.compile(
    r"(?<![\d.])(\d{1,3}(?:,\d{3})*\.\d{2})(\s|&nbsp;|\s*\n\s*)+MXN(?=[^0-9A-Za-z]|$)",
    re.MULTILINE,
)

SKIP_ANCESTORS = {"script", "style", "noscript", "textarea"}

# After </strong>, don't insert space if next is these (punctuation / closers)
NO_SPACE_AFTER = frozenset(".,;:!?)]}»\"'")


def _first_meaningful_char(node) -> str | None:
    if isinstance(node, NavigableString):
        s = str(node).lstrip()
        return s[0] if s else None
    if isinstance(node, Tag):
        if node.name == "br":
            return None
        for s in node.strings:
            sl = str(s).lstrip()
            if sl:
                return sl[0]
    return None


def _last_char_needs_space_before_strong(prev) -> bool:
    if prev is None:
        return False
    if isinstance(prev, NavigableString):
        s = str(prev).rstrip()
        if not s:
            return False
        return s[-1] not in " \n\t\xa0"
    if isinstance(prev, Tag):
        if prev.name == "br":
            return False
        for s in reversed(list(prev.strings)):
            sr = str(s).rstrip()
            if sr:
                return sr[-1] not in " \n\t\xa0"
    return False


def ensure_space_before_strong(tag: Tag) -> None:
    prev = tag.previous_sibling
    if not _last_char_needs_space_before_strong(prev):
        return
    if isinstance(prev, NavigableString):
        prev.replace_with(str(prev) + " ")
    else:
        tag.insert_before(NavigableString(" "))


def ensure_space_after_strong(tag: Tag) -> None:
    nxt = tag.next_sibling
    if nxt is None:
        return
    if isinstance(nxt, NavigableString):
        s = str(nxt)
        if not s:
            return
        ch = s.lstrip()[:1] if s.lstrip() else ""
        if ch in NO_SPACE_AFTER or not ch:
            return
        if not s.startswith((" ", "\n", "\t", "\xa0")):
            nxt.replace_with(" " + s)
        return
    if isinstance(nxt, Tag) and nxt.name != "br":
        for child in nxt.children:
            if isinstance(child, NavigableString):
                cs = str(child)
                if cs and cs.strip():
                    if cs.startswith((" ", "\n", "\t", "\xa0")):
                        return
                    break
        ch = _first_meaningful_char(nxt)
        if ch and ch not in NO_SPACE_AFTER:
            tag.insert_after(NavigableString(" "))


def fix_strong_spacing(soup: BeautifulSoup) -> None:
    for strong in list(soup.find_all("strong")):
        p = strong.parent
        skip = False
        while p is not None:
            if p.name in SKIP_ANCESTORS:
                skip = True
                break
            p = p.parent
        if skip:
            continue
        ensure_space_before_strong(strong)
        ensure_space_after_strong(strong)


def nbsp_mxn(html: str) -> str:
    def repl(m: re.Match) -> str:
        return m.group(1) + "\xa0MXN"

    return PRICE_MXN.sub(repl, html)


def collapse_double_spaces_in_text(soup: BeautifulSoup) -> None:
    """Turn accidental '  ' in text nodes to single space (conservative)."""
    for el in soup.find_all(string=True):
        if el.parent and el.parent.name in SKIP_ANCESTORS:
            continue
        s = str(el)
        if isinstance(el, NavigableString) and "  " in s:
            el.replace_with(re.sub(r" {2,}", " ", s))


def process(path: Path) -> None:
    html = path.read_text(encoding="utf-8")
    html = nbsp_mxn(html)
    soup = BeautifulSoup(html, "html.parser")
    fix_strong_spacing(soup)
    collapse_double_spaces_in_text(soup)
    path.write_text(str(soup), encoding="utf-8")
    print(path)


def main() -> None:
    for p in FILES:
        if p.exists():
            process(p)


if __name__ == "__main__":
    main()
