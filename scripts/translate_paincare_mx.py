#!/usr/bin/env python3
"""
Translate PainCare MX funnel HTML to Spanish (Mexico), MXN pricing, localized geography.
Run: .venv_mx/bin/python scripts/translate_paincare_mx.py
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString
from deep_translator import GoogleTranslator

REPO = Path(__file__).resolve().parents[1]
FILES = [
    REPO / "PainCare/MX/mexico.html",
    REPO / "PainCare/MX/mexico2.html",
]

TRANSLATOR = GoogleTranslator(source="en", target="es")

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")
PLACEHOLDER_PATTERN = re.compile(r"\{\{[^}]+\}\}")

SKIP_EXACT = {
    "",
    "x",
    "-",
    "↓",
    "™",
    "|",
}

MXN_SUFFIX = " MXN"
MAX_BATCH = 35
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
    out = out.replace("PainCare™", put("PainCare™"))
    for m in PLACEHOLDER_PATTERN.findall(out):
        out = out.replace(m, put(m), 1)
    out = re.sub(r"(%s|%\([^)]+\)[sdif])", lambda m: put(m.group(0)), out)
    for m in URL_PATTERN.findall(out):
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
    if re.fullmatch(r"[\d\s\.,\-–—+%/°:;!?¡¿\(\)\[\]\"'x↓™|]+", t):
        return False
    if not re.search(r"[A-Za-zÀ-ÿ]", t):
        return False
    return True


def translate_long(text: str) -> str:
    """Split very long strings on sentence boundaries."""
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
            time.sleep(0.4)
        for h in heavy:
            try:
                mapping[h] = translate_long(h)
            except Exception:
                time.sleep(1.0)
                mapping[h] = TRANSLATOR.translate(h[:MAX_CHARS])
            time.sleep(0.3)
    return mapping


def apply_rand_to_mxn(html: str) -> str:
    return re.sub(
        r"R(\d{1,3}(?:,\d{3})*\.\d{2})",
        lambda m: m.group(1) + MXN_SUFFIX,
        html,
    )


def fix_broken_rand_markup(html: str) -> str:
    pat = r"</strong>R</span>(\d[\d,]*\.\d{2})\s*<strong><s>R</s></strong><span\s+[^>]*>\s*<strong><s>([\d,]+\.\d{2})</s></strong></span>"
    repl = r'</strong></span>\1 MXN <span style="font-size: inherit; font-family: inherit; margin: 0px;"><strong><s>\2 MXN</s></strong></span>'
    return re.sub(pat, repl, html, flags=re.DOTALL)


def fix_mobile_column1_save(html: str) -> str:
    marker = '<div class="element-wrapper" data-eid="906690">'
    end = '<div class="element-wrapper" data-eid="599447">'
    i = html.find(marker)
    if i == -1:
        return html
    j = html.find(end, i)
    if j == -1:
        return html
    chunk = html[i:j]
    chunk = chunk.replace("Save R2,599.99", "Save 549.99" + MXN_SUFFIX, 1)
    chunk = re.sub(
        r"Save 2,599\.99\s*MXN",
        "Save 549.99" + MXN_SUFFIX,
        chunk,
        count=1,
    )
    return html[:i] + chunk + html[j:]


def geography_pre_pass(html: str) -> str:
    html = re.sub(r"\bSouth Africans\b", "Mexicans", html)
    html = re.sub(r"\bSouth African\b", "Mexican", html)
    html = re.sub(r"\bSouth Africa\b", "Mexico", html)
    html = re.sub(r"\bin South Africa\b", "in Mexico", html)
    html = re.sub(r"\bacross South Africa\b", "across Mexico", html)
    html = re.sub(
        r"\bFREE\s+shipping\s+in\s+South Africa\b",
        "FREE shipping in Mexico",
        html,
        flags=re.I,
    )
    return html


def funnel_meta(html: str) -> str:
    html = html.replace('"name": "ZA - PainCare™ "', '"name": "MX - PainCare™ "')
    html = html.replace('"currency_code": "ZAR"', '"currency_code": "MXN"')
    html = html.replace('lang="en"', 'lang="es"')
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


def post_normalize_mxn_html(html: str) -> str:
    """After MT, Google sometimes rewrites amounts as 'pesos' or EU decimals — standardize to MXN."""
    subs = [
        ("1.099,99 pesos", "1,099.99 MXN"),
        ("549.99 pesos", "549.99 MXN"),
        ("314.99 pesos", "314.99 MXN"),
        ("232.99 pesos", "232.99 MXN"),
        ("629.99 pesos", "629.99 MXN"),
        ("699.99 pesos", "699.99 MXN"),
        ("2,199.99 pesos", "2,199.99 MXN"),
    ]
    for a, b in subs:
        html = html.replace(a, b)
    html = re.sub(r"\b549,99 MXN\b", "549.99 MXN", html)
    html = re.sub(
        r"(PainCare™|BioEdge™)</strong>([a-záéíóúñA-ZÁÉÍÓÚÑ])",
        r"\1</strong> \2",
        html,
    )
    html = re.sub(r":</strong>([a-záéíóúñ])", r":</strong> \1", html)
    html = re.sub(r"Con<strong>PainCare™", r"Con <strong>PainCare™", html)
    html = re.sub(r"Llevar<strong>", r"Llevar <strong>", html)
    html = re.sub(r"Ofrecemos<strong>", r"Ofrecemos <strong>", html)
    html = re.sub(r"([a-záéíóúñ])<strong>PainCare™", r"\1 <strong>PainCare™", html)
    html = re.sub(r"([a-záéíóúñ])<strong>BioEdge™", r"\1 <strong>BioEdge™", html)
    html = re.sub(r"seguro<strong>BioEdge™", r"seguro <strong>BioEdge™", html)
    html = re.sub(r"dia</strong>con", r"día </strong>con", html)
    html = re.sub(r"al día</strong>con", r"al día </strong>con", html)
    return html


def process_file(path: Path) -> None:
    print(f"Processing {path}...")
    html = path.read_text(encoding="utf-8", errors="ignore")
    html = funnel_meta(html)
    html = geography_pre_pass(html)
    html = fix_broken_rand_markup(html)
    html = fix_mobile_column1_save(html)
    html = apply_rand_to_mxn(html)

    soup = BeautifulSoup(html, "html.parser")
    translate_soup_strings(soup)

    out = str(soup)
    out = out.replace("ZAR", "MXN")
    out = post_normalize_mxn_html(out)
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
