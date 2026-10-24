"""Print logged edge cases (backend/logs/failures.jsonl) grouped by reason. Add the real ones to eval/gold_cases.jsonl
(with a clinician-approved label) or to eval/stress.py HELD phrasings."""
import json
import sys
from collections import defaultdict
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "logs" / "failures.jsonl"
rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []
by = defaultdict(list)
for r in rows:
    for w in r["why"]:
        by[w].append(r)
for w, rs in by.items():
    print(f"\n## {w} ({len(rs)})")
    for r in rs[-25:]:
        print(f"- {r['user_input']!r} -> {r['care_type'] or r['follow_up']}")
if not rows:
    print("no failures logged yet", file=sys.stderr)
