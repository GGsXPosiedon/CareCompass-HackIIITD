"""Stage 0: read-only inventory of the raw data files.

Hashes every data file and records shape, columns and empty-value counts. Raw files are never modified.
Zip archives are listed without extraction.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

DATA_SUFFIXES = {".csv", ".tsv", ".json", ".jsonl", ".parquet", ".xlsx", ".zip"}
MAX_ZIP_RATIO = 200  # flag suspicious compression ratios (archive-bomb guard)


@dataclass
class FileRecord:
    path: str
    bytes: int
    sha256: str
    kind: str
    rows: int | None = None
    columns: list[str] | None = None
    empty_counts: dict[str, int] | None = None
    notes: list[str] = field(default_factory=list)


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def inspect_delimited(path: Path, sep: str) -> tuple[int, list[str], dict[str, int]]:
    rows = 0
    columns: list[str] = []
    empties: dict[str, int] = {}
    for chunk in pd.read_csv(
        path, sep=sep, dtype=str, keep_default_na=False, chunksize=200_000, encoding="utf-8-sig"
    ):
        if not columns:
            columns = [str(c) for c in chunk.columns]
            empties = {c: 0 for c in columns}
        rows += len(chunk)
        for col in columns:
            empties[col] += int((chunk[col] == "").sum())
    return rows, columns, empties


def inspect_jsonl(path: Path) -> tuple[int, list[str]]:
    rows = 0
    keys: dict[str, None] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rows += 1
            record = json.loads(line)
            if isinstance(record, dict):
                keys.update(dict.fromkeys(record))
    return rows, list(keys)


def inspect_json(path: Path) -> tuple[int, list[str]]:
    with open(path, encoding="utf-8") as fh:
        obj = json.load(fh)
    if isinstance(obj, dict):
        return len(obj), list(obj)[:5]
    if isinstance(obj, list):
        return len(obj), []
    return 1, []


def inspect_zip(path: Path) -> tuple[int, list[str], list[str]]:
    notes: list[str] = []
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        for info in infos:
            name = info.filename
            if name.startswith(("/", "\\")) or ".." in Path(name).parts:
                notes.append(f"unsafe member path: {name}")
            if info.compress_size and info.file_size / info.compress_size > MAX_ZIP_RATIO:
                notes.append(f"high compression ratio: {name}")
        return len(infos), [i.filename for i in infos][:20], notes


def inspect_file(path: Path, root: Path) -> FileRecord:
    suffix = path.suffix.lower()
    record = FileRecord(
        path=path.relative_to(root).as_posix(),
        bytes=path.stat().st_size,
        sha256=sha256_file(path),
        kind=suffix.lstrip("."),
    )
    try:
        if suffix in (".csv", ".tsv"):
            record.rows, record.columns, record.empty_counts = inspect_delimited(
                path, "\t" if suffix == ".tsv" else ","
            )
        elif suffix == ".jsonl":
            record.rows, record.columns = inspect_jsonl(path)
        elif suffix == ".json":
            record.rows, record.columns = inspect_json(path)
        elif suffix == ".zip":
            record.rows, record.columns, extra = inspect_zip(path)
            record.notes.extend(extra)
        else:
            record.notes.append("not inspected (format needs an optional reader)")
    except Exception as exc:  # report, do not crash the whole inventory
        record.notes.append(f"inspection failed: {type(exc).__name__}: {exc}")
    return record


def build_inventory(root: Path) -> list[FileRecord]:
    if not root.is_dir():
        raise FileNotFoundError(f"data root not found: {root}")
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in DATA_SUFFIXES)
    return [inspect_file(p, root) for p in files]


def write_manifest(records: list[FileRecord], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"files": [asdict(r) for r in records]}
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def render_report(records: list[FileRecord], root_label: str) -> str:
    lines = [
        "# 00 — Data inventory",
        "",
        f"Data root: `{root_label}`  ·  files: {len(records)}",
        "",
        "| File | Bytes | Rows | Columns | SHA-256 | Notes |",
        "|---|---:|---:|---|---|---|",
    ]
    for r in records:
        cols = ", ".join(r.columns[:8]) + (" …" if r.columns and len(r.columns) > 8 else "") if r.columns else ""
        lines.append(
            f"| `{r.path}` | {r.bytes:,} | {'' if r.rows is None else f'{r.rows:,}'} | {cols} "
            f"| `{r.sha256[:16]}…` | {'; '.join(r.notes)} |"
        )
    lines += ["", "Full hashes are in `data/manifests/source_manifest.json`.", ""]
    return "\n".join(lines)
