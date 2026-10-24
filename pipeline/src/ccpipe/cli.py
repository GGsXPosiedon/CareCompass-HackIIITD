"""Command line entry: python -m ccpipe.cli {inventory,splits}  ."""
from __future__ import annotations

import argparse
import json
import sys

from .inventory import build_inventory, render_report, write_manifest
from .paths import MANIFEST_DIR, REPORTS_DIR, data_root


def cmd_inventory(_: argparse.Namespace) -> int:
    root = data_root()
    records = build_inventory(root)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    write_manifest(records, MANIFEST_DIR / "source_manifest.json")
    (REPORTS_DIR / "00_inventory.md").write_text(render_report(records, str(root)), encoding="utf-8")
    print(f"inventoried {len(records)} files under {root}")
    return 0


def cmd_splits(args: argparse.Namespace) -> int:
    from .splits import run_splits

    summary = run_splits(skip_ddx=args.skip_ddx)
    problems = summary["carecompass"]["problems"]
    print(f"carecompass leakage problems: {problems or 'none'}")
    return 1 if problems else 0


def cmd_harmonize(_: argparse.Namespace) -> int:
    from .harmonize import run_harmonize

    summary = run_harmonize()
    print(json.dumps(summary, indent=1)[:1500])
    return 0


def cmd_extract_eval(_: argparse.Namespace) -> int:
    from .extraction.evaluate import run_extraction_eval

    res = run_extraction_eval()
    print(json.dumps(res, indent=1, ensure_ascii=False)[:2500])
    return 0


def cmd_triage_eval(args: argparse.Namespace) -> int:
    from .triage.run import run, warm_cache

    if not warm_cache(args.budget):
        print("cache incomplete; rerun the same command to continue")
        return 2
    res = run()
    print(json.dumps({k: res[k] for k in ("nested", "nested_text_only", "nested_ci", "nested_text_only_ci", "latency_ms")}, indent=1, default=str))
    return 0


def cmd_emergency(_: argparse.Namespace) -> int:
    from .triage.emergency import write_report

    print(write_report())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ccpipe")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inventory").set_defaults(func=cmd_inventory)
    sp = sub.add_parser("splits")
    sp.add_argument("--skip-ddx", action="store_true")
    sp.set_defaults(func=cmd_splits)
    sub.add_parser("harmonize").set_defaults(func=cmd_harmonize)
    sub.add_parser("extract-eval").set_defaults(func=cmd_extract_eval)
    te = sub.add_parser("triage-eval")
    te.add_argument("--budget", type=float, default=150.0, help="seconds of model fitting per invocation")
    te.set_defaults(func=cmd_triage_eval)
    sub.add_parser("emergency-threshold").set_defaults(func=cmd_emergency)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
