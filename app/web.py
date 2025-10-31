"""Interface web para a aplicação de gestão do Vila-Caiz."""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Dict, Optional, Tuple
from uuid import uuid4

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from .services import ClubService, YOUTH_SQUADS
from .storage import parse_date


def create_app() -> Flask:
    """Criar e configurar a aplicação Flask."""

    base_dir = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
    )
    app.config["SECRET_KEY"] = "vila-caiz-demo"
    upload_folder = Path(app.static_folder) / "uploads"
    upload_folder.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = upload_folder
    app.config["ALLOWED_IMAGE_EXTENSIONS"] = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

    def get_service() -> ClubService:
        return ClubService()

    @app.context_processor
    def inject_season_context():
        service = get_service()
        seasons = service.list_seasons()
        active_season = None
        try:
            active_id = service.active_season_id
        except ValueError:
            active_id = None
        if active_id is not None:
            for season in seasons:
                if season.id == active_id:
                    active_season = season
                    break
        elif seasons:
            active_season = seasons[0]
        return {
            "season_options": seasons,
            "active_season": active_season,
        }

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

    @app.template_filter("photo_path")
    def photo_path(source: Optional[str]) -> Optional[str]:
        if not source:
            return None
        if source.startswith(("http://", "https://", "/")):
            return source
        return url_for("static", filename=source)

    def _process_photo_upload(field_name: str, *, existing: Optional[str] = None) -> Tuple[Optional[str], bool, Optional[str]]:
        file = request.files.get(field_name)
        if file is None or not file.filename:
            return existing, False, None
        filename = secure_filename(file.filename)
        if not filename:
            return existing, False, "Ficheiro de imagem inválido."
        extension = Path(filename).suffix.lower()
        allowed_extensions = app.config["ALLOWED_IMAGE_EXTENSIONS"]
        if extension not in allowed_extensions:
            return existing, False, "Formato de imagem não suportado. Utilize PNG, JPG, JPEG, GIF ou WEBP."
        upload_dir = Path(app.config["UPLOAD_FOLDER"])
        upload_dir.mkdir(parents=True, exist_ok=True)
        new_filename = f"{uuid4().hex}{extension}"
        destination = upload_dir / new_filename
        file.save(destination)
        if existing and not existing.startswith(("http://", "https://", "/")):
            old_path = Path(app.static_folder) / existing
            if old_path.exists():
                old_path.unlink()
        return f"uploads/{new_filename}", True, None

    @app.get("/")
    def dashboard():
        service = get_service()
        players = service.list_players()
        coaches = service.list_coaches()
        physios = service.list_physiotherapists()
        youth_teams = service.list_youth_teams()
        members = service.list_members()
        summary = service.financial_summary()
        active_treatments = service.list_active_treatments()
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
            active_treatments=active_treatments,
        )

    @app.get("/epocas")
    def seasons_page():
        service = get_service()
        seasons = service.list_seasons()
        editing_season = None
        edit_id = _parse_optional_int(request.args.get("edit"))
        if edit_id is not None:
            editing_season = next((season for season in seasons if season.id == edit_id), None)
            if editing_season is None:
                _flash_invalid("Época selecionada para edição não encontrada.")
        return render_template(
            "seasons.html",
            title="Épocas",
            active_page="seasons",
            seasons=seasons,
            editing_season=editing_season,
        )

    @app.get("/jogadores")
    def players_page():
        service = get_service()
        players = service.list_players()
        player_treatments = service.treatments_by_player(active_only=True)
        editing_player = None
        edit_id = _parse_optional_int(request.args.get("edit"))
        if edit_id is not None:
            editing_player = next((player for player in players if player.id == edit_id), None)
        return render_template(
            "players.html",
            title="Jogadores",
            active_group="plantel",
            active_page="players",
            players=players,
            editing_player=editing_player,
            player_treatments=player_treatments,
        )

    @app.post("/epocas")
    def save_season():
        season_id = _parse_optional_int(request.form.get("season_id"))
        name = request.form.get("name", "").strip()
        notes_raw = request.form.get("notes", "").strip()
        notes = notes_raw or None
        ok_start, start_date = _handle_date("start_date")
        ok_end, end_date = _handle_date("end_date")
        target = url_for("seasons_page", edit=season_id) if season_id else url_for("seasons_page")
        if not name:
            _flash_invalid("O nome da época é obrigatório.")
            return redirect(target)
        if not ok_start or start_date is None:
            _flash_invalid("A data de início é inválida.")
            return redirect(target)
        if not ok_end or end_date is None:
            _flash_invalid("A data de fim é inválida.")
            return redirect(target)
        service = get_service()
        try:
            if season_id is None:
                service.create_season(name=name, start_date=start_date, end_date=end_date, notes=notes)
                flash("Nova época criada com sucesso!", "success")
            else:
                service.update_season(
                    season_id,
                    name=name,
                    start_date=start_date,
                    end_date=end_date,
                    notes=notes,
                )
                flash("Época atualizada com sucesso!", "success")
        except ValueError as exc:
            _flash_invalid(str(exc))
            return redirect(target)
        return redirect(url_for("seasons_page"))

    @app.post("/epocas/ativa")
    def set_active_season_route():
        season_id = _parse_optional_int(request.form.get("season_id"))
        fallback = url_for("dashboard")
        next_url = request.form.get("next") or request.referrer or fallback
        if not next_url or next_url.startswith("http"):
            next_url = fallback
        if season_id is None:
            _flash_invalid("Selecione uma época válida.")
            return redirect(next_url)
        service = get_service()
        try:
            season = service.set_active_season(season_id)
        except ValueError as exc:
            _flash_invalid(str(exc))
        else:
            flash(f"Época {season.name} definida como ativa.", "success")
        return redirect(next_url)

    @app.post("/epocas/<int:season_id>/ativar")
    def activate_season(season_id: int):
        service = get_service()
        try:
            service.set_active_season(season_id)
        except ValueError as exc:
            _flash_invalid(str(exc))
        else:
            flash("Época marcada como ativa.", "success")
        return redirect(url_for("seasons_page"))

    @app.post("/epocas/<int:season_id>/eliminar")
    def delete_season(season_id: int):
        service = get_service()
        try:
            service.remove_season(season_id)
        except ValueError as exc:
            _flash_invalid(str(exc))
        else:
            flash("Época eliminada com sucesso.", "success")
        return redirect(url_for("seasons_page"))

    @app.get("/equipa-tecnica")
    def coaches_page():
        service = get_service()
        coaches = service.list_coaches()
        editing_coach = None
        edit_id = _parse_optional_int(request.args.get("edit"))
        if edit_id is not None:
            editing_coach = next((coach for coach in coaches if coach.id == edit_id), None)
        return render_template(
            "coaches.html",
            title="Equipa Técnica",
            active_group="plantel",
            active_page="coaches",
            coaches=coaches,
            editing_coach=editing_coach,
        )

    @app.get("/planificacao-equipa")
    def match_plans_page():
        service = get_service()
        players = service.list_players()
        active_treatments = service.treatments_by_player(active_only=True)
        plans = service.list_match_plans()
        squad_options = sorted(
            {player.squad or "senior" for player in players}
            | {plan.squad or "senior" for plan in plans}
        ) or ["senior"]
        selected_squad = request.args.get("squad", "").strip()
        if not selected_squad:
            selected_squad = squad_options[0]
        elif selected_squad not in squad_options:
            selected_squad = squad_options[0]
        editing_plan = None
        edit_id = _parse_optional_int(request.args.get("edit"))
        if edit_id is not None:
            try:
                editing_plan = service.get_match_plan(edit_id)
                selected_squad = editing_plan.squad or selected_squad
            except ValueError:
                _flash_invalid("Plano de jogo selecionado não existe.")
        player_lookup = {player.id: player for player in players}
        available_players = [
            player for player in players if (player.squad or "senior") == selected_squad
        ]
        if editing_plan is not None:
            referenced = set(editing_plan.starters + editing_plan.substitutes)
            for player_id in referenced:
                player = player_lookup.get(player_id)
                if player and player not in available_players:
                    available_players.append(player)
        available_players.sort(key=lambda player: (player.squad or "", player.name))
        squad_plans = [
            plan for plan in plans if (plan.squad or "senior") == selected_squad
        ]
        return render_template(
            "match_plans.html",
            title="Planificação de Jogo",
            active_group="plantel",
            active_page="match-plans",
            squads=squad_options,
            selected_squad=selected_squad,
            players=available_players,
            plans=squad_plans,
            editing_plan=editing_plan,
            player_lookup=player_lookup,
            active_treatments=active_treatments,
        )

    @app.post("/planificacao-equipa")
    def save_match_plan():
        plan_id = _parse_optional_int(request.form.get("plan_id"))
        squad = request.form.get("squad", "").strip()
        if not squad:
            squad = "senior"

        def _redirect_back(include_edit: bool = False):
            params: Dict[str, str] = {}
            if squad:
                params["squad"] = squad
            if include_edit and plan_id is not None:
                params["edit"] = str(plan_id)
            return redirect(url_for("match_plans_page", **params))

        ok_date, match_date = _handle_date("match_date")
        if not ok_date or match_date is None:
            _flash_invalid("Indique uma data válida para o jogo.")
            return _redirect_back(include_edit=True)
        kickoff_time = request.form.get("kickoff_time", "").strip()
        if not kickoff_time:
            _flash_invalid("Indique a hora do jogo.")
            return _redirect_back(include_edit=True)
        opponent = request.form.get("opponent", "").strip()
        if not opponent:
            _flash_invalid("Indique o adversário do jogo.")
            return _redirect_back(include_edit=True)
        venue = request.form.get("venue", "").strip()
        if not venue:
            _flash_invalid("Indique o local do jogo.")
            return _redirect_back(include_edit=True)
        competition = request.form.get("competition", "").strip()
        notes = request.form.get("notes", "").strip()
        starters = request.form.getlist("starters")
        substitutes = request.form.getlist("substitutes")

        service = get_service()
        try:
            if plan_id is None:
                plan = service.create_match_plan(
                    squad=squad,
                    match_date=match_date,
                    kickoff_time=kickoff_time,
                    venue=venue,
                    opponent=opponent,
                    competition=competition or None,
                    notes=notes or None,
                    starters=starters,
                    substitutes=substitutes,
                )
                flash("Plano de jogo registado com sucesso!", "success")
            else:
                plan = service.update_match_plan(
                    plan_id,
                    squad=squad,
                    match_date=match_date,
                    kickoff_time=kickoff_time,
                    venue=venue,
                    opponent=opponent,
                    competition=competition or None,
                    notes=notes or None,
                    starters=starters,
                    substitutes=substitutes,
                )
                flash("Plano de jogo atualizado com sucesso!", "success")
        except ValueError as exc:
            _flash_invalid(str(exc))
            return _redirect_back(include_edit=True)

        redirect_params: Dict[str, str] = {}
        target_squad = plan.squad or squad
        if target_squad:
            redirect_params["squad"] = target_squad
        return redirect(url_for("match_plans_page", **redirect_params))

    @app.post("/planificacao-equipa/<int:plan_id>/eliminar")
    def delete_match_plan(plan_id: int):
        service = get_service()
        try:
            plan = service.get_match_plan(plan_id)
        except ValueError:
            _flash_invalid("Plano de jogo não encontrado.")
            return redirect(url_for("match_plans_page"))
        try:
            service.remove_match_plan(plan_id)
        except ValueError as exc:
            _flash_invalid(str(exc))
        else:
            flash("Plano de jogo eliminado.", "success")
        redirect_params: Dict[str, str] = {}
        if plan.squad:
            redirect_params["squad"] = plan.squad
        return redirect(url_for("match_plans_page", **redirect_params))

    @app.get("/planificacao-equipa/<int:plan_id>/imprimir")
    def print_match_plan(plan_id: int):
        service = get_service()
        try:
            plan = service.get_match_plan(plan_id)
        except ValueError:
            _flash_invalid("Plano de jogo não encontrado.")
            return redirect(url_for("match_plans_page"))
        players = service.list_players()
        player_lookup = {player.id: player for player in players}
        physio_lookup = {physio.id: physio for physio in service.list_physiotherapists()}
        active_treatments = service.treatments_by_player(active_only=True)
        starters = [player_lookup[pid] for pid in plan.starters if pid in player_lookup]
        substitutes = [
            player_lookup[pid]
            for pid in plan.substitutes
            if pid in player_lookup
        ]
        generated_at = date.today()
        return render_template(
            "match_plan_print.html",
            title=f"Plano de jogo vs {plan.opponent}",
            plan=plan,
            starters=starters,
            substitutes=substitutes,
            generated_at=generated_at,
            active_treatments=active_treatments,
            physio_lookup=physio_lookup,
            player_lookup=player_lookup,
        )

    @app.get("/departamento-medico")
    def physios_page():
        service = get_service()
        physios = service.list_physiotherapists()
        editing_physio = None
        edit_id = _parse_optional_int(request.args.get("edit"))
        if edit_id is not None:
            editing_physio = next((physio for physio in physios if physio.id == edit_id), None)
        return render_template(
            "physios.html",
            title="Departamento Médico",
            active_group="plantel",
            active_page="physios",
            physios=physios,
            editing_physio=editing_physio,
        )

    @app.get("/departamento-medico/tratamentos")
    def treatments_page():
        service = get_service()
        treatments = service.list_treatments()
        players = sorted(service.list_players(), key=lambda player: player.name)
        physios = sorted(service.list_physiotherapists(), key=lambda physio: physio.name)
        player_lookup = {player.id: player for player in players}
        physio_lookup = {physio.id: physio for physio in physios}
        editing_treatment = None
        edit_id = _parse_optional_int(request.args.get("edit"))
        if edit_id is not None:
            editing_treatment = next((t for t in treatments if t.id == edit_id), None)
            if editing_treatment is None:
                _flash_invalid("Tratamento selecionado para edição não existe.")
        return render_template(
            "treatments.html",
            title="Tratamentos Clínicos",
            active_group="plantel",
            active_page="treatments",
            treatments=treatments,
            players=players,
            physios=physios,
            player_lookup=player_lookup,
            physio_lookup=physio_lookup,
            editing_treatment=editing_treatment,
        )

    @app.get("/camadas-jovens")
    def youth_page():
        service = get_service()
        youth_teams = service.list_youth_teams()
        coaches = service.list_coaches()
        coach_lookup = {coach.id: coach.name for coach in coaches}
        editing_team = None
        edit_id = _parse_optional_int(request.args.get("edit"))
        if edit_id is not None:
            editing_team = next((team for team in youth_teams if team.id == edit_id), None)
        return render_template(
            "youth.html",
            title="Camadas Jovens",
            active_group="plantel",
            active_page="youth",
            youth_teams=youth_teams,
            coaches=coaches,
            coach_lookup=coach_lookup,
            editing_team=editing_team,
        )

    @app.get("/socios")
    def members_page():
        service = get_service()
        members = service.list_members()
        membership_types = service.list_membership_types()
        payments = service.list_membership_payments()
        member_lookup = {member.id: member for member in members}
        type_lookup = {membership_type.id: membership_type for membership_type in membership_types}
        payment_totals: Dict[int | str, float] = {}
        total_payments = 0.0
        for payment in payments:
            key = payment.membership_type_id if payment.membership_type_id is not None else "outros"
            payment_totals[key] = payment_totals.get(key, 0.0) + payment.amount
            total_payments += payment.amount
        editing_member = None
        edit_member = _parse_optional_int(request.args.get("edit_member"))
        if edit_member is not None:
            editing_member = next((member for member in members if member.id == edit_member), None)
        editing_type = None
        edit_type = _parse_optional_int(request.args.get("edit_type"))
        if edit_type is not None:
            editing_type = next((item for item in membership_types if item.id == edit_type), None)
        return render_template(
            "members.html",
            title="Sócios",
            active_group="financas",
            active_page="members",
            members=members,
            membership_types=membership_types,
            payments=payments,
            member_lookup=member_lookup,
            type_lookup=type_lookup,
            payment_totals=payment_totals,
            total_payments=total_payments,
            editing_member=editing_member,
            editing_type=editing_type,
        )

    @app.get("/socios/<int:member_id>/cartao")
    def member_card_preview(member_id: int):
        service = get_service()
        members = service.list_members()
        member = next((item for item in members if item.id == member_id), None)
        if member is None:
            abort(404)
        membership_type = None
        if member.membership_type_id is not None:
            membership_types = service.list_membership_types()
            membership_type = next(
                (item for item in membership_types if item.id == member.membership_type_id),
                None,
            )
        payments = service.list_member_payments(member.id)
        member_since_value = None
        latest_period = None
        if member.membership_since:
            member_since_value = member.membership_since.strftime("%d/%m/%Y")
        if payments:
            earliest_payment = min(payments, key=lambda payment: payment.paid_on)
            if member_since_value is None:
                member_since_value = earliest_payment.paid_on.strftime("%d/%m/%Y")
            latest_payment = max(payments, key=lambda payment: payment.paid_on)
            latest_period = latest_payment.period
        elif member.dues_paid_until:
            latest_period = member.dues_paid_until
        return render_template(
            "member_card.html",
            title="Cartão de Sócio",
            active_group="financas",
            active_page="members",
            member=member,
            membership_type_name=membership_type.name if membership_type else member.membership_type,
            member_since=member_since_value,
            latest_period=latest_period,
            body_class="card-preview-page",
        )

    def _render_finances(
        template: str,
        active_page: str,
        *,
        edit_revenue_id: Optional[int] = None,
        edit_expense_id: Optional[int] = None,
    ):
        service = get_service()
        revenues, expenses = service.list_financial_records()
        summary = service.financial_summary()
        revenue_categories, expense_categories = _split_categories(summary)
        editing_revenue = None
        if edit_revenue_id is not None:
            editing_revenue = next((record for record in revenues if record.id == edit_revenue_id), None)
        editing_expense = None
        if edit_expense_id is not None:
            editing_expense = next((record for record in expenses if record.id == edit_expense_id), None)
        return render_template(
            template,
            title="Finanças",
            active_group="financas",
            active_page=active_page,
            revenues=revenues,
            expenses=expenses,
            summary=summary,
            revenue_categories=revenue_categories,
            expense_categories=expense_categories,
            editing_revenue=editing_revenue,
            editing_expense=editing_expense,
        )

    @app.get("/financas")
    def finances_page():
        revenue_id = _parse_optional_int(request.args.get("edit_revenue"))
        expense_id = _parse_optional_int(request.args.get("edit_expense"))
        return _render_finances(
            "finances_overview.html",
            "finances-overview",
            edit_revenue_id=revenue_id,
            edit_expense_id=expense_id,
        )

    @app.get("/financas/receitas")
    def finances_revenue_page():
        revenue_id = _parse_optional_int(request.args.get("edit"))
        return _render_finances(
            "finances_revenue.html",
            "finances-revenue",
            edit_revenue_id=revenue_id,
        )

    @app.get("/financas/despesas")
    def finances_expense_page():
        expense_id = _parse_optional_int(request.args.get("edit"))
        return _render_finances(
            "finances_expense.html",
            "finances-expense",
            edit_expense_id=expense_id,
        )

    def _handle_date(field: str) -> Tuple[bool, date | None]:
        value = request.form.get(field)
        try:
            parsed = parse_date(value)
        except ValueError:
            return False, None
        return True, parsed

    def _handle_amount(field: str) -> Tuple[bool, Optional[float]]:
        raw = request.form.get(field, "")
        if raw is None:
            return True, None
        text = raw.strip().replace(",", ".")
        if not text:
            return True, None
        try:
            value = float(text)
        except ValueError:
            return False, None
        if value < 0:
            return False, None
        return True, value

    def _flash_invalid(message: str) -> None:
        flash(message, "error")

    def _parse_optional_int(value: Optional[str]) -> Optional[int]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @app.post("/players")
    def add_player():
        player_id_raw = request.form.get("player_id")
        player_id = _parse_optional_int(player_id_raw)
        if player_id_raw and player_id is None:
            _flash_invalid("Jogador selecionado é inválido para edição.")
            return redirect(url_for("players_page"))
        target = url_for("players_page", edit=player_id) if player_id is not None else url_for("players_page")
        name = request.form.get("name", "").strip()
        position = request.form.get("position", "").strip()
        squad = request.form.get("squad", "senior").strip()
        contact = request.form.get("contact", "").strip() or None
        af_porto_id = request.form.get("af_porto_id", "").strip() or None
        shirt_number_raw = request.form.get("shirt_number", "").strip()
        ok_birthdate, birthdate = _handle_date("birthdate")
        if not ok_birthdate:
            _flash_invalid("Data de nascimento inválida para o jogador.")
            return redirect(target)
        shirt_number = None
        if shirt_number_raw:
            try:
                shirt_number = int(shirt_number_raw)
            except ValueError:
                _flash_invalid("Número da camisola inválido.")
                return redirect(target)
        ok_monthly_fee, youth_monthly_fee = _handle_amount("youth_monthly_fee")
        if not ok_monthly_fee:
            _flash_invalid("O valor da mensalidade é inválido.")
            return redirect(target)
        ok_kit_fee, youth_kit_fee = _handle_amount("youth_kit_fee")
        if not ok_kit_fee:
            _flash_invalid("O valor do kit de treino é inválido.")
            return redirect(target)
        youth_monthly_paid = request.form.get("youth_monthly_paid") == "on"
        youth_kit_paid = request.form.get("youth_kit_paid") == "on"
        is_youth_squad = squad.lower() in YOUTH_SQUADS
        if is_youth_squad and youth_monthly_paid and (youth_monthly_fee is None or youth_monthly_fee <= 0):
            _flash_invalid("Indique um valor para a mensalidade antes de a marcar como paga.")
            return redirect(target)
        if is_youth_squad and youth_kit_paid and (youth_kit_fee is None or youth_kit_fee <= 0):
            _flash_invalid("Indique um valor para o kit de treino antes de o marcar como pago.")
            return redirect(target)
        if not is_youth_squad:
            youth_monthly_fee = None
            youth_monthly_paid = False
            youth_kit_fee = None
            youth_kit_paid = False
        if not name or not position:
            _flash_invalid("Nome e posição são obrigatórios.")
            return redirect(target)
        service = get_service()
        existing_player = None
        if player_id is not None:
            players = service.list_players()
            existing_player = next((player for player in players if player.id == player_id), None)
            if existing_player is None:
                _flash_invalid("Jogador não encontrado para edição.")
                return redirect(target)
        photo_value, photo_changed, photo_error = _process_photo_upload(
            "photo", existing=existing_player.photo_url if existing_player else None
        )
        if photo_error:
            _flash_invalid(photo_error)
            return redirect(target)
        if player_id is None:
            try:
                service.add_player(
                    name=name,
                    position=position,
                    squad=squad or "senior",
                    birthdate=birthdate,
                    contact=contact,
                    shirt_number=shirt_number,
                    af_porto_id=af_porto_id,
                    photo_url=photo_value if photo_changed else None,
                    youth_monthly_fee=youth_monthly_fee,
                    youth_monthly_paid=youth_monthly_paid,
                    youth_kit_fee=youth_kit_fee,
                    youth_kit_paid=youth_kit_paid,
                )
            except ValueError as exc:
                _flash_invalid(str(exc))
                return redirect(target)
            flash("Jogador gravado com sucesso!", "success")
        else:
            try:
                update_kwargs = dict(
                    name=name,
                    position=position,
                    squad=squad or "senior",
                    birthdate=birthdate,
                    contact=contact,
                    shirt_number=shirt_number,
                    af_porto_id=af_porto_id,
                    youth_monthly_fee=youth_monthly_fee,
                    youth_monthly_paid=youth_monthly_paid,
                    youth_kit_fee=youth_kit_fee,
                    youth_kit_paid=youth_kit_paid,
                )
                if photo_changed:
                    update_kwargs["photo_url"] = photo_value
                service.update_player(
                    player_id,
                    **update_kwargs,
                )
            except ValueError as exc:
                _flash_invalid(str(exc))
                return redirect(target)
            flash("Jogador atualizado com sucesso!", "success")
        return redirect(url_for("players_page"))

    @app.post("/players/<int:player_id>/delete")
    def delete_player(player_id: int):
        service = get_service()
        try:
            service.remove_player(player_id)
        except ValueError as exc:
            _flash_invalid(str(exc))
        else:
            flash("Jogador eliminado.", "success")
        return redirect(url_for("players_page"))

    @app.post("/coaches")
    def add_coach():
        coach_id_raw = request.form.get("coach_id")
        coach_id = _parse_optional_int(coach_id_raw)
        if coach_id_raw and coach_id is None:
            _flash_invalid("Treinador selecionado é inválido para edição.")
            return redirect(url_for("coaches_page"))
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
        existing_coach = None
        if coach_id is not None:
            coaches = service.list_coaches()
            existing_coach = next((coach for coach in coaches if coach.id == coach_id), None)
            if existing_coach is None:
                _flash_invalid("Treinador não encontrado para edição.")
                return redirect(url_for("coaches_page"))
        photo_value, photo_changed, photo_error = _process_photo_upload(
            "photo", existing=existing_coach.photo_url if existing_coach else None
        )
        if photo_error:
            _flash_invalid(photo_error)
            target = url_for("coaches_page", edit=coach_id) if coach_id is not None else url_for("coaches_page")
            return redirect(target)
        if coach_id is None:
            service.add_coach(
                name=name,
                role=role,
                license_level=license_level,
                birthdate=birthdate,
                contact=contact,
                photo_url=photo_value if photo_changed else None,
            )
            flash("Treinador gravado com sucesso!", "success")
        else:
            try:
                update_kwargs = dict(
                    name=name,
                    role=role,
                    license_level=license_level,
                    birthdate=birthdate,
                    contact=contact,
                )
                if photo_changed:
                    update_kwargs["photo_url"] = photo_value
                service.update_coach(
                    coach_id,
                    **update_kwargs,
                )
            except ValueError as exc:
                _flash_invalid(str(exc))
                return redirect(url_for("coaches_page", edit=coach_id))
            flash("Treinador atualizado com sucesso!", "success")
        return redirect(url_for("coaches_page"))

    @app.post("/coaches/<int:coach_id>/delete")
    def delete_coach(coach_id: int):
        service = get_service()
        try:
            service.remove_coach(coach_id)
        except ValueError as exc:
            _flash_invalid(str(exc))
        else:
            flash("Treinador eliminado.", "success")
        return redirect(url_for("coaches_page"))

    @app.post("/physios")
    def add_physio():
        physio_id_raw = request.form.get("physio_id")
        physio_id = _parse_optional_int(physio_id_raw)
        if physio_id_raw and physio_id is None:
            _flash_invalid("Profissional selecionado é inválido para edição.")
            return redirect(url_for("physios_page"))
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
        existing_physio = None
        if physio_id is not None:
            physios = service.list_physiotherapists()
            existing_physio = next((physio for physio in physios if physio.id == physio_id), None)
            if existing_physio is None:
                _flash_invalid("Profissional não encontrado para edição.")
                return redirect(url_for("physios_page"))
        photo_value, photo_changed, photo_error = _process_photo_upload(
            "photo", existing=existing_physio.photo_url if existing_physio else None
        )
        if photo_error:
            _flash_invalid(photo_error)
            target = url_for("physios_page", edit=physio_id) if physio_id is not None else url_for("physios_page")
            return redirect(target)
        if physio_id is None:
            service.add_physiotherapist(
                name=name,
                specialization=specialization,
                birthdate=birthdate,
                contact=contact,
                photo_url=photo_value if photo_changed else None,
            )
            flash("Profissional gravado com sucesso!", "success")
        else:
            try:
                update_kwargs = dict(
                    name=name,
                    specialization=specialization,
                    birthdate=birthdate,
                    contact=contact,
                )
                if photo_changed:
                    update_kwargs["photo_url"] = photo_value
                service.update_physiotherapist(
                    physio_id,
                    **update_kwargs,
                )
            except ValueError as exc:
                _flash_invalid(str(exc))
                return redirect(url_for("physios_page", edit=physio_id))
            flash("Profissional atualizado com sucesso!", "success")
        return redirect(url_for("physios_page"))

    @app.post("/physios/<int:physio_id>/delete")
    def delete_physio(physio_id: int):
        service = get_service()
        try:
            service.remove_physiotherapist(physio_id)
        except ValueError as exc:
            _flash_invalid(str(exc))
        else:
            flash("Profissional eliminado.", "success")
        return redirect(url_for("physios_page"))

    @app.post("/departamento-medico/tratamentos")
    def save_treatment():
        treatment_id_raw = request.form.get("treatment_id")
        treatment_id = _parse_optional_int(treatment_id_raw)
        if treatment_id_raw and treatment_id is None:
            _flash_invalid("Tratamento selecionado para edição é inválido.")
            return redirect(url_for("treatments_page"))
        player_id = _parse_optional_int(request.form.get("player_id"))
        if player_id is None:
            _flash_invalid("Selecione o jogador em tratamento.")
            target = url_for("treatments_page", edit=treatment_id) if treatment_id is not None else url_for("treatments_page")
            return redirect(target)
        physio_id = _parse_optional_int(request.form.get("physio_id"))
        diagnosis = request.form.get("diagnosis", "").strip()
        treatment_plan = request.form.get("treatment_plan", "").strip()
        ok_start, start_date = _handle_date("start_date")
        if not ok_start or start_date is None:
            _flash_invalid("Data de início do tratamento inválida.")
            target = url_for("treatments_page", edit=treatment_id) if treatment_id is not None else url_for("treatments_page")
            return redirect(target)
        ok_expected, expected_return = _handle_date("expected_return")
        if not ok_expected:
            _flash_invalid("Data prevista de regresso inválida.")
            target = url_for("treatments_page", edit=treatment_id) if treatment_id is not None else url_for("treatments_page")
            return redirect(target)
        unavailable = request.form.get("unavailable") == "on"
        notes = request.form.get("notes", "").strip() or None
        service = get_service()
        try:
            if treatment_id is None:
                service.add_treatment(
                    player_id=player_id,
                    physio_id=physio_id,
                    diagnosis=diagnosis,
                    treatment_plan=treatment_plan,
                    start_date=start_date,
                    expected_return=expected_return,
                    unavailable=unavailable,
                    notes=notes,
                )
                flash("Tratamento registado com sucesso!", "success")
            else:
                service.update_treatment(
                    treatment_id,
                    physio_id=physio_id,
                    diagnosis=diagnosis,
                    treatment_plan=treatment_plan,
                    start_date=start_date,
                    expected_return=expected_return,
                    unavailable=unavailable,
                    notes=notes,
                )
                flash("Tratamento atualizado com sucesso!", "success")
        except ValueError as exc:
            _flash_invalid(str(exc))
            target = url_for("treatments_page", edit=treatment_id) if treatment_id is not None else url_for("treatments_page")
            return redirect(target)
        return redirect(url_for("treatments_page"))

    @app.post("/departamento-medico/tratamentos/<int:treatment_id>/eliminar")
    def delete_treatment(treatment_id: int):
        service = get_service()
        try:
            service.remove_treatment(treatment_id)
        except ValueError as exc:
            _flash_invalid(str(exc))
        else:
            flash("Tratamento eliminado.", "success")
        return redirect(url_for("treatments_page"))

    @app.post("/youth-teams")
    def add_youth_team():
        team_id_raw = request.form.get("team_id")
        team_id = _parse_optional_int(team_id_raw)
        if team_id_raw and team_id is None:
            _flash_invalid("Equipa selecionada é inválida para edição.")
            return redirect(url_for("youth_page"))
        name = request.form.get("name", "").strip()
        age_group = request.form.get("age_group", "").strip()
        coach_id_raw = request.form.get("coach_id", "")
        coach_id = _parse_optional_int(coach_id_raw)
        if coach_id_raw and coach_id is None:
            _flash_invalid("ID do treinador inválido.")
            return redirect(url_for("youth_page"))
        if not name or not age_group:
            _flash_invalid("Nome e escalão da equipa são obrigatórios.")
            return redirect(url_for("youth_page"))
        service = get_service()
        if team_id is None:
            service.add_youth_team(
                name=name,
                age_group=age_group,
                coach_id=coach_id,
            )
            flash("Equipa de formação gravada!", "success")
        else:
            try:
                service.update_youth_team(
                    team_id,
                    name=name,
                    age_group=age_group,
                    coach_id=coach_id,
                )
            except ValueError as exc:
                _flash_invalid(str(exc))
                return redirect(url_for("youth_page", edit=team_id))
            flash("Equipa de formação atualizada!", "success")
        return redirect(url_for("youth_page"))

    @app.post("/youth-teams/<int:team_id>/delete")
    def delete_youth_team(team_id: int):
        service = get_service()
        try:
            service.remove_youth_team(team_id)
        except ValueError as exc:
            _flash_invalid(str(exc))
        else:
            flash("Equipa removida.", "success")
        return redirect(url_for("youth_page"))

    @app.post("/members")
    def add_member():
        member_id_raw = request.form.get("member_id")
        member_id = _parse_optional_int(member_id_raw)
        if member_id_raw and member_id is None:
            _flash_invalid("Sócio selecionado é inválido para edição.")
            return redirect(url_for("members_page"))
        name = request.form.get("name", "").strip()
        membership_type = request.form.get("membership_type", "").strip()
        membership_type_id_raw = request.form.get("membership_type_id", "").strip()
        membership_type_id = _parse_optional_int(membership_type_id_raw)
        if membership_type_id_raw and membership_type_id is None:
            _flash_invalid("Tipo de sócio selecionado é inválido.")
            return redirect(url_for("members_page"))
        contact = request.form.get("contact", "").strip() or None
        dues_paid_until = request.form.get("dues_paid_until", "").strip() or None
        ok_birthdate, birthdate = _handle_date("birthdate")
        if not ok_birthdate:
            _flash_invalid("Data de nascimento inválida para o sócio.")
            return redirect(url_for("members_page"))
        ok_member_since, membership_since = _handle_date("membership_since")
        if not ok_member_since:
            _flash_invalid("Data de adesão inválida para o sócio.")
            return redirect(url_for("members_page"))
        dues_paid = request.form.get("dues_paid") == "on"
        member_number_raw = request.form.get("member_number", "").strip()
        member_number = None
        if member_number_raw:
            try:
                member_number = int(member_number_raw)
            except ValueError:
                _flash_invalid("Número de sócio inválido.")
                return redirect(url_for("members_page"))
        if not name:
            _flash_invalid("O nome do sócio é obrigatório.")
            return redirect(url_for("members_page"))
        if member_id is None and not membership_type_id and not membership_type:
            _flash_invalid("Escolha um tipo de sócio ou indique um novo tipo de quota.")
            return redirect(url_for("members_page"))
        service = get_service()
        existing_member = None
        if member_id is not None:
            members = service.list_members()
            existing_member = next((member for member in members if member.id == member_id), None)
            if existing_member is None:
                _flash_invalid("Sócio não encontrado para edição.")
                return redirect(url_for("members_page"))
        photo_value, photo_changed, photo_error = _process_photo_upload(
            "photo", existing=existing_member.photo_url if existing_member else None
        )
        if photo_error:
            _flash_invalid(photo_error)
            target = url_for("members_page", edit_member=member_id) if member_id is not None else url_for("members_page")
            return redirect(target)
        try:
            if member_id is None:
                service.add_member(
                    name=name,
                    membership_type=membership_type,
                    dues_paid=dues_paid,
                    contact=contact,
                    birthdate=birthdate,
                    membership_type_id=membership_type_id,
                    dues_paid_until=dues_paid_until,
                    member_number=member_number,
                    photo_url=photo_value if photo_changed else None,
                    membership_since=membership_since,
                )
                flash("Sócio gravado com sucesso!", "success")
            else:
                update_kwargs = dict(
                    name=name,
                    dues_paid=dues_paid,
                    dues_paid_until=dues_paid_until,
                    contact=contact,
                    birthdate=birthdate,
                    member_number=member_number,
                    membership_since=membership_since,
                )
                if photo_changed:
                    update_kwargs["photo_url"] = photo_value
                if membership_type_id is not None:
                    type_info = service.get_membership_type(membership_type_id)
                    if type_info is None:
                        raise ValueError("Tipo de sócio não existe.")
                    update_kwargs["membership_type_id"] = membership_type_id
                    update_kwargs["membership_type"] = type_info.name
                elif membership_type:
                    update_kwargs["membership_type"] = membership_type
                service.update_member(
                    member_id,
                    **update_kwargs,
                )
                flash("Sócio atualizado com sucesso!", "success")
        except ValueError as exc:
            _flash_invalid(str(exc))
            target = url_for("members_page")
            if member_id is not None:
                target = url_for("members_page", edit_member=member_id)
            return redirect(target)
        return redirect(url_for("members_page"))

    @app.post("/members/<int:member_id>/delete")
    def delete_member(member_id: int):
        service = get_service()
        try:
            service.remove_member(member_id)
        except ValueError as exc:
            _flash_invalid(str(exc))
        else:
            flash("Sócio eliminado.", "success")
        return redirect(url_for("members_page"))

    @app.post("/membership-types")
    def create_membership_type():
        type_id_raw = request.form.get("type_id")
        type_id = _parse_optional_int(type_id_raw)
        if type_id_raw and type_id is None:
            _flash_invalid("Tipo de sócio selecionado é inválido para edição.")
            return redirect(url_for("members_page"))
        name = request.form.get("name", "").strip()
        frequency = request.form.get("frequency", "").strip() or "Mensal"
        description = request.form.get("description", "").strip() or None
        amount = _parse_amount("amount")
        if not name or amount is None or amount <= 0:
            _flash_invalid("Indique o nome e o valor da quota para o tipo de sócio.")
            target = url_for("members_page")
            if type_id is not None:
                target = url_for("members_page", edit_type=type_id)
            return redirect(target)
        service = get_service()
        if type_id is None:
            service.add_membership_type(name=name, amount=amount, frequency=frequency, description=description)
            flash("Tipo de sócio gravado!", "success")
        else:
            service.update_membership_type(
                type_id,
                name=name,
                amount=amount,
                frequency=frequency,
                description=description,
            )
            flash("Tipo de sócio atualizado!", "success")
        return redirect(url_for("members_page"))

    @app.post("/membership-types/<int:type_id>/delete")
    def delete_membership_type(type_id: int):
        service = get_service()
        try:
            service.remove_membership_type(type_id)
        except ValueError as exc:
            _flash_invalid(str(exc))
        else:
            flash("Tipo de sócio eliminado.", "success")
        return redirect(url_for("members_page"))

    @app.post("/membership-payments")
    def record_membership_payment():
        member_id_raw = request.form.get("member_id", "").strip()
        membership_type_id_raw = request.form.get("membership_type_id", "").strip()
        period = request.form.get("period", "").strip()
        notes = request.form.get("notes", "").strip() or None
        if not member_id_raw:
            _flash_invalid("Selecione o sócio a quem se aplica o pagamento.")
            return redirect(url_for("members_page"))
        try:
            member_id = int(member_id_raw)
        except ValueError:
            _flash_invalid("Sócio inválido para registo de pagamento.")
            return redirect(url_for("members_page"))
        membership_type_id = None
        if membership_type_id_raw:
            try:
                membership_type_id = int(membership_type_id_raw)
            except ValueError:
                _flash_invalid("Tipo de sócio inválido para o pagamento.")
                return redirect(url_for("members_page"))
        amount = _parse_amount("amount")
        if amount is None or amount <= 0:
            _flash_invalid("Indique o valor pago na quota.")
            return redirect(url_for("members_page"))
        if not period:
            _flash_invalid("Indique o período a que se refere o pagamento.")
            return redirect(url_for("members_page"))
        try:
            paid_on = _handle_financial_date()
        except ValueError:
            return redirect(url_for("members_page"))
        service = get_service()
        try:
            service.register_membership_payment(
                member_id=member_id,
                amount=amount,
                period=period,
                paid_on=paid_on,
                membership_type_id=membership_type_id,
                notes=notes,
            )
        except ValueError as exc:
            _flash_invalid(str(exc))
            return redirect(url_for("members_page"))
        flash("Pagamento de quotas registado!", "success")
        return redirect(url_for("members_page"))

    @app.post("/membership-payments/<int:payment_id>/delete")
    def delete_membership_payment(payment_id: int):
        service = get_service()
        try:
            service.remove_membership_payment(payment_id)
        except ValueError as exc:
            _flash_invalid(str(exc))
        else:
            flash("Pagamento removido.", "success")
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
        revenue_id_raw = request.form.get("revenue_id")
        revenue_id = _parse_optional_int(revenue_id_raw)
        if revenue_id_raw and revenue_id is None:
            _flash_invalid("Registo de receita inválido para edição.")
            return redirect(url_for("finances_revenue_page"))
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
        if revenue_id is None:
            service.add_revenue(
                description=description,
                amount=amount,
                category=category,
                record_date=record_date,
                source=source,
            )
            flash("Receita gravada com sucesso!", "success")
        else:
            try:
                service.update_revenue(
                    revenue_id,
                    description=description,
                    amount=amount,
                    category=category,
                    record_date=record_date,
                    source=source,
                )
            except ValueError as exc:
                _flash_invalid(str(exc))
                return redirect(url_for("finances_revenue_page", edit=revenue_id))
            flash("Receita atualizada com sucesso!", "success")
        return redirect(url_for("finances_revenue_page"))

    @app.post("/finance/revenue/<int:revenue_id>/delete")
    def delete_revenue(revenue_id: int):
        service = get_service()
        try:
            service.remove_revenue(revenue_id)
        except ValueError as exc:
            _flash_invalid(str(exc))
        else:
            flash("Receita eliminada.", "success")
        return redirect(url_for("finances_revenue_page"))

    @app.post("/finance/expense")
    def add_expense():
        expense_id_raw = request.form.get("expense_id")
        expense_id = _parse_optional_int(expense_id_raw)
        if expense_id_raw and expense_id is None:
            _flash_invalid("Registo de despesa inválido para edição.")
            return redirect(url_for("finances_expense_page"))
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
        if expense_id is None:
            service.add_expense(
                description=description,
                amount=amount,
                category=category,
                record_date=record_date,
                vendor=vendor,
            )
            flash("Despesa gravada com sucesso!", "success")
        else:
            try:
                service.update_expense(
                    expense_id,
                    description=description,
                    amount=amount,
                    category=category,
                    record_date=record_date,
                    vendor=vendor,
                )
            except ValueError as exc:
                _flash_invalid(str(exc))
                return redirect(url_for("finances_expense_page", edit=expense_id))
            flash("Despesa atualizada com sucesso!", "success")
        return redirect(url_for("finances_expense_page"))

    @app.post("/finance/expense/<int:expense_id>/delete")
    def delete_expense(expense_id: int):
        service = get_service()
        try:
            service.remove_expense(expense_id)
        except ValueError as exc:
            _flash_invalid(str(exc))
        else:
            flash("Despesa eliminada.", "success")
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
