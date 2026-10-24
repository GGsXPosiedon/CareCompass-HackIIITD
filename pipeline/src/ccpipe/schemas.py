"""Internal (offline) schemas for the unified patient-state format.

These are NOT the online API contract; that follows the organizers' final schema.
Invariants enforced here:
  * approved CareCompass labels exist only on CareCompass cases, and only with a real mapping version;
  * DDXPlus decoding never produces an 'absent' fact (unknown != absent);
  * every non-DDXPlus case has at least one utterance.
"""
from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Source(StrEnum):
    CARECOMPASS = "carecompass"
    DDXPLUS = "ddxplus"
    SYNAPSE = "synapse"
    MEDIQ = "mediq"
    DIALOGUE = "dialogue"


class Assertion(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"
    CONFLICTING = "conflicting"
    HYPOTHETICAL = "hypothetical"
    HISTORICAL = "historical"


class Temporality(StrEnum):
    CURRENT = "current"
    PAST = "past"
    UNSPECIFIED = "unspecified"


class Origin(StrEnum):
    EXTRACTED_RULE = "extracted_rule"
    EXTRACTED_MODEL = "extracted_model"
    DECODED_SOURCE_CODE = "decoded_source_code"
    SIMULATED_ORACLE = "simulated_oracle"


class Split(StrEnum):
    UNASSIGNED = "unassigned"
    TRAIN = "train"
    VAL = "val"
    TEST = "test"
    ADVERSARIAL = "adversarial_holdout"


class ReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    IN_REVIEW = "in_review"
    ACCEPTED = "reviewed_accepted"
    CORRECTED = "reviewed_corrected"
    REJECTED = "rejected"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LanguageInfo(_Model):
    declared: str | None = None
    detected: str | None = None
    script: Literal["latin", "devanagari", "mixed", "unknown"] = "unknown"


class Utterance(_Model):
    turn: int = Field(default=0, ge=0)
    speaker: Literal["patient", "system"] = "patient"
    text_original: str = Field(min_length=1)
    text_normalized: str | None = None


class Fact(_Model):
    concept_id: str
    assertion: Assertion
    value: bool | int | float | str | list[str] | None = None
    value_label: str | None = None
    temporality: Temporality = Temporality.UNSPECIFIED
    evidence_turn: int | None = None
    text_span: tuple[int, int] | None = None
    origin: Origin
    is_initial: bool = False
    experiencer: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class Demographics(_Model):
    age_years: int | None = Field(default=None, ge=0, le=130)
    age_bucket: str | None = None
    sex_reported: str | None = None


class Duration(_Model):
    days: int | None = None
    bucket: str | None = None


class SourceLabels(_Model):
    """Verbatim labels from the originating dataset, in that dataset's vocabulary."""

    care_type: str | None = None
    urgency: str | None = None
    red_flags_raw: str | None = None  # quarantined: known to be unreliable
    severity: str | None = None
    recommendation: str | None = None
    pathology: str | None = None


class ApprovedLabels(_Model):
    care_type: str | None = None
    urgency: str | None = None
    red_flag_ids: list[str] = Field(default_factory=list)


class RequestContext(_Model):
    """Matching only. Never a classifier feature."""

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class Review(_Model):
    clinical_review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    reviewer: str | None = None
    mapping_version: str = "pending"
    notes: str | None = None


class Provenance(_Model):
    source_row_id: str
    source_file: str
    source_version: str | None = None
    license: str | None = None
    generation_method: Literal["source", "translation", "paraphrase", "simulated"] = "source"
    derivative_from: list[str] = Field(default_factory=list)


class CanonicalCase(_Model):
    case_id: str
    source: Source
    source_split: str = "none"
    source_patient_id: str | None = None
    scenario_group_id: str
    split: Split = Split.UNASSIGNED
    fold: str | None = None
    augmentation_parent_id: str | None = None
    language: LanguageInfo = Field(default_factory=LanguageInfo)
    utterances: list[Utterance] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)
    demographics: Demographics = Field(default_factory=Demographics)
    duration: Duration = Field(default_factory=Duration)
    source_labels: SourceLabels = Field(default_factory=SourceLabels)
    approved_labels: ApprovedLabels | None = None
    request_context: RequestContext | None = None
    # Reference-only fields (never model inputs): reasoning, seed follow-up question, matches, scores.
    reference: dict[str, str] = Field(default_factory=dict)
    quality_flags: list[str] = Field(default_factory=list)
    review: Review = Field(default_factory=Review)
    provenance: Provenance

    @model_validator(mode="after")
    def _invariants(self) -> "CanonicalCase":
        if self.approved_labels is not None:
            if self.source is not Source.CARECOMPASS:
                raise ValueError("approved_labels are only allowed on CareCompass cases")
            has_label = bool(self.approved_labels.care_type or self.approved_labels.urgency)
            if has_label and self.review.mapping_version == "pending":
                raise ValueError("approved labels require a non-pending mapping_version")
        if self.source is Source.DDXPLUS:
            for fact in self.facts:
                if fact.assertion is Assertion.ABSENT:
                    raise ValueError("DDXPlus decoding must not create 'absent' facts (unknown != absent)")
        elif not self.utterances:
            raise ValueError(f"{self.source.value} cases need at least one utterance")
        return self


_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class Caregiver(_Model):
    caregiver_id: str
    name: str
    role: str
    qualification: str
    gender: str
    languages: list[str]
    skills: list[str]
    base_area: str
    base_lat: float = Field(ge=-90, le=90)
    base_lng: float = Field(ge=-180, le=180)
    max_radius_km: float = Field(gt=0)
    tier: str | None = None
    rating: float = Field(ge=0, le=5)
    experience_years: int = Field(ge=0)
    free_from: str
    free_until: str
    active: bool

    @model_validator(mode="after")
    def _window(self) -> "Caregiver":
        for value in (self.free_from, self.free_until):
            if not _HHMM.match(value):
                raise ValueError(f"time must be HH:MM, got {value!r}")
        if self.free_from >= self.free_until:
            raise ValueError("free_from must be earlier than free_until")
        return self
