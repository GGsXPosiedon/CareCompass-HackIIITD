"""Frozen scenario families: the leakage-control unit for CareCompass data."""
from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml


class FamilyTableError(ValueError):
    """The family table does not cover the data exactly."""


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


@dataclass(frozen=True)
class Family:
    id: str
    care_type: str | None
    members: tuple[str, ...]
    note: str = ""


@dataclass(frozen=True)
class FamilyTable:
    version: int
    families: dict[str, Family]
    folds: dict[str, tuple[str, ...]]

    def __post_init__(self) -> None:
        index: dict[str, str] = {}
        for fam in self.families.values():
            for member in fam.members:
                key = _nfc(member)
                if key in index:
                    raise FamilyTableError(f"utterance in two families: {member!r}")
                index[key] = fam.id
        object.__setattr__(self, "_index", index)
        fold_of: dict[str, str] = {}
        for fold, ids in self.folds.items():
            for fid in ids:
                if fid in fold_of:
                    raise FamilyTableError(f"family {fid} is in two folds")
                fold_of[fid] = fold
        object.__setattr__(self, "_fold_of", fold_of)

    def family_of(self, utterance: str) -> str:
        try:
            return self._index[_nfc(utterance)]  # type: ignore[attr-defined]
        except KeyError:
            raise FamilyTableError(f"utterance not in any family: {utterance!r}") from None

    def fold_of(self, family_id: str) -> str:
        try:
            return self._fold_of[family_id]  # type: ignore[attr-defined]
        except KeyError:
            raise FamilyTableError(f"family {family_id} is not assigned to a fold") from None


def load_family_table(path: Path) -> FamilyTable:
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    families = {
        f["id"]: Family(f["id"], f.get("care_type"), tuple(f["members"]), f.get("note", ""))
        for f in raw["families"]
    }
    folds = {name: tuple(ids) for name, ids in raw["folds"].items()}
    return FamilyTable(raw["version"], families, folds)


def validate_table(table: FamilyTable, utterances: Iterable[str]) -> None:
    """Every observed utterance is in exactly one family; no stale members; every family has a fold."""
    observed = {_nfc(u) for u in utterances}
    members = set(table._index)  # type: ignore[attr-defined]
    if observed - members:
        raise FamilyTableError(f"{len(observed - members)} utterances missing from the table")
    if members - observed:
        raise FamilyTableError(f"{len(members - observed)} table members not present in the data")
    unassigned = set(table.families) - set(table._fold_of)  # type: ignore[attr-defined]
    if unassigned:
        raise FamilyTableError(f"families without a fold: {sorted(unassigned)}")
    unknown = set(table._fold_of) - set(table.families)  # type: ignore[attr-defined]
    if unknown:
        raise FamilyTableError(f"folds reference unknown families: {sorted(unknown)}")
