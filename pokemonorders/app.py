from __future__ import annotations

from functools import wraps
from pathlib import Path

import click
from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from .db import (
    add_pricing_rows,
    create_request,
    create_user,
    dashboard_stats,
    get_user,
    get_user_by_username,
    init_db,
    list_people,
    list_pricing_entries,
    list_requests,
    list_users,
)
from .importer import import_workbook
from .pricing import parse_cardmarket_receipt

LANGUAGES = ["English", "Japanese", "German", "French", "Italian", "Spanish", "Any"]
QUANTITIES = list(range(1, 13))
CONDITIONS = ["Mint", "Near Mint", "Excellent", "Good", "Light Played", "Played", "Poor", "Booster", "Half Booster Box", "Full Booster Box", "Sealed"]
VARIANTS = ["Default", "Reverse Holo", "Holo", "Cosmo", "Ball Reverse", "Other"]
SELLERS = ["bubusini", "cardmarket", "specific seller not needed"]


def parse_bulk_cards(text: str) -> list[dict]:
    cards: list[dict] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        variant = None
        if " - " in line:
            possible_name, variant_text = line.rsplit(" - ", 1)
            clean_variant = variant_text.strip()
            known_variants = {item.lower(): item for item in VARIANTS}
            if clean_variant.lower() in known_variants:
                line = possible_name.strip()
                variant = known_variants[clean_variant.lower()]

        qty = 1
        name = line
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            first = parts[0].lower().rstrip("x")
            if first.isdigit():
                qty = int(first)
                name = parts[1].strip()

        cards.append({"quantity": qty, "card_name_code": name, "variant": variant})
    return cards


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login", next=request.path))
        if not g.user["is_admin"]:
            flash("Admin access required.", "error")
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapped


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config["SECRET_KEY"] = __import__("os").environ.get("POKEMONORDERS_SECRET_KEY", "dev-only-change-me")
    init_db()

    @app.before_request
    def load_logged_in_user():
        user_id = session.get("user_id")
        g.user = get_user(user_id) if user_id else None

    @app.get("/")
    def index():
        if g.user and not g.user["is_admin"]:
            recent = list_requests(8, user_id=g.user["id"])
        else:
            recent = list_requests(8)
        return render_template(
            "index.html",
            languages=LANGUAGES,
            quantities=QUANTITIES,
            conditions=CONDITIONS,
            variants=VARIANTS,
            sellers=SELLERS,
            stats=dashboard_stats(),
            recent=recent,
            user=g.user,
        )

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            user = get_user_by_username(request.form.get("username", ""))
            if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
                session.clear()
                session["user_id"] = user["id"]
                return redirect(request.args.get("next") or url_for("index"))
            flash("Invalid username or password.", "error")
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.post("/requests")
    @login_required
    def submit_request():
        bulk_text = request.form.get("bulk_cards", "")
        cards = parse_bulk_cards(bulk_text)
        if not cards and request.form.get("card_name_code"):
            cards = [{
                "quantity": int(request.form.get("quantity", 1)),
                "card_name_code": request.form["card_name_code"],
                "variant": request.form.get("variant"),
            }]
        required = ["language", "minimum_condition", "variant"]
        missing = [field for field in required if not request.form.get(field)]
        if missing or not cards:
            flash("Add at least one card and fill in all required shared fields.", "error")
            return redirect(url_for("index"))

        count = 0
        for card in cards:
            create_request({
                "email": g.user["email"] or f"{g.user['username']}@local.user",
                "name": g.user["display_name"],
                "user_id": g.user["id"],
                "card_name_code": card["card_name_code"],
                "language": request.form["language"],
                "quantity": card["quantity"],
                "minimum_condition": request.form["minimum_condition"],
                "variant": card["variant"] or request.form["variant"],
                "seller": request.form.get("seller"),
                "new_seller": request.form.get("new_seller"),
                "notes": request.form.get("notes"),
                "source": "web:bulk" if len(cards) > 1 else "web",
            })
            count += 1
        flash(f"Submitted {count} request line{'s' if count != 1 else ''}.", "success")
        return redirect(url_for("index"))

    @app.get("/admin")
    @admin_required
    def admin():
        return render_template(
            "admin.html",
            stats=dashboard_stats(),
            people=list_people(),
            users=list_users(),
            requests=list_requests(),
            pricing_entries=list_pricing_entries(80),
        )

    @app.post("/admin/pricing/receipt")
    @admin_required
    def import_cardmarket_receipt():
        rows = parse_cardmarket_receipt(request.form.get("receipt", ""))
        if not rows:
            flash("No Cardmarket pricing rows found in that receipt paste.", "error")
            return redirect(url_for("admin"))
        count = add_pricing_rows(rows, requester_name=request.form.get("requester_name") or None)
        flash(f"Imported {count} pricing rows from receipt.", "success")
        return redirect(url_for("admin"))

    @app.post("/admin/users")
    @admin_required
    def admin_create_user():
        required = ["username", "password", "display_name"]
        if any(not request.form.get(field) for field in required):
            flash("Username, password, and display name are required.", "error")
            return redirect(url_for("admin"))
        create_user(
            request.form["username"],
            request.form["password"],
            request.form["display_name"],
            request.form.get("email") or None,
            bool(request.form.get("is_admin")),
        )
        flash("User saved.", "success")
        return redirect(url_for("admin"))

    @app.post("/admin/import")
    @admin_required
    def import_excel():
        upload = request.files.get("workbook")
        if not upload or not upload.filename:
            flash("Choose an .xlsx file to import.", "error")
            return redirect(url_for("admin"))
        upload_dir = Path("/uploads") if Path("/uploads").exists() else Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        path = upload_dir / upload.filename
        upload.save(path)
        summary = import_workbook(path)
        flash(
            f"Imported {summary['requests']} requests, {summary['people']} people, "
            f"{summary['pricing_entries']} pricing rows, and {summary['shipping_rules']} shipping rules.",
            "success",
        )
        return redirect(url_for("admin"))

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Database initialized.")

    @app.cli.command("create-user")
    @click.argument("username")
    @click.argument("password")
    @click.option("--name", default=None, help="Display name")
    @click.option("--email", default=None, help="Optional email")
    @click.option("--admin", is_flag=True, help="Make the user an admin")
    def create_user_command(username: str, password: str, name: str | None, email: str | None, admin: bool):
        user_id = create_user(username, password, name, email, admin)
        print(f"Saved user {username} with id {user_id}.")

    @app.cli.command("import-xlsx")
    @click.argument("path")
    def import_xlsx_command(path: str):
        summary = import_workbook(path)
        print(summary)

    return app


app = create_app()
