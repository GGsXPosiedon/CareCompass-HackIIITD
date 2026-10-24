"""caregivers.csv -> Caregiver."""
from __future__ import annotations

import pandas as pd

from ..schemas import Caregiver


def _split(value: str) -> list[str]:
    return [p.strip() for p in value.split(";") if p.strip()]


def build_caregivers(df: pd.DataFrame) -> list[Caregiver]:
    out = []
    for r in df.to_dict("records"):
        out.append(Caregiver(
            caregiver_id=r["caregiver_id"], name=r["name"], role=r["role"],
            qualification=r["qualification"], gender=r["gender"],
            languages=_split(r["languages"]), skills=_split(r["skills"]),
            base_area=r["base_area"], base_lat=float(r["base_lat"]), base_lng=float(r["base_lng"]),
            max_radius_km=float(r["max_radius_km"]), tier=r["tier"] or None,
            rating=float(r["rating"]), experience_years=int(r["experience_years"]),
            free_from=r["free_from"], free_until=r["free_until"],
            active=r["active"].strip().lower() == "true",
        ))
    return out
