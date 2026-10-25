"""FastAPI app. Endpoints are served both at root (what the frontend calls today)
and under /api/v1 so the team can pick whichever the organisers' final schema needs."""
from __future__ import annotations

from datetime import date as Date
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from .config import ROLE_BY_CARE_TYPE, get_settings
from .schemas.external import BookingRequest, BookingResponse, CaregiverProfile, Location, TriageRequest, TriageResponse
from .services.matching import Matcher, haversine_km
from .services.pipeline import Pipeline

HI_ROLE = {"medic": "मेडिक", "doctor": "डॉक्टर", "phlebotomist": "फ्लेबोटॉमिस्ट"}
HI_SKILL = {
    "injection_im": "इंजेक्शन (IM)", "injection_iv": "इंजेक्शन (IV)", "wound_dressing": "घाव की ड्रेसिंग",
    "catheter_care": "कैथेटर देखभाल", "nebulization": "नेबुलाइज़ेशन", "vitals_monitoring": "वाइटल्स की निगरानी",
    "bp_sugar_check": "बीपी/शुगर जांच", "elderly_care": "बुजुर्गों की देखभाल", "post_surgical_care": "ऑपरेशन के बाद देखभाल",
    "sample_collection": "सैंपल कलेक्शन", "home_phlebotomy": "घर पर सैंपल", "teleconsultation": "टेलीकंसल्टेशन",
    "prescription": "पर्चा", "report_review": "रिपोर्ट समीक्षा",
}
TINTS = ["blue", "sage", "rose"]  # classes the frontend styles


@lru_cache
def get_pipeline() -> Pipeline:
    return Pipeline()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="CareCompass API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["GET", "POST"], allow_headers=["Content-Type"]
    )
    api = APIRouter()

    @api.post("/triage", response_model=TriageResponse, response_model_exclude_none=False)
    def triage(req: TriageRequest) -> JSONResponse:
        """Organiser contract. Response is validated by TriageResponse before it leaves the server."""
        return JSONResponse(get_pipeline().triage(req).to_wire())

    @api.post("/triage/trace")
    def triage_trace(req: TriageRequest):
        """Same decision + a plain-language trace of every graph node (for mentors/judges and debugging)."""
        return get_pipeline().trace(req)

    @api.get("/graph", response_class=PlainTextResponse)
    def graph():
        """Mermaid source of the LangGraph triage graph."""
        return get_pipeline().graph.mermaid()

    @api.get("/caregivers", response_model=list[CaregiverProfile])
    def caregivers(
        ids: str = Query(..., description="comma separated caregiver ids"),
        lat: Optional[float] = Query(None, ge=-90, le=90),
        lng: Optional[float] = Query(None, ge=-180, le=180),
        date: Optional[str] = None,
        care_type: Optional[str] = Query(None, description="care type the profiles are being shown for"),
    ):
        pipe = get_pipeline()
        if (lat is None) != (lng is None):
            raise HTTPException(422, "provide both lat and lng")
        loc = Location(lat=lat, lng=lng) if lat is not None and lng is not None else None
        try:
            on = Date.fromisoformat(date) if date else pipe.matcher.now().date()
        except ValueError:
            raise HTTPException(422, "invalid date")
        out: list[CaregiverProfile] = []
        for i, cid in enumerate(x for x in ids.split(",") if x.strip()):
            cg = pipe.repo.get(cid.strip())
            if cg is None:
                raise HTTPException(404, f"caregiver {cid} not found")
            care_types = [c for c, r in ROLE_BY_CARE_TYPE.items() if r == cg.role]
            if care_type is not None:
                if ROLE_BY_CARE_TYPE.get(care_type) != cg.role:
                    raise HTTPException(422, f"caregiver {cid} cannot serve {care_type}")
                care_types = [care_type]
            out.append(
                CaregiverProfile(
                    id=cg.caregiver_id, name=cg.name, initials="".join(w[0] for w in cg.name.split()[:2]).upper(),
                    role=cg.role.capitalize(), roleHi=HI_ROLE.get(cg.role, cg.role),
                    careType=care_types[0] if care_types else None, experience=cg.experience_years,
                    distance=round(haversine_km(loc.lat, loc.lng, cg.lat, cg.lng), 1) if loc else None,
                    languages=list(cg.languages), rating=cg.rating,
                    skills=sorted(s.replace("_", " ") for s in cg.skills),
                    skillsHi=[HI_SKILL.get(s, s) for s in sorted(cg.skills)],
                    slots=pipe.matcher.slots_for(cg, on), tint=TINTS[i % len(TINTS)],
                )
            )
        return out

    @api.post("/bookings", response_model=BookingResponse)
    def bookings(req: BookingRequest):
        pipe = get_pipeline()
        cg = pipe.repo.get(req.caregiver_id)
        if cg is None or not cg.active:
            raise HTTPException(404, "caregiver not available")
        try:
            on = Date.fromisoformat(req.date)
        except ValueError:
            raise HTTPException(422, "invalid date")
        if req.slot not in pipe.matcher.slots_for(cg, on):
            raise HTTPException(409, "slot is not available")
        booking_id = pipe.repo.book(cg.caregiver_id, req.date, req.slot)
        if booking_id is None:
            raise HTTPException(409, "slot already booked")
        return BookingResponse(id=booking_id)

    app.include_router(api)  # /triage, /caregivers, /bookings
    app.include_router(api, prefix="/api/v1")  # /api/v1/triage ...

    @app.post("/api/v1/route")
    def route(req: TriageRequest) -> JSONResponse:  # alias used in our architecture doc
        return JSONResponse(get_pipeline().triage(req).to_wire())

    @app.get("/health")
    def health():
        p = get_pipeline()
        st = p.settings
        return {"status": "ok", "classifier": p.router.name, "llm": p.llm.model if p.llm.enabled else "off",
                "ruleset": p.safety.version, "fusion_policy": p.settings.fusion_policy,
                # Diagnostics for "Gemini could not complete all checks": presence flags only, never key values.
                "llm_backend": st.llm_backend,
                "llm_keys_set": {"gemini": bool(st.gemini_api_key), "gemini2": bool(st.gemini_api_key_2), "groq": bool(st.groq_api_key), "compat": bool(st.compat_api_key)},
                "llm_chains": getattr(p.llm, "chains", None)}

    return app


app = create_app()
