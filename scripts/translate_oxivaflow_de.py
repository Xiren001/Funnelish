#!/usr/bin/env python3
"""
Translate OxivaFlow DE funnel HTML to German, EUR pricing, Germany geography.
Run: python3 scripts/translate_oxivaflow_de.py
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
    REPO / "OxivaFlow/DE/german.html",
    REPO / "OxivaFlow/DE/german2.html",
]

TRANSLATOR = GoogleTranslator(source="en", target="de")

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

# ZAR display amounts from the SA funnel -> target EUR (user-specified offers)
ZAR_TO_EUR: list[tuple[str, str]] = [
    ("R4,699.99", "€231.99"),
    ("R5,499.99", "€269.99"),
    ("R3,299.99", "€161.99"),
    ("R2,599.99", "€128.99"),
    ("R1,099.99", "€53.99"),
    ("R699.99", "€32.99"),
    ("R549.99", "€26.99"),
    ("R799.99", "€37.99"),
    ("R232.99", "€10.99"),
    ("R159.99", "€7.99"),
]


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


def apply_zar_to_eur(html: str) -> str:
    for zar, eur in ZAR_TO_EUR:
        html = html.replace(zar, eur)
    html = html.replace("Save €", "Save €")  # placeholder for clarity
    return html


def geography_pre_pass(html: str) -> str:
    html = re.sub(r"\bSouth Africans\b", "Germans", html)
    html = re.sub(r"\bSouth African\b", "German", html)
    html = re.sub(r"\bSouth Africa\b", "Germany", html)
    html = re.sub(r"\bin South Africa\b", "in Germany", html)
    html = re.sub(r"\bacross South Africa\b", "across Germany", html)
    html = re.sub(
        r"\bFREE\s+shipping\s+in\s+South\s+Africa\b",
        "FREE shipping in Germany",
        html,
        flags=re.I,
    )
    html = html.replace("Johannesburg, South Africa", "Berlin, Germany")
    html = re.sub(r"\bJohannesburg\b", "Berlin", html, flags=re.I)
    html = html.replace(
        "South African Journal of Gastroenterology",
        "German Journal of Gastroenterology",
    )
    html = html.replace('"name": "South Africa - OxivaFlow™ "', '"name": "Germany - OxivaFlow™ "')
    return html


def funnel_currency_meta(html: str) -> str:
    html = html.replace('"currency_code": "ZAR"', '"currency_code": "EUR"')
    html = html.replace('lang="en"', 'lang="de"')
    return html


def normalize_scandinavian_cta(html: str) -> str:
    """Replace stray Swedish UI with English so DE MT is consistent."""
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
    new_en = 'style="font-size: 18px">GET UP TO 80% OFF ➞</span>'
    html = html.replace(old_sv, new_en)
    old_sv2 = (
        'style="font-size: 12px">100%\n'
        "                                                                                                    Nöjdhetsgaranti\n"
        "                                                                                                    eller pengarna\n"
        "                                                                                                    tillbaka!</span>"
    )
    new_en2 = 'style="font-size: 12px">100% satisfaction guarantee or your money back!</span>'
    html = html.replace(old_sv2, new_en2)
    return html


def patch_offer2_discount_block(html: str) -> str:
    """Inside checkout sidebar offer-2 card: show 80% instead of 50%."""
    start = html.find('<div class="container el-651982">')
    if start == -1:
        return html
    end = html.find('<div class="section_row el-875439"', start)
    if end == -1:
        return html
    seg = html[start:end]
    seg = seg.replace("UP TO 50%", "UP TO 80%")
    seg = seg.replace("GET UP TO 50% OFF", "GET UP TO 80% OFF")
    return html[:start] + seg + html[end:]


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
        t = raw.strip()
        if not should_translate(raw):
            continue
        protected, store = protect_special(t)
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


def fix_corrupted_mobile_gesamt_lines(html: str) -> str:
    """Repair MT/HTML corruption where currency was split across tags."""
    block1 = """<p style="text-align: center;"><span style="font-size: inherit; font-family: inherit; margin: 0px;"><strong>Gesamt:</strong>R</span>549.99
                                                                <strong><s>R</s></strong><span style="font-size: inherit; font-family: inherit; margin: 0px;"><strong><s>1,099.99</s></strong></span>
