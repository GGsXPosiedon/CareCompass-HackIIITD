# CareCompass data pipeline (Stages 0–3)

Offline, deterministic data foundation. Does not touch `backend/`.

```bash
cd pipeline
uv venv && uv pip install -e . pytest   # or: pip install pydantic pyyaml pandas pytest
export PYTHONPATH=src                   # CC_DATA_DIR=/path/to/datasets overrides configs/paths.yaml
python -m ccpipe.cli inventory          # reports/00_inventory.md, data/manifests/source_manifest.json
python -m ccpipe.cli splits             # reports/01_splits.md, data/splits/*   (--skip-ddx for speed)
python -m ccpipe.cli harmonize          # reports/03_harmonization.md, data/processed/* (git-ignored)
pytest
```

Rules enforced in code and tests: no SYNAPSE severity/recommendation, DDXPlus pathology, or MediQ answer
becomes `care_type`/`urgency`; labels use interim vocabulary `interim-csv-v0.1` (not organizer-approved);
DDXPlus decoding never emits `absent` facts; CareCompass folds are grouped by scenario family.
