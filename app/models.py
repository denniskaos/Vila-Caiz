"""Domain models for the Vila-Caiz club management application."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Dict, List, Optional


@dataclass
class Person:
    """Base entity for staff and members."""

    id: int
    name: str
    birthdate: Optional[date] = None
    contact: Optional[str] = None
    photo_url: Optional[str] = None
    season_id: Optional[int] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        for key, value in list(data.items()):
            if isinstance(value, date):
                data[key] = value.isoformat()
        return data


@dataclass
class User:
    """Representa um utilizador autenticado na aplicação."""

    id: int
    username: str
    password_hash: str
    role: str
    full_name: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Player(Person):
    position: str = ""
    squad: str = "senior"
    shirt_number: Optional[int] = None
    af_porto_id: Optional[str] = None
    youth_monthly_fee: Optional[float] = None
    youth_monthly_paid: bool = False
    youth_kit_fee: Optional[float] = None
    youth_kit_paid: bool = False
    youth_monthly_revenue_id: Optional[int] = None
    youth_kit_revenue_id: Optional[int] = None


@dataclass
class Coach(Person):
    role: str = "Head Coach"
    license_level: Optional[str] = None


@dataclass
class Physiotherapist(Person):
    specialization: Optional[str] = None


@dataclass
class Treatment:
    id: int
    player_id: int
    physio_id: Optional[int] = None
    diagnosis: str = ""
    treatment_plan: str = ""
    start_date: date = field(default_factory=date.today)
    expected_return: Optional[date] = None
    unavailable: bool = True
    notes: Optional[str] = None
    season_id: Optional[int] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["start_date"] = self.start_date.isoformat()
        if self.expected_return is not None:
            data["expected_return"] = self.expected_return.isoformat()
        return data


@dataclass
class MatchPlan:
    id: int
    squad: str
    match_date: date
    kickoff_time: Optional[str] = None
    venue: Optional[str] = None
    opponent: str = ""
    competition: Optional[str] = None
    coach_id: Optional[int] = None
    notes: Optional[str] = None
    starters: List[int] = field(default_factory=list)
    substitutes: List[int] = field(default_factory=list)
    season_id: Optional[int] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["match_date"] = self.match_date.isoformat()
        return data


@dataclass
class YouthTeam:
    id: int
    name: str
    age_group: str
    coach_id: Optional[int] = None
    player_ids: List[int] = field(default_factory=list)
    season_id: Optional[int] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MembershipType:
    id: int
    name: str
    amount: float
    frequency: str = "Mensal"
    description: Optional[str] = None
    season_id: Optional[int] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Member(Person):
    member_number: Optional[int] = None
    membership_type: str = "standard"
    membership_type_id: Optional[int] = None
    dues_paid: bool = False
    dues_paid_until: Optional[str] = None
    membership_since: Optional[date] = None


@dataclass
class MembershipPayment:
    id: int
    member_id: int
    membership_type_id: Optional[int]
    amount: float
    period: str
    paid_on: date
    notes: Optional[str] = None
    season_id: Optional[int] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["paid_on"] = self.paid_on.isoformat()
        return data


@dataclass
class FinancialRecord:
    id: int
    description: str
    amount: float
    category: str
    record_date: date
    season_id: Optional[int] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["record_date"] = self.record_date.isoformat()
        return data


@dataclass
class Revenue(FinancialRecord):
    source: Optional[str] = None


@dataclass
class Expense(FinancialRecord):
    vendor: Optional[str] = None


@dataclass
class Season:
    id: int
    name: str
    start_date: date
    end_date: date
    notes: Optional[str] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["start_date"] = self.start_date.isoformat()
        data["end_date"] = self.end_date.isoformat()
        return data


EntityType = Dict[str, List[Dict]]