</p>"""
    fix1 = """<p style="text-align: center;"><span style="font-size: inherit; font-family: inherit; margin: 0px;"><strong>Gesamt:
                                                                        nur</strong></span> €26.99</p>
<p style="text-align: center;"><span style="font-size: inherit; font-family: inherit; margin: 0px;"><strong><s>€53.99</s></strong></span>
</p>"""
    block2 = """<p style="text-align: center;"><span style="font-size: inherit; font-family: inherit; margin: 0px;"><strong>Gesamt:</strong>R</span>699.99
                                                                <strong><s>R</s></strong><span style="font-size: inherit; font-family: inherit; margin: 0px;"><strong><s>3,299.99</s></strong></span>
</p>"""
    fix2 = """<p style="text-align: center;"><span style="font-size: inherit; font-family: inherit; margin: 0px;"><strong>Gesamt:
                                                                        nur</strong></span> €32.99</p>
<p style="text-align: center;"><span style="font-size: inherit; font-family: inherit; margin: 0px;"><strong><s>€161.99</s></strong></span>
</p>"""
    block3 = """<p style="text-align: center;"><span style="font-size: inherit; font-family: inherit; margin: 0px;"><strong>Gesamt:</strong>R</span>799.99
                                                                <strong><s>R</s></strong><span style="font-size: inherit; font-family: inherit; margin: 0px;"><strong><s>5,499.99</s></strong></span>
</p>"""
    fix3 = """<p style="text-align: center;"><span style="font-size: inherit; font-family: inherit; margin: 0px;"><strong>Gesamt:
                                                                        nur</strong></span> €37.99</p>
<p style="text-align: center;"><span style="font-size: inherit; font-family: inherit; margin: 0px;"><strong><s>€269.99</s></strong></span>
</p>"""
    for bad, good in ((block1, fix1), (block2, fix2), (block3, fix3)):
        html = html.replace(bad, good)
    return html


def post_normalize_de(html: str) -> str:
    """Tidy spacing and keep brand tokens readable after MT."""
    html = re.sub(
        r"(OxivaFlow™|BioEdge™)</strong>([a-zäöüßA-ZÄÖÜ])",
        r"\1</strong> \2",
        html,
    )
    html = re.sub(r"([a-zäöüß])<strong>OxivaFlow™", r"\1 <strong>OxivaFlow™", html)
    html = re.sub(r"([a-zäöüß])<strong>BioEdge™", r"\1 <strong>BioEdge™", html)
    # Timer labels (German storefront style)
    html = html.replace(">HRS</span>", ">Std</span>")
    html = html.replace(">SEC</span>", ">Sek</span>")
    # Normalize "12,34 €" from MT → "€12.34" per brief
    html = re.sub(r"(?<![,\d])(\d+),(\d{2})\s*€", r"€\1.\2", html)
    html = html.replace("Johannesburg, Deutschland", "Berlin, Deutschland")
    return html


def process_file(path: Path) -> None:
    print(f"Processing {path}...")
    html = path.read_text(encoding="utf-8", errors="ignore")
    html = apply_zar_to_eur(html)
    html = geography_pre_pass(html)
    html = funnel_currency_meta(html)
    html = normalize_scandinavian_cta(html)
    if path.name == "german2.html":
        html = patch_offer2_discount_block(html)

    soup = BeautifulSoup(html, "html.parser")
    translate_soup_strings(soup)

    out = str(soup)
    out = out.replace("ZAR", "EUR")
    out = merge_oxiva_trademark_splits(out)
    out = fix_corrupted_mobile_gesamt_lines(out)
    out = post_normalize_de(out)
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
