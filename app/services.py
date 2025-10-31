"""Business services for managing the football club entities."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Tuple

from . import models, storage


UNSET = object()

SEASONAL_COLLECTIONS = {
    "players",
    "coaches",
    "physiotherapists",
    "treatments",
    "match_plans",
    "youth_teams",
    "members",
    "membership_types",
    "membership_payments",
    "revenues",
    "expenses",
}

YOUTH_SQUADS = {"juniores", "juvenis", "iniciados", "infantis"}
YOUTH_REVENUE_CATEGORY = "Camadas Jovens"
YOUTH_MONTHLY_SOURCE = "Mensalidade Formação"
YOUTH_KIT_SOURCE = "Kit de Treino Formação"


class ClubService:
    """Facade that exposes CRUD helpers for the different entities."""

    def __init__(self) -> None:
        self._data = storage.load_data()
        self._active_season_id: Optional[int] = None
        self._ensure_season_setup()
        self._migrate_legacy_fields()

    def _migrate_legacy_fields(self) -> None:
        changed = False
        players = self._data.setdefault("players", [])
        for player in players:
            if "af_porto_id" not in player and "federation_id" in player:
                player["af_porto_id"] = player.pop("federation_id")
                changed = True
        if changed:
            self._persist()

    # Season helpers -------------------------------------------------
    def _ensure_season_setup(self) -> None:
        seasons = self._data.setdefault("seasons", [])
        active_id = self._data.get("active_season_id")
        changed = False

        if not seasons:
            today = date.today()
            start_year = today.year if today.month >= 7 else today.year - 1
            end_year = start_year + 1
            default_name = f"Época {start_year}/{end_year}"
            default_season = storage.serialize_entity(
                models.Season(
                    id=0,
                    name=default_name,
                    start_date=date(start_year, 7, 1),
                    end_date=date(end_year, 6, 30),
                )
            )
            default_season["id"] = storage.next_id(seasons)
            seasons.append(default_season)
            active_id = default_season["id"]
            changed = True

        active_int: Optional[int] = None
        if active_id is not None:
            try:
                active_int = int(active_id)
            except (TypeError, ValueError):
                active_int = None

        if seasons and (active_int is None or all(int(season.get("id", 0)) != active_int for season in seasons)):
            first = seasons[0]
            active_int = int(first.get("id", 1))
            changed = True

        self._active_season_id = active_int
        self._data["active_season_id"] = active_int

        if self._assign_missing_season_ids(active_int):
            changed = True

        if changed:
            self._persist()

    def _assign_missing_season_ids(self, season_id: Optional[int]) -> bool:
        if season_id is None:
            return False
        changed = False
        for key in SEASONAL_COLLECTIONS:
            collection = self._data.setdefault(key, [])
            for item in collection:
                current = item.get("season_id")
                try:
                    current_int = int(current) if current is not None else None
                except (TypeError, ValueError):
                    current_int = None
                if current_int is None or current_int == 0:
                    item["season_id"] = season_id
                    changed = True
        return changed

    @property
    def active_season_id(self) -> int:
        if self._active_season_id is None:
            active_id = self._data.get("active_season_id")
            if active_id is None:
                self._ensure_season_setup()
                active_id = self._data.get("active_season_id")
            if active_id is None:
                raise ValueError("Nenhuma época ativa definida")
            self._active_season_id = int(active_id)
        return self._active_season_id

    def list_seasons(self) -> List[models.Season]:
        seasons = self._data.setdefault("seasons", [])
        return [storage.instantiate(models.Season, item) for item in seasons]

    def get_active_season(self) -> models.Season:
        active_id = self.active_season_id
        for season in self._data.setdefault("seasons", []):
            if int(season.get("id", 0)) == active_id:
                return storage.instantiate(models.Season, season)
        raise ValueError("Época ativa não encontrada")

    def create_season(self, name: str, start_date: date, end_date: date, notes: Optional[str] = None) -> models.Season:
        if end_date < start_date:
            raise ValueError("A data de fim deve ser posterior à data de início da época.")
        seasons = self._data.setdefault("seasons", [])
        payload = storage.serialize_entity(
            models.Season(id=0, name=name, start_date=start_date, end_date=end_date, notes=notes)
        )
        payload["id"] = storage.next_id(seasons)
        seasons.append(payload)
        self._persist()
        return storage.instantiate(models.Season, payload)

    def update_season(
        self,
        season_id: int,
        *,
        name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        notes: Optional[str] = UNSET,
    ) -> models.Season:
        seasons = self._data.setdefault("seasons", [])
        for season in seasons:
            if int(season.get("id", 0)) != season_id:
                continue
            current_start = storage.parse_date(season.get("start_date"))
            current_end = storage.parse_date(season.get("end_date"))
            new_start = start_date or current_start
            new_end = end_date or current_end
            if new_start and new_end and new_end < new_start:
                raise ValueError("A data de fim deve ser posterior à data de início da época.")
            if name is not None:
                season["name"] = name
            if start_date is not None:
                season["start_date"] = start_date.isoformat()
            if end_date is not None:
                season["end_date"] = end_date.isoformat()
            if notes is not UNSET:
                season["notes"] = notes
            self._persist()
            return storage.instantiate(models.Season, season)
        raise ValueError(f"Época com id {season_id} não encontrada")

    def set_active_season(self, season_id: int) -> models.Season:
        seasons = self._data.setdefault("seasons", [])
        for season in seasons:
            if int(season.get("id", 0)) == season_id:
                self._data["active_season_id"] = season_id
                self._active_season_id = season_id
                self._persist()
                return storage.instantiate(models.Season, season)
        raise ValueError(f"Época com id {season_id} não encontrada")

    def remove_season(self, season_id: int) -> None:
        if season_id == self.active_season_id:
            raise ValueError("Não é possível eliminar a época ativa.")
        seasons = self._data.setdefault("seasons", [])
        for index, season in enumerate(seasons):
            if int(season.get("id", 0)) == season_id:
                del seasons[index]
                break
        else:
            raise ValueError(f"Época com id {season_id} não encontrada")

        for key in SEASONAL_COLLECTIONS:
            collection = self._data.setdefault(key, [])
            self._data[key] = [
                item for item in collection if int(item.get("season_id", 0) or 0) != season_id
            ]
        self._persist()

    # Generic helpers -------------------------------------------------
    def _create_entity(self, key: str, payload: Dict) -> Dict:
        collection = self._data.setdefault(key, [])
        payload = dict(payload)
        payload["id"] = storage.next_id(collection)
        if key in SEASONAL_COLLECTIONS:
            payload["season_id"] = payload.get("season_id") or self.active_season_id
        collection.append(payload)
        self._persist()
        return payload

    def _list_entities(self, key: str, *, include_all: bool = False) -> List[Dict]:
        collection = self._data.setdefault(key, [])
        if include_all or key not in SEASONAL_COLLECTIONS:
            return list(collection)
        active_id = self.active_season_id
        filtered: List[Dict] = []
        for item in collection:
            season_value = item.get("season_id")
            try:
                season_int = int(season_value) if season_value is not None else None
            except (TypeError, ValueError):
                season_int = None
            if season_int == active_id:
                filtered.append(item)
        return filtered

    def _find_entity(self, key: str, entity_id: int) -> Dict | None:
        for item in self._data.setdefault(key, []):
            if int(item.get("id")) == entity_id:
                return item
        return None

    def _update_entity(self, key: str, entity_id: int, updates: Dict) -> Dict:
        for item in self._data.setdefault(key, []):
            if int(item.get("id")) == entity_id:
                item.update(updates)
                self._persist()
                return item
        raise ValueError(f"{key[:-1].capitalize()} with id {entity_id} not found")

    def _remove_entity(self, key: str, entity_id: int) -> None:
        collection = self._data.setdefault(key, [])
        for index, item in enumerate(collection):
            if int(item.get("id")) == entity_id:
                del collection[index]
                self._persist()
                return
        raise ValueError(f"{key[:-1].capitalize()} with id {entity_id} not found")

    def _persist(self) -> None:
        storage.save_data(self._data)
        active_id = self._data.get("active_season_id")
        self._active_season_id = int(active_id) if active_id is not None else None

    def _is_youth_squad(self, squad: Optional[str]) -> bool:
        if squad is None:
            return False
        return squad.lower() in YOUTH_SQUADS

    def _coerce_amount(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            text = str(value).strip()
        except Exception:  # pragma: no cover - defensive branch
            return None
        if not text:
            return None
        text = text.replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return None

    def _coerce_int(self, value: Any) -> Optional[int]:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _normalize_player_selection(
        self, player_ids: Iterable[Any], *, exclude: Iterable[int] | None = None
    ) -> List[int]:
        valid_players = {player.id for player in self.list_players()}
        exclude_set = set(exclude or [])
        normalized: List[int] = []
        seen: set[int] = set()
        for raw in player_ids:
            player_id = self._coerce_int(raw)
            if player_id is None:
                continue
            if player_id in exclude_set or player_id in seen:
                continue
            if player_id not in valid_players:
                continue
            normalized.append(player_id)
            seen.add(player_id)
        return normalized

    def _sync_youth_revenue(
        self,
        *,
        player_id: int,
        player_name: str,
        squad: str,
        amount: Optional[float],
        paid: bool,
        existing_revenue_id: Optional[int],
        description_label: str,
        source_label: str,
    ) -> Optional[int]:
        if not paid or amount is None or amount <= 0:
            if existing_revenue_id is not None:
                try:
                    self.remove_revenue(existing_revenue_id)
                except ValueError:
                    pass
            return None

        name = player_name.strip() if isinstance(player_name, str) else str(player_name)
        if not name:
            name = f"Jogador #{player_id}"
        squad_label = squad.title() if isinstance(squad, str) else str(squad)
        description = f"{description_label} - {name} ({squad_label})"

        if existing_revenue_id is not None:
            try:
                revenue = self.update_revenue(
                    existing_revenue_id,
                    description=description,
                    amount=amount,
                    category=YOUTH_REVENUE_CATEGORY,
                    record_date=date.today(),
                    source=source_label,
                )
                return revenue.id
            except ValueError:
                existing_revenue_id = None

        revenue = self.add_revenue(
            description=description,
            amount=amount,
            category=YOUTH_REVENUE_CATEGORY,
            record_date=date.today(),
            source=source_label,
        )
        return revenue.id

    # Players ---------------------------------------------------------
    def add_player(
        self,
        name: str,
        position: str,
        squad: str = "senior",
        birthdate: Optional[date] = None,
        contact: Optional[str] = None,
        shirt_number: Optional[int] = None,
        af_porto_id: Optional[str] = None,
        photo_url: Optional[str] = None,
        youth_monthly_fee: Optional[float] = None,
        youth_monthly_paid: bool = False,
        youth_kit_fee: Optional[float] = None,
        youth_kit_paid: bool = False,
    ) -> models.Player:
        is_youth = self._is_youth_squad(squad)
        monthly_fee = self._coerce_amount(youth_monthly_fee) if is_youth else None
        kit_fee = self._coerce_amount(youth_kit_fee) if is_youth else None
        monthly_paid_flag = bool(youth_monthly_paid) if is_youth else False
        kit_paid_flag = bool(youth_kit_paid) if is_youth else False

        if is_youth and monthly_paid_flag and (monthly_fee is None or monthly_fee <= 0):
            raise ValueError("Indique um valor para a mensalidade antes de a marcar como paga.")
        if is_youth and kit_paid_flag and (kit_fee is None or kit_fee <= 0):
            raise ValueError("Indique um valor para o kit de treino antes de o marcar como pago.")

        payload = storage.serialize_entity(
            models.Player(
                id=0,
                name=name,
                position=position,
                squad=squad,
                birthdate=birthdate,
                contact=contact,
                shirt_number=shirt_number,
                af_porto_id=af_porto_id,
                photo_url=photo_url or None,
                season_id=self.active_season_id,
                youth_monthly_fee=monthly_fee,
                youth_monthly_paid=monthly_paid_flag,
                youth_kit_fee=kit_fee,
                youth_kit_paid=kit_paid_flag,
            )
        )
        stored = self._create_entity("players", payload)
        updates: Dict[str, Any] = {}
        if is_youth:
            revenue_id = self._sync_youth_revenue(
                player_id=stored["id"],
                player_name=name,
                squad=squad,
                amount=monthly_fee,
                paid=monthly_paid_flag,
                existing_revenue_id=None,
                description_label=YOUTH_MONTHLY_SOURCE,
                source_label=YOUTH_MONTHLY_SOURCE,
            )
            if revenue_id is not None:
                updates["youth_monthly_revenue_id"] = revenue_id
            kit_revenue_id = self._sync_youth_revenue(
                player_id=stored["id"],
                player_name=name,
                squad=squad,
                amount=kit_fee,
                paid=kit_paid_flag,
                existing_revenue_id=None,
                description_label=YOUTH_KIT_SOURCE,
                source_label=YOUTH_KIT_SOURCE,
            )
            if kit_revenue_id is not None:
                updates["youth_kit_revenue_id"] = kit_revenue_id
        if updates:
            stored = self._update_entity("players", stored["id"], updates)
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
        af_porto_id: object | str | None = UNSET,
        photo_url: object | str | None = UNSET,
        youth_monthly_fee: object = UNSET,
        youth_monthly_paid: object = UNSET,
        youth_kit_fee: object = UNSET,
        youth_kit_paid: object = UNSET,
    ) -> models.Player:
        record = self._find_entity("players", player_id)
        if record is None:
            raise ValueError(f"Jogador com id {player_id} não encontrado")

        current_name = record.get("name", "")
        current_squad = record.get("squad", "senior")
        final_name = name if name is not None else current_name
        final_squad = squad if squad is not None else current_squad
        final_squad = str(final_squad or "senior")

        current_monthly_fee = self._coerce_amount(record.get("youth_monthly_fee"))
        current_kit_fee = self._coerce_amount(record.get("youth_kit_fee"))
        final_monthly_fee = current_monthly_fee
        final_kit_fee = current_kit_fee
        if youth_monthly_fee is not UNSET:
            final_monthly_fee = self._coerce_amount(youth_monthly_fee)
        if youth_kit_fee is not UNSET:
            final_kit_fee = self._coerce_amount(youth_kit_fee)

        current_monthly_paid = bool(record.get("youth_monthly_paid", False))
        current_kit_paid = bool(record.get("youth_kit_paid", False))
        final_monthly_paid = current_monthly_paid
        final_kit_paid = current_kit_paid
        if youth_monthly_paid is not UNSET:
            final_monthly_paid = bool(youth_monthly_paid)
        if youth_kit_paid is not UNSET:
            final_kit_paid = bool(youth_kit_paid)

        is_youth = self._is_youth_squad(final_squad)
        if not is_youth:
            final_monthly_fee = None
            final_monthly_paid = False
            final_kit_fee = None
            final_kit_paid = False

        if is_youth and final_monthly_paid and (final_monthly_fee is None or final_monthly_fee <= 0):
            raise ValueError("Indique um valor para a mensalidade antes de a marcar como paga.")
        if is_youth and final_kit_paid and (final_kit_fee is None or final_kit_fee <= 0):
            raise ValueError("Indique um valor para o kit de treino antes de o marcar como pago.")

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
        if af_porto_id is not UNSET:
            updates["af_porto_id"] = af_porto_id or None
        if photo_url is not UNSET:
            updates["photo_url"] = photo_url or None
        updates["youth_monthly_fee"] = final_monthly_fee
        updates["youth_monthly_paid"] = final_monthly_paid
        updates["youth_kit_fee"] = final_kit_fee
        updates["youth_kit_paid"] = final_kit_paid

        current_monthly_revenue_id = self._coerce_int(record.get("youth_monthly_revenue_id"))
        current_kit_revenue_id = self._coerce_int(record.get("youth_kit_revenue_id"))

        new_monthly_revenue_id = self._sync_youth_revenue(
            player_id=player_id,
            player_name=final_name,
            squad=final_squad,
            amount=final_monthly_fee,
            paid=final_monthly_paid,
            existing_revenue_id=current_monthly_revenue_id,
            description_label=YOUTH_MONTHLY_SOURCE,
            source_label=YOUTH_MONTHLY_SOURCE,
        )
        updates["youth_monthly_revenue_id"] = new_monthly_revenue_id

        new_kit_revenue_id = self._sync_youth_revenue(
            player_id=player_id,
            player_name=final_name,
            squad=final_squad,
            amount=final_kit_fee,
            paid=final_kit_paid,
            existing_revenue_id=current_kit_revenue_id,
            description_label=YOUTH_KIT_SOURCE,
            source_label=YOUTH_KIT_SOURCE,
        )
        updates["youth_kit_revenue_id"] = new_kit_revenue_id

        record = self._update_entity("players", player_id, updates)
        return storage.instantiate(models.Player, record)

    def remove_player(self, player_id: int) -> None:
        record = self._find_entity("players", player_id)
        if record is None:
            raise ValueError(f"Jogador com id {player_id} não encontrado")
        for key in ("youth_monthly_revenue_id", "youth_kit_revenue_id"):
            revenue_id = self._coerce_int(record.get(key))
            if revenue_id is None:
                continue
            try:
                self.remove_revenue(revenue_id)
            except ValueError:
                pass
        plans = self._data.setdefault("match_plans", [])
        for plan in plans:
            starters = [
                pid
                for pid in plan.get("starters", [])
                if self._coerce_int(pid) != player_id
            ]
            substitutes = [
                pid
                for pid in plan.get("substitutes", [])
                if self._coerce_int(pid) != player_id
            ]
            plan["starters"] = starters
            plan["substitutes"] = substitutes
        treatments = self._data.setdefault("treatments", [])
        removed = [
            idx
            for idx, treatment in enumerate(list(treatments))
            if self._coerce_int(treatment.get("player_id")) == player_id
        ]
        if removed:
            treatments[:] = [treatment for treatment in treatments if self._coerce_int(treatment.get("player_id")) != player_id]
            self._persist()
        self._remove_entity("players", player_id)

    # Coaches ---------------------------------------------------------
    def add_coach(
        self,
        name: str,
        role: str,
        license_level: Optional[str] = None,
        birthdate: Optional[date] = None,
        contact: Optional[str] = None,
        photo_url: Optional[str] = None,
    ) -> models.Coach:
        payload = storage.serialize_entity(
            models.Coach(
                id=0,
                name=name,
                role=role,
                license_level=license_level,
                birthdate=birthdate,
                contact=contact,
                photo_url=photo_url or None,
                season_id=self.active_season_id,
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
        photo_url: object | str | None = UNSET,
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
        if photo_url is not UNSET:
            updates["photo_url"] = photo_url or None
        record = self._update_entity("coaches", coach_id, updates)
        return storage.instantiate(models.Coach, record)

    def remove_coach(self, coach_id: int) -> None:
        self._remove_entity("coaches", coach_id)

    # Match planning --------------------------------------------------
    def list_match_plans(self) -> List[models.MatchPlan]:
        plans = [
            storage.instantiate(models.MatchPlan, item)
            for item in self._list_entities("match_plans")
        ]
        return sorted(
            plans,
            key=lambda plan: (plan.match_date, plan.kickoff_time or "", plan.id),
        )

    def get_match_plan(self, plan_id: int) -> models.MatchPlan:
        record = self._find_entity("match_plans", plan_id)
        if record is None:
            raise ValueError(f"Plano de jogo com id {plan_id} não encontrado")
        return storage.instantiate(models.MatchPlan, record)

    def create_match_plan(
        self,
        *,
        squad: str,
        match_date: date,
        kickoff_time: Optional[str],
        venue: Optional[str],
        opponent: str,
        competition: Optional[str],
        notes: Optional[str],
        starters: Iterable[Any],
        substitutes: Iterable[Any],
    ) -> models.MatchPlan:
        clean_squad = squad.strip() if isinstance(squad, str) else str(squad)
        if not clean_squad:
            clean_squad = "senior"
        starter_ids = self._normalize_player_selection(starters)
        substitute_ids = self._normalize_player_selection(substitutes, exclude=starter_ids)
        kickoff_clean = kickoff_time.strip() if isinstance(kickoff_time, str) and kickoff_time.strip() else None
        venue_clean = venue.strip() if isinstance(venue, str) and venue.strip() else None
        opponent_clean = opponent.strip() if isinstance(opponent, str) else str(opponent)
        competition_clean = (
            competition.strip() if isinstance(competition, str) and competition.strip() else None
        )
        notes_clean = notes.strip() if isinstance(notes, str) and notes.strip() else None
        if kickoff_clean is None:
            raise ValueError("Indique uma hora válida para o jogo.")
        if venue_clean is None:
            raise ValueError("Indique um local válido para o jogo.")
        if not opponent_clean:
            raise ValueError("Indique um adversário válido para o plano de jogo.")

        payload = storage.serialize_entity(
            models.MatchPlan(
                id=0,
                squad=clean_squad,
                match_date=match_date,
                kickoff_time=kickoff_clean,
                venue=venue_clean,
                opponent=opponent_clean,
                competition=competition_clean,
                notes=notes_clean,
                starters=starter_ids,
                substitutes=substitute_ids,
                season_id=self.active_season_id,
            )
        )
        stored = self._create_entity("match_plans", payload)
        return storage.instantiate(models.MatchPlan, stored)

    def update_match_plan(
        self,
        plan_id: int,
        *,
        squad: Optional[str] = None,
        match_date: Optional[date] = None,
        kickoff_time: object = UNSET,
        venue: object = UNSET,
        opponent: Optional[str] = None,
        competition: object = UNSET,
        notes: object = UNSET,
        starters: Optional[Iterable[Any]] = None,
        substitutes: Optional[Iterable[Any]] = None,
    ) -> models.MatchPlan:
        record = self._find_entity("match_plans", plan_id)
        if record is None:
            raise ValueError(f"Plano de jogo com id {plan_id} não encontrado")

        updates: Dict[str, Any] = {}
        if squad is not None:
            clean_squad = squad.strip() if isinstance(squad, str) else str(squad)
            updates["squad"] = clean_squad or "senior"
        if match_date is not None:
            updates["match_date"] = match_date.isoformat()
        if kickoff_time is not UNSET:
            kickoff_clean = kickoff_time.strip() if isinstance(kickoff_time, str) and kickoff_time.strip() else None
            if kickoff_clean is None:
                raise ValueError("Indique uma hora válida para o jogo.")
            updates["kickoff_time"] = kickoff_clean
        if venue is not UNSET:
            venue_clean = venue.strip() if isinstance(venue, str) and venue.strip() else None
            if venue_clean is None:
                raise ValueError("Indique um local válido para o jogo.")
            updates["venue"] = venue_clean
        if opponent is not None:
            opponent_clean = opponent.strip() if isinstance(opponent, str) else str(opponent)
            if not opponent_clean:
                raise ValueError("Indique um adversário válido para o plano de jogo.")
            updates["opponent"] = opponent_clean
        if competition is not UNSET:
            updates["competition"] = competition.strip() if competition else None
        if notes is not UNSET:
            updates["notes"] = notes.strip() if notes else None
        if starters is not None:
            starter_ids = self._normalize_player_selection(starters)
            updates["starters"] = starter_ids
            if substitutes is None:
                current_substitutes = record.get("substitutes", [])
                substitutes = current_substitutes
        if substitutes is not None:
            exclude = updates.get("starters")
            if exclude is None:
                exclude = [self._coerce_int(pid) for pid in record.get("starters", [])]
            exclude_ids = [pid for pid in exclude if pid is not None]
            substitute_ids = self._normalize_player_selection(substitutes, exclude=exclude_ids)
            updates["substitutes"] = substitute_ids

        updated = self._update_entity("match_plans", plan_id, updates)
        return storage.instantiate(models.MatchPlan, updated)

    def remove_match_plan(self, plan_id: int) -> None:
        self._remove_entity("match_plans", plan_id)

    # Physiotherapists ------------------------------------------------
    def add_physiotherapist(
        self,
        name: str,
        specialization: Optional[str] = None,
        birthdate: Optional[date] = None,
        contact: Optional[str] = None,
        photo_url: Optional[str] = None,
    ) -> models.Physiotherapist:
        payload = storage.serialize_entity(
            models.Physiotherapist(
                id=0,
                name=name,
                specialization=specialization,
                birthdate=birthdate,
                contact=contact,
                photo_url=photo_url or None,
                season_id=self.active_season_id,
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
        photo_url: object | str | None = UNSET,
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
        if photo_url is not UNSET:
            updates["photo_url"] = photo_url or None
        record = self._update_entity("physiotherapists", physio_id, updates)
        return storage.instantiate(models.Physiotherapist, record)

    def remove_physiotherapist(self, physio_id: int) -> None:
        self._remove_entity("physiotherapists", physio_id)
        treatments = self._data.setdefault("treatments", [])
        changed = False
        for treatment in treatments:
            if self._coerce_int(treatment.get("physio_id")) == physio_id:
                treatment["physio_id"] = None
                changed = True
        if changed:
            self._persist()

    # Treatments -----------------------------------------------------
    def add_treatment(
        self,
        *,
        player_id: int,
        physio_id: Optional[int],
        diagnosis: str,
        treatment_plan: str,
        start_date: date,
        expected_return: Optional[date] = None,
        unavailable: bool = True,
        notes: Optional[str] = None,
    ) -> models.Treatment:
        if self._find_entity("players", player_id) is None:
            raise ValueError("Jogador selecionado para tratamento não existe.")
        if physio_id is not None and self._find_entity("physiotherapists", physio_id) is None:
            raise ValueError("Fisioterapeuta selecionado não existe.")
        if not diagnosis.strip():
            raise ValueError("Descreva o problema clínico do jogador.")
        if not treatment_plan.strip():
            raise ValueError("Indique o tratamento em curso.")

        if start_date is None:
            raise ValueError("Indique a data de início do tratamento.")

        payload = storage.serialize_entity(
            models.Treatment(
                id=0,
                player_id=player_id,
                physio_id=physio_id,
                diagnosis=diagnosis.strip(),
                treatment_plan=treatment_plan.strip(),
                start_date=start_date,
                expected_return=expected_return,
                unavailable=bool(unavailable),
                notes=notes.strip() if notes else None,
                season_id=self.active_season_id,
            )
        )
        stored = self._create_entity("treatments", payload)
        return storage.instantiate(models.Treatment, stored)

    def list_treatments(self) -> List[models.Treatment]:
        treatments = [
            storage.instantiate(models.Treatment, item) for item in self._list_entities("treatments")
        ]
        return sorted(treatments, key=lambda entry: (entry.start_date, entry.id), reverse=True)

    def update_treatment(
        self,
        treatment_id: int,
        *,
        physio_id: object = UNSET,
        diagnosis: Optional[str] = None,
        treatment_plan: Optional[str] = None,
        start_date: Optional[date] = None,
        expected_return: object = UNSET,
        unavailable: Optional[bool] = None,
        notes: object = UNSET,
    ) -> models.Treatment:
        record = self._find_entity("treatments", treatment_id)
        if record is None:
            raise ValueError("Tratamento não encontrado.")
        updates: Dict[str, Any] = {}
        if physio_id is not UNSET:
            physio_value = self._coerce_int(physio_id)
            if physio_value is not None and physio_value != 0 and self._find_entity("physiotherapists", physio_value) is None:
                raise ValueError("Fisioterapeuta selecionado não existe.")
            updates["physio_id"] = physio_value or None
        if diagnosis is not None:
            if not diagnosis.strip():
                raise ValueError("A descrição clínica não pode ficar vazia.")
            updates["diagnosis"] = diagnosis.strip()
        if treatment_plan is not None:
            if not treatment_plan.strip():
                raise ValueError("O plano de tratamento não pode ficar vazio.")
            updates["treatment_plan"] = treatment_plan.strip()
        if start_date is not None:
            updates["start_date"] = start_date.isoformat()
        if expected_return is not UNSET:
            if expected_return:
                if not isinstance(expected_return, date):
                    raise ValueError("Data de regresso prevista inválida.")
                updates["expected_return"] = expected_return.isoformat()
            else:
                updates["expected_return"] = None
        if unavailable is not None:
            updates["unavailable"] = bool(unavailable)
        if notes is not UNSET:
            updates["notes"] = notes.strip() if isinstance(notes, str) and notes.strip() else None
        record = self._update_entity("treatments", treatment_id, updates)
        return storage.instantiate(models.Treatment, record)

    def remove_treatment(self, treatment_id: int) -> None:
        self._remove_entity("treatments", treatment_id)

    def list_active_treatments(self) -> List[models.Treatment]:
        return [treatment for treatment in self.list_treatments() if treatment.unavailable]

    def treatments_by_player(self, *, active_only: bool = False) -> Dict[int, List[models.Treatment]]:
        mapping: Dict[int, List[models.Treatment]] = defaultdict(list)
        for treatment in self.list_treatments():
            if active_only and not treatment.unavailable:
                continue
            mapping[treatment.player_id].append(treatment)
        for treatments in mapping.values():
            treatments.sort(key=lambda entry: (entry.start_date, entry.id), reverse=True)
        return mapping

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
            season_id=self.active_season_id,
        ).to_dict()
        stored = self._create_entity("youth_teams", payload)
        return storage.instantiate(models.YouthTeam, stored)

    def assign_player_to_team(self, team_id: int, player_id: int) -> models.YouthTeam:
        for team in self._data.setdefault("youth_teams", []):
            if int(team.get("id")) == team_id:
                team_season = team.get("season_id")
                if team_season is not None and int(team_season) != self.active_season_id:
                    raise ValueError("Apenas é possível gerir equipas da época ativa.")
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
                season_id=self.active_season_id,
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
        photo_url: Optional[str] = None,
        membership_since: Optional[date] = None,
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
                photo_url=photo_url or None,
                membership_since=membership_since,
                season_id=self.active_season_id,
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
        photo_url: object | str | None = UNSET,
        membership_since: object | date | None = UNSET,
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
        if photo_url is not UNSET:
            updates["photo_url"] = photo_url or None
        if membership_since is not UNSET:
            updates["membership_since"] = membership_since.isoformat() if membership_since else None
        record = self._update_entity("members", member_id, updates)
        return storage.instantiate(models.Member, record)

    def remove_member(self, member_id: int) -> None:
        payments = self._data.setdefault("membership_payments", [])
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
        member_season = member_record.get("season_id")
        if member_season is not None and int(member_season) != self.active_season_id:
            raise ValueError("Só é possível registar pagamentos para sócios da época ativa.")
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
                season_id=self.active_season_id,
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
        if not member_record.get("membership_since"):
            updates["membership_since"] = paid_on.isoformat()
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

        payments = self._data.setdefault("membership_payments", [])
        self._data["membership_payments"] = [
            item for item in payments if int(item.get("id", 0)) != payment_id
        ]
        self._persist()

        if member_id:
            member_record = self._find_entity("members", member_id)
            member_season = None
            if member_record is not None:
                member_season = member_record.get("season_id")
            remaining_payments = [
                storage.instantiate(models.MembershipPayment, item)
                for item in self._data["membership_payments"]
                if int(item.get("member_id", 0)) == member_id
                and (
                    member_season is None
                    or int(item.get("season_id", 0) or 0) == int(member_season)
                )
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
                season_id=self.active_season_id,
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
                season_id=self.active_season_id,
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
        self._ensure_season_setup()


def format_person(person: models.Person) -> str:
    birthdate = person.birthdate.isoformat() if person.birthdate else "-"
    return f"[{person.id}] {person.name} | {birthdate} | {person.contact or '-'}"


def format_financial(record: models.FinancialRecord) -> str:
    date_str = record.record_date.isoformat()
    return f"[{record.id}] {record.description} | {date_str} | {record.category} | €{record.amount:.2f}"
