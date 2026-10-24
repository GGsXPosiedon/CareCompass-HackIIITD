"""Locations of configs, outputs and raw data. No data is read here."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

PIPELINE_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = PIPELINE_DIR.parent
CONFIG_DIR = PIPELINE_DIR / "configs"
REPORTS_DIR = PIPELINE_DIR / "reports"
MANIFEST_DIR = PIPELINE_DIR / "data" / "manifests"
SPLITS_DIR = PIPELINE_DIR / "data" / "splits"
PROCESSED_DIR = PIPELINE_DIR / "data" / "processed"


def load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def data_root() -> Path:
    override = os.environ.get("CC_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return (REPO_ROOT / load_yaml("paths.yaml")["data_root"]).resolve()


def data_file(key: str) -> Path:
    return data_root() / load_yaml("paths.yaml")["files"][key]
