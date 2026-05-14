#!/usr/bin/env python3
"""
Translate BioEdge™ JOYPRETTY funnel (ZA English) to German (DE), EUR / Germany.

Reads JOYPRETTY/ZA/english*.html and writes JOYPRETTY/DE/german*.html.

Offer pricing (EUR) matches funnel brief:
  Offer 1: €26.99 total, €107.99 MSRP strike, €12.99/bottle, 75% OFF
  Offer 2: €32.99, €215.99 strike, €7.99/bottle, 85% OFF
  Offer 3: €37.99, €323.99 strike, €5.99/bottle, 88% OFF

Prices outside checkout blocks use Offer 1 selling total (€26.99).

Run: python3 scripts/translate_joypretty_de.py
Requires: pip install beautifulsoup4 deep-translator
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString
from deep_translator import GoogleTranslator

REPO = Path(__file__).resolve().parents[1]
SOURCES_DESTS = [
    (REPO / "JOYPRETTY/ZA/english.html", REPO / "JOYPRETTY/DE/german.html"),
    (REPO / "JOYPRETTY/ZA/english2.html", REPO / "JOYPRETTY/DE/german2.html"),
]

TRANSLATOR = GoogleTranslator(source="en", target="de")

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PLACEHOLDER_PATTERN = re.compile(r"\{\{[^}]+\}\}")
BRACE_CONST_PATTERN = re.compile(r"\{[A-Z][A-Z0-9_]*\}")

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

# Longest-first ZAR → EUR for this funnel (checkout + story mentions).
ZAR_TO_EUR: list[tuple[str, str]] = [
    ("R6,599.99", "€323.99"),
    ("R5,799.99", "€285.99"),
    ("R4,399.99", "€215.99"),
    ("R2,199.99", "€107.99"),
    ("R799.99", "€37.99"),
    ("R699.99", "€32.99"),
    ("R549.99", "€26.99"),
    ("R274.99", "€12.99"),
    ("R174.99", "€7.99"),
    ("R132.99", "€5.99"),
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
    for token in (
        "BioEdge™",
        "BioEdge",
        "JOYPRETTY",
    ):
        idx = out.find(token)
        while idx != -1:
            end = idx + len(token)
            if idx > 0 and out[idx - 1].isalpha():
                idx = out.find(token, end)
                continue
            if end < len(out) and out[end].isalpha():
                idx = out.find(token, end)
                continue
            out = out.replace(token, put(token), 1)
            idx = out.find(token)
    for m in PLACEHOLDER_PATTERN.findall(out):
        out = out.replace(m, put(m), 1)
    for m in BRACE_CONST_PATTERN.findall(out):
        out = out.replace(m, put(m), 1)
    out = re.sub(r"(%s|%\([^)]+\)[sdif])", lambda m: put(m.group(0)), out)
    for m in URL_PATTERN.findall(out):
        if m not in store.values():
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
    if re.fullmatch(r"[\d\s\.,€\-–—+%/°:;!?¡¿\(\)\[\]\"'x↓™|➞★✔❮❯&amp;/]+", t):
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
    return html


def germany_visuals_pass(html: str) -> str:
    html = html.replace(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/Flag_of_South_Africa.svg/"
        "1920px-Flag_of_South_Africa.svg.png",
        "https://upload.wikimedia.org/wikipedia/en/thumb/b/ba/Flag_of_Germany.svg/"
        "1000px-Flag_of_Germany.svg.png",
    )
    return html


def normalize_markup_text(html: str) -> str:
    """Prevent MT fragments: ZWSP splits words; line-broken currency words."""
    html = re.sub(r"&(ZeroWidthSpace|zwsp);", "", html, flags=re.I)
    html = re.sub(r"thousands\s+of\s+rand\b", "thousands of euros", html, flags=re.I)
    return html


def geography_and_copy_pre_pass(html: str) -> str:
    html = html.replace('"name": "ZA - BioEdge™ JOYPRETTY"', '"name": "DE - BioEdge™ JOYPRETTY"')
    html = re.sub(r"\bSouth Africans\b", "Germans", html)
    html = re.sub(r"\bSouth African\b", "German", html)
    html = re.sub(r"\bSouth Africa\b", "Germany", html)
    html = re.sub(r"\bin South Africa\b", "in Germany", html)
    html = re.sub(r"\bacross South Africa\b", "across Germany", html)
    html = re.sub(
        r"Proudly serving South Africa:",
        "Proudly serving Germany:",
        html,
        flags=re.I,
    )
    html = re.sub(
        r"Special offer for South Africa\b",
        "Special offer for Germany",
        html,
        flags=re.I,
    )
    html = html.replace(
        "Gauteng 2196, South Africa",
        "Germany",
    )
    html = re.sub(
        r"13\s+Riviera Crescent,\s*Johannesburg,\s*Gauteng 2196,\s*South Africa",
        "Germany",
        html,
        flags=re.I,
    )
    html = re.sub(
        r"\bthe South African market\b",
        "the German market",
        html,
        flags=re.I,
    )
    # Align funnel copy with 75% introductory positioning (replacing leftover 50% claims).
    html = html.replace(
        "available at an exclusive introductory price of 50% off",
        "available at an exclusive introductory price of 75% off",
    )
    html = html.replace(
        "to 50% discount on package purchases!",
        "to 75% discount on package purchases!",
    )
    html = re.sub(r"\band now it's 50%\b", "and now it's 75%", html, flags=re.I)
    return html


def funnel_currency_meta(html: str) -> str:
    html = html.replace('"currency_code": "ZAR"', '"currency_code": "EUR"')
    html = html.replace('lang="en-ZA"', 'lang="de"')
    html = html.replace('lang="en"', 'lang="de"')
    return html


def patch_checkout_discount_ctas(html: str) -> str:
    """Checkout blocks say UP TO 88% but CTAs still said 79%."""
    return html.replace("</span><strong>79%", "</span><strong>88%")


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
            if not should_translate(val.strip()):
                continue
            protected, store = protect_special(val.strip())
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


def localize_payment_apps_script(html: str) -> str:
    html = html.replace(
        '\"title\": \"Credit/Debit Card\"',
        '\"title\": \"Kredit-/Debitkarte\"',
    )
    html = html.replace('\\"cc\\":\\"Card number\\"', '\\"cc\\":\\"Kartennummer\\"')
    html = html.replace('\\"expiry\\":\\"MM/YY\\"', '\\"expiry\\":\\"MM/JJ\\"')
    html = html.replace('\\"cvc\\":\\"CVC\\"', '\\"cvc\\":\\"Prüfziffer\\"')
    old_info = (
        "After clicking {SUBMIT_BUTTON}, you will be redirected to PayPal to complete your "
        "purchase securely."
    )
    de_info = (
        "Nach Klick auf {SUBMIT_BUTTON} werden Sie zu PayPal weitergeleitet, um den Kauf sicher "
        "abzuschließen."
    )
    html = html.replace(old_info, de_info)
    return html


def post_normalize_de(html: str) -> str:
    html = html.replace("</strong>€", "</strong> €")
    html = re.sub(
        r"(JOYPRETTY|BioEdge™|BioEdge)</strong>([a-zäöüßA-ZÄÖÜ])",
        r"\1</strong> \2",
        html,
    )
    html = re.sub(r"([a-zäöüß])<strong>BioEdge™", r"\1 <strong>BioEdge™", html)
    html = re.sub(r"([a-zäöüß])<strong>JOYPRETTY", r"\1 <strong>JOYPRETTY", html)
    html = html.replace("€€", "€")
    html = re.sub(r"(?<![,\d])(\d+),(\d{2})\s*€", r"€\1.\2", html)
    html = html.replace(">HRS</span>", ">Std</span>")
    html = html.replace(">SEC</span>", ">Sek</span>")
    html = html.replace(">MIN</span>", ">Min</span>")
    return html


def process_pair(src: Path, dest: Path) -> None:
    print(f"{src.name} → {dest.name}...")
    html = src.read_text(encoding="utf-8", errors="ignore")

    html = normalize_markup_text(html)
    html = geography_and_copy_pre_pass(html)
    html = germany_visuals_pass(html)
    html = funnel_currency_meta(html)
    html = apply_zar_to_eur(html)
    if src.name == "english2.html":
        html = patch_checkout_discount_ctas(html)

    soup = BeautifulSoup(html, "html.parser")
    translate_soup_strings(soup)

    out = str(soup)
    out = localize_payment_apps_script(out)
    out = post_normalize_de(out)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(out, encoding="utf-8")
    print(f"Wrote {dest}")


def main() -> None:
    for src, dst in SOURCES_DESTS:
        if not src.exists():
            print(f"Missing source: {src}")
            continue
        process_pair(src, dst)


if __name__ == "__main__":
    main()
