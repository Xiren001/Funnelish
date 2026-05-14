import re
from pathlib import Path


FILES = [
    Path("/Applications/Projects/Funnelish/A - EXPANDING/PowerVibe/IT/italian.html"),
    Path("/Applications/Projects/Funnelish/A - EXPANDING/PowerVibe/IT/italian2.html"),
]

LOCATION_REPLACEMENTS = {
    r"\bSouth Africa\b": "Italia",
    r"\bSouth African\b": "italiano",
    r"\bWestern Cape\b": "Italia",
    r"\bZA\b": "IT",
}

DIRECT_TEXT_MAP = {
    "ADD TO CART": "AGGIUNGI AL CARRELLO",
    "Check Availability": "Controlla disponibilita",
    "EXCLUSIVE": "ESCLUSIVA",
    "OFFER": "OFFERTA",
    "OFF!": "DI SCONTO!",
    "MOST CHOSEN": "PIU SCELTO",
    "BEST OFFER": "MIGLIORE OFFERTA",
    "Only": "Solo",
    "piece": "pezzo",
    "Total": "Totale",
    "Not satisfied? 30-day FREE return guarantee!": "Non soddisfatto? Garanzia di reso GRATUITO di 30 giorni!",
    "GET UP TO 80% OFF": "OTTIENI FINO ALL'80% DI SCONTO",
    "Use the discount while it’s still available.": "Usa lo sconto finche e ancora disponibile.",
    "Available for a limited time only.": "Disponibile solo per un periodo limitato.",
    "Revolutionary Breakthrough: Leading South African Sexologist Approves Seaweed-Based Spray for Erectile Issues": "Svolta rivoluzionaria: una rinomata sessuologa italiana approva uno spray a base di alghe per i problemi erettili",
    "ADD TO CART": "AGGIUNGI AL CARRELLO",
    "Not satisfied? 30-day FREE return guarantee!": "Non soddisfatto? Garanzia di reso GRATUITO di 30 giorni!",
    "Not satisfied? 30-day FREE return": "Non soddisfatto? Reso GRATUITO di 30 giorni",
    "guarantee!": "garantito!",
    "Only ": "Solo ",
    " / piece": " / pezzo",
}

OFFER_BLOCKS = {
    "1x PowerVibe™": {
        "unit": "Solo €26.99 / pezzo",
        "total": "Totale: €26.99",
        "strike": "€53.99",
        "badge": "50% DI SCONTO!",
    },
    "2x PowerVibe™": {
        "unit": "Solo €14.99 / pezzo",
        "total": "Totale: €29.99",
        "strike": "€107.99",
        "badge": "72% DI SCONTO!",
    },
    "3x PowerVibe™": {
        "unit": "Solo €10.99 / pezzo",
        "total": "Totale: €32.99",
        "strike": "€161.99",
        "badge": "80% DI SCONTO!",
    },
    "5x PowerVibe™": {
        "unit": "Solo €7.99 / pezzo",
        "total": "Totale: €37.99",
        "strike": "€269.99",
        "badge": "86% DI SCONTO!",
    },
}


def apply_location_rules(text: str) -> str:
    out = text
    for pattern, replacement in LOCATION_REPLACEMENTS.items():
        out = re.sub(pattern, replacement, out)
    return out


def translate_html(content: str) -> str:
    output = content
    output = output.replace('lang="en"', 'lang="it"')

    output = apply_location_rules(output)
    for src, dest in DIRECT_TEXT_MAP.items():
        output = output.replace(src, dest)

    output = output.replace('"currency_code":"ZAR"', '"currency_code":"EUR"')
    output = output.replace('"currency_code": "ZAR"', '"currency_code": "EUR"')

    output = re.sub(r"\bR(?=\d)", "€", output)
    output = re.sub(r"(?<!\w)\$(\s*\d[\d,]*(?:\.\d{2})?)", r"€\1", output)

    for key, vals in OFFER_BLOCKS.items():
        if key in output:
            block_start = output.find(key)
            window_start = max(0, block_start - 3000)
            window_end = min(len(output), block_start + 5000)
            chunk = output[window_start:window_end]

            chunk = re.sub(r"Solo\s*€[\d\.,]+\s*/\s*pezzo", vals["unit"], chunk)
            chunk = re.sub(r"Totale\s*:\s*€[\d\.,]+", vals["total"], chunk)
            chunk = re.sub(r"<s>\s*€[\d\.,]+\s*</s>", f"<s>{vals['strike']}</s>", chunk)
            chunk = re.sub(r"\d{2}%\s*(?:DI SCONTO!|OFF!)", vals["badge"], chunk)

            output = output[:window_start] + chunk + output[window_end:]

    output = output.replace("1x PowerVibe™", "1x PowerVibe™")
    output = output.replace("2x PowerVibe™", "2x PowerVibe™")
    output = output.replace("3x PowerVibe™", "3x PowerVibe™")
    output = output.replace("5x PowerVibe™", "5x PowerVibe™")

    output = output.replace("en-za", "it-it")
    return output


def main():
    for file_path in FILES:
        html = file_path.read_text(encoding="utf-8", errors="ignore")
        translated = translate_html(html)
        file_path.write_text(translated, encoding="utf-8")
        print(f"Updated: {file_path}")


if __name__ == "__main__":
    main()
