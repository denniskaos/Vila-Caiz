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

    def to_dict(self) -> Dict:
        data = asdict(self)
        if self.birthdate is not None:
            data["birthdate"] = self.birthdate.isoformat()
        return data


@dataclass
class Player(Person):
    position: str = ""
    squad: str = "senior"
    shirt_number: Optional[int] = None


@dataclass
class Coach(Person):
    role: str = "Head Coach"
    license_level: Optional[str] = None


@dataclass
class Physiotherapist(Person):
    specialization: Optional[str] = None


@dataclass
class YouthTeam:
    id: int
    name: str
    age_group: str
    coach_id: Optional[int] = None
    player_ids: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Member(Person):
    membership_type: str = "standard"
    dues_paid: bool = False


@dataclass
class FinancialRecord:
    id: int
    description: str
    amount: float
    category: str
    record_date: date

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


EntityType = Dict[str, List[Dict]]
