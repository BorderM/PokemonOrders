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
4. Shared fields apply to the whole batch unless a line overrides the variant:
   - language
   - condition/type
   - default variant
   - seller/new seller
   - notes
5. App stores separate request rows linked to the logged-in user.
6. Admin can later price/allocate requests and calculate shipping.

Bulk entry examples:

```text
Misty's Starmie (DRI 047) | Reverse Holo
2 Cramorant (LOR 050) | Holo
Black Bolt JP Booster Box
```

Use `| Variant` when a specific line needs a different variant. Lines without a pipe use the selected default variant.

## Run with Docker Compose

```bash
docker compose up --build
```

Open:

http://localhost:8000

Data is stored in a SQLite database under the Docker volume `pokemonorders-data`.

## Default admin user

The app creates a default admin login automatically:

```text
username: admin
password: admin
```

This keeps local/dev setup simple. Change it later from the admin user form or by running `create-user` again with a stronger password.

CLI example:

```bash
flask --app pokemonorders.app create-user admin NEW_PASSWORD --name "Admin" --admin
```

Docker equivalent:

```bash
docker compose exec web flask --app pokemonorders.app create-user admin NEW_PASSWORD --name "Admin" --admin
```

## Public/requester access

- Anyone can view the request overview and quantities.
- Users must log in to add requests, so their cards attach to the right person automatically.
- Admin users can create logins, import Excel, and paste Cardmarket receipt/pricing data.

## Run locally without Docker

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
flask --app pokemonorders.app init-db
flask --app pokemonorders.app run --debug
```

## Import an Excel workbook

In the web app, log in as an admin, go to **Admin → Import Excel**, and upload the workbook.

CLI:

```bash
flask --app pokemonorders.app import-xlsx /path/to/Poke_Order.xlsx
```

The importer does not need the original file committed to the repo. Do **not** commit real order spreadsheets because they contain personal emails/order data.

## Paste Cardmarket receipt pricing

Admins can paste receipt text in the admin page. The parser supports receipt blocks like:

```text
1x    Magnezone Lv.48 (DP 8)
#8
EX
    3,99 €
```

It converts condition codes such as `EX`, `GD`, and `NM`, parses comma-decimal euro prices, and stores quantity, card/product, condition, unit price, and total price as pricing entries.

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
