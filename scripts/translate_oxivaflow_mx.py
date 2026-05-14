#!/usr/bin/env python3
"""
Translate OxivaFlow MX funnel HTML to Spanish (Mexico), MXN pricing, Mexico geography.

Run from repo root:
  python3 scripts/translate_oxivaflow_mx.py

Requires: pip install beautifulsoup4 deep-translator
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString
from deep_translator import GoogleTranslator

REPO = Path(__file__).resolve().parents[1]
FILES = [
    REPO / "OxivaFlow/MX/mexico.html",
    REPO / "OxivaFlow/MX/mexico2.html",
]

TRANSLATOR = GoogleTranslator(source="en", target="es")

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PLACEHOLDER_PATTERN = re.compile(r"\{\{[^}]+\}\}")

SKIP_EXACT = {
    "",
    "x",
    "-",
    "↓",
    "™",
    "|",
    "❮",
    "❯",
    "➞",
    "★",
    "✔",
}

MAX_BATCH = 30
MAX_CHARS = 4200


def protect_special(s: str) -> tuple[str, dict[str, str]]:
    store: dict[str, str] = {}
    i = 0

    def put(val: str) -> str:
        nonlocal i
        key = f"⟦{i}⟧"
        store[key] = val
        i += 1
        return key

    out = s
    for token in ("OxivaFlow™", "BioEdge™"):
        while token in out:
            out = out.replace(token, put(token), 1)
    for m in PLACEHOLDER_PATTERN.findall(out):
        out = out.replace(m, put(m), 1)
    out = re.sub(r"(%s|%\([^)]+\)[sdif])", lambda m: put(m.group(0)), out)
    for m in URL_PATTERN.findall(out):
        out = out.replace(m, put(m), 1)
    for m in EMAIL_PATTERN.findall(out):
        out = out.replace(m, put(m), 1)
    return out, store


def restore_special(s: str, store: dict[str, str]) -> str:
    out = s
    for k, v in store.items():
        out = out.replace(k, v)
    return out


def should_translate(s: str) -> bool:
    t = s.strip()
    if len(t) < 2:
        return False
    if t in SKIP_EXACT:
        return False
    if re.fullmatch(r"[\d\s\.,\-–—+%/°:;!?¡¿\(\)\[\]\"'x↓™|➞★✔❮❯&amp;]+", t):
        return False
    if not re.search(r"[A-Za-zÀ-ÿ]", t):
        return False
    return True


def translate_long(text: str) -> str:
    if len(text) <= MAX_CHARS:
        return TRANSLATOR.translate(text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    buf: list[str] = []
    chunk = ""
    for p in parts:
        if len(chunk) + len(p) + 1 > MAX_CHARS and chunk:
            buf.append(TRANSLATOR.translate(chunk.strip()))
            time.sleep(0.2)
            chunk = p
        else:
            chunk = f"{chunk} {p}".strip()
    if chunk:
        buf.append(TRANSLATOR.translate(chunk))
    return " ".join(buf)


def batch_translate_map(texts: list[str]) -> dict[str, str]:
    unique: list[str] = []
    seen: set[str] = set()
    for t in texts:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    mapping: dict[str, str] = {}
    for i in range(0, len(unique), MAX_BATCH):
        batch = unique[i : i + MAX_BATCH]
        heavy = [b for b in batch if len(b) > MAX_CHARS]
        light = [b for b in batch if len(b) <= MAX_CHARS]
        if light:
            try:
                outs = TRANSLATOR.translate_batch(light)
            except Exception:
                time.sleep(1.5)
                outs = [TRANSLATOR.translate(x) for x in light]
            for src, dst in zip(light, outs):
                mapping[src] = dst
            time.sleep(0.35)
        for h in heavy:
            mapping[h] = translate_long(h)
            time.sleep(0.25)
    return mapping


def apply_rand_to_mxn(html: str) -> str:
    """R1,234.56 -> $1,234.56 MXN (only Rand price tokens, not arbitrary R + digits)."""
    return re.sub(
        r"R(\d{1,3}(?:,\d{3})*\.\d{2})",
        r"$\1 MXN",
        html,
    )


def fix_broken_rand_markup(html: str) -> str:
    pat = (
        r"</strong>R</span>(\d[\d,]*\.\d{2})\s*<strong><s>R</s></strong><span\s+[^>]*>\s*"
        r"<strong><s>([\d,]+\.\d{2})</s></strong></span>"
    )
    repl = (
        r'</strong></span>$\1 MXN <span style="font-size: inherit; font-family: inherit; margin: 0px;">'
        r"<strong><s>$\2 MXN</s></strong></span>"
    )
    return re.sub(pat, repl, html, flags=re.DOTALL)


def fix_stray_r_notation(html: str) -> str:
    """Broken patterns like '</strong>R</span>799.99' or orphan '<strong><s>R</s></strong>'."""
    html = re.sub(
        r"</strong>R</span>(\d[\d,]*\.\d{2})",
        r"</strong></span>$\1 MXN",
        html,
    )
    html = html.replace("<strong><s>R</s></strong>", "")
    return html


def normalize_bare_strikethrough_totals(html: str) -> str:
    """After Rand→MXN, catch strikethrough totals that were missing the R prefix."""
    html = re.sub(
        r"<strong><s>(\d[\d,]*\.\d{2})</s></strong>",
        r"<strong><s>$\1 MXN</s></strong>",
        html,
    )
    return html


def geography_pre_pass(html: str) -> str:
    html = re.sub(r"\bSouth Africans\b", "Mexicans", html)
    html = re.sub(r"\bSouth African\b", "Mexican", html)
    html = re.sub(r"\bSouth Africa\b", "Mexico", html)
    html = re.sub(r"\bin South Africa\b", "in Mexico", html)
    html = re.sub(r"\bacross South Africa\b", "across Mexico", html)
    html = re.sub(
        r"\bFREE\s+shipping\s+in\s+South\s+Africa\b",
        "FREE shipping in Mexico",
        html,
        flags=re.I,
    )
    html = re.sub(r"\bJohannesburg\b", "Mexico City", html, flags=re.I)
    html = html.replace("Johannesburg, Mexico", "Mexico City, Mexico")
    html = html.replace(
        "South African Journal of Gastroenterology",
        "Mexican Journal of Gastroenterology",
    )
    html = html.replace(
        "South Africa Health",
        "Mexico public health regulators",
    )
    html = re.sub(r"\bAfricans?\b", "Mexicans", html)
    html = re.sub(r"\bAfrican\b", "Mexican", html)
    html = html.replace(
        '"name": "South Africa - OxivaFlow™ "',
        '"name": "Mexico - OxivaFlow™ "',
    )
    return html


def funnel_currency_meta(html: str) -> str:
    html = html.replace('"currency_code": "ZAR"', '"currency_code": "MXN"')
    html = html.replace('lang="en"', 'lang="es"')
    return html


def normalize_scandinavian_cta(html: str) -> str:
    """Replace stray Swedish UI with English so ES MT is consistent."""
    html = html.replace(
        'class="btn-headline">BESTÄLL NU OCH 1 +1 GRATIS ↓</span>',
        'class="btn-headline">ORDER NOW AND GET 1+1 FREE ↓</span>',
    )
    old_sv = (
        'style="font-size: 18px">FÅ\n'
        "                                                                                                        UPPTILL 50%\n"
        "                                                                                                        RABATT\n"
        "                                                                                                        ➞</span>"
    )
    new_en = 'style="font-size: 18px">GET UP TO 79% OFF ➞</span>'
    html = html.replace(old_sv, new_en)
    old_sv2 = (
        'style="font-size: 12px">100%\n'
        "                                                                                                    Nöjdhetsgaranti\n"
        "                                                                                                    eller pengarna\n"
        "                                                                                                    tillbaka!</span>"
    )
    new_en2 = 'style="font-size: 12px">100% satisfaction guarantee or your money back!</span>'
    html = html.replace(old_sv2, new_en2)
    html = html.replace("UPPTILL 50%", "UP TO 79%")
    return html


def patch_offer2_column_mxn(html: str) -> str:
    """Offer 2 card (el-651982): show 79% instead of 50% in headline + CTA."""
    start = html.find('<div class="container el-651982">')
    end = html.find('<div class="section_row el-875439"', start)
    if start == -1 or end == -1 or end <= start:
        return html
    seg = html[start:end]
    seg = seg.replace(
        "<strong>UP TO 50%\n                                                                                                    OFF!</strong>",
        "<strong>UP TO 79%\n                                                                                                    OFF!</strong>",
        1,
    )
    seg = seg.replace(
        "<strong>GET\n                                                                                                        UP TO 50% OFF\n                                                                                                        ➞</strong>",
        "<strong>GET\n                                                                                                        UP TO 79% OFF\n                                                                                                        ➞</strong>",
        1,
    )
    return html[:start] + seg + html[end:]


def patch_second_work_sans_discount_badge(html: str) -> str:
    """
    Two identical 'Work Sans' 50% OFF strips (hero columns). Replace only the **second**
    occurrence → 79% for the offer-2 teaser column.
    """
    needle = (
        '<span\n'
        '                                                                                                    style="font-size: 18px; background-color: rgb(255, 249, 237); color: rgb(48, 48, 48); '
        'font-family: &quot;Work Sans&quot;; text-transform: none; margin: 0px;"><strong>50%\n'
        '                                                                                                        OFF</strong></span>'
    )
    rep = needle.replace("50%", "79%", 1)
    first = html.find(needle)
    if first == -1:
        return html
    second = html.find(needle, first + len(needle))
    if second == -1:
        return html
    return html[:second] + rep + html[second + len(needle) :]


def fix_product_title_typo(html: str) -> str:
    return html.replace("3 + 2 xivaFlow™", "3 + 2 OxivaFlow™")


def translate_soup_strings(soup: BeautifulSoup) -> None:
    skip_parents = {"script", "style", "noscript", "textarea"}

    text_jobs: list[tuple[NavigableString, str, dict[str, str]]] = []
    for element in soup.find_all(string=True):
        if isinstance(element, Comment):
            continue
        parent = getattr(element, "parent", None)
        if parent is None or parent.name in skip_parents:
            continue
        raw = str(element)
        if not should_translate(raw):
            continue
        protected, store = protect_special(raw.strip())
        if not should_translate(protected):
            continue
        text_jobs.append((element, protected, store))

    attr_jobs: list[tuple[object, str, str, dict[str, str]]] = []
    for tag in soup.find_all(True):
        for attr in ("alt", "title", "placeholder", "aria-label"):
            val = tag.get(attr)
            if not val or not isinstance(val, str):
                continue
            if not should_translate(val):
                continue
            t = val.strip()
            protected, store = protect_special(t)
            if not should_translate(protected):
                continue
            attr_jobs.append((tag, attr, protected, store))

    to_translate = [p for _, p, _ in text_jobs] + [p for _, _, p, _ in attr_jobs]
    mapping = batch_translate_map(to_translate)

    for element, protected, store in text_jobs:
        trans = restore_special(mapping[protected], store)
        element.replace_with(NavigableString(trans))

    for tag, attr, protected, store in attr_jobs:
        tag[attr] = restore_special(mapping[protected], store)


def merge_oxiva_trademark_splits(html: str) -> str:
    return html.replace(
        '<strong>OxivaFlow</strong></span><span style="font-size: 23px; margin: 0px;"><strong>™</strong></span>',
        '<strong>OxivaFlow™</strong></span>',
    )


def post_normalize_es_mx(html: str) -> str:
    html = re.sub(r"(\$\d[\d,]*\.\d{2})\s+pesos", r"\1 MXN", html)
    html = html.replace("<strong>MÁS POPULÄR</strong>", "<strong>MÁS POPULAR</strong>")
    html = re.sub(
        r"Todos los productos han sido certificados por el\s*<strong>\s*México Salud\s*Autoridades\s*</strong>",
        "Todos los productos cumplen con estándares avalados por las <strong>autoridades sanitarias de México</strong>.",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html = re.sub(
        r"(OxivaFlow™|BioEdge™)</strong>([a-záéíóúñA-ZÁÉÍÓÚÑ])",
        r"\1</strong> \2",
        html,
    )
    html = re.sub(r"([a-záéíóúñ])<strong>OxivaFlow™", r"\1 <strong>OxivaFlow™", html)
    html = re.sub(r"([a-záéíóúñ])<strong>BioEdge™", r"\1 <strong>BioEdge™", html)
    # MT sometimes turns "$123.45 MXN" into words or EU decimals
    html = re.sub(r"\b(\d+),(\d{2})\s+MXN\b", r"$\1.\2 MXN", html)
    html = re.sub(r"\b549,99\s+MXN\b", "$549.99 MXN", html)
    return html


def process_file(path: Path) -> None:
    print(f"Processing {path}...")
    html = path.read_text(encoding="utf-8", errors="ignore")
    html = fix_product_title_typo(html)
    html = geography_pre_pass(html)
    html = funnel_currency_meta(html)
    if path.name == "mexico2.html":
        html = normalize_scandinavian_cta(html)
        html = patch_offer2_column_mxn(html)
        html = patch_second_work_sans_discount_badge(html)
    html = fix_broken_rand_markup(html)
    html = fix_stray_r_notation(html)
    html = apply_rand_to_mxn(html)
    html = normalize_bare_strikethrough_totals(html)

    soup = BeautifulSoup(html, "html.parser")
    translate_soup_strings(soup)

    out = str(soup)
    out = out.replace("ZAR", "MXN")
    out = merge_oxiva_trademark_splits(out)
    out = post_normalize_es_mx(out)
    path.write_text(out, encoding="utf-8")
    print(f"Wrote {path}")


def main() -> None:
    for p in FILES:
        if p.exists():
            process_file(p)
        else:
            print(f"Missing: {p}")


if __name__ == "__main__":
    main()
