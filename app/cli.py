"""Command line interface for the Vila-Caiz club management application."""
from __future__ import annotations

import argparse
import shlex
import sys
from datetime import date
from typing import Callable, Dict, Optional

from . import services, storage

DATE_HELP = "Formato ISO (AAAA-MM-DD)."


class CommandError(RuntimeError):
    """Raised when CLI validation fails."""


def parse_date(value: Optional[str]) -> Optional[date]:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - defensive branch
        raise CommandError(f"Data inválida: {value}") from exc


def _configure_player_commands(subparsers: argparse._SubParsersAction, service: services.ClubService) -> None:
    player_parser = subparsers.add_parser("players", help="Gerir jogadores")
    player_sub = player_parser.add_subparsers(dest="players_command", required=True)

    add_player = player_sub.add_parser("add", help="Adicionar jogador")
    add_player.add_argument("name", help="Nome completo")
    add_player.add_argument("position", help="Posição em campo")
    add_player.add_argument("--squad", default="senior", help="Escalão (senior, sub-23, etc.)")
    add_player.add_argument("--birthdate", help=DATE_HELP)
    add_player.add_argument("--contact", help="Contacto (email ou telefone)")
    add_player.add_argument("--shirt-number", type=int, dest="shirt_number", help="Número da camisola")
    add_player.add_argument(
        "--youth-monthly-fee",
        type=float,
        dest="youth_monthly_fee",
        help="Valor da mensalidade (camadas jovens)",
    )
    add_player.add_argument(
        "--youth-monthly-paid",
        action="store_true",
        dest="youth_monthly_paid",
        help="Assinala mensalidade como paga",
    )
    add_player.add_argument(
        "--youth-kit-fee",
        type=float,
        dest="youth_kit_fee",
        help="Valor do kit de treino (camadas jovens)",
    )
    add_player.add_argument(
        "--youth-kit-paid",
        action="store_true",
        dest="youth_kit_paid",
        help="Assinala kit de treino como pago",
    )

    def handle_add(args: argparse.Namespace) -> None:
        try:
            player = service.add_player(
                name=args.name,
                position=args.position,
                squad=args.squad,
                birthdate=parse_date(args.birthdate),
                contact=args.contact,
                shirt_number=args.shirt_number,
                youth_monthly_fee=args.youth_monthly_fee,
                youth_monthly_paid=args.youth_monthly_paid,
                youth_kit_fee=args.youth_kit_fee,
                youth_kit_paid=args.youth_kit_paid,
            )
        except ValueError as exc:
            print(f"Erro: {exc}")
            return
        print("Jogador criado:")
        print(f"  {services.format_person(player)} | {player.position} | {player.squad} | #{player.shirt_number or '-'}")

    add_player.set_defaults(func=handle_add)

    list_player = player_sub.add_parser("list", help="Listar jogadores")

    def handle_list(_: argparse.Namespace) -> None:
        players = service.list_players()
        if not players:
            print("Sem jogadores registados.")
            return
        for player in players:
            base = f"- {services.format_person(player)} | {player.position} | {player.squad} | #{player.shirt_number or '-'}"
            extras = []
            squad_value = (player.squad or "").lower()
            if squad_value in services.YOUTH_SQUADS:
                if player.youth_monthly_fee is not None or player.youth_monthly_paid:
                    monthly = "Mensalidade: " + ("Pago" if player.youth_monthly_paid else "Em falta")
                    if player.youth_monthly_fee is not None:
                        monthly += f" ({player.youth_monthly_fee:.2f}€)"
                    extras.append(monthly)
                if player.youth_kit_fee is not None or player.youth_kit_paid:
                    kit = "Kit: " + ("Pago" if player.youth_kit_paid else "Em falta")
                    if player.youth_kit_fee is not None:
                        kit += f" ({player.youth_kit_fee:.2f}€)"
                    extras.append(kit)
            if extras:
                base = f"{base} | {' / '.join(extras)}"
            print(base)

    list_player.set_defaults(func=handle_list)


def _configure_coach_commands(subparsers: argparse._SubParsersAction, service: services.ClubService) -> None:
    coach_parser = subparsers.add_parser("coaches", help="Gerir treinadores")
    coach_sub = coach_parser.add_subparsers(dest="coaches_command", required=True)

    add_coach = coach_sub.add_parser("add", help="Adicionar treinador")
    add_coach.add_argument("name", help="Nome completo")
    add_coach.add_argument("role", help="Função (ex: Treinador Principal)")
    add_coach.add_argument("--license", dest="license_level", help="Licença UEFA")
    add_coach.add_argument("--birthdate", help=DATE_HELP)
    add_coach.add_argument("--contact", help="Contacto")

    def handle_add(args: argparse.Namespace) -> None:
        coach = service.add_coach(
            name=args.name,
            role=args.role,
            license_level=args.license_level,
            birthdate=parse_date(args.birthdate),
            contact=args.contact,
        )
        print("Treinador criado:")
        print(f"  {services.format_person(coach)} | {coach.role} | {coach.license_level or 'N/A'}")

    add_coach.set_defaults(func=handle_add)

    list_coach = coach_sub.add_parser("list", help="Listar treinadores")

    def handle_list(_: argparse.Namespace) -> None:
        coaches = service.list_coaches()
        if not coaches:
            print("Sem treinadores registados.")
            return
        for coach in coaches:
            print(f"- {services.format_person(coach)} | {coach.role} | {coach.license_level or 'N/A'}")

    list_coach.set_defaults(func=handle_list)


