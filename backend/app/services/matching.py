"""Module E: caregiver eligibility filtering + explainable weighted ranking."""
from __future__ import annotations

import math
from datetime import date as Date
from datetime import datetime, timedelta
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from ..config import ROLE_BY_CARE_TYPE, Settings, get_settings
from ..db.repository import Caregiver, CaregiverRepository
from ..schemas.external import Location
from ..schemas.internal import Candidate

TIER_SCORE = {"": 0.5, "base": 0.25, "standard": 0.5, "advanced": 0.75, "expert": 1.0}
SLOT_STEP_MIN = 60

LANG_NAMES_HI = {"Hindi": "हिंदी", "English": "अंग्रेज़ी"}
PHRASES = {
    "en": {
        "lang": lambda l: f"{l}-speaking",
        "dist": lambda d: f"{d:.1f} km away",
        "avail": lambda a, b: f"free {a}–{b}",
        "rating": lambda r: f"rated {r:.1f}/5",
        "skill": lambda s: f"skilled in {s}",
    },
    "hi": {
        "lang": lambda l: f"{LANG_NAMES_HI.get(l, l)} बोलते हैं",
        "dist": lambda d: f"{d:.1f} किमी दूर",
        "avail": lambda a, b: f"{a}–{b} उपलब्ध",
        "rating": lambda r: f"रेटिंग {r:.1f}/5",
        "skill": lambda s: f"{s} में दक्ष",
    },
    "hinglish": {
        "lang": lambda l: f"{l} bolte hain",
        "dist": lambda d: f"{d:.1f} km door",
        "avail": lambda a, b: f"{a}–{b} free",
        "rating": lambda r: f"rating {r:.1f}/5",
        "skill": lambda s: f"{s} mein skilled",
    },
}


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


