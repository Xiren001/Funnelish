#!/usr/bin/env python3
"""
Translate JOYPRETTY MX funnel HTML to Spanish (Mexico), MXN pricing, localized copy.
Run from repo root: python3 JOYPRETTY/MX/translate_mx_spanish.py

Dependencies: pip install beautifulsoup4 lxml deep-translator
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString
from deep_translator import GoogleTranslator

HERE = Path(__file__).resolve().parent

TARGET_FILES = [
    HERE / "mexico.html",
    HERE / "mexico2.html",
]

CURRENCY_REPLACEMENTS: list[tuple[str, str]] = [
    ('"currency_code": "ZAR"', '"currency_code": "MXN"'),
    ('"name": "ZA - BioEdge™ JOYPRETTY"', '"name": "MX - BioEdge™ JOYPRETTY"'),
    ("R5,799.99", "$5,799.99 MXN"),
    ("R3,699.99", "$3,699.99 MXN"),
    ("R1,649.99", "$1,649.99 MXN"),
    ("R6,599.99", "$6,599.99 MXN"),
    ("R4,399.99", "$4,399.99 MXN"),
    ("R2,199.99", "$2,199.99 MXN"),
    ("R549.99", "$549.99 MXN"),
    ("R699.99", "$699.99 MXN"),
    ("R799.99", "$799.99 MXN"),
    ("R274.99", "$274.99 MXN"),
    ("R174.99", "$174.99 MXN"),
    ("R132.99", "$132.99 MXN"),
]

PCT_CTA_FIX = ("</strong></span><strong>79%", "</strong></span><strong>88%")


PROTECT_SUBSTITUTIONS: list[tuple[str, str]] = [
    ("BioEdge™ JOYPRETTY", "⟦BR0⟧"),
    ("BioEdge™", "⟦BR1⟧"),
    ("JOYPRETTY", "⟦BR2⟧"),
    ("Hair Disruption Molecule", "⟦BR3⟧"),
]


def protect_brands(s: str) -> str:
    for a, b in PROTECT_SUBSTITUTIONS:
        s = s.replace(a, b)
    return s


def unprotect_brands(s: str) -> str:
    for a, b in PROTECT_SUBSTITUTIONS:
        s = s.replace(b, a)
    return s


def patch_raw(html: str) -> str:
    for old, new in CURRENCY_REPLACEMENTS:
        html = html.replace(old, new)
    # Align copy with Offer 1 headline discount (75%)
    html = html.replace(
        "exclusive introductory price of 50% off",
        "exclusive introductory price of 75% off",
    )
    html = html.replace(
        "to 50% discount on package purchases!",
        "to 75% discount on package purchases!",
    )
    html = html.replace("now it's 50%", "now it's 75%")
    html = html.replace("Gauteng 2196, South Africa", "Ciudad de México, México")
    html = html.replace("South African market", "Mexican market")
    html = html.replace("South African", "Mexican")
    html = html.replace("South Africa", "Mexico")
    html = html.replace("thousands of rand", "miles de pesos mexicanos")
    html = html.replace("Thousands of rand", "Miles de pesos mexicanos")
    html = html.replace(*PCT_CTA_FIX)
    html = re.sub(r"<html\s+lang=\"en\"", '<html lang="es"', html, count=1)
    return html


def should_translate(t: str) -> bool:
    t = t.strip()
    if len(t) < 2:
        return False
    if re.fullmatch(r"[\W\d_$.,·\s%-]+", t, re.UNICODE):
        return False
    if not re.search(r"[A-Za-zÀ-ÿ]", t):
        return False
    if t in ("→", "➞", "-"):
        return False
    return True


def translate_html_strings(html: str, translator: GoogleTranslator) -> str:
    soup = BeautifulSoup(html, "lxml")
    cache: dict[str, str] = {}

    text_nodes: list[NavigableString] = []
    for node in soup.descendants:
        if not isinstance(node, NavigableString) or isinstance(node, Comment):
            continue
        parent = getattr(node, "parent", None)
        if parent and parent.name in ("script", "style", "noscript"):
            continue
        if not should_translate(str(node)):
            continue
        text_nodes.append(node)

    unique_keys: list[str] = []
    seen: set[str] = set()
    for node in text_nodes:
        k = str(node)
        if k not in seen:
            seen.add(k)
            unique_keys.append(k)

    print(f"  Unique text chunks: {len(unique_keys)}", flush=True)
    for i, text in enumerate(unique_keys):
        pb = protect_brands(text)
        stripped = pb.replace("⟦BR0⟧", "").replace("⟦BR1⟧", "").replace("⟦BR2⟧", "").replace("⟦BR3⟧", "")
        if not should_translate(stripped):
            cache[text] = text
            continue
        try:
            translated = translator.translate(pb)
            cache[text] = unprotect_brands(translated)
        except Exception as exc:
            print(f"  WARN [{i}]: {exc!s} | {text[:60]!r}", flush=True)
            cache[text] = text
        if i and i % 30 == 0:
            time.sleep(0.35)
        time.sleep(0.02)

    for node in text_nodes:
        k = str(node)
        if k in cache:
            node.replace_with(cache[k])

    # Avoid XML declaration / extra wrapper from lxml
    return soup.decode(formatter="html")


def tidy_html(html: str) -> str:
    html = re.sub(r"info\s*@\s*thebioedge\.co", "info@thebioedge.co", html, flags=re.I)
    # MT sometimes rewrites "MXN" as "pesos" next to amounts
    html = re.sub(r"\$(\d{1,3}(?:,\d{3})*\.\d{2})\s*pesos", r"$\1 MXN", html)
    return html


def process_file(path: Path) -> None:
    print(f"Processing {path} ...", flush=True)
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = patch_raw(raw)
    translator = GoogleTranslator(source="auto", target="es")
    out = translate_html_strings(raw, translator)
    out = tidy_html(out)
    path.write_text(out, encoding="utf-8")
    print(f"  Wrote {path.name}", flush=True)


def main() -> None:
    try:
        import lxml  # noqa: F401
    except ImportError:
        print("Install: pip install beautifulsoup4 lxml deep-translator", file=sys.stderr)
        sys.exit(1)
    for f in TARGET_FILES:
        if not f.is_file():
            print(f"Missing {f}", file=sys.stderr)
            sys.exit(1)
        process_file(f)
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
