"""Live check of every configured LLM provider, with the real safety and triage prompts.

    uv run python -m eval.llm_check            # one call per provider per decision
    uv run python -m eval.llm_check --models   # also verify the Gemini model id exists for each key

Prints status, latency and the failure reason (e.g. "HTTP 429"). Never prints keys or response bodies.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import get_settings  # noqa: E402
from app.graph.nodes import SAFETY_PROMPT, TRIAGE_PROMPT  # noqa: E402
from app.prompts import load, render_case  # noqa: E402
from app.schemas.llm import SafetyReview, TriageAssessment  # noqa: E402
from app.services.gemini import LLMError  # noqa: E402
from app.services.llm_router import build_llm  # noqa: E402

CASE = render_case(language="hinglish", history=[], message="sar dard hora h", profile=None, follow_ups_asked=0)


def check_models(router, s) -> None:
    print("\nGemini model availability")
    for name, key in (("gemini", s.gemini_api_key), ("gemini2", s.gemini_api_key_2)):
        if not key:
            continue
        try:
            r = httpx.get("https://generativelanguage.googleapis.com/v1beta/models", params={"pageSize": 200},
                          headers={"x-goog-api-key": key}, timeout=15)
            r.raise_for_status()
            ids = {m["name"].removeprefix("models/") for m in r.json().get("models", [])}
            status = "available" if s.gemini_model in ids else f"NOT FOUND for this key (try one of: {', '.join(sorted(i for i in ids if 'flash' in i))[:300]})"
            print(f"  {name:8} {s.gemini_model}: {status}")
        except httpx.HTTPStatusError as e:
            print(f"  {name:8} model list failed: HTTP {e.response.status_code}")
        except httpx.HTTPError as e:
            print(f"  {name:8} model list failed: {type(e).__name__}")


def check_compat_models(router) -> None:
    print("\nOpenAI-compatible model availability")
    for name, c in router.providers.items():
        if not hasattr(c, "base"):
            continue
        try:
            r = httpx.get(f"{c.base}/models", headers={"Authorization": f"Bearer {c.key}"}, timeout=15)
            r.raise_for_status()
            ids = sorted(m["id"] for m in r.json().get("data", []))
            ok = c.model in ids
            print(f"  {name:8} {c.model}: {'available' if ok else 'NOT FOUND for this key'}")
            if not ok:
                print(f"           models you can use: {', '.join(ids)[:400]}")
        except httpx.HTTPStatusError as e:
            print(f"  {name:8} model list failed: HTTP {e.response.status_code}")
        except httpx.HTTPError as e:
            print(f"  {name:8} model list failed: {type(e).__name__}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", action="store_true")
    args = ap.parse_args()
    s = get_settings()
    router = build_llm(s)
    if not router.providers:
        print("No LLM provider is configured (check backend/.env keys and LLM_BACKEND).")
        return 1
    print("Providers:", ", ".join(f"{n} ({c.model})" for n, c in router.providers.items()))
    print("Chains   :", " | ".join(f"{role}: {' > '.join(chain)}" for role, chain in router.chains.items()))
    failures = 0
    for role, prompt, schema, max_tokens in (("safety", SAFETY_PROMPT, SafetyReview, 600), ("triage", TRIAGE_PROMPT, TriageAssessment, 900)):
        print(f"\n{role} decision")
        for name, client in router.providers.items():
            t0 = time.perf_counter()
            try:
                out = client.structured(load(prompt).text, CASE, schema, max_tokens)
                detail = f"care_type={out.care_type} urgency={out.urgency}" if role == "triage" else f"findings={len(out.findings)}"
                print(f"  {name:8} OK    {time.perf_counter() - t0:4.1f}s  {detail}")
            except LLMError as e:
                failures += 1
                print(f"  {name:8} FAIL  {time.perf_counter() - t0:4.1f}s  {e}")
    if args.models:
        check_models(router, s)
        check_compat_models(router)
    print("\nAll providers answered." if not failures else f"\n{failures} call(s) failed - the first provider in each chain is the one that matters; the rest are backups.")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
