"""Business services for managing the football club entities."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

from . import models, storage


class ClubService:
    """Facade that exposes CRUD helpers for the different entities."""

    def __init__(self) -> None:
        self._data = storage.load_data()

    # Generic helpers -------------------------------------------------
    def _create_entity(self, key: str, payload: Dict) -> Dict:
        collection = self._data[key]
        payload = dict(payload)
        payload["id"] = storage.next_id(collection)
        collection.append(payload)
        self._persist()
        return payload

    def _list_entities(self, key: str) -> List[Dict]:
        return list(self._data[key])

    def _find_entity(self, key: str, entity_id: int) -> Dict | None:
        for item in self._data[key]:
            if int(item.get("id")) == entity_id:
                return item
        return None

    def _update_entity(self, key: str, entity_id: int, updates: Dict) -> Dict:
        for item in self._data[key]:
            if int(item.get("id")) == entity_id:
                item.update({k: v for k, v in updates.items() if v is not None})
                self._persist()
                return item
        raise ValueError(f"{key[:-1].capitalize()} with id {entity_id} not found")

    def _remove_entity(self, key: str, entity_id: int) -> None:
        collection = self._data[key]
        for index, item in enumerate(collection):
            if int(item.get("id")) == entity_id:
                del collection[index]
                self._persist()
                return
        raise ValueError(f"{key[:-1].capitalize()} with id {entity_id} not found")

    def _persist(self) -> None:
        storage.save_data(self._data)

    # Players ---------------------------------------------------------
    def add_player(
        self,
        name: str,
        position: str,
        squad: str = "senior",
        birthdate: Optional[date] = None,
        contact: Optional[str] = None,
        shirt_number: Optional[int] = None,
    ) -> models.Player:
        payload = storage.serialize_entity(
            models.Player(
                id=0,
                name=name,
                position=position,
                squad=squad,
                birthdate=birthdate,
                contact=contact,
                shirt_number=shirt_number,
            )
        )
        stored = self._create_entity("players", payload)
        return storage.instantiate(models.Player, stored)

    def list_players(self) -> List[models.Player]:
        return [storage.instantiate(models.Player, item) for item in self._list_entities("players")]

    # Coaches ---------------------------------------------------------
    def add_coach(
        self,
        name: str,
        role: str,
        license_level: Optional[str] = None,
        birthdate: Optional[date] = None,
        contact: Optional[str] = None,
    ) -> models.Coach:
        payload = storage.serialize_entity(
            models.Coach(
                id=0,
                name=name,
                role=role,
                license_level=license_level,
                birthdate=birthdate,
                contact=contact,
            )
        )
        stored = self._create_entity("coaches", payload)
        return storage.instantiate(models.Coach, stored)

    def list_coaches(self) -> List[models.Coach]:
        return [storage.instantiate(models.Coach, item) for item in self._list_entities("coaches")]

    # Physiotherapists ------------------------------------------------
    def add_physiotherapist(
        self,
        name: str,
        specialization: Optional[str] = None,
        birthdate: Optional[date] = None,
        contact: Optional[str] = None,
    ) -> models.Physiotherapist:
        payload = storage.serialize_entity(
            models.Physiotherapist(
                id=0,
                name=name,
                specialization=specialization,
                birthdate=birthdate,
                contact=contact,
            )
        )
        stored = self._create_entity("physiotherapists", payload)
        return storage.instantiate(models.Physiotherapist, stored)

    def list_physiotherapists(self) -> List[models.Physiotherapist]:
        return [
            storage.instantiate(models.Physiotherapist, item)
            for item in self._list_entities("physiotherapists")
        ]

    # Youth teams -----------------------------------------------------
    def add_youth_team(
        self,
        name: str,
        age_group: str,
        coach_id: Optional[int] = None,
    ) -> models.YouthTeam:
        payload = models.YouthTeam(
            id=0,
            name=name,
            age_group=age_group,
            coach_id=coach_id,
        ).to_dict()
        stored = self._create_entity("youth_teams", payload)
        return storage.instantiate(models.YouthTeam, stored)

    def assign_player_to_team(self, team_id: int, player_id: int) -> models.YouthTeam:
        for team in self._data["youth_teams"]:
            if int(team.get("id")) == team_id:
                players = set(team.setdefault("player_ids", []))
                players.add(player_id)
                team["player_ids"] = sorted(players)
                self._persist()
                return storage.instantiate(models.YouthTeam, team)
        raise ValueError(f"Youth team with id {team_id} not found")

    def list_youth_teams(self) -> List[models.YouthTeam]:
        return [storage.instantiate(models.YouthTeam, item) for item in self._list_entities("youth_teams")]

    # Members ---------------------------------------------------------
    def add_membership_type(
        self,
        name: str,
        amount: float,
        frequency: str = "Mensal",
        description: Optional[str] = None,
    ) -> models.MembershipType:
        payload = storage.serialize_entity(
            models.MembershipType(
                id=0,
                name=name,
                amount=amount,
                frequency=frequency,
                description=description,
            )
        )
        stored = self._create_entity("membership_types", payload)
        return storage.instantiate(models.MembershipType, stored)

    def list_membership_types(self) -> List[models.MembershipType]:
        return [
            storage.instantiate(models.MembershipType, item)
            for item in self._list_entities("membership_types")
        ]

    def get_membership_type(self, membership_type_id: int) -> Optional[models.MembershipType]:
        record = self._find_entity("membership_types", membership_type_id)
        if record is None:
            return None
        return storage.instantiate(models.MembershipType, record)

    def add_member(
        self,
        name: str,
        membership_type: str,
        dues_paid: bool = False,
        contact: Optional[str] = None,
        birthdate: Optional[date] = None,
        membership_type_id: Optional[int] = None,
        dues_paid_until: Optional[str] = None,
    ) -> models.Member:
        resolved_type = membership_type
        if membership_type_id is not None:
            type_info = self.get_membership_type(membership_type_id)
            if type_info is None:
                raise ValueError(f"Membership type with id {membership_type_id} not found")
            resolved_type = type_info.name
        payload = storage.serialize_entity(
            models.Member(
                id=0,
                name=name,
                membership_type=resolved_type,
                membership_type_id=membership_type_id,
                dues_paid=dues_paid,
                dues_paid_until=dues_paid_until,
                contact=contact,
                birthdate=birthdate,
            )
        )
        stored = self._create_entity("members", payload)
        return storage.instantiate(models.Member, stored)

    def list_members(self) -> List[models.Member]:
        return [storage.instantiate(models.Member, item) for item in self._list_entities("members")]

    def register_membership_payment(
        self,
        member_id: int,
        amount: float,
        period: str,
        paid_on: date,
        membership_type_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> models.MembershipPayment:
        member_record = self._find_entity("members", member_id)
        if member_record is None:
            raise ValueError(f"Member with id {member_id} not found")
        membership_type_name = member_record.get("membership_type")
        if membership_type_id is not None:
            type_record = self._find_entity("membership_types", membership_type_id)
            if type_record is None:
                raise ValueError(f"Membership type with id {membership_type_id} not found")
            membership_type_name = type_record.get("name", membership_type_name)
        payload = storage.serialize_entity(
            models.MembershipPayment(
                id=0,
                member_id=member_id,
                membership_type_id=membership_type_id,
                amount=amount,
                period=period,
                paid_on=paid_on,
                notes=notes,
            )
        )
        stored = self._create_entity("membership_payments", payload)
        updates = {
            "dues_paid": True,
            "dues_paid_until": period,
        }
        if membership_type_id is not None and membership_type_name:
            updates["membership_type_id"] = membership_type_id
            updates["membership_type"] = membership_type_name
        self._update_entity("members", member_id, updates)
        return storage.instantiate(models.MembershipPayment, stored)

    def list_membership_payments(self) -> List[models.MembershipPayment]:
        return [
            storage.instantiate(models.MembershipPayment, item)
            for item in self._list_entities("membership_payments")
        ]

    def list_member_payments(self, member_id: int) -> List[models.MembershipPayment]:
        payments = self.list_membership_payments()
        return [payment for payment in payments if payment.member_id == member_id]

    # Finance ---------------------------------------------------------
    def add_revenue(
        self,
        description: str,
        amount: float,
        category: str,
        record_date: date,
        source: Optional[str] = None,
    ) -> models.Revenue:
        payload = storage.serialize_entity(
            models.Revenue(
                id=0,
                description=description,
                amount=amount,
                category=category,
                record_date=record_date,
                source=source,
            )
        )
        stored = self._create_entity("revenues", payload)
        return storage.instantiate(models.Revenue, stored)

    def add_expense(
        self,
        description: str,
        amount: float,
        category: str,
        record_date: date,
        vendor: Optional[str] = None,
    ) -> models.Expense:
        payload = storage.serialize_entity(
            models.Expense(
                id=0,
                description=description,
                amount=amount,
                category=category,
                record_date=record_date,
                vendor=vendor,
            )
        )
        stored = self._create_entity("expenses", payload)
        return storage.instantiate(models.Expense, stored)

    def list_financial_records(self) -> Tuple[List[models.Revenue], List[models.Expense]]:
        revenues = [storage.instantiate(models.Revenue, item) for item in self._list_entities("revenues")]
        expenses = [storage.instantiate(models.Expense, item) for item in self._list_entities("expenses")]
        return revenues, expenses

    def financial_summary(self) -> Dict[str, float]:
        revenues, expenses = self.list_financial_records()
        total_revenue = sum(record.amount for record in revenues)
        total_expense = sum(record.amount for record in expenses)
        balance = total_revenue - total_expense

        summary: Dict[str, float] = {
            "total_revenue": round(total_revenue, 2),
            "total_expense": round(total_expense, 2),
            "balance": round(balance, 2),
        }

        category_totals: Dict[str, float] = defaultdict(float)
        for record in revenues:
            category_totals[f"revenue:{record.category}"] += record.amount
        for record in expenses:
            category_totals[f"expense:{record.category}"] += record.amount

        for key, value in category_totals.items():
            summary[key] = round(value, 2)

        return summary

    # Utility ---------------------------------------------------------
    def refresh(self) -> None:
        """Reload data from disk to reflect external changes."""
        self._data = storage.load_data()


def format_person(person: models.Person) -> str:
    birthdate = person.birthdate.isoformat() if person.birthdate else "-"
    return f"[{person.id}] {person.name} | {birthdate} | {person.contact or '-'}"


def format_financial(record: models.FinancialRecord) -> str:
    date_str = record.record_date.isoformat()
    return f"[{record.id}] {record.description} | {date_str} | {record.category} | €{record.amount:.2f}"