def _configure_physio_commands(subparsers: argparse._SubParsersAction, service: services.ClubService) -> None:
    physio_parser = subparsers.add_parser("physios", help="Gerir fisioterapeutas")
    physio_sub = physio_parser.add_subparsers(dest="physios_command", required=True)

    add_physio = physio_sub.add_parser("add", help="Adicionar fisioterapeuta")
    add_physio.add_argument("name", help="Nome completo")
    add_physio.add_argument("--specialization", help="Área de especialização")
    add_physio.add_argument("--birthdate", help=DATE_HELP)
    add_physio.add_argument("--contact", help="Contacto")

    def handle_add(args: argparse.Namespace) -> None:
        physio = service.add_physiotherapist(
            name=args.name,
            specialization=args.specialization,
            birthdate=parse_date(args.birthdate),
            contact=args.contact,
        )
        print("Fisioterapeuta criado:")
        print(f"  {services.format_person(physio)} | {physio.specialization or 'N/A'}")

    add_physio.set_defaults(func=handle_add)

    list_physio = physio_sub.add_parser("list", help="Listar fisioterapeutas")

    def handle_list(_: argparse.Namespace) -> None:
        physios = service.list_physiotherapists()
        if not physios:
            print("Sem fisioterapeutas registados.")
            return
        for physio in physios:
            print(f"- {services.format_person(physio)} | {physio.specialization or 'N/A'}")

    list_physio.set_defaults(func=handle_list)


def _configure_youth_commands(subparsers: argparse._SubParsersAction, service: services.ClubService) -> None:
    youth_parser = subparsers.add_parser("youth", help="Gerir camadas jovens")
    youth_sub = youth_parser.add_subparsers(dest="youth_command", required=True)

    add_team = youth_sub.add_parser("add", help="Adicionar equipa de formação")
    add_team.add_argument("name", help="Nome da equipa")
    add_team.add_argument("age_group", help="Escalão etário (ex: Sub-17)")
    add_team.add_argument("--coach-id", type=int, dest="coach_id", help="ID do treinador responsável")

    def handle_add(args: argparse.Namespace) -> None:
        team = service.add_youth_team(
            name=args.name,
            age_group=args.age_group,
            coach_id=args.coach_id,
        )
        print("Equipa criada:")
        print(f"  [{team.id}] {team.name} | {team.age_group} | Treinador: {team.coach_id or '-'}")

    add_team.set_defaults(func=handle_add)

    assign_player = youth_sub.add_parser("assign-player", help="Associar jogador a uma equipa")
    assign_player.add_argument("team_id", type=int, help="ID da equipa")
    assign_player.add_argument("player_id", type=int, help="ID do jogador")

    def handle_assign(args: argparse.Namespace) -> None:
        team = service.assign_player_to_team(team_id=args.team_id, player_id=args.player_id)
        print("Jogador associado:")
        print(
            f"  [{team.id}] {team.name} | Jogadores: {', '.join(map(str, team.player_ids)) or 'Nenhum'}"
        )

    assign_player.set_defaults(func=handle_assign)

    list_teams = youth_sub.add_parser("list", help="Listar equipas de formação")

    def handle_list(_: argparse.Namespace) -> None:
        teams = service.list_youth_teams()
        if not teams:
            print("Sem equipas de formação registadas.")
            return
        for team in teams:
            players = ", ".join(map(str, team.player_ids)) or "Nenhum"
            print(f"- [{team.id}] {team.name} | {team.age_group} | Treinador: {team.coach_id or '-'} | Jogadores: {players}")

    list_teams.set_defaults(func=handle_list)


def _configure_member_commands(subparsers: argparse._SubParsersAction, service: services.ClubService) -> None:
    member_parser = subparsers.add_parser("members", help="Gerir sócios")
    member_sub = member_parser.add_subparsers(dest="members_command", required=True)

    add_member = member_sub.add_parser("add", help="Adicionar sócio")
    add_member.add_argument("name", help="Nome completo")
    add_member.add_argument("membership_type", help="Tipo de quota (ex: anual)")
    add_member.add_argument("--dues-paid", action="store_true", help="Quota em dia")
    add_member.add_argument("--contact", help="Contacto")
    add_member.add_argument("--birthdate", help=DATE_HELP)

    def handle_add(args: argparse.Namespace) -> None:
        member = service.add_member(
            name=args.name,
            membership_type=args.membership_type,
            dues_paid=args.dues_paid,
            contact=args.contact,
            birthdate=parse_date(args.birthdate),
        )
        status = "Quota em dia" if member.dues_paid else "Quota em atraso"
        print("Sócio criado:")
        print(f"  {services.format_person(member)} | {member.membership_type} | {status}")

    add_member.set_defaults(func=handle_add)

    list_member = member_sub.add_parser("list", help="Listar sócios")

    def handle_list(_: argparse.Namespace) -> None:
        members = service.list_members()
        if not members:
            print("Sem sócios registados.")
            return
        for member in members:
            status = "Quota em dia" if member.dues_paid else "Quota em atraso"
            print(f"- {services.format_person(member)} | {member.membership_type} | {status}")

    list_member.set_defaults(func=handle_list)


