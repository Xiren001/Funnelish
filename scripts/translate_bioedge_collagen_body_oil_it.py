#!/usr/bin/env python3
"""
BioEdge Collagen Lifting Body Oil — IT funnel: Italian copy, Italy localization, EUR.

Updates:
  BioEdge - Collagen Lifting Body Oil/IT/italian.html
  BioEdge - Collagen Lifting Body Oil/IT/italian2.html

Requires: pip install beautifulsoup4 deep-translator

Run: python3 scripts/translate_bioedge_collagen_body_oil_it.py
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
    REPO / "BioEdge - Collagen Lifting Body Oil/IT/italian.html",
    REPO / "BioEdge - Collagen Lifting Body Oil/IT/italian2.html",
]

# Auto-detect leaves pre-localized Italian UI strings mostly unchanged.
TRANSLATOR = GoogleTranslator(source="auto", target="it")

SA_FLAG = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/Flag_of_South_Africa.svg/1920px-Flag_of_South_Africa.svg.png"
IT_FLAG = "https://upload.wikimedia.org/wikipedia/en/thumb/0/03/Flag_of_Italy.svg/1920px-Flag_of_Italy.svg.png"

UK_MAG_SRCSET = "//img.funnelish.com/61731/0/1760074904-uk%20%282%29.png"
IT_MAG_SRCSET = "https://cdn.shopify.com/s/files/1/0953/3993/8072/files/italy.png?v=1778380402"


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
    "↑",
    "⬇",
    "⬆",
    "™",
    "|",
    "❮",
    "❯",
    "➞",
    "★",
    "✔",
    "·",
}

MAX_BATCH = 28
MAX_CHARS = 4200

PROTECT_TOKENS = [
    "BioEdge™ Collagen Oil",
    "BioEdge™",
    "BioEdge",
    "Collagen Oil",
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
    if re.fullmatch(r"[\d\s\.,€\-–—+%/°:;!?¡¿\(\)\[\]\"'x↓↑⬇⬆™|➞★✔❮❯&amp;/]+", t):
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


def replace_flags_and_assets(html: str) -> str:
    html = html.replace(SA_FLAG, IT_FLAG)
    html = html.replace(UK_MAG_SRCSET, IT_MAG_SRCSET)
    return html


def fix_hebrew_comment_block(html: str) -> str:
    """Wrong-language testimonial → Italian + correct product."""
    html = re.sub(
        r"<p><strong id=\"inm1ej\">ג'וליה</strong></p>\s*"
        r"<p>\s*אני הולכת להזמין את VeinCare מיד![^<]*</p>",
        '<p><strong id="inm1ej">Giulia</strong></p>\n'
        "                                    <p>Sto per ordinare subito BioEdge™ Collagen Oil! Non vedo l'ora di vedere "
        "come funziona e condividerò la mia esperienza appena vedrò i risultati!</p>",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r"<p id=\"icu5xw\"><u id=\"iuw9sl\">לייק</u><span id=\"imz56v\"> · </span><u\s*"
        r'id="ijmwai">תגובה</u><span id="i39t44"> · 👍1 · 3 שעות&nbsp;</span></p>',
        '<p id="icu5xw"><u id="iuw9sl">Mi piace</u><span id="imz56v"> · </span><u '
        'id="ijmwai">Commenta</u><span id="i39t44"> · 👍1 · 3 ore&nbsp;</span></p>',
        html,
    )
    return html


def geography_it(html: str) -> str:
    html = re.sub(r"Trends in\s+South Africa", "Tendenze in Italia", html, flags=re.I)
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
        r"Trends in South Africa",
        "Tendenze in Italia",
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
    html = re.sub(r"\bUnited Kingdom\b", "Italia", html)
    html = re.sub(r"\bthe UK\b", "l'Italia", html)
    html = re.sub(r"\bUK\b", "Italia", html)
    html = re.sub(r"\bU\.S\.A\.\b|\bUSA\b|\bUnited States\b", "Italia", html)
    return html


def apply_zar_snippets(html: str) -> str:
    html = html.replace("R1,000+", "€100+")
    html = html.replace("R 1,000+", "€100+")
    html = re.sub(r"\bZAR\b", "EUR", html)
    return html


def funnel_currency_meta(html: str) -> str:
    html = html.replace('"currency_code": "ZAR"', '"currency_code": "EUR"')
    html = html.replace('"currency_code":"ZAR"', '"currency_code":"EUR"')
    html = html.replace('lang="en-ZA"', 'lang="it"')
    html = html.replace('<html lang="en">', '<html lang="it">')
    html = html.replace('<html lang="en" ', '<html lang="it" ')
    return html


def patch_shipping_script(html: str) -> str:
    html = html.replace("toLocaleString('en-ZA'", "toLocaleString('it-IT'")
    html = html.replace('toLocaleString("en-ZA"', 'toLocaleString("it-IT"')
    html = html.replace(
        "const shippingText = 'Ships by ' + formattedDate + ' | FREE Shipping'",
        "const shippingText = 'Spedizione prevista entro il ' + formattedDate + ' | SPEDIZIONE GRATUITA'",
    )
    return html


def patch_emergency_number(html: str) -> str:
    html = re.sub(
        r"call your doctor or 911 immediately",
        "chiama subito il medico o il 112",
        html,
        flags=re.I,
    )
    return html


def translate_hebrew_nodes(soup: BeautifulSoup) -> None:
    """Source lander embeds Hebrew blocks; auto translator skips non-Latin."""
    hebrew = re.compile(r"[\u0590-\u05FF]")
    skip_parents = {"script", "style", "noscript", "textarea"}
    ht = GoogleTranslator(source="iw", target="it")
    for element in soup.find_all(string=True):
        if isinstance(element, Comment):
            continue
        parent = getattr(element, "parent", None)
        if parent is None or parent.name in skip_parents:
            continue
        raw = str(element)
        if not hebrew.search(raw):
            continue
        stripped = raw.strip()
        if not stripped:
            continue
        try:
            translated = ht.translate(stripped)
            time.sleep(0.12)
        except Exception:
            translated = stripped
        new_val = raw.replace(stripped, translated) if stripped in raw else translated
        element.replace_with(NavigableString(new_val))


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


def apply_ui_phrases(html: str) -> str:
    """Tight CTAs and commerce strings (deterministic). Run before ML translate."""
    pairs = [
        ("ORDER NOW ⬇", "ORDINA ORA ⬇"),
        ("ORDER NOW ⬆", "ORDINA ORA ⬆"),
        ("ORDER NOW", "ORDINA ORA"),
        ("USE THE DISCOUNT AND CHECK AVAILABILITY >>", "USA LO SCONTO E CONTROLLA DISPONIBILITÀ >>"),
        ("USE THE DISCOUNT AND\n                      CHECK AVAILABILITY >>", "USA LO SCONTO E\n                      CONTROLLA DISPONIBILITÀ >>"),
        ("USE THE DISCOUNT AND CHECK AVAILABILITY &gt;&gt;", "USA LO SCONTO E CONTROLLA DISPONIBILITÀ &gt;&gt;"),
        ("Comments", "Commenti"),
        ("OFFER ENDS IN:", "L'OFFERTA SCADE TRA:"),
        (">HRS<", ">ORE<"),
        (">MIN<", ">MIN<"),
        (">SEC<", ">SEC<"),
        ("FREE Shipping", "SPEDIZIONE GRATUITA"),
        ("FREE SHIPPING", "SPEDIZIONE GRATUITA"),
        ("% OFF • You Save", "% DI SCONTO • Risparmi"),
        ("% OFF</span>", "% DI SCONTO</span>"),
        ("UP TO 82% OFF", "FINO AL 82% DI SCONTO"),
        ("SAVE UP TO 82% OFF", "RISPARMIA FINO AL 82%"),
        ("Enjoy UP TO 82% OFF today", "Approfitta FINO AL 82% DI SCONTO oggi"),
        ("Only<b>", "Solo<b>"),
        ("</b> each</div>", "</b> cad.</div>"),
        ("</b> each\n                                    </div>", "</b> cad.\n                                    </div>"),
        ("Ultimate Deal", "Offerta max"),
        ("Best Deal", "Più venduto"),
        ("Smart Choice", "Scelta smart"),
        ("Basic Choice", "Base"),
        ("Published on", "Pubblicato il"),
        ("Recommended", "Consigliato"),
        ("SATISFACTION GUARANTEE OR YOUR MONEY BACK", "SODDISFATTI O RIMBORSATI"),
        ("🎁 + Mystery gift for the first 100 customers!", "🎁 + Regalo sorpresa per i primi 100 clienti!"),
        ("DAILY: FIRST 100 CUSTOMERS!", "OGGI: PRIMI 100 CLIENTI!"),
        ("FREE</b> <b", "GRATIS</b> <b"),
        ("Mystery Gifts Worth €100+", "Regali sorpresa del valore di €100+"),
        ("Mystery Gifts Worth R1,000+", "Regali sorpresa del valore di €100+"),
        ("⚡️ EXCLUSIVE FACEBOOK SALE!", "⚡️ SALDI ESCLUSIVI SU FACEBOOK!"),
        ("Only here. Last chance!", "Solo qui. Ultima occasione!"),
        ("Like</span>", "Mi piace</span>"),
        ("Comment</span>", "Commenta</span>"),
        ("Reply</span>", "Rispondi</span>"),
        ("From €28.99 ", "Da €28.99 "),
        ("• Up to 82% OFF", "• Fino al 82% di sconto"),
        ("Ships by ", "Spedizione prevista entro il "),
        (" | FREE Shipping", " | SPEDIZIONE GRATUITA"),
        ("Over 14,000 verified customers", "Oltre 14.000 clienti verificati"),
        ("Join thousands of transformational stories today!", "Unisciti oggi a migliaia di storie di trasformazione!"),
    ]
    for a, b in pairs:
        html = html.replace(a, b)
    return html


def post_geo_after_hebrew(html: str) -> str:
    """Places referenced in MT output → Italy."""
    html = html.replace("Chicago", "Milano")
    html = re.sub(r"\bUSA\b", "Italia", html)
    html = html.replace("Stati Uniti", "Italia")
    html = html.replace("United States", "Italia")
    html = html.replace("EDT", "CET")
    return html


def post_normalize_it(html: str) -> str:
    html = html.replace("€€", "€")
    html = html.replace("cadavere</div>", "cad.</div>")
    html = html.replace("cadavere</", "cad.</")
    html = re.sub(r"(BioEdge|Collagen)™</strong>([a-zàèéìòù])", r"\1™</strong> \2", html, flags=re.I)
    html = re.sub(r"([a-zàèéìòù])<strong>(BioEdge)", r"\1 <strong>\2", html, flags=re.I)
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

    html = fix_hebrew_comment_block(html)
    html = geography_it(html)
    html = replace_flags_and_assets(html)
    html = funnel_currency_meta(html)
    html = apply_zar_snippets(html)
    html = patch_emergency_number(html)
    html = patch_shipping_script(html)
    html = apply_ui_phrases(html)

    soup = BeautifulSoup(html, "html.parser")
    translate_soup_strings(soup)
    translate_hebrew_nodes(soup)

    out = str(soup)
    out = post_normalize_it(out)
    out = localize_payment_gateways(out)
    out = post_geo_after_hebrew(out)
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
