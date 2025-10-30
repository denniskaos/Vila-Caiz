"""Interface web para a aplicação de gestão do Vila-Caiz."""
from __future__ import annotations

import argparse
from datetime import date
from typing import Dict, Tuple

from flask import Flask, flash, redirect, render_template, request, url_for

from .services import ClubService
from .storage import parse_date


def create_app() -> Flask:
    """Criar e configurar a aplicação Flask."""

    app = Flask(__name__, template_folder="../templates")
    app.config["SECRET_KEY"] = "vila-caiz-demo"

    def get_service() -> ClubService:
        return ClubService()

    @app.template_filter("format_currency")
    def format_currency(value: float) -> str:
        formatted = f"{value:,.2f}"
        formatted = formatted.replace(",", "_")
        formatted = formatted.replace(".", ",")
        formatted = formatted.replace("_", ".")
        return f"€{formatted}"

    @app.get("/")
    def dashboard():
        service = get_service()
        players = service.list_players()
        coaches = service.list_coaches()
        physios = service.list_physiotherapists()
        youth_teams = service.list_youth_teams()
        members = service.list_members()
        revenues, expenses = service.list_financial_records()
        summary = service.financial_summary()
        coach_lookup = {coach.id: coach.name for coach in coaches}
        revenue_categories: Dict[str, float] = {}
        expense_categories: Dict[str, float] = {}
        for key, value in summary.items():
            if key.startswith("revenue:"):
                revenue_categories[key.split(":", 1)[1]] = value
            elif key.startswith("expense:"):
                expense_categories[key.split(":", 1)[1]] = value
        return render_template(
            "dashboard.html",
            title="Centro Operacional",
            players=players,
            coaches=coaches,
            physios=physios,
            youth_teams=youth_teams,
            members=members,
            revenues=revenues,
            expenses=expenses,
            summary=summary,
            coach_lookup=coach_lookup,
            revenue_categories=revenue_categories,
            expense_categories=expense_categories,
        )

    def _handle_date(field: str) -> Tuple[bool, date | None]:
        value = request.form.get(field)
        try:
            parsed = parse_date(value)
        except ValueError:
            return False, None
        return True, parsed

    def _flash_invalid(message: str) -> None:
        flash(message, "error")

    @app.post("/players")
    def add_player():
        name = request.form.get("name", "").strip()
        position = request.form.get("position", "").strip()
        squad = request.form.get("squad", "senior").strip()
        contact = request.form.get("contact", "").strip() or None
        shirt_number_raw = request.form.get("shirt_number", "").strip()
        ok_birthdate, birthdate = _handle_date("birthdate")
        if not ok_birthdate:
            _flash_invalid("Data de nascimento inválida para o jogador.")
            return redirect(url_for("dashboard") + "#jogadores")
        shirt_number = None
        if shirt_number_raw:
            try:
                shirt_number = int(shirt_number_raw)
            except ValueError:
                _flash_invalid("Número da camisola inválido.")
                return redirect(url_for("dashboard") + "#jogadores")
        if not name or not position:
            _flash_invalid("Nome e posição são obrigatórios.")
            return redirect(url_for("dashboard") + "#jogadores")
        service = get_service()
        service.add_player(
            name=name,
            position=position,
            squad=squad or "senior",
            birthdate=birthdate,
            contact=contact,
            shirt_number=shirt_number,
        )
        flash("Jogador registado com sucesso!", "success")
        return redirect(url_for("dashboard") + "#jogadores")

    @app.post("/coaches")
    def add_coach():
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "").strip()
        license_level = request.form.get("license_level", "").strip() or None
        contact = request.form.get("contact", "").strip() or None
        ok_birthdate, birthdate = _handle_date("birthdate")
        if not ok_birthdate:
            _flash_invalid("Data de nascimento inválida para o treinador.")
            return redirect(url_for("dashboard") + "#equipa-tecnica")
        if not name or not role:
            _flash_invalid("Nome e função são obrigatórios.")
            return redirect(url_for("dashboard") + "#equipa-tecnica")
        service = get_service()
        service.add_coach(
            name=name,
            role=role,
            license_level=license_level,
            birthdate=birthdate,
            contact=contact,
        )
        flash("Treinador registado com sucesso!", "success")
        return redirect(url_for("dashboard") + "#equipa-tecnica")

    @app.post("/physios")
    def add_physio():
        name = request.form.get("name", "").strip()
        specialization = request.form.get("specialization", "").strip() or None
        contact = request.form.get("contact", "").strip() or None
        ok_birthdate, birthdate = _handle_date("birthdate")
        if not ok_birthdate:
            _flash_invalid("Data de nascimento inválida para o profissional.")
            return redirect(url_for("dashboard") + "#fisioterapia")
        if not name:
            _flash_invalid("O nome do profissional é obrigatório.")
            return redirect(url_for("dashboard") + "#fisioterapia")
        service = get_service()
        service.add_physiotherapist(
            name=name,
            specialization=specialization,
            birthdate=birthdate,
            contact=contact,
        )
        flash("Profissional registado com sucesso!", "success")
        return redirect(url_for("dashboard") + "#fisioterapia")

    @app.post("/youth-teams")
    def add_youth_team():
        name = request.form.get("name", "").strip()
        age_group = request.form.get("age_group", "").strip()
        coach_id_raw = request.form.get("coach_id", "").strip()
        coach_id = None
        if coach_id_raw:
            try:
                coach_id = int(coach_id_raw)
            except ValueError:
                _flash_invalid("ID do treinador inválido.")
                return redirect(url_for("dashboard") + "#formacao")
        if not name or not age_group:
            _flash_invalid("Nome e escalão da equipa são obrigatórios.")
            return redirect(url_for("dashboard") + "#formacao")
        service = get_service()
        service.add_youth_team(
            name=name,
            age_group=age_group,
            coach_id=coach_id,
        )
        flash("Equipa de formação criada!", "success")
        return redirect(url_for("dashboard") + "#formacao")

    @app.post("/members")
    def add_member():
        name = request.form.get("name", "").strip()
        membership_type = request.form.get("membership_type", "").strip()
        contact = request.form.get("contact", "").strip() or None
        ok_birthdate, birthdate = _handle_date("birthdate")
        if not ok_birthdate:
            _flash_invalid("Data de nascimento inválida para o sócio.")
            return redirect(url_for("dashboard") + "#socios")
        dues_paid = request.form.get("dues_paid") == "on"
        if not name or not membership_type:
            _flash_invalid("Nome e tipo de quota são obrigatórios.")
            return redirect(url_for("dashboard") + "#socios")
        service = get_service()
        service.add_member(
            name=name,
            membership_type=membership_type,
            dues_paid=dues_paid,
            contact=contact,
            birthdate=birthdate,
        )
        flash("Sócio registado com sucesso!", "success")
        return redirect(url_for("dashboard") + "#socios")

    def _parse_amount(field: str) -> float | None:
        raw = request.form.get(field, "").strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    def _handle_financial_date() -> date:
        ok, record_date = _handle_date("record_date")
        if not ok or record_date is None:
            _flash_invalid("Data inválida para o registo financeiro.")
            raise ValueError("invalid date")
        return record_date

    @app.post("/finance/revenue")
    def add_revenue():
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        source = request.form.get("source", "").strip() or None
        amount = _parse_amount("amount")
        if amount is None or amount <= 0:
            _flash_invalid("Montante da receita inválido.")
            return redirect(url_for("dashboard") + "#receitas")
        try:
            record_date = _handle_financial_date()
        except ValueError:
            return redirect(url_for("dashboard") + "#receitas")
        if not description or not category:
            _flash_invalid("Descrição e categoria são obrigatórias.")
            return redirect(url_for("dashboard") + "#receitas")
        service = get_service()
        service.add_revenue(
            description=description,
            amount=amount,
            category=category,
            record_date=record_date,
            source=source,
        )
        flash("Receita registada com sucesso!", "success")
        return redirect(url_for("dashboard") + "#receitas")

    @app.post("/finance/expense")
    def add_expense():
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        vendor = request.form.get("vendor", "").strip() or None
        amount = _parse_amount("amount")
        if amount is None or amount <= 0:
            _flash_invalid("Montante da despesa inválido.")
            return redirect(url_for("dashboard") + "#despesas")
        try:
            record_date = _handle_financial_date()
        except ValueError:
            return redirect(url_for("dashboard") + "#despesas")
        if not description or not category:
            _flash_invalid("Descrição e categoria são obrigatórias.")
            return redirect(url_for("dashboard") + "#despesas")
        service = get_service()
        service.add_expense(
            description=description,
            amount=amount,
            category=category,
            record_date=record_date,
            vendor=vendor,
        )
        flash("Despesa registada com sucesso!", "success")
        return redirect(url_for("dashboard") + "#despesas")

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Iniciar interface web do Vila-Caiz")
    parser.add_argument("--host", default="0.0.0.0", help="Host a utilizar")
    parser.add_argument("--port", type=int, default=5000, help="Porta do servidor")
    parser.add_argument("--debug", action="store_true", help="Ativar modo debug")
    args = parser.parse_args()
    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
