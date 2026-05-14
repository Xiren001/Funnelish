#!/usr/bin/env python3
"""
Translate EaseFlow ZA funnel HTML to German (DE), EUR / Germany localization.
Reads EaseFlow/ZA/english*.html and writes EaseFlow/DE/german*.html.

Run: python3 scripts/translate_easeflow_de.py
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
    (REPO / "EaseFlow/ZA/english.html", REPO / "EaseFlow/DE/german.html"),
    (REPO / "EaseFlow/ZA/english2.html", REPO / "EaseFlow/DE/german2.html"),
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

MAX_CHARS = 4200

# Longest-first: ZAR from SA funnel -> target EUR (user-specified)
ZAR_TO_EUR: list[tuple[str, str]] = [
    ("R3,299.99", "€161.99"),
    ("R2,199.99", "€107.99"),
    ("R2,599.99", "€128.99"),
    ("R1,569.99", "€77.99"),
    ("R1,099.99", "€53.99"),
    ("R699.99", "€32.99"),
    ("R629.99", "€29.99"),
    ("R549.99", "€26.99"),
    ("R314.99", "€14.99"),
    ("R232.99", "€10.99"),
]

# Testimonial / narrative ZAR lump sums
EXTRA_MONEY: list[tuple[str, str]] = [
    ("R8,000", "€4.000"),
]

GERMAN_OFFER_BLOCK = r"""    <section class="pgc-shipping-banner" style="background-color: #073E69;">
        Kostenloser Versand bei Bestellungen mit 2 oder 3 Flaschen
    </section>
    
    <section class="pgc-pricing-section" id="offer">
        <div class="pgc-pricing-container">
            
                        <div class="pgc-pricing-card " style="">
                            
                        <div class="pgc-discount-badge" style="background-color: #073E69;">
                            <svg width="90" height="90" viewBox="0 0 90 90" style="position: absolute; top: 0; left: 0;">
                                <circle cx="45" cy="45" r="42" fill="none" stroke="rgba(255,255,255,0.3)" stroke-width="2" stroke-dasharray="4 4"/>
                                <circle cx="45" cy="45" r="38" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1.5" stroke-dasharray="3 3"/>
                            </svg>
                            <span style="position: relative; z-index: 1;">50% <span style="font-size: 16px;">OFF</span></span>
                        </div>
                    
                            <div class="pgc-card-label" style="background-color: #073E69; color: white;">STARTER-ANGEBOT</div>
                            <div class="pgc-image-area">
                                <a href="https://thebioedge.co/en-za/cart/52040445002008:1"  style="display: block; width: 100%; height: 100%;"><img src="https://cdn.shopify.com/s/files/1/0953/3993/8072/files/11_4e6b2acd-8d47-405d-bbb3-921651e6378f.png?v=1778263841" class="pgc-product-image" alt="Produkt" style="width: 100%; height: 100%; object-fit: cover; cursor: pointer;"></a>
                        </div>
                            <div class="pgc-price" style="color: #073E69;">€26.99</div>
                            <div class="pgc-per-bottle" style="color: #073E69;">Pro Flasche</div>
                            <div class="pgc-total">Gesamt: <span class="pgc-original-price">€53.99</span>€26.99</div>
                            <a href="https://thebioedge.co/en-za/cart/52040445002008:1"  class="pgc-add-to-cart" style="background-color: #073E69 !important;">IN DEN WARENKORB</a>
                            <div class="pgc-you-save" style="color: #073E69;">Sie sparen: €26.99</div>
                            <div class="pgc-guarantee">
                                <div class="pgc-guarantee-item">60 TAGE GELD-ZURÜCK-GARANTIE</div>
                                <div class="pgc-guarantee-item">KOSTENLOSER VERSAND</div>
                    </div>
                </div>
                    
                        <div class="pgc-pricing-card " style="">
                            
                        <div class="pgc-discount-badge" style="background-color: #073E69;">
                            <svg width="90" height="90" viewBox="0 0 90 90" style="position: absolute; top: 0; left: 0;">
                                <circle cx="45" cy="45" r="42" fill="none" stroke="rgba(255,255,255,0.3)" stroke-width="2" stroke-dasharray="4 4"/>
                                <circle cx="45" cy="45" r="38" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1.5" stroke-dasharray="3 3"/>
                            </svg>
                            <span style="position: relative; z-index: 1;">72% <span style="font-size: 16px;">OFF</span></span>
                        </div>
                    
                            <div class="pgc-card-label" style="background-color: #073E69; color: white;">2 FLASCHEN</div>
                            <div class="pgc-image-area">
                                <a href="https://thebioedge.co/en-za/cart/52040445034776:1"  style="display: block; width: 100%; height: 100%;"><img src="https://cdn.shopify.com/s/files/1/0953/3993/8072/files/2_e4783b3d-7207-400c-a0f6-d79d6d63cf7e.png?v=1778263841" class="pgc-product-image" alt="Produkt" style="width: 100%; height: 100%; object-fit: cover; cursor: pointer;"></a>
                        </div>
                            <div class="pgc-price" style="color: #073E69;">€14.99</div>
                            <div class="pgc-per-bottle" style="color: #073E69;">Pro Flasche</div>
                            <div class="pgc-total">Gesamt: <span class="pgc-original-price">€107.99</span>€29.99</div>
                            <a href="https://thebioedge.co/en-za/cart/52040445034776:1"  class="pgc-add-to-cart" style="background-color: #073E69 !important;">IN DEN WARENKORB</a>
                            <div class="pgc-you-save" style="color: #073E69;">Sie sparen: €77.99</div>
                            <div class="pgc-guarantee">
                                <div class="pgc-guarantee-item">60 TAGE GELD-ZURÜCK-GARANTIE</div>
                                <div class="pgc-guarantee-item">KOSTENLOSER VERSAND</div>
                    </div>
                </div>
                    
                        <div class="pgc-pricing-card pgc-highlighted" style="border: 3px solid #073E69 !important;">
                            
                        <div class="pgc-discount-badge" style="background-color: #073E69;">
                            <svg width="90" height="90" viewBox="0 0 90 90" style="position: absolute; top: 0; left: 0;">
                                <circle cx="45" cy="45" r="42" fill="none" stroke="rgba(255,255,255,0.3)" stroke-width="2" stroke-dasharray="4 4"/>
                                <circle cx="45" cy="45" r="38" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1.5" stroke-dasharray="3 3"/>
                            </svg>
                            <span style="position: relative; z-index: 1;">80% <span style="font-size: 16px;">OFF</span></span>
                        </div>
                    
                            <div class="pgc-card-label" style="background-color: #073E69; color: white;">BELIEBTESTE OPTION</div>
                            <div class="pgc-image-area">
                                <a href="https://thebioedge.co/en-za/cart/52040445067544:1"  style="display: block; width: 100%; height: 100%;"><img src="https://cdn.shopify.com/s/files/1/0953/3993/8072/files/3_05081487-5237-49b5-b833-8cc4c29df901.png?v=1778263841" class="pgc-product-image" alt="Produkt" style="width: 100%; height: 100%; object-fit: cover; cursor: pointer;"></a>
                        </div>
                            <div class="pgc-price" style="color: #073E69;">€10.99</div>
                            <div class="pgc-per-bottle" style="color: #073E69;">Pro Flasche</div>
                            <div class="pgc-total">Gesamt: <span class="pgc-original-price">€161.99</span>€32.99</div>
                            <a href="https://thebioedge.co/en-za/cart/52040445067544:1"  class="pgc-add-to-cart" style="background-color: #073E69 !important;">IN DEN WARENKORB</a>
                            <div class="pgc-you-save" style="color: #073E69;">Sie sparen: €128.99</div>
                            <div class="pgc-guarantee">
                                <div class="pgc-guarantee-item">60 TAGE GELD-ZURÜCK-GARANTIE</div>
                                <div class="pgc-guarantee-item">KOSTENLOSER VERSAND</div>
                    </div>
                </div>
                    
                    </div>
    
        <div class="pgc-bottom-section">
            <div>
                <div class="pgc-payment-text">Unsere vertrauenswürdigen Zahlungsanbieter:</div>
                <div class="pgc-payment-logos">
                    <img src="https://img.funnelish.com/77498/831339/1749739498-Group%201000002576.png" alt="Zahlungsmethoden" style="max-height: 50px; width: auto;">
                </div>
            </div>
    
            <div class="pgc-security-info">
                <div class="pgc-ssl-icon">
                    <img src="https://img.funnelish.com/77498/831339/1749739518-Capa_1.png" alt="SSL-sicher" style="width: 80px; height: auto;">
                </div>
                <div class="pgc-security-text">
                        Wir verwenden einen 256-Bit-Warenkorb, bei dem 100 % Ihrer Daten verschlüsselt, geschützt und sicher sind. Dies entspricht dem Sicherheitsstandard vieler Banken, Behörden und militärischer Einrichtungen.
                    </div>
                </div>
            </div>
    </section>"""


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
        "EaseFlow™",
        "EaseFlow",
        "Flomax",
        "Rezum",
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
    # Skip pure EUR/price-ish tokens MT might garble
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
    for i, phrase in enumerate(unique):
        if len(phrase) > MAX_CHARS:
            mapping[phrase] = translate_long(phrase)
            time.sleep(0.2)
            continue
        try:
            mapping[phrase] = TRANSLATOR.translate(phrase)
        except Exception:
            time.sleep(1.0)
            mapping[phrase] = TRANSLATOR.translate(phrase)
        time.sleep(0.06)
        if (i + 1) % 40 == 0:
            print(f"  translated {i + 1}/{len(unique)}", flush=True)
    return mapping


def apply_zar_to_eur(html: str) -> str:
    for zar, eur in ZAR_TO_EUR:
        html = html.replace(zar, eur)
    for a, b in EXTRA_MONEY:
        html = html.replace(a, b)
    return html


def geography_and_copy_pre_pass(html: str) -> str:
    # Funnel JSON first so global "South Africa" → "Germany" does not touch this title.
    html = html.replace('"name": "BioEdge™ EaseFlow | South Africa"', '"name": "BioEdge™ EaseFlow | Deutschland"')
    html = re.sub(r"\bSouth Africans\b", "Germans", html)
    html = re.sub(r"\bSouth African\b", "German", html)
    html = re.sub(r"\bSouth Africa\b", "Germany", html)
    html = re.sub(r"\bin South Africa\b", "in Germany", html)
    html = re.sub(r"\bacross South Africa\b", "across Germany", html)
    html = re.sub(r"\bThousands of rand\b", "Thousands of euros", html, flags=re.I)
    # Typo fix so MT + readers get intended meaning ("compounds")
    html = html.replace("Finding comrand", "Finding compounds")
    html = html.replace("These comrand break", "These compounds break")
    html = html.replace("These comrank break", "These compounds break")
    return html


def narrative_price_clarity(html: str) -> str:
    """Align three-month paragraph with offer-1 per-bottle economics (outside offer section)."""
    pat = re.compile(
        r"<p>Get the three-month supply at <strong>€26\.99 per bottle</strong> — works out\s+"
        r"to about <strong>€26\.99</strong>\. Less than a cup of coffee\.</p>",
        re.DOTALL,
    )
    new = (
        "<p>For a three-month supply (three bottles), plan on about "
        "<strong>€26.99 per bottle</strong> — around <strong>€80.97</strong> in total — "
        "less than a cup of coffee a day.</p>"
    )
    html = pat.sub(new, html, count=1)
    return html


def funnel_currency_meta(html: str) -> str:
    html = html.replace('"currency_code": "ZAR"', '"currency_code": "EUR"')
    html = html.replace('lang="en"', 'lang="de"')
    return html


def patch_german_offer_section(html: str) -> str:
    marker_start = html.find('<section class="pgc-shipping-banner"')
    if marker_start == -1:
        return html
    rest = html[marker_start:]
    offer_open = rest.find('<section class="pgc-pricing-section" id="offer">')
    if offer_open == -1:
        return html
    sub = rest[offer_open:]
    depth = 0
    close_idx = -1
    i = 0
    while i < len(sub):
        if sub[i : i + 8] == "<section":
            depth += 1
            i = sub.find(">", i) + 1
            continue
        if sub[i : i + 10] == "</section>":
            depth -= 1
            i += 10
            if depth == 0:
                close_idx = i
                break
            continue
        i += 1
    if close_idx == -1:
        return html
    tail = marker_start + offer_open + close_idx
    html = html[:marker_start] + GERMAN_OFFER_BLOCK + html[tail:]
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


def post_normalize_de(html: str) -> str:
    html = html.replace('"BioEdge™ EaseFlow | Germany"', '"BioEdge™ EaseFlow | Deutschland"')
    html = re.sub(
        r"(EaseFlow™|BioEdge™|EaseFlow)</strong>([a-zäöüßA-ZÄÖÜ])",
        r"\1</strong> \2",
        html,
    )
    html = re.sub(r"([a-zäöüß])<strong>EaseFlow", r"\1 <strong>EaseFlow", html)
    html = re.sub(r"([a-zäöüß])<strong>BioEdge™", r"\1 <strong>BioEdge™", html)
    # MT sometimes duplicates euro symbol from ZAR fixes
    html = html.replace("€€", "€")
    html = re.sub(r"(?<![,\d])(\d+),(\d{2})\s*€", r"€\1.\2", html)
    return html


def process_pair(src: Path, dest: Path) -> None:
    print(f"{src.name} → {dest.name}...")
    html = src.read_text(encoding="utf-8", errors="ignore")
    html = geography_and_copy_pre_pass(html)
    html = funnel_currency_meta(html)
    html = apply_zar_to_eur(html)
    html = narrative_price_clarity(html)

    soup = BeautifulSoup(html, "html.parser")
    translate_soup_strings(soup)

    out = str(soup)
    if src.name == "english2.html":
        out = patch_german_offer_section(out)
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
