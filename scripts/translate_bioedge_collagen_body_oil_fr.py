#!/usr/bin/env python3
"""
BioEdge Collagen Lifting Body Oil — FR funnel: French copy, France localization, EUR.

Updates:
  BioEdge - Collagen Lifting Body Oil/FR/french.html
  BioEdge - Collagen Lifting Body Oil/FR/french2.html

Requires: pip install beautifulsoup4 deep-translator

Run: python3 scripts/translate_bioedge_collagen_body_oil_fr.py
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
    REPO / "BioEdge - Collagen Lifting Body Oil/FR/french.html",
    REPO / "BioEdge - Collagen Lifting Body Oil/FR/french2.html",
]

TRANSLATOR = GoogleTranslator(source="auto", target="fr")

SA_FLAG = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/Flag_of_South_Africa.svg/1920px-Flag_of_South_Africa.svg.png"
FR_FLAG = "https://upload.wikimedia.org/wikipedia/en/thumb/c/c3/Flag_of_France.svg/1920px-Flag_of_France.svg.png"

UK_MAG_SRCSET = "//img.funnelish.com/61731/0/1760074904-uk%20%282%29.png"
FR_MAG_SRCSET = "https://upload.wikimedia.org/wikipedia/en/thumb/c/c3/Flag_of_France.svg/1920px-Flag_of_France.svg.png"


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
    "COMMANDER",
    "COMMANDER ⬇",
    "COMMANDER ⬆",
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
    html = html.replace(SA_FLAG, FR_FLAG)
    html = html.replace(UK_MAG_SRCSET, FR_MAG_SRCSET)
    return html


def fix_hebrew_comment_block(html: str) -> str:
    html = re.sub(
        r"<p><strong id=\"inm1ej\">ג'וליה</strong></p>\s*"
        r"<p>\s*אני הולכת להזמין את VeinCare מיד![^<]*</p>",
        '<p><strong id="inm1ej">Julie</strong></p>\n'
        "                                    <p>Je vais commander tout de suite BioEdge™ Collagen Oil ! J'ai tellement "
        "hâte de voir comment cela fonctionne et je partagerai mon retour dès que j'aurai des résultats !</p>",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r"<p id=\"icu5xw\"><u id=\"iuw9sl\">לייק</u><span id=\"imz56v\"> · </span><u\s*"
        r'id="ijmwai">תגובה</u><span id="i39t44"> · 👍1 · 3 שעות&nbsp;</span></p>',
        '<p id="icu5xw"><u id="iuw9sl">J\'aime</u><span id="imz56v"> · </span><u '
        'id="ijmwai">Commenter</u><span id="i39t44"> · 👍1 · 3 h&nbsp;</span></p>',
        html,
    )
    return html


def geography_fr(html: str) -> str:
    html = re.sub(r"Trends in\s+South Africa", "Tendances en France", html, flags=re.I)
    html = re.sub(r"\bSouth Africans\b", "Français", html)
    html = re.sub(r"\bSouth African\b", "français", html)
    html = re.sub(r"\bSouth Africa\b", "France", html)
    html = re.sub(r"\bin South Africa\b", "en France", html)
    html = re.sub(r"\bacross South Africa\b", "partout en France", html)
    html = re.sub(
        r"Proudly serving South Africa:",
        "Fiers de servir la France :",
        html,
        flags=re.I,
    )
    html = re.sub(
        r"Special offer for South Africa\b",
        "Offre spéciale pour la France",
        html,
        flags=re.I,
    )
    html = re.sub(r"Trending in South Africa\s*&nbsp;", "Tendances en France&nbsp;", html, flags=re.I)
    html = re.sub(r"Trending in South Africa\b", "Tendances en France", html, flags=re.I)
    html = re.sub(r"\bUnited Kingdom\b", "France", html)
    html = re.sub(r"\bthe UK\b", "la France", html)
    html = re.sub(r"\bUK\b", "France", html)
    html = re.sub(r"\bU\.S\.A\.\b|\bUSA\b|\bUnited States\b", "France", html)
    return html


def apply_zar_snippets(html: str) -> str:
    html = html.replace("R1,000+", "€100+")
    html = html.replace("R 1,000+", "€100+")
    html = re.sub(r"\bZAR\b", "EUR", html)
    return html


def funnel_currency_meta(html: str) -> str:
    html = html.replace('"currency_code": "ZAR"', '"currency_code": "EUR"')
    html = html.replace('"currency_code":"ZAR"', '"currency_code":"EUR"')
    html = html.replace('lang="en-ZA"', 'lang="fr"')
    html = html.replace('<html lang="en">', '<html lang="fr">')
    html = html.replace('<html lang="en" ', '<html lang="fr" ')
    return html


def patch_shipping_script(html: str) -> str:
    html = html.replace("toLocaleString('en-ZA'", "toLocaleString('fr-FR'")
    html = html.replace('toLocaleString("en-ZA"', 'toLocaleString("fr-FR"')
    html = html.replace(
        "const shippingText = 'Ships by ' + formattedDate + ' | FREE Shipping'",
        "const shippingText = 'Expédition prévue avant le ' + formattedDate + ' | LIVRAISON GRATUITE'",
    )
    # If a previous locale left Italian string
    html = html.replace(
        "const shippingText = 'Spedizione prevista entro il ' + formattedDate + ' | SPEDIZIONE GRATUITA'",
        "const shippingText = 'Expédition prévue avant le ' + formattedDate + ' | LIVRAISON GRATUITE'",
    )
    return html


def patch_emergency_number(html: str) -> str:
    html = re.sub(
        r"call your doctor or 911 immediately",
        "appelez immédiatement votre médecin ou le 15 / le 112",
        html,
        flags=re.I,
    )
    html = re.sub(
        r"chiama subito il medico o il 112",
        "appelez immédiatement votre médecin ou le 15 / le 112",
        html,
        flags=re.I,
    )
    return html


def translate_hebrew_nodes(soup: BeautifulSoup) -> None:
    hebrew = re.compile(r"[\u0590-\u05FF]")
    skip_parents = {"script", "style", "noscript", "textarea"}
    ht = GoogleTranslator(source="iw", target="fr")
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
    pairs = [
        ("ORDER NOW ⬇", "COMMANDER ⬇"),
        ("ORDER NOW ⬆", "COMMANDER ⬆"),
        ("ORDER NOW", "COMMANDER"),
        ("USE THE DISCOUNT AND CHECK AVAILABILITY >>", "PROFITEZ DE LA RÉDUCTION ET VÉRIFIEZ LA DISPONIBILITÉ >>"),
        (
            "USE THE DISCOUNT AND\n                      CHECK AVAILABILITY >>",
            "PROFITEZ DE LA RÉDUCTION ET\n                      VÉRIFIEZ LA DISPONIBILITÉ >>",
        ),
        ("USE THE DISCOUNT AND CHECK AVAILABILITY &gt;&gt;", "PROFITEZ DE LA RÉDUCTION ET VÉRIFIEZ LA DISPONIBILITÉ &gt;&gt;"),
        ("Comments", "Commentaires"),
        ("OFFER ENDS IN:", "L'OFFRE SE TERMINE DANS :"),
        (">HRS<", ">H<"),
        (">MIN<", ">MIN<"),
        (">SEC<", ">S<"),
        ("FREE Shipping", "LIVRAISON GRATUITE"),
        ("FREE SHIPPING", "LIVRAISON GRATUITE"),
        ("% OFF • You Save", "% • Vous économisez"),
        ("% OFF</span>", " % DE RÉDUCTION</span>"),
        ("UP TO 82% OFF", "JUSQU'À 82 % DE RÉDUCTION"),
        ("SAVE UP TO 82% OFF", "ÉCONOMISEZ JUSQU'À 82 %"),
        ("Enjoy UP TO 82% OFF today", "Profitez jusqu'à 82 % de réduction aujourd'hui"),
        ("Only<b>", "Seulement<b>"),
        ("</b> each</div>", "</b> l'unité</div>"),
        ("</b> each\n                                    </div>", "</b> l'unité\n                                    </div>"),
        ("Ultimate Deal", "Offre max"),
        ("Best Deal", "Meilleure vente"),
        ("Smart Choice", "Choix malin"),
        ("Basic Choice", "Essentiel"),
        ("Published on", "Publié le"),
        ("Recommended", "Recommandé"),
        ("SATISFACTION GUARANTEE OR YOUR MONEY BACK", "SATISFAIT OU REMBOURSÉ"),
        ("🎁 + Mystery gift for the first 100 customers!", "🎁 + Cadeau mystère pour les 100 premiers clients !"),
        ("DAILY: FIRST 100 CUSTOMERS!", "CHAQUE JOUR : LES 100 PREMIERS CLIENTS !"),
        ("FREE</b> <b", "OFFERT</b> <b"),
        ("Mystery Gifts Worth €100+", "Cadeaux mystères d'une valeur de €100+"),
        ("Mystery Gifts Worth R1,000+", "Cadeaux mystères d'une valeur de €100+"),
        ("⚡️ EXCLUSIVE FACEBOOK SALE!", "⚡️ VENTE EXCLUSIVE FACEBOOK !"),
        ("Only here. Last chance!", "Ici uniquement. Dernière chance !"),
        ("Like</span>", "J'aime</span>"),
        ("Comment</span>", "Commenter</span>"),
        ("Reply</span>", "Répondre</span>"),
        ("From €28.99 ", "À partir de €28.99 "),
        ("• Up to 82% OFF", "• Jusqu'à 82 % de réduction"),
        ("Ships by ", "Expédition prévue avant le "),
        ("Spedizione prevista entro il ", "Expédition prévue avant le "),
        (" | FREE Shipping", " | LIVRAISON GRATUITE"),
        (" | SPEDIZIONE GRATUITA", " | LIVRAISON GRATUITE"),
        ("Over 14,000 verified customers", "Plus de 14 000 clients vérifiés"),
        ("Join thousands of transformational stories today!", "Rejoignez des milliers de transformations dès aujourd'hui !"),
    ]
    for a, b in pairs:
        html = html.replace(a, b)
    return html


def post_geo_after_hebrew(html: str) -> str:
    html = html.replace("Chicago", "Paris")
    html = re.sub(r"\bUSA\b", "France", html)
    html = html.replace("United States", "France")
    html = html.replace("Italie", "France")
    html = re.sub(r"\bItaly\b", "France", html)
    html = re.sub(r"\bItaliano\b", "français", html)
    html = html.replace("EDT", "CET")
    return html


def post_normalize_fr(html: str) -> str:
    html = html.replace("€€", "€")
    html = html.replace("COMMANDANT", "COMMANDER")
    html = html.replace("cadavre</div>", "l'unité</div>")
    html = html.replace("cadavre</", "l'unité</")
    html = re.sub(r"(BioEdge|Collagen)™</strong>([a-zàâäéèêëïîôùûç])", r"\1™</strong> \2", html, flags=re.I)
    html = re.sub(r"([a-zàâäéèêëïîôùûç])<strong>(BioEdge)", r"\1 <strong>\2", html, flags=re.I)
    return html


def localize_payment_gateways(html: str) -> str:
    html = html.replace("info: \"Select your bank below\"", 'info: "Sélectionnez votre banque ci-dessous"')
    html = html.replace(
        "info: 'After clicking \"{SUBMIT_BUTTON}\" you will be redirected to Bancontact to securely complete your payment.'",
        "info: 'Après avoir cliqué sur « {SUBMIT_BUTTON} », vous serez redirigé vers Bancontact pour finaliser votre paiement en toute sécurité.'",
    )
    html = html.replace('title: "Credit / Debit Card"', 'title: "Carte bancaire"')
    html = html.replace(
        "info: '{\"cc\":\"Card number\",\"expiry\":\"MM/YY\",\"cvc\":\"CVC\"}'",
        "info: '{\"cc\":\"Numéro de carte\",\"expiry\":\"MM/AA\",\"cvc\":\"CVC\"}'",
    )
    html = html.replace(
        "info: \"After clicking {SUBMIT_BUTTON} you will be redirected to PayPal to securely complete your purchase.\"",
        "info: \"Après avoir cliqué sur {SUBMIT_BUTTON}, vous serez redirigé vers PayPal pour finaliser votre achat en toute sécurité.\"",
    )
    return html


def process_file(path: Path) -> None:
    print(f"Processing {path.name}...")
    html = path.read_text(encoding="utf-8", errors="ignore")

    html = fix_hebrew_comment_block(html)
    html = geography_fr(html)
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
    out = post_normalize_fr(out)
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
