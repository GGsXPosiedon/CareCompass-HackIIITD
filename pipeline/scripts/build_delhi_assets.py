"""Build backend/app/rules/delhi.json from caregivers.csv (service areas) + a small, UNREVIEWED seasonal/emergency block.

    python scripts/build_delhi_assets.py --csv <datasets>/caregivers.csv
Areas are derived from the data (every distinct base_area with the mean coordinates and the largest service radius there); aliases are
only spelling variants a user is likely to type. Emergency numbers and seasonal notes are curated and marked unreviewed.
"""
import argparse, json
from pathlib import Path
import pandas as pd

OUT = Path(__file__).resolve().parents[2] / "backend" / "app" / "rules" / "delhi.json"
ALIASES = {"Gurugram DLF": ["gurgaon", "dlf", "cyber city"], "Gurugram Sec 29": ["gurgaon", "sector 29"], "Noida Sec 18": ["noida", "sector 18"],
           "Noida Sec 62": ["noida", "sector 62"], "Greater Noida": ["gr noida", "greater noida"], "Faridabad NIT": ["faridabad", "nit"],
           "Indirapuram": ["ghaziabad", "indrapuram"], "Karol Bagh": ["karolbagh"], "Lajpat Nagar": ["lajpatnagar"], "Mayur Vihar": ["mayurvihar"],
           "Vasant Kunj": ["vasantkunj"], "Govindpuri": ["govind puri"], "Saket": ["saket"], "Dwarka": ["dwarka"], "Rohini": ["rohini"],
           "Pitampura": ["pitampura"], "Janakpuri": ["janak puri"], "Kalkaji": ["kalka ji"]}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--csv", required=True); a = ap.parse_args()
    d = pd.read_csv(a.csv)
    areas = []
    for name, g in d.groupby("base_area"):
        areas.append({"name": name, "lat": round(float(g.base_lat.mean()), 4), "lng": round(float(g.base_lng.mean()), 4), "max_radius_km": int(g.max_radius_km.max()),
                      "caregivers": int(len(g)), "active": int(g.active.sum()), "aliases": sorted({name.lower(), *ALIASES.get(name, [])})})
    doc = {"status": "UNREVIEWED (demo)", "source": "areas derived from caregivers.csv; numbers/seasons curated",
           "emergency": {"unified": "112", "ambulance_note": "102 (patient transport) is listed for Delhi; verify before launch", "verified": False},
           "seasons": [{"months": [8, 9, 10, 11], "topic": "dengue_malaria", "note": "Mosquito-borne fever season: ask about fever days, rash, bleeding gums, severe abdominal pain."},
                       {"months": [10, 11, 12, 1], "topic": "air_pollution", "note": "Smog season: breathing complaints and asthma flares are more likely; lower threshold for breathing pathways."},
                       {"months": [4, 5, 6], "topic": "heat", "note": "Heat illness: ask about exposure, confusion, no sweating."},
                       {"months": [12, 1, 2], "topic": "winter_respiratory", "note": "Cold/flu and chest infections; elderly and children need stricter thresholds."}],
           "areas": sorted(areas, key=lambda x: x["name"])}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(areas)} areas -> {OUT}")

if __name__ == "__main__":
    main()
