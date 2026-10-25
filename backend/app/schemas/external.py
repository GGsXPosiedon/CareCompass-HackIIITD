"""External API schemas. Keep these aligned with the organiser contract; adapt here only."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

CareType = Literal[
    "paramedic_home_visit", "home_nursing", "lab_test_home", "teleconsultation", "emergency_112"
]
Urgency = Literal["emergency", "same_day", "scheduled"]
RedFlag = Literal[
    "chest_pain",
    "breathlessness",
    "unconsciousness",
    "severe_bleeding",
    "stroke_symptoms",
    "seizure",
    "high_fever_infant",
    "suicidal_ideation",
    "severe_dehydration",
]
LanguageMode = Literal["auto", "en", "hi", "hinglish", "english", "hindi"]


class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = ""
    kind: Optional[Literal["follow_up", "recommendation", "emergency"]] = None

    @model_validator(mode="before")
    @classmethod
    def _aliases(cls, v: Any) -> Any:
        # Accept organiser multi-turn style (text / follow_up_question) as well.
        if isinstance(v, dict) and not v.get("content"):
            alt = v.get("text") or v.get("follow_up_question") or ""
            v = {**v, "content": alt}
        return v



class TriageRequest(BaseModel):
    # Unknown keys are ignored (the organiser harness may send extras); types/ranges are enforced.
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    user_input: str = Field(min_length=1, max_length=2000)
    language: LanguageMode = "auto"
    location: Optional[Location] = None
    conversation_history: list[Turn] = Field(default_factory=list, max_length=40)


class MatchedCaregiver(BaseModel):
    caregiver_id: str
    score: float = Field(ge=0, le=1)
    reason: str


class TriageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    follow_up_question: Optional[str] = None
    care_type: Optional[CareType] = None
    urgency: Optional[Urgency] = None
    red_flags: list[RedFlag] = Field(default_factory=list)
    reasoning: str = ""
    matched_caregivers: list[MatchedCaregiver] = Field(default_factory=list)
    # Non-contract convenience for the UI; omitted from the wire when None.
    answer_options: Optional[list[str]] = None
    response_source: Optional[Literal["gemini", "rules", "safety_rules"]] = None
    service_notice: Optional[str] = None
    response_language: Optional[Literal["en", "hi", "hinglish"]] = None

    @model_validator(mode="after")
    def _invariants(self) -> "TriageResponse":
        emergency = self.care_type == "emergency_112" or self.urgency == "emergency"
        if self.red_flags and not emergency:
            raise ValueError("red flags require an emergency response")
        if emergency and self.matched_caregivers:
            raise ValueError("emergency responses must not include caregivers")
        if self.follow_up_question and (self.care_type or self.urgency or self.matched_caregivers):
            raise ValueError("a follow-up response carries no decision")
        return self

    def to_wire(self) -> dict:
        data = self.model_dump()
        if data.get("answer_options") is None:
            data.pop("answer_options", None)
        return data


class CaregiverProfile(BaseModel):
    id: str
    name: str
    initials: str
    role: str
    roleHi: str
    careType: Optional[CareType] = None
    experience: int
    distance: Optional[float] = None
    languages: list[str]
    rating: float
    skills: list[str]
    skillsHi: list[str]
    slots: list[str]
    tint: str = "sage"


class BookingRequest(BaseModel):
    caregiver_id: str
    slot: str = Field(pattern=r"^\d{2}:\d{2}$")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    location: Optional[Location] = None


class BookingResponse(BaseModel):
    id: str
