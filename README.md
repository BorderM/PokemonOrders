# PokemonOrders

A Docker Compose-ready Flask web app for collecting and managing Pokémon card/product requests.

This project replaces the Google Form + spreadsheet workflow with:

- username/password login for each requester
- automatic requester identity from the logged-in account
- mobile-friendly bulk request entry
- multiple cards/products submitted at once with shared seller/order details
- admin user management
- request/order dashboard
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

## Core workflow

1. Admin creates a user login for each requester.
2. Requester logs in on desktop or mobile.
3. Requester pastes one or more cards/products into the batch box.
4. Shared fields apply to the whole batch:
   - language
   - condition/type
   - variant
   - seller/new seller
   - notes
5. App stores separate request rows linked to the logged-in user.
6. Admin can later price/allocate requests and calculate shipping.

Bulk entry examples:

```text
Misty's Starmie (DRI 047)
2 Cramorant (LOR 050)
Black Bolt JP Booster Box
```

## Run with Docker Compose

```bash
docker compose up --build
```

Open:

http://localhost:8000

Data is stored in a SQLite database under the Docker volume `pokemonorders-data`.

## Create the first admin user

After the container is running:

```bash
docker compose exec web flask --app pokemonorders.app create-user admin CHANGE_ME --name "Admin" --admin
```

Local equivalent:

```bash
flask --app pokemonorders.app create-user admin CHANGE_ME --name "Admin" --admin
```

## Run locally without Docker

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
flask --app pokemonorders.app init-db
flask --app pokemonorders.app create-user admin CHANGE_ME --name "Admin" --admin
flask --app pokemonorders.app run --debug
```

## Import an Excel workbook

In the web app, log in as an admin, go to **Admin → Import Excel**, and upload the workbook.

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

- Add pricing/allocation workflow similar to `Pricing` and `Order_Ledger` sheets.
- Add shipping-rule calculator from `Shipping_Rules`.
- Add request status changes: requested, found, purchased, paid, shipped/handed over.
- Add export back to `.xlsx` or CSV.
- Add password reset/change flow.
