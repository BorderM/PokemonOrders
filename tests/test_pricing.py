from pokemonorders.pricing import parse_cardmarket_receipt


def test_parse_cardmarket_receipt_extracts_qty_condition_and_prices():
    receipt = """
    1x    Magnezone Lv.48 (DP 8)
    #8
    EX
        3,99 €
    1x    Silvally GX (CEC 262)
    #262
    GD
        14,99 €
    2x    Ariados (BRS TG09)
    #TG09
    NM
        1,49 €
    """

    rows = parse_cardmarket_receipt(receipt)

    assert rows == [
        {"quantity": 1, "card_product": "Magnezone Lv.48 (DP 8)", "condition": "Excellent", "unit_price": 3.99, "total_price": 3.99, "variant": "Default"},
        {"quantity": 1, "card_product": "Silvally GX (CEC 262)", "condition": "Good", "unit_price": 14.99, "total_price": 14.99, "variant": "Default"},
        {"quantity": 2, "card_product": "Ariados (BRS TG09)", "condition": "Near Mint", "unit_price": 1.49, "total_price": 2.98, "variant": "Default"},
    ]
