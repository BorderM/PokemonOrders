from __future__ import annotations

from pathlib import Path

import click
from flask import Flask, flash, redirect, render_template, request, url_for

from .db import create_request, dashboard_stats, init_db, list_people, list_requests
from .importer import import_workbook

LANGUAGES = ["English", "Japanese", "German", "French", "Italian", "Spanish", "Any"]
QUANTITIES = list(range(1, 13))
CONDITIONS = ["Mint", "Near Mint", "Excellent", "Good", "Light Played", "Played", "Poor", "Booster", "Half Booster Box", "Full Booster Box", "Sealed"]
VARIANTS = ["Default", "Reverse Holo", "Holo", "Cosmo", "Ball Reverse", "Other"]
SELLERS = ["bubusini", "cardmarket", "specific seller not needed"]


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config["SECRET_KEY"] = "dev-only-change-me"
    init_db()

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            languages=LANGUAGES,
            quantities=QUANTITIES,
            conditions=CONDITIONS,
            variants=VARIANTS,
            sellers=SELLERS,
            stats=dashboard_stats(),
            recent=list_requests(8),
        )

    @app.post("/requests")
    def submit_request():
        required = ["email", "card_name_code", "language", "quantity", "minimum_condition", "variant"]
        missing = [field for field in required if not request.form.get(field)]
        if missing:
            flash("Please fill in all required fields: " + ", ".join(missing), "error")
            return redirect(url_for("index"))
        create_request(request.form.to_dict())
        flash("Request submitted.", "success")
        return redirect(url_for("index"))

    @app.get("/admin")
    def admin():
        return render_template("admin.html", stats=dashboard_stats(), people=list_people(), requests=list_requests())

    @app.post("/admin/import")
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

    @app.cli.command("import-xlsx")
    @click.argument("path")
    def import_xlsx_command(path: str):
        summary = import_workbook(path)
        print(summary)

    return app


app = create_app()
