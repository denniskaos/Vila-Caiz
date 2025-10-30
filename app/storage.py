"""Persistent storage helpers for the club management application."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Type, TypeVar

from . import models

DATA_FILE = Path("data/club.json")
DEFAULT_STRUCTURE = {
    "players": [],
    "coaches": [],
    "physiotherapists": [],
    "youth_teams": [],
    "members": [],
    "revenues": [],
    "expenses": [],
}

T = TypeVar("T")


def ensure_storage() -> None:
    """Create the storage file if it does not exist."""
    if not DATA_FILE.parent.exists():
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text(json.dumps(DEFAULT_STRUCTURE, indent=2), encoding="utf-8")


def load_data() -> Dict[str, List[Dict[str, Any]]]:
    ensure_storage()
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    for key, default in DEFAULT_STRUCTURE.items():
        data.setdefault(key, default.copy())
    return data


def save_data(data: Dict[str, List[Dict[str, Any]]]) -> None:
    ensure_storage()
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def next_id(items: Iterable[Dict[str, Any]]) -> int:
    """Return the next integer id for a collection of dictionaries."""
    max_id = 0
    for item in items:
        max_id = max(max_id, int(item.get("id", 0)))
    return max_id + 1


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return date.fromisoformat(value)


def serialize_entity(entity: Any) -> Dict[str, Any]:
    if hasattr(entity, "to_dict"):
        return entity.to_dict()  # type: ignore[return-value]
    result = asdict(entity)
    for field_name, field_value in list(result.items()):
        if isinstance(field_value, date):
            result[field_name] = field_value.isoformat()
    return result


def instantiate(model_cls: Type[T], payload: Dict[str, Any]) -> T:
    """Create a dataclass instance from the stored payload."""
    kwargs = dict(payload)
    for field in model_cls.__dataclass_fields__.values():  # type: ignore[attr-defined]
        if field.type is date and isinstance(kwargs.get(field.name), str):
            kwargs[field.name] = date.fromisoformat(kwargs[field.name])
    return model_cls(**kwargs)  # type: ignore[arg-type]
