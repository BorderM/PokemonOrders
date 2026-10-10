from __future__ import annotations

import re

CONDITIONS = {
    "MT": "Mint",
    "MINT": "Mint",
    "NM": "Near Mint",
    "NEAR MINT": "Near Mint",
    "EX": "Excellent",
    "EXC": "Excellent",
    "EXCELLENT": "Excellent",
    "GD": "Good",
    "GOOD": "Good",
    "SEALED": "Sealed",
}


def parse_euro_price(value: str) -> float:
    s = str(value).replace("€", "").replace(" ", "").strip()
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    return round(float(s), 2)


def normalize_condition(value: str) -> str:
    return CONDITIONS.get(str(value).strip().upper(), str(value).strip())


def detect_variant(text: str) -> str:
    s = text.lower()
    if "reverse" in s:
        return "Reverse Holo"
    if "holo" in s:
        return "Holo"
    return "Default"


def parse_cardmarket_receipt(text: str) -> list[dict]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    rows: list[dict] = []

    for index, line in enumerate(lines):
        match = re.match(r"^(\d+)x\s+(.+)$", line, flags=re.IGNORECASE)
        if not match:
            continue

        quantity = int(match.group(1))
        card_product = match.group(2).strip()
        condition = ""
        unit_price = None
        nearby_text = " ".join(lines[index : index + 8])
        variant = detect_variant(nearby_text)

        for nearby in lines[index + 1 : index + 8]:
            condition_match = re.fullmatch(r"(MT|NM|EX|EXC|GD|GOOD|MINT|NEAR MINT|EXCELLENT|SEALED)", nearby, flags=re.IGNORECASE)
            if condition_match and not condition:
                condition = normalize_condition(condition_match.group(1))
            if "€" in nearby and unit_price is None:
                unit_price = parse_euro_price(nearby)

        if unit_price is None:
            continue

        rows.append({
            "quantity": quantity,
            "card_product": card_product,
            "condition": condition,
            "unit_price": unit_price,
            "total_price": round(quantity * unit_price, 2),
            "variant": variant,
        })

    return rows
