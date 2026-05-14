#!/usr/bin/env python3
"""
BioFit IT funnel: translate visible English copy to Italian, set Italy + EUR pricing.

Updates in place:
  - BioFit/IT/italian.html
  - BioFit/IT/italian2.html

Offer totals (EUR) per brief; prices outside checkout use Offer 1 (€34.99 / €69.99 strike where applicable).

Requires: pip install beautifulsoup4 deep-translator

Run: python3 scripts/translate_biofit_it.py
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString
from deep_translator import GoogleTranslator
from deep_translator.exceptions import TranslationNotFound

REPO = Path(__file__).resolve().parents[1]
FILES = [
    REPO / "BioFit/IT/italian.html",
    REPO / "BioFit/IT/italian2.html",
]

TRANSLATOR = GoogleTranslator(source="en", target="it")


def safe_translate(text: str) -> str:
    try:
        return TRANSLATOR.translate(text)
    except (TranslationNotFound, Exception):
        return text

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
    "1+1 GRATIS",
}

MAX_BATCH = 28
MAX_CHARS = 4200

PROTECT_TOKENS = [
    "BioEdge™",
    "BioEdge",
    "BioFit™",
    "BioFit",
]

# Longest ZAR strings first → EUR (unique amounts in this funnel).
ZAR_TO_EUR_ORDERED: list[tuple[str, str]] = [
    ("R8,399.99", "€419.99"),
    ("R7,299.99", "€354.99"),
    ("R4,199.99", "€209.99"),
    ("R3,399.99", "€164.99"),
    ("R2,799.99", "€139.99"),
    ("R2,099.99", "€104.99"),
    ("R1,399.99", "€69.99"),
    ("R1,099.99", "€64.99"),
    ("R699.99", "€34.99"),
    ("R799.99", "€44.99"),
    ("R349.99", "€16.99"),
    ("R266.99", "€14.99"),
    ("R182.99", "€10.99"),
    ("R999", "€69.99"),
    ("R499", "€34.99"),
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
    for token in PROTECT_TOKENS:
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
        return safe_translate(text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    buf: list[str] = []
    chunk = ""
    for p in parts:
        if len(chunk) + len(p) + 1 > MAX_CHARS and chunk:
            buf.append(safe_translate(chunk.strip()))
            time.sleep(0.2)
            chunk = p
        else:
            chunk = f"{chunk} {p}".strip()
    if chunk:
        buf.append(safe_translate(chunk))
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
                outs = [safe_translate(x) for x in light]
            for src, dst in zip(light, outs):
                mapping[src] = dst
            time.sleep(0.35)
        for h in heavy:
            mapping[h] = translate_long(h)
            time.sleep(0.25)
    return mapping


def apply_zar_to_eur(html: str) -> str:
    for zar, eur in ZAR_TO_EUR_ORDERED:
        html = html.replace(zar, eur)
    html = re.sub(r"\bZAR\b", "EUR", html)
    return html


def patch_pgc_discount_badges(html: str) -> str:
    html = html.replace(
        '<span style="position: relative; z-index: 1">81% <span style="font-size: 16px">OFF</span></span>',
        '<span style="position: relative; z-index: 1">79% <span style="font-size: 16px">OFF</span></span>',
    )
    html = html.replace(
        '<span style="position: relative; z-index: 1">87% <span style="font-size: 16px">OFF</span></span>',
        '<span style="position: relative; z-index: 1">85% <span style="font-size: 16px">OFF</span></span>',
    )
    return html


def geography_it(html: str) -> str:
    html = html.replace('name: "NLBE - BioEdge™ "', 'name: "IT - BioEdge™ "')
    html = re.sub(r"\bSouth Africans\b", "italiani", html)
    html = re.sub(r"\bSouth African\b", "italiano", html)
    html = re.sub(r"\bSouth Africa\b", "Italia", html)
    html = re.sub(r"\bin South Africa\b", "in Italia", html)
    html = re.sub(r"\bacross South Africa\b", "in tutta Italia", html)
    html = re.sub(
        r"Proudly serving South Africa:",
        "Siamo orgogliosi di servire l'Italia:",
        html,
        flags=re.I,
    )
    html = re.sub(
        r"Special offer for South Africa\b",
        "Offerta speciale per l'Italia",
        html,
        flags=re.I,
    )
    html = re.sub(
        r"Trending in South Africa\s*&nbsp;",
        "Tendenze in Italia&nbsp;",
        html,
        flags=re.I,
    )
    html = re.sub(
        r"Trending in South Africa\b",
        "Tendenze in Italia",
        html,
        flags=re.I,
    )
    return html


def funnel_currency_meta(html: str) -> str:
    html = html.replace('"currency_code": "ZAR"', '"currency_code": "EUR"')
    html = html.replace('"currency_code":"ZAR"', '"currency_code":"EUR"')
    html = html.replace('lang="en-ZA"', 'lang="it"')
    html = html.replace('lang="en"', 'lang="it"')
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


def post_normalize_it(html: str) -> str:
    html = html.replace("€€", "€")
    html = html.replace('™Patch', '™ Patch')
    html = html.replace('font-size: 16px">SPENTO</span>', 'font-size: 16px">SCONTO</span>')
    html = re.sub(r"Risparmi:\s*€\s*(\d+),(\d+)", r"Risparmi: €\1.\2", html)
    html = re.sub(r"(BioFit|BioEdge)™</strong>([a-zàèéìòù])", r"\1™</strong> \2", html, flags=re.I)
    html = re.sub(r"([a-zàèéìòù])<strong>(BioFit|BioEdge)", r"\1 <strong>\2", html, flags=re.I)
    html = re.sub(r"(?<![,\d])(\d+),(\d{2})\s*€", r"€\1.\2", html)
    return html


def localize_payment_gateways(html: str) -> str:
    html = html.replace("info: \"Select your bank below\"", 'info: "Seleziona la tua banca qui sotto"')
    html = html.replace(
        "info: 'After clicking \"{SUBMIT_BUTTON}\" you will be redirected to Bancontact to securely complete your payment.'",
        "info: 'Dopo aver cliccato \"{SUBMIT_BUTTON}\" verrai reindirizzato a Bancontact per completare il pagamento in sicurezza.'",
    )
    html = html.replace('title: "Credit / Debit Card"', 'title: "Carta di credito / debito"')
    html = html.replace(
        "info: '{\"cc\":\"Card number\",\"expiry\":\"MM/YY\",\"cvc\":\"CVC\"}'",
        "info: '{\"cc\":\"Numero carta\",\"expiry\":\"MM/AA\",\"cvc\":\"CVC\"}'",
    )
    html = html.replace(
        "info: \"After clicking {SUBMIT_BUTTON} you will be redirected to PayPal to securely complete your purchase.\"",
        "info: \"Dopo aver cliccato {SUBMIT_BUTTON} verrai reindirizzato a PayPal per completare l'acquisto in sicurezza.\"",
    )
    return html


def process_file(path: Path) -> None:
    print(f"Processing {path.name}...")
    html = path.read_text(encoding="utf-8", errors="ignore")

    html = geography_it(html)
    html = funnel_currency_meta(html)
    html = apply_zar_to_eur(html)
    html = patch_pgc_discount_badges(html)

    soup = BeautifulSoup(html, "html.parser")
    translate_soup_strings(soup)

    out = str(soup)
    out = post_normalize_it(out)
    out = localize_payment_gateways(out)
    path.write_text(out, encoding="utf-8")
    print(f"Wrote {path}")


def main() -> None:
    for fp in FILES:
        if not fp.exists():
            print(f"Missing: {fp}")
            continue
        process_file(fp)


if __name__ == "__main__":
    main()