class Matcher:
    def __init__(
        self,
        repo: CaregiverRepository,
        settings: Optional[Settings] = None,
        now_fn: Optional[Callable[[], datetime]] = None,
    ):
        self.repo = repo
        self.settings = settings or get_settings()
        self._tz = ZoneInfo(self.settings.timezone)
        self._now = now_fn or (lambda: datetime.now(self._tz))

    def now(self) -> datetime:
        n = self._now()
        return n if n.tzinfo else n.replace(tzinfo=self._tz)

    # ---- availability / slots -------------------------------------------
    def slots_for(self, cg: Caregiver, on: Date) -> list[str]:
        start, end = _minutes(cg.free_from), _minutes(cg.free_until)
        now = self.now()
        if on < now.date():
            return []
        if on == now.date():
            cur = now.hour * 60 + now.minute
            first = max(start, ((cur + SLOT_STEP_MIN - 1) // SLOT_STEP_MIN) * SLOT_STEP_MIN)
        else:
            first = start
        slots = []
        t = first
        while t + SLOT_STEP_MIN <= end:
            slots.append(_hhmm(t))
            t += SLOT_STEP_MIN
        return [s for s in slots if not self.repo.is_booked(cg.caregiver_id, on.isoformat(), s)]

    def _availability(self, cg: Caregiver, urgency: str) -> Optional[int]:
        """Minutes until the caregiver is free (0 = free now), or None if they cannot serve this urgency.

        same_day: must still have at least one slot left today.
        scheduled: any caregiver with a working window qualifies (a later slot or tomorrow is fine).
        """
        now = self.now()
        cur = now.hour * 60 + now.minute
        start, end = _minutes(cg.free_from), _minutes(cg.free_until)
        if end - start < SLOT_STEP_MIN:
            return None
        if urgency == "scheduled":
            return 0 if start <= cur <= end - SLOT_STEP_MIN else max(0, start - cur) if cur < start else 24 * 60 - cur + start
        if cur > end - SLOT_STEP_MIN:  # today's window is over
            return None
        return max(0, start - cur)

    # ---- eligibility (HARD constraints) ---------------------------------
    def _eligible(
        self,
        cg: Caregiver,
        care_type: str,
        urgency: str,
        required: list[set[str]],
        loc: Optional[Location],
    ) -> Optional[tuple[Optional[float], int]]:
        """Return (distance_km or None, minutes_until_free) when eligible, else None."""
        if not cg.active or cg.role != ROLE_BY_CARE_TYPE.get(care_type):
            return None
        if any(not (group & cg.skills) for group in required):
            return None
        wait = self._availability(cg, urgency)
        if wait is None:
            return None
        on = self.now().date() + timedelta(days=1 if urgency == "scheduled" else 0)
        if not self.slots_for(cg, on):
            return None
        dist: Optional[float] = None
        if care_type != "teleconsultation" and loc is not None:
            dist = haversine_km(loc.lat, loc.lng, cg.lat, cg.lng)
            if dist > cg.max_radius_km:
                return None
        return dist, wait

    # ---- ranking (SOFT score) -------------------------------------------
    def score_components(self, cg: Caregiver, dist: Optional[float], language: str, hint_skills: set[str]) -> tuple[dict, dict, str]:
        """Organiser-compatible blend: language .35, proximity .30, skill .20, rating .15.
        Proximity is dropped (and weights renormalised) for teleconsultation / unknown location."""
        w = self.settings.weights
        lang_score, lang_name = self._language(cg, language)
        coverage = (len(hint_skills & cg.skills) / len(hint_skills)) if hint_skills else 1.0
        tier = TIER_SCORE.get(cg.tier, 0.5) if cg.role == "medic" else 1.0
        comps = {
            "language": lang_score,
            "skill": round(0.85 * coverage + 0.15 * tier, 4),
            "rating": max(0.0, min(1.0, cg.rating / 5.0)),
        }
        weights = {k: w[k] for k in comps}
        if dist is not None:
            comps["proximity"] = round(max(0.0, 1.0 - dist / max(cg.max_radius_km, 0.1)), 4)
            weights["proximity"] = w["proximity"]
        return comps, weights, lang_name

    def match(
        self,
        care_type: str,
        urgency: str,
        required: list[set[str]],
        hint_skills: set[str],
        language: str,
        loc: Optional[Location],
    ) -> list[Candidate]:
        out: list[tuple[Candidate, int]] = []
        for cg in self.repo.all():
            ok = self._eligible(cg, care_type, urgency, required, loc)
            if ok is None:
                continue
            dist, wait = ok
            comps, weights, lang_name = self.score_components(cg, dist, language, hint_skills)
            total_w = sum(weights.values())
            score = sum(comps[k] * weights[k] for k in comps) / total_w
            comps = {**comps, "wait_min": wait, "distance_km": round(dist, 2) if dist is not None else None}
            out.append(
                (Candidate(cg.caregiver_id, round(score, 4), self._reason(cg, comps, weights, dist, lang_name, language, hint_skills, wait), comps), wait)
            )
        # Ties broken by who is free sooner, then id (deterministic).
        out.sort(key=lambda cw: (-cw[0].score, cw[1], cw[0].caregiver_id))
        return [c for c, _ in out[: self.settings.top_k]]

    @staticmethod
    def _language(cg: Caregiver, language: str) -> tuple[float, str]:
        langs = set(cg.languages)
        if language == "en":
            return (1.0, "English") if "English" in langs else (0.0, cg.languages[0] if cg.languages else "")
        if "Hindi" in langs:
            return 1.0, "Hindi"
        if language == "hinglish" and "English" in langs:
            return 0.5, "English"
        return 0.0, cg.languages[0] if cg.languages else ""

    def _reason(self, cg, comps, weights, dist, lang_name, language, hint_skills, wait) -> str:
        """Plain-words reason built ONLY from real profile fields: top weighted factors + availability."""
        ph = PHRASES[language]
        parts = {
            "language": ph["lang"](lang_name) if lang_name and comps.get("language", 0) > 0 else "",
            "proximity": ph["dist"](dist) if dist is not None else "",
            "rating": ph["rating"](cg.rating),
            "skill": ph["skill"](", ".join(sorted(s.replace("_", " ") for s in (hint_skills & cg.skills)))) if hint_skills & cg.skills else "",
        }
        ranked = sorted(weights, key=lambda k: -(comps[k] * weights[k]))
        chosen = [parts[k] for k in ranked if parts.get(k)][:2]
        chosen.append(ph["avail"](cg.free_from, cg.free_until))
        return ", ".join(chosen)
