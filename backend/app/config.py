"""Central configuration. Everything tunable lives here or in env vars."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
RULES_DIR = APP_DIR / "rules"

def _clean_value(raw: str) -> str:
    """Quoted values are taken as-is; unquoted ones lose a trailing ' # comment' (a pasted comment must not become part of a key)."""
    v = raw.strip()
    if v[:1] in ("'", '"') and v.count(v[0]) >= 2:
        return v[1:v.index(v[0], 1)]
    return v.split(" #", 1)[0].split("\t#", 1)[0].strip().strip("\"'")


def _load_dotenv() -> None:
    """Tiny .env loader (backend/.env). Real environment variables win. The file is git-ignored."""
    f = APP_DIR.parent / ".env"
    if not f.is_file():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), _clean_value(v))


_load_dotenv()

# --- Official contract enums (organiser README, v1 24 Oct 2026) -------------
CARE_TYPES = (
    "paramedic_home_visit",
    "home_nursing",
    "lab_test_home",
    "teleconsultation",
    "emergency_112",
)
URGENCIES = ("emergency", "same_day", "scheduled")
RED_FLAGS = (
    "chest_pain",
    "breathlessness",
    "unconsciousness",
    "severe_bleeding",
    "stroke_symptoms",
    "seizure",
    "high_fever_infant",
    "suicidal_ideation",
    "severe_dehydration",
)

# Conservative urgency defaults for deterministic fallback and older assessments.
# Validated Gemini urgency is used directly when available.
URGENCY_BY_CARE_TYPE = {
    "emergency_112": "emergency",
    "paramedic_home_visit": "same_day",
    "home_nursing": "same_day",
    "teleconsultation": "same_day",
    "lab_test_home": "scheduled",
}

# Which caregiver role serves which care type.
ROLE_BY_CARE_TYPE = {
    "paramedic_home_visit": "medic",
    "home_nursing": "medic",
    "lab_test_home": "phlebotomist",
    "teleconsultation": "doctor",
}

# Caregiver ranking weights. Same blend as the organiser's reference labels
# (language .35, proximity .30, skill .20, rating .15) so our scores are comparable;
# we add HARD constraints on top (active, right role, required skill, within service
# radius, free in the needed window) which the baseline does not enforce.
MATCH_WEIGHTS = {
    "language": 0.35,
    "proximity": 0.30,
    "skill": 0.20,
    "rating": 0.15,
}

# TODO(clinical review): confirm numbers with mentors before the demo.
EMERGENCY_NUMBER = "112"
MENTAL_HEALTH_HELPLINE = "14416"  # Tele-MANAS; verify before relying on it


@dataclass(frozen=True)
class Settings:
    # Deterministic classifier slot (your trained model plugs in here later): rules | <your model>
    router_backend: str = os.getenv("ROUTER_BACKEND", "rules")   # rules | trained (rules first, e5 head for the rest)
    encoder_path: str = os.getenv("ENCODER_PATH", os.getenv("INTENT_ENCODER_PATH", ""))  # local multilingual-e5-base folder
    # LLM layer: auto = Gemini when GEMINI_API_KEY is set, otherwise off. Values: auto | gemini | off
    llm_backend: str = os.getenv("LLM_BACKEND", "auto")
    # How the deterministic classifier and the LLM are combined (see app/graph/nodes.py::fuse)
    fusion_policy: str = os.getenv("FUSION_POLICY", "llm_first")  # llm_first | model_first | agree_or_ask
    model_trust_threshold: float = float(os.getenv("MODEL_TRUST_THRESHOLD", "0.85"))
    caregivers_path: str = os.getenv("CAREGIVERS_PATH", str(DATA_DIR / "caregivers.csv"))
    redflag_rules_path: str = os.getenv("REDFLAG_RULES_PATH", str(RULES_DIR / "redflags.json"))
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""), repr=False)
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    gemini_thinking_level: str = os.getenv("GEMINI_THINKING_LEVEL", "low")
    # Optional extra providers. Chains are comma lists of: gemini, gemini2, groq, compat (default: every configured one).
    gemini_api_key_2: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY_2", ""), repr=False)
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""), repr=False)
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    compat_api_key: str = field(default_factory=lambda: os.getenv("COMPAT_API_KEY", ""), repr=False)  # any OpenAI-compatible API
    compat_base_url: str = os.getenv("COMPAT_BASE_URL", "")
    compat_model: str = os.getenv("COMPAT_MODEL", "")
    llm_safety_chain: str = os.getenv("LLM_SAFETY_CHAIN", "")
    llm_triage_chain: str = os.getenv("LLM_TRIAGE_CHAIN", "")
    gemini_timeout_s: float = float(os.getenv("GEMINI_TIMEOUT_S", "15"))
    gemini_thinking_budget: int = int(os.getenv("GEMINI_THINKING_BUDGET", "0"))  # -1 = model default
    max_follow_ups: int = int(os.getenv("MAX_FOLLOW_UPS", "2"))
    # Ask symptom-specific questions (duration, temperature, ...) before routing a bare symptom message.
    # Set ADAPTIVE_SLOT_QUESTIONS=off to route such messages immediately (older behaviour).
    timing_question: bool = os.getenv("TIMING_QUESTION", "off").lower() in ("on", "1", "true")
    adaptive_slot_questions: bool = os.getenv("ADAPTIVE_SLOT_QUESTIONS", "on").lower() not in ("off", "0", "false")
    fallback_care_type: str = os.getenv("FALLBACK_CARE_TYPE", "paramedic_home_visit")
    top_k: int = int(os.getenv("TOP_K", "3"))
    timezone: str = os.getenv("SERVICE_TZ", "Asia/Kolkata")
    cors_origins: tuple = tuple(
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if o.strip()
    )
    weights: dict = field(default_factory=lambda: dict(MATCH_WEIGHTS))


@lru_cache
def get_settings() -> Settings:
    return Settings()
