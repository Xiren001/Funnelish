#!/usr/bin/env python3
"""
Localize Nicorex MX funnels: EN -> ES (MX), MXN pricing, México geography.

Run from repo root:
  . .venv_mx/bin/activate
  python3 scripts/nicorex_mx_es_localize.py Nicorex/MX/mexico.html Nicorex/MX/mexico2.html
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString
from deep_translator import GoogleTranslator


TRANSLATOR = GoogleTranslator(source="en", target="es")

# Narrative Rand amounts -> MXN equivalents (marketing round numbers).
ZAR_AMOUNT_MAP = (
    ("R171,500", "$165,450 MXN"),
    ("R24,500", "$23,595 MXN"),
    ("R3,675", "$3,540 MXN"),
    ("R1,835", "$1,766 MXN"),
)

MXN_PRICE_TOKENS: tuple[str, ...] = (
    "R1,099.99",
    "R1,569.99",
    "R2,199.99",
    "R2,599.99",
    "R3,299.99",
    "R4,699.99",
    "R5,499.99",
    "R171,500",
    "R24,500",
    "R3,675",
    "R1,835",
    "R99.99",
    "R159.99",
    "R232.99",
    "R314.99",
    "R549.99",
    "R629.99",
    "R699.99",
    "R799.99",
)

PRE_TRANSLATE_HTML = (
    ('lang="en-ZA"', 'lang="es-MX"'),
    ('"ZA - Nicorex"', '"MX - Nicorex"'),
    ('"currency_code": "ZAR"', '"currency_code": "MXN"'),
    ("Trends in&nbsp;South Africa", "Trends in Mexico"),
    ("Trends in South Africa", "Trends in Mexico"),
    ("South African", "Mexican"),
    ("South Africa", "Mexico"),
    ("// ZA:", "// MX:"),
)

FLAG_URL_REPLACE = (
    (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/Flag_of_South_Africa.svg/"
        "1920px-Flag_of_South_Africa.svg.png",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Flag_of_Mexico.svg/"
        "1920px-Flag_of_Mexico.svg.png",
    ),
)


def combined_shield_pattern() -> re.Pattern[str]:
    price_alt = "|".join(re.escape(p) for p in sorted(set(MXN_PRICE_TOKENS), key=len, reverse=True))
    return re.compile(
        "("
        r"https?://[^\s<>\"']+|//[^\s<>\"']+|www\.[^\s<>\"']+|"
        r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|"
        r"\{\{[^}]+\}\}|"
        r"%\d*\$?[sdifu]|"
        r"BioEdge™|Nicorex™|\bBioEdge\b|\bNicorex\b|"
        r"/[pP][cC]\.?|"
        f"(?:{price_alt})"
        ")",
        flags=re.UNICODE,
    )


SHIELD_RX = combined_shield_pattern()


def shield_fragments(text: str) -> tuple[str, list[str]]:
    vault: list[str] = []

    def _rep(m: re.Match[str]) -> str:
        vault.append(m.group(0))
        idx = len(vault) - 1
        return f"\uE0AD{idx}\uE0DE"

    return SHIELD_RX.sub(_rep, text), vault


def unshield_fragments(text: str, vault: list[str]) -> str:
    for i, fragment in enumerate(vault):
        text = text.replace(f"\uE0AD{i}\uE0DE", fragment)
    return text


def should_skip_chunk(s: str) -> bool:
    st = s.strip()
    if not st:
        return True
    if st in ("\u200b",):
        return True
    if re.search(r"[a-zA-ZÀ-ÖØ-öø-ÿ]", st):
        return False  # prose / UI — translate

    # No letters — numbers, punctuation, emoji-like stars only → keep as-is (ratings etc.)
    if re.fullmatch(r"[\s★\d\.,\-\+\(\)%/&x×]+", st, flags=re.I):
        return True
    return False


_TRANSL_CACHE: dict[str, str] = {}
_UNIQUE_CALLS = 0


def translate_chunk(fragment: str) -> str:
    global _UNIQUE_CALLS
    if fragment not in _TRANSL_CACHE:
        shielded, vault = shield_fragments(fragment)
        if not shielded.strip():
            translated = shielded
        else:
            try:
                translated = TRANSLATOR.translate(shielded)
            except Exception:
                time.sleep(3)
                translated = TRANSLATOR.translate(shielded)
            if translated is None or translated == "":
                translated = shielded
        final = unshield_fragments(translated, vault)
        if final is None or final.strip() == "":
            final = fragment
        _TRANSL_CACHE[fragment] = final
        _UNIQUE_CALLS += 1
        if _UNIQUE_CALLS % 120 == 0:
            time.sleep(2)
        else:
            time.sleep(0.05)
    return _TRANSL_CACHE[fragment]


def translate_bs_text(html_path: Path) -> str:
    raw = html_path.read_text(encoding="utf-8", errors="surrogateescape")
    for a, b in PRE_TRANSLATE_HTML:
        raw = raw.replace(a, b)
    for a, b in FLAG_URL_REPLACE:
        raw = raw.replace(a, b)

    soup = BeautifulSoup(raw, "lxml")

    for text in soup.find_all(string=True):
        if isinstance(text, Comment):
            continue
        parent = getattr(text, "parent", None)
        if parent and parent.name in {"script", "style", "noscript"}:
            continue
        original = str(text)
        if should_skip_chunk(original):
            continue

        stripped_lead = len(original) - len(original.lstrip())
        stripped_trail = len(original) - len(original.rstrip())
        lead = original[:stripped_lead]
        trail = original[len(original) - stripped_trail :] if stripped_trail else ""
        core = (
            original[stripped_lead : len(original) - stripped_trail]
            if stripped_trail
            else original[stripped_lead:]
        )
        if not core.strip():
            continue
        translated = translate_chunk(core)
        text.replace_with(NavigableString(lead + translated + trail))

    # Use meta charset-preserving serialization (BS/lxml keeps structure).
    return str(soup)


def apply_mxn_on_html(html: str) -> str:
    pairs = sorted(
        [
            ("R99.99", "$99.99 MXN"),
            ("R159.99", "$159.99 MXN"),
            ("R232.99", "$232.99 MXN"),
            ("R314.99", "$314.99 MXN"),
            ("R549.99", "$549.99 MXN"),
            ("R629.99", "$629.99 MXN"),
            ("R699.99", "$699.99 MXN"),
            ("R799.99", "$799.99 MXN"),
            ("R1,099.99", "$1,099.99 MXN"),
            ("R1,569.99", "$1,569.99 MXN"),
            ("R2,199.99", "$2,199.99 MXN"),
            ("R2,599.99", "$2,599.99 MXN"),
            ("R3,299.99", "$3,299.99 MXN"),
            ("R4,699.99", "$4,699.99 MXN"),
            ("R5,499.99", "$5,499.99 MXN"),
        ],
        key=lambda kv: len(kv[0]),
        reverse=True,
    )

    html = re.sub(
        r">R549</strong><strong>\.99\b",
        ">$549.99 MXN</strong><strong>",
        html,
        flags=re.I,
    )

    for old, new in pairs:
        html = html.replace(old, new)

    for zar, mxn in ZAR_AMOUNT_MAP:
        html = html.replace(zar, mxn)

    for a, b in (
        ("/pc", "/pieza"),
        ("/Pc", "/pieza"),
        ("/PC", "/pieza"),
        ("ordenador personal", "pieza"),
        ("(Guardar ", "(Ahorras "),
        ("AÑADIR A LA CESTA", "AGREGAR AL CARRITO"),
        ("APAGADO</strong>", "OFF</strong>"),
        ("Total: sólo ", "Total: solo "),
    ):
        html = html.replace(a, b)

    html = html.replace("MXN MXN", "MXN")
    html = html.replace("$ MXN MXN", "$ MXN")

    return html


def mexico_lexicon_touchups(html: str) -> str:
    tweaks = (
        ('lang="Mexico"', 'lang="es-MX"'),
        ("/Pieza", "/pieza"),
    )
    for a, b in tweaks:
        html = html.replace(a, b)
    return html


def process_file(html_path: Path) -> None:
    global _UNIQUE_CALLS
    _UNIQUE_CALLS = 0
    print(f"Translating → MXN localize: {html_path}")
    out = translate_bs_text(html_path)
    out = apply_mxn_on_html(out)
    out = mexico_lexicon_touchups(out)
    html_path.write_text(out, encoding="utf-8")
    print(f"Done. Unique translation API chunks: {_UNIQUE_CALLS}")


def main() -> None:
    paths = [Path(p).resolve() for p in sys.argv[1:] if str(p).endswith(".html")]
    if not paths:
        print("Usage: python3 scripts/nicorex_mx_es_localize.py <html files...>")
        sys.exit(1)
    if paths[0].parent.name != "MX":
        print("Warn: expected Nicorex/MX/*.html paths")
    for p in paths:
        process_file(p)


if __name__ == "__main__":
    main()
