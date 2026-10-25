"""Service-area aliases and seasonal context from the UNREVIEWED Delhi asset."""
import json
import re
from functools import lru_cache

from ..config import RULES_DIR
from ..schemas.external import Location
from .matching import haversine_km


@lru_cache(maxsize=1)
def load():
    return json.loads((RULES_DIR / "delhi.json").read_text(encoding="utf-8"))


def resolve(text, location=None):
    areas = load()["areas"]
    if location is not None:
        nearby = sorted(areas, key=lambda a: haversine_km(location.lat, location.lng, a["lat"], a["lng"]))
        a = nearby[0]
        return a if haversine_km(location.lat, location.lng, a["lat"], a["lng"]) <= a["max_radius_km"] else None
    hits = [(len(alias), a) for a in areas for alias in a["aliases"]
            if re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text, re.I)]
    if not hits:
        return None
    longest = max(n for n, _ in hits)
    best = {a["name"]: a for n, a in hits if n == longest}
    return next(iter(best.values())) if len(best) == 1 else None


def matching_location(area):
    return Location(lat=area["lat"], lng=area["lng"]) if area else None


def seasonal_notes(step, month):
    """Emphasise existing questions only; seasons never change a disposition."""
    topics = {("fever", "bleed"): {"dengue_malaria"},
              ("cough_breathing", "danger"): {"air_pollution", "winter_respiratory"}}
    relevant = topics.get((step.pathway, step.question_id), set())
    return [s["note"] for s in load()["seasons"] if month in s["months"] and s["topic"] in relevant]