def _configure_finance_commands(subparsers: argparse._SubParsersAction, service: services.ClubService) -> None:
    finance_parser = subparsers.add_parser("finance", help="Gerir finanças")
    finance_sub = finance_parser.add_subparsers(dest="finance_command", required=True)

    add_revenue = finance_sub.add_parser("add-revenue", help="Registar receita")
    add_revenue.add_argument("description", help="Descrição")
    add_revenue.add_argument("amount", type=float, help="Valor em euros")
    add_revenue.add_argument("category", help="Categoria (ex: Bilheteira)")
    add_revenue.add_argument("record_date", help=DATE_HELP)
    add_revenue.add_argument("--source", help="Origem da receita")

    def handle_add_revenue(args: argparse.Namespace) -> None:
        revenue = service.add_revenue(
            description=args.description,
            amount=args.amount,
            category=args.category,
            record_date=parse_date(args.record_date) or date.today(),
            source=args.source,
        )
        print("Receita registada:")
        print(f"  {services.format_financial(revenue)} | Origem: {revenue.source or 'N/A'}")

    add_revenue.set_defaults(func=handle_add_revenue)

    add_expense = finance_sub.add_parser("add-expense", help="Registar despesa")
    add_expense.add_argument("description", help="Descrição")
    add_expense.add_argument("amount", type=float, help="Valor em euros")
    add_expense.add_argument("category", help="Categoria (ex: Infraestruturas)")
    add_expense.add_argument("record_date", help=DATE_HELP)
    add_expense.add_argument("--vendor", help="Fornecedor")

    def handle_add_expense(args: argparse.Namespace) -> None:
        expense = service.add_expense(
            description=args.description,
            amount=args.amount,
            category=args.category,
            record_date=parse_date(args.record_date) or date.today(),
            vendor=args.vendor,
        )
        print("Despesa registada:")
        print(f"  {services.format_financial(expense)} | Fornecedor: {expense.vendor or 'N/A'}")

    add_expense.set_defaults(func=handle_add_expense)

    summary = finance_sub.add_parser("summary", help="Resumo financeiro")

    def handle_summary(_: argparse.Namespace) -> None:
        report = service.financial_summary()
        print("Resumo financeiro:")
        for key, value in sorted(report.items()):
            label = key.replace(":", " -> ")
            print(f"  {label}: €{value:.2f}")

    summary.set_defaults(func=handle_summary)


def build_parser(service: services.ClubService) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gestão completa para o clube Vila-Caiz")
    subparsers = parser.add_subparsers(dest="command")

    _configure_player_commands(subparsers, service)
    _configure_coach_commands(subparsers, service)
    _configure_physio_commands(subparsers, service)
    _configure_youth_commands(subparsers, service)
    _configure_member_commands(subparsers, service)
    _configure_finance_commands(subparsers, service)

    return parser


def dispatch_command(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if getattr(args, "command", None) is None:
        parser.print_help()
        return
    handler: Callable[[argparse.Namespace], None] = getattr(args, "func", None)
    if handler is None:
        parser.print_help()
        return
    handler(args)


def run_interactive_shell(parser: argparse.ArgumentParser) -> None:
    print("Modo interativo do Vila-Caiz CLI.")
    print("Escreva comandos como faria na linha de comandos (ex.: 'players list').")
    print("Use 'help' para ver a ajuda geral e 'exit' ou 'quit' para terminar.\n")
    while True:
        try:
            raw = input("vila-caiz> ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("\nInterrupção recebida. A sair do modo interativo.")
            break
        if not raw:
            continue
        lowered = raw.lower()
        if lowered in {"exit", "quit"}:
            print("Até breve!")
            break
        if lowered in {"help", "?"}:
            parser.print_help()
            continue
        try:
            args = parser.parse_args(shlex.split(raw))
        except SystemExit:
            # argparse already imprimiu a mensagem de erro/ajuda
            continue
        dispatch_command(parser, args)


def main(argv: Optional[list[str]] = None) -> None:
    storage.ensure_storage()
    service = services.ClubService()
    parser = build_parser(service)

    if argv is None:
        actual_args = sys.argv[1:]
    else:
        actual_args = argv

    if not actual_args:
        run_interactive_shell(parser)
        return

    args = parser.parse_args(actual_args)
    dispatch_command(parser, args)


if __name__ == "__main__":
    main()
