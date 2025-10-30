"""Business services for managing the football club entities."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Tuple

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

    def update_player(
        self,
        player_id: int,
        *,
        name: Optional[str] = None,
        position: Optional[str] = None,
        squad: Optional[str] = None,
        birthdate: Optional[date] = None,
        contact: Optional[str] = None,
        shirt_number: Optional[int] = None,
    ) -> models.Player:
        updates: Dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if position is not None:
            updates["position"] = position
        if squad is not None:
            updates["squad"] = squad
        if birthdate is not None:
            updates["birthdate"] = birthdate.isoformat()
        if contact is not None:
            updates["contact"] = contact
        if shirt_number is not None:
            updates["shirt_number"] = shirt_number
        record = self._update_entity("players", player_id, updates)
        return storage.instantiate(models.Player, record)

    def remove_player(self, player_id: int) -> None:
        self._remove_entity("players", player_id)

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

    def update_coach(
        self,
        coach_id: int,
        *,
        name: Optional[str] = None,
        role: Optional[str] = None,
        license_level: Optional[str] = None,
        birthdate: Optional[date] = None,
        contact: Optional[str] = None,
    ) -> models.Coach:
        updates: Dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if role is not None:
            updates["role"] = role
        if license_level is not None:
            updates["license_level"] = license_level
        if birthdate is not None:
            updates["birthdate"] = birthdate.isoformat()
        if contact is not None:
            updates["contact"] = contact
        record = self._update_entity("coaches", coach_id, updates)
        return storage.instantiate(models.Coach, record)

    def remove_coach(self, coach_id: int) -> None:
        self._remove_entity("coaches", coach_id)

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

    def update_physiotherapist(
        self,
        physio_id: int,
        *,
        name: Optional[str] = None,
        specialization: Optional[str] = None,
        birthdate: Optional[date] = None,
        contact: Optional[str] = None,
    ) -> models.Physiotherapist:
        updates: Dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if specialization is not None:
            updates["specialization"] = specialization
        if birthdate is not None:
            updates["birthdate"] = birthdate.isoformat()
        if contact is not None:
            updates["contact"] = contact
        record = self._update_entity("physiotherapists", physio_id, updates)
        return storage.instantiate(models.Physiotherapist, record)

    def remove_physiotherapist(self, physio_id: int) -> None:
        self._remove_entity("physiotherapists", physio_id)

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

    def update_youth_team(
        self,
        team_id: int,
        *,
        name: Optional[str] = None,
        age_group: Optional[str] = None,
        coach_id: Optional[int] = None,
    ) -> models.YouthTeam:
        updates: Dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if age_group is not None:
            updates["age_group"] = age_group
        if coach_id is not None:
            updates["coach_id"] = coach_id
        record = self._update_entity("youth_teams", team_id, updates)
        return storage.instantiate(models.YouthTeam, record)

    def remove_youth_team(self, team_id: int) -> None:
        self._remove_entity("youth_teams", team_id)

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

    def update_membership_type(
        self,
        membership_type_id: int,
        *,
        name: Optional[str] = None,
        amount: Optional[float] = None,
        frequency: Optional[str] = None,
        description: Optional[str] = None,
    ) -> models.MembershipType:
        updates: Dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if amount is not None:
            updates["amount"] = amount
        if frequency is not None:
            updates["frequency"] = frequency
        if description is not None:
            updates["description"] = description
        record = self._update_entity("membership_types", membership_type_id, updates)
        return storage.instantiate(models.MembershipType, record)

    def remove_membership_type(self, membership_type_id: int) -> None:
        self._remove_entity("membership_types", membership_type_id)

    def _next_member_number(self) -> int:
        highest = 0
        for record in self._data["members"]:
            raw = record.get("member_number") or record.get("id")
            if raw is None:
                continue
            try:
                number = int(raw)
            except (TypeError, ValueError):
                continue
            highest = max(highest, number)
        return highest + 1

    def add_member(
        self,
        name: str,
        membership_type: str,
        dues_paid: bool = False,
        contact: Optional[str] = None,
        birthdate: Optional[date] = None,
        membership_type_id: Optional[int] = None,
        dues_paid_until: Optional[str] = None,
        member_number: Optional[int] = None,
    ) -> models.Member:
        resolved_type = membership_type
        if membership_type_id is not None:
            type_info = self.get_membership_type(membership_type_id)
            if type_info is None:
                raise ValueError(f"Membership type with id {membership_type_id} not found")
            resolved_type = type_info.name
        number = member_number if member_number is not None else self._next_member_number()
        payload = storage.serialize_entity(
            models.Member(
                id=0,
                name=name,
                member_number=number,
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

    def update_member(
        self,
        member_id: int,
        *,
        name: Optional[str] = None,
        membership_type: Optional[str] = None,
        membership_type_id: Optional[int] = None,
        dues_paid: Optional[bool] = None,
        dues_paid_until: Optional[str] = None,
        contact: Optional[str] = None,
        birthdate: Optional[date] = None,
        member_number: Optional[int] = None,
    ) -> models.Member:
        updates: Dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if membership_type is not None:
            updates["membership_type"] = membership_type
        if membership_type_id is not None:
            updates["membership_type_id"] = membership_type_id
        if dues_paid is not None:
            updates["dues_paid"] = dues_paid
        if dues_paid_until is not None:
            updates["dues_paid_until"] = dues_paid_until
        if contact is not None:
            updates["contact"] = contact
        if birthdate is not None:
            updates["birthdate"] = birthdate.isoformat()
        if member_number is not None:
            updates["member_number"] = member_number
        record = self._update_entity("members", member_id, updates)
        return storage.instantiate(models.Member, record)

    def remove_member(self, member_id: int) -> None:
        payments = self._data["membership_payments"]
        self._data["membership_payments"] = [
            payment for payment in payments if int(payment.get("member_id", 0)) != member_id
        ]
        self._persist()
        self._remove_entity("members", member_id)

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
        member_name = member_record.get("name", f"Sócio #{member_id}")
        member_number = member_record.get("member_number") or member_record.get("id")
        description_parts = ["Quota"]
        if membership_type_name:
            description_parts.append(membership_type_name)
        description = " ".join(description_parts)
        descriptor = f"{description} - {member_name}"
        if member_number is not None:
            descriptor = f"{descriptor} (#{member_number})"
        self.add_revenue(
            description=descriptor,
            amount=amount,
            category="Quotas de Sócios",
            record_date=paid_on,
            source="Sócios",
        )
        return storage.instantiate(models.MembershipPayment, stored)

    def list_membership_payments(self) -> List[models.MembershipPayment]:
        return [
            storage.instantiate(models.MembershipPayment, item)
            for item in self._list_entities("membership_payments")
        ]

    def list_member_payments(self, member_id: int) -> List[models.MembershipPayment]:
        payments = self.list_membership_payments()
        return [payment for payment in payments if payment.member_id == member_id]

    def remove_membership_payment(self, payment_id: int) -> None:
        payment_record = self._find_entity("membership_payments", payment_id)
        if payment_record is None:
            raise ValueError(f"Membership payment with id {payment_id} not found")

        member_id = int(payment_record.get("member_id", 0))

        payments = self._data["membership_payments"]
        self._data["membership_payments"] = [
            item for item in payments if int(item.get("id", 0)) != payment_id
        ]
        self._persist()

        if member_id:
            remaining_payments = [
                storage.instantiate(models.MembershipPayment, item)
                for item in self._data["membership_payments"]
                if int(item.get("member_id", 0)) == member_id
            ]
            dues_paid = bool(remaining_payments)
            dues_paid_until: Optional[str]
            if remaining_payments:
                latest_payment = max(remaining_payments, key=lambda payment: payment.paid_on)
                dues_paid_until = latest_payment.period
            else:
                dues_paid_until = None

            updates = {
                "dues_paid": dues_paid,
                "dues_paid_until": dues_paid_until,
            }
            self._update_entity("members", member_id, updates)

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

    def update_revenue(
        self,
        revenue_id: int,
        *,
        description: Optional[str] = None,
        amount: Optional[float] = None,
        category: Optional[str] = None,
        record_date: Optional[date] = None,
        source: Optional[str] = None,
    ) -> models.Revenue:
        updates: Dict[str, Any] = {}
        if description is not None:
            updates["description"] = description
        if amount is not None:
            updates["amount"] = amount
        if category is not None:
            updates["category"] = category
        if record_date is not None:
            updates["record_date"] = record_date.isoformat()
        if source is not None:
            updates["source"] = source
        record = self._update_entity("revenues", revenue_id, updates)
        return storage.instantiate(models.Revenue, record)

    def remove_revenue(self, revenue_id: int) -> None:
        self._remove_entity("revenues", revenue_id)

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

    def update_expense(
        self,
        expense_id: int,
        *,
        description: Optional[str] = None,
        amount: Optional[float] = None,
        category: Optional[str] = None,
        record_date: Optional[date] = None,
        vendor: Optional[str] = None,
    ) -> models.Expense:
        updates: Dict[str, Any] = {}
        if description is not None:
            updates["description"] = description
        if amount is not None:
            updates["amount"] = amount
        if category is not None:
            updates["category"] = category
        if record_date is not None:
            updates["record_date"] = record_date.isoformat()
        if vendor is not None:
            updates["vendor"] = vendor
        record = self._update_entity("expenses", expense_id, updates)
        return storage.instantiate(models.Expense, record)

    def remove_expense(self, expense_id: int) -> None:
        self._remove_entity("expenses", expense_id)

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
