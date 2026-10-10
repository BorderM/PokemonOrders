# PokemonOrders

A Docker Compose-ready Flask web app for collecting and managing Pokémon card/product requests.

This is intended to replace the current Google Form + spreadsheet workflow with:

- email-based requester identity
- request form matching the current Poke Requests fields
- order/request dashboard
- people/requester mapping
- pricing/allocation ledger foundation
- Excel import support for the existing workbook structure

## What was inferred from the uploaded workbook

The uploaded `Poke_Order.xlsx` contains sheets such as:

- `Orders_Clean` — normalized request rows with timestamp, name, email, card, quantity, language, condition, variant, seller, notes.
- `Orders` — raw Google Form responses.
- `People` — email-to-display-name mapping.
- `Pricing`, `Pricing Manual`, and archive sheets — priced/purchased rows with requester, qty, card, condition, variant, price, total price, shipping units, notes.
- `Order_Ledger` — historical purchase/allocation ledger.
- `Shipping_Rules` — unit rules for cards, boosters, sealed products, and value-based extra units.

The screenshots show a public request form with these fields:

- Email
- Card Name + code
- Language
- Quantity
- Minimum Condition / Type of Booster/Box
- Variant: Default / Reverse Holo / Other
- Specific Seller
- New Seller if not listed
- Notes

## Run with Docker Compose

```bash
docker compose up --build
```

Open:

http://localhost:8000

Data is stored in a SQLite database under the Docker volume `pokemonorders-data`.

## Run locally without Docker

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
flask --app pokemonorders.app init-db
flask --app pokemonorders.app run --debug
```

## Import an Excel workbook

In the web app, go to **Admin → Import Excel** and upload the workbook.

CLI:

```bash
flask --app pokemonorders.app import-xlsx /path/to/Poke_Order.xlsx
```

The importer does not need the original file committed to the repo. Do **not** commit real order spreadsheets because they contain personal emails/order data.

## Tests

```bash
python -m pytest -q
```

## Next steps

- Add proper authentication if desired: Google OAuth, magic-link email login, or simple admin password.
- Add seller management and dropdown values from database.
- Add pricing/allocation workflow similar to `Pricing` and `Order_Ledger` sheets.
- Add shipping-rule calculator from `Shipping_Rules`.
- Add export back to `.xlsx` or CSV.
