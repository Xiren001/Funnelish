#!/usr/bin/env python3
"""
Translate Nicorex funnel HTML (ZA English) to German (DE), EUR / Germany.

Reads Nicorex/ZA/english*.html and writes Nicorex/DE/german*.html.

Run: python3 scripts/translate_nicorex_de.py
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
    (REPO / "Nicorex/ZA/english.html", REPO / "Nicorex/DE/german.html"),
    (REPO / "Nicorex/ZA/english2.html", REPO / "Nicorex/DE/german2.html"),
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

# ZAR from funnel → EUR (offers 1–4 + per-unit display). Longest-first.
ZAR_TO_EUR: list[tuple[str, str]] = [
    ("R5,499.99", "€269.99"),
    ("R4,699.99", "€231.99"),
    ("R3,299.99", "€161.99"),
    ("R2,599.99", "€128.99"),
    ("R2,199.99", "€107.99"),
    ("R1,569.99", "€77.99"),
    ("R1,099.99", "€53.99"),
    ("R1,835", "€92"),
    ("R3,675", "€184"),
    ("R699.99", "€32.99"),
    ("R629.99", "€29.99"),
    ("R549.99", "€26.99"),
    ("R314.99", "€14.99"),
    ("R232.99", "€10.99"),
    ("R171,500", "€8.575"),
    ("R159.99", "€7.99"),
    ("R99.99", "€4.99"),
    ("R24,500", "€1.225"),
    ("R799.99", "€37.99"),
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
        "Nicorex™",
        "Nicorex",
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
    """Replace ZA flag imagery with Germany (same dimensions in URL)."""
    html = html.replace(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/Flag_of_South_Africa.svg/1920px-Flag_of_South_Africa.svg.png",
        "https://upload.wikimedia.org/wikipedia/en/thumb/b/ba/Flag_of_Germany.svg/1000px-Flag_of_Germany.svg.png",
    )
    return html


def geography_pre_pass(html: str) -> str:
    html = html.replace('"name": "ZA - Nicorex"', '"name": "DE - Nicorex"')
    html = re.sub(r"\bSouth Africans\b", "Deutsche", html)
    html = re.sub(r"\bSouth African\b", "deutsch", html)
    html = re.sub(r"\bSouth Africa\b", "Deutschland", html)
    html = re.sub(r"\bin South Africa\b", "in Deutschland", html)
    html = re.sub(r"\bacross South Africa\b", "in ganz Deutschland", html)
    html = re.sub(
        r"\bFREE\s+shipping\s+in\s+South\s+Africa\b",
        "KOSTENLOSER Versand in Deutschland",
        html,
        flags=re.I,
    )
    html = re.sub(r"\bThousands of rand\b", "Tausende Euro", html, flags=re.I)
    return html


def funnel_currency_meta(html: str) -> str:
    html = html.replace('"currency_code": "ZAR"', '"currency_code": "EUR"')
    html = html.replace('lang="en-ZA"', 'lang="de"')
    html = html.replace('lang="en"', 'lang="de"')
    return html


def fix_split_currency_headlines(html: str) -> str:
    """Funnelish sometimes splits R549 and .99 across tags (not matched by R549.99)."""
    html = re.sub(
        r">R549</strong><strong>\s*\.99[ \n\t]*</strong>",
        ">€26.99</strong>",
        html,
    )
    return html


def patch_checkout_scarcity_copy(html: str) -> str:
    """Align urgency line with strongest bundle discount (80 %), same idea as OxivaFlow."""
    html = html.replace("The 50% discount ends at 23:59", "The 80% discount ends at 23:59")
    # Many blocks omit the leading "The" (line break inside the span).
    html = html.replace("50% discount ends at 23:59", "80% discount ends at 23:59")
    return html


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


def fix_de_checkout_urgency_line(html: str) -> str:
    """Fix split-span MT glitch: '(Only 7 units left)' became '(nur). … 7 … verbleibende'."""
    bad = (
        'Der Rabatt von 50 % endet um 23:59 Uhr (nur).</span><strong style="background-color: rgba(0, 0, 0, 0); '
        'color: rgb(255, 13, 42); font-size: 14px;">7</strong><span style="background-color: rgba(0, 0, 0, 0); '
        'color: rgb(99, 106, 123); font-size: 14px;">verbleibende Einheiten)</span>'
    )
    good = (
        'Bis zu 80 % Rabatt – endet um 23:59 Uhr (nur noch </span><strong style="background-color: rgba(0, 0, 0, 0); '
        'color: rgb(255, 13, 42); font-size: 14px;">7</strong><span style="background-color: rgba(0, 0, 0, 0); '
        'color: rgb(99, 106, 123); font-size: 14px;"> Stück verfügbar)</span>'
    )
    html = html.replace(bad, good)
    bad80 = bad.replace("50 %", "80 %")
    html = html.replace(bad80, good)
    return html


def post_normalize_de(html: str) -> str:
    html = re.sub(
        r"(Nicorex™|BioEdge™|Nicorex|BioEdge)</strong>([a-zäöüßA-ZÄÖÜ])",
        r"\1</strong> \2",
        html,
    )
    html = re.sub(r"([a-zäöüß])<strong>Nicorex", r"\1 <strong>Nicorex", html)
    html = re.sub(r"([a-zäöüß])<strong>BioEdge™", r"\1 <strong>BioEdge™", html)
    html = html.replace("€€", "€")
    html = re.sub(r"(?<![,\d])(\d+),(\d{2})\s*€", r"€\1.\2", html)
    html = html.replace(">HRS</span>", ">Std</span>")
    html = html.replace(">SEC</span>", ">Sek</span>")
    html = html.replace(">MIN</span>", ">Min</span>")
    return html


def process_pair(src: Path, dest: Path) -> None:
    print(f"{src.name} → {dest.name}...")
    html = src.read_text(encoding="utf-8", errors="ignore")

    html = geography_pre_pass(html)
    html = germany_visuals_pass(html)
    html = funnel_currency_meta(html)
    html = apply_zar_to_eur(html)
    html = fix_split_currency_headlines(html)

    if src.name == "english2.html":
        html = patch_checkout_scarcity_copy(html)

    soup = BeautifulSoup(html, "html.parser")
    translate_soup_strings(soup)

    out = str(soup)
    out = out.replace("ZAR", "EUR")
    out = localize_payment_apps_script(out)
    out = post_normalize_de(out)
    out = fix_de_checkout_urgency_line(out)

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
