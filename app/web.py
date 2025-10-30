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

    def _split_categories(summary: Dict[str, float]) -> Tuple[Dict[str, float], Dict[str, float]]:
        revenue_categories: Dict[str, float] = {}
        expense_categories: Dict[str, float] = {}
        for key, value in summary.items():
            if key.startswith("revenue:"):
                revenue_categories[key.split(":", 1)[1]] = value
            elif key.startswith("expense:"):
                expense_categories[key.split(":", 1)[1]] = value
        return revenue_categories, expense_categories

    @app.get("/")
    def dashboard():
        service = get_service()
        players = service.list_players()
        coaches = service.list_coaches()
        physios = service.list_physiotherapists()
        youth_teams = service.list_youth_teams()
        members = service.list_members()
        summary = service.financial_summary()
        return render_template(
            "dashboard.html",
            title="Centro Operacional",
            active_page="dashboard",
            players=players,
            coaches=coaches,
            physios=physios,
            youth_teams=youth_teams,
            members=members,
            summary=summary,
        )

    @app.get("/jogadores")
    def players_page():
        service = get_service()
        players = service.list_players()
        return render_template(
            "players.html",
            title="Jogadores",
            active_group="plantel",
            active_page="players",
            players=players,
        )

    @app.get("/equipa-tecnica")
    def coaches_page():
        service = get_service()
        coaches = service.list_coaches()
        return render_template(
            "coaches.html",
            title="Equipa Técnica",
            active_group="plantel",
            active_page="coaches",
            coaches=coaches,
        )

    @app.get("/departamento-medico")
    def physios_page():
        service = get_service()
        physios = service.list_physiotherapists()
        return render_template(
            "physios.html",
            title="Departamento Médico",
            active_group="plantel",
            active_page="physios",
            physios=physios,
        )

    @app.get("/camadas-jovens")
    def youth_page():
        service = get_service()
        youth_teams = service.list_youth_teams()
        coaches = service.list_coaches()
        coach_lookup = {coach.id: coach.name for coach in coaches}
        return render_template(
            "youth.html",
            title="Camadas Jovens",
            active_group="plantel",
            active_page="youth",
            youth_teams=youth_teams,
            coaches=coaches,
            coach_lookup=coach_lookup,
        )

    @app.get("/socios")
    def members_page():
        service = get_service()
        members = service.list_members()
        return render_template(
            "members.html",
            title="Sócios",
            active_group="plantel",
            active_page="members",
            members=members,
        )

    def _render_finances(active_page: str, focus_section: str | None = None):
        service = get_service()
        revenues, expenses = service.list_financial_records()
        summary = service.financial_summary()
        revenue_categories, expense_categories = _split_categories(summary)
        return render_template(
            "finances.html",
            title="Finanças",
            active_group="financas",
            active_page=active_page,
            focus_section=focus_section,
            revenues=revenues,
            expenses=expenses,
            summary=summary,
            revenue_categories=revenue_categories,
            expense_categories=expense_categories,
        )

    @app.get("/financas")
    def finances_page():
        return _render_finances("finances-overview")

    @app.get("/financas/receitas")
    def finances_revenue_page():
        return _render_finances("finances-revenue", "receitas")

    @app.get("/financas/despesas")
    def finances_expense_page():
        return _render_finances("finances-expense", "despesas")

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
            return redirect(url_for("players_page"))
        shirt_number = None
        if shirt_number_raw:
            try:
                shirt_number = int(shirt_number_raw)
            except ValueError:
                _flash_invalid("Número da camisola inválido.")
                return redirect(url_for("players_page"))
        if not name or not position:
            _flash_invalid("Nome e posição são obrigatórios.")
            return redirect(url_for("players_page"))
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
        return redirect(url_for("players_page"))

    @app.post("/coaches")
    def add_coach():
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "").strip()
        license_level = request.form.get("license_level", "").strip() or None
        contact = request.form.get("contact", "").strip() or None
        ok_birthdate, birthdate = _handle_date("birthdate")
        if not ok_birthdate:
            _flash_invalid("Data de nascimento inválida para o treinador.")
            return redirect(url_for("coaches_page"))
        if not name or not role:
            _flash_invalid("Nome e função são obrigatórios.")
            return redirect(url_for("coaches_page"))
        service = get_service()
        service.add_coach(
            name=name,
            role=role,
            license_level=license_level,
            birthdate=birthdate,
            contact=contact,
        )
        flash("Treinador registado com sucesso!", "success")
        return redirect(url_for("coaches_page"))

    @app.post("/physios")
    def add_physio():
        name = request.form.get("name", "").strip()
        specialization = request.form.get("specialization", "").strip() or None
        contact = request.form.get("contact", "").strip() or None
        ok_birthdate, birthdate = _handle_date("birthdate")
        if not ok_birthdate:
            _flash_invalid("Data de nascimento inválida para o profissional.")
            return redirect(url_for("physios_page"))
        if not name:
            _flash_invalid("O nome do profissional é obrigatório.")
            return redirect(url_for("physios_page"))
        service = get_service()
        service.add_physiotherapist(
            name=name,
            specialization=specialization,
            birthdate=birthdate,
            contact=contact,
        )
        flash("Profissional registado com sucesso!", "success")
        return redirect(url_for("physios_page"))

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
                return redirect(url_for("youth_page"))
        if not name or not age_group:
            _flash_invalid("Nome e escalão da equipa são obrigatórios.")
            return redirect(url_for("youth_page"))
        service = get_service()
        service.add_youth_team(
            name=name,
            age_group=age_group,
            coach_id=coach_id,
        )
        flash("Equipa de formação criada!", "success")
        return redirect(url_for("youth_page"))

    @app.post("/members")
    def add_member():
        name = request.form.get("name", "").strip()
        membership_type = request.form.get("membership_type", "").strip()
        contact = request.form.get("contact", "").strip() or None
        ok_birthdate, birthdate = _handle_date("birthdate")
        if not ok_birthdate:
            _flash_invalid("Data de nascimento inválida para o sócio.")
            return redirect(url_for("members_page"))
        dues_paid = request.form.get("dues_paid") == "on"
        if not name or not membership_type:
            _flash_invalid("Nome e tipo de quota são obrigatórios.")
            return redirect(url_for("members_page"))
        service = get_service()
        service.add_member(
            name=name,
            membership_type=membership_type,
            dues_paid=dues_paid,
            contact=contact,
            birthdate=birthdate,
        )
        flash("Sócio registado com sucesso!", "success")
        return redirect(url_for("members_page"))

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
            return redirect(url_for("finances_revenue_page"))
        try:
            record_date = _handle_financial_date()
        except ValueError:
            return redirect(url_for("finances_revenue_page"))
        if not description or not category:
            _flash_invalid("Descrição e categoria são obrigatórias.")
            return redirect(url_for("finances_revenue_page"))
        service = get_service()
        service.add_revenue(
            description=description,
            amount=amount,
            category=category,
            record_date=record_date,
            source=source,
        )
        flash("Receita registada com sucesso!", "success")
        return redirect(url_for("finances_revenue_page"))

    @app.post("/finance/expense")
    def add_expense():
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        vendor = request.form.get("vendor", "").strip() or None
        amount = _parse_amount("amount")
        if amount is None or amount <= 0:
            _flash_invalid("Montante da despesa inválido.")
            return redirect(url_for("finances_expense_page"))
        try:
            record_date = _handle_financial_date()
        except ValueError:
            return redirect(url_for("finances_expense_page"))
        if not description or not category:
            _flash_invalid("Descrição e categoria são obrigatórias.")
            return redirect(url_for("finances_expense_page"))
        service = get_service()
        service.add_expense(
            description=description,
            amount=amount,
            category=category,
            record_date=record_date,
            vendor=vendor,
        )
        flash("Despesa registada com sucesso!", "success")
        return redirect(url_for("finances_expense_page"))

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Iniciar interface web do Vila-Caiz")
    parser.add_argument("--host", default="0.0.0.0", help="Host a utilizar")
    parser.add_argument("--port", type=int, default=5000, help="Porta do servidor")
    parser.add_argument("--debug", action="store_true", help="Ativar modo debug")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
