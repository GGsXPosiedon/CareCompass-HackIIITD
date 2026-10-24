"""Caregiver repository (CSV-backed prototype) + in-memory bookings.

The CSV uses the same columns as the organiser roster so a real roster can be dropped in via
CAREGIVERS_PATH. The default file is the supplied roster; the synthetic seed remains a test fixture.
"""
from __future__ import annotations

import csv
import threading
from dataclasses import dataclass
from functools import lru_cache

from ..config import get_settings


@dataclass(frozen=True)
class Caregiver:
    caregiver_id: str
    name: str
    role: str
    qualification: str
    languages: tuple[str, ...]
    skills: frozenset[str]
    base_area: str
    lat: float
    lng: float
    max_radius_km: float
    tier: str
    rating: float
    experience_years: int
    free_from: str  # HH:mm
    free_until: str
    active: bool


def _row_to_caregiver(r: dict) -> Caregiver:
    return Caregiver(
        caregiver_id=r["caregiver_id"].strip(),
        name=r["name"].strip(),
        role=r["role"].strip().lower(),
        qualification=r.get("qualification", "").strip(),
        languages=tuple(x.strip() for x in r["languages"].split(";") if x.strip()),
        skills=frozenset(x.strip() for x in r["skills"].split(";") if x.strip()),
        base_area=r.get("base_area", "").strip(),
        lat=float(r["base_lat"]),
        lng=float(r["base_lng"]),
        max_radius_km=float(r["max_radius_km"]),
        tier=(r.get("tier") or "").strip().lower(),
        rating=float(r["rating"]),
        experience_years=int(float(r.get("experience_years") or 0)),
        free_from=r["free_from"].strip(),
        free_until=r["free_until"].strip(),
        active=r["active"].strip().lower() in {"true", "1", "yes"},
    )


class CaregiverRepository:
    def __init__(self, path: str):
        with open(path, newline="", encoding="utf-8-sig") as fh:
            self._items = [_row_to_caregiver(r) for r in csv.DictReader(fh)]
        self._by_id = {c.caregiver_id: c for c in self._items}
        self._bookings: dict[tuple[str, str, str], str] = {}
        self._lock = threading.Lock()

    def all(self) -> list[Caregiver]:
        return list(self._items)

    def get(self, caregiver_id: str) -> Caregiver | None:
        return self._by_id.get(caregiver_id)

    def is_booked(self, caregiver_id: str, date: str, slot: str) -> bool:
        return (caregiver_id, date, slot) in self._bookings

    def book(self, caregiver_id: str, date: str, slot: str) -> str | None:
        """Atomically reserve a slot. Returns booking id, or None if already taken."""
        key = (caregiver_id, date, slot)
        with self._lock:
            if key in self._bookings:
                return None
            booking_id = f"BK-{len(self._bookings) + 1:05d}"
            self._bookings[key] = booking_id
            return booking_id


@lru_cache
def get_repository() -> CaregiverRepository:
    return CaregiverRepository(get_settings().caregivers_path)
