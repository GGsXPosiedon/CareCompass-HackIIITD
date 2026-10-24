"""Interim taxonomy validation and the label adapter.

The adapter refuses anything that is not explicitly approved in configs/label_adapter.yaml.
"""
from __future__ import annotations

from dataclasses import dataclass

from .paths import load_yaml


class TaxonomyError(ValueError):
    """A label pair violates the taxonomy."""


class UnapprovedMappingError(TaxonomyError):
    """A mapping or source is not approved."""


class ForbiddenTransformError(TaxonomyError):
    """A diagnosis, severity or consultation label was used as a routing label."""


# Hard-coded as well as configured, so removing a line from YAML cannot silently allow one.
FORBIDDEN_TRANSFORMS: frozenset[tuple[str, str]] = frozenset(
    {
        ("synapse", "severity"),
        ("synapse", "recommendation"),
        ("ddxplus", "pathology"),
        ("ddxplus", "differential"),
        ("ddxplus", "condition_severity"),
        ("mediq", "answer"),
    }
)
ROUTING_TARGETS = frozenset({"care_type", "urgency"})


def assert_allowed_target(source: str, source_field: str, target_field: str) -> None:
    if (source, source_field) in FORBIDDEN_TRANSFORMS and target_field in ROUTING_TARGETS:
        raise ForbiddenTransformError(
            f"{source}.{source_field} must never be mapped to {target_field}"
        )


@dataclass(frozen=True)
class Taxonomy:
    version: str
    status: str
    care_types: frozenset[str]
    urgencies: frozenset[str]
    pair_rules: tuple[dict, ...]

    def validate_labels(self, care_type: str | None, urgency: str | None) -> None:
        if care_type is None and urgency is None:
            return
        if care_type is None or urgency is None:
            raise TaxonomyError("routing_conflict: exactly one of care_type/urgency is set")
        if care_type not in self.care_types:
            raise TaxonomyError(f"unknown care_type {care_type!r}")
        if urgency not in self.urgencies:
            raise TaxonomyError(f"unknown urgency {urgency!r}")
        for rule in self.pair_rules:
            if rule.get("if_care_type") == care_type and urgency != rule["require_urgency"]:
                raise TaxonomyError(f"{care_type} requires urgency {rule['require_urgency']}")
            if rule.get("if_urgency") == urgency and care_type != rule["require_care_type"]:
                raise TaxonomyError(f"urgency {urgency} requires care_type {rule['require_care_type']}")


def load_taxonomy() -> Taxonomy:
    cfg = load_yaml("taxonomy.yaml")
    return Taxonomy(
        version=cfg["version"],
        status=cfg["status"],
        care_types=frozenset(cfg["care_types"]),
        urgencies=frozenset(cfg["urgencies"]),
        pair_rules=tuple(cfg.get("pair_rules", [])),
    )


@dataclass(frozen=True)
class LabelAdapter:
    taxonomy: Taxonomy
    mapping_version: str
    approved_sources: frozenset[str]
    urgency_aliases: dict[str, dict]

    def approve(
        self, source: str, care_type: str | None, urgency: str | None
    ) -> tuple[str | None, str | None]:
        """Return CareCompass-approved labels for a source row, or raise."""
        if source not in self.approved_sources:
            raise UnapprovedMappingError(f"source {source!r} has no approved routing labels")
        self.taxonomy.validate_labels(care_type, urgency)
        return care_type, urgency

    def serialize_urgency(self, urgency: str, vocabulary: str = "csv") -> str:
        """Render an urgency in an external vocabulary; alias vocabularies must be approved."""
        if vocabulary == "csv":
            if urgency not in self.taxonomy.urgencies:
                raise TaxonomyError(f"unknown urgency {urgency!r}")
            return urgency
        if vocabulary == "problem_statement":
            alias = self.urgency_aliases.get(urgency)
            if alias is None or not alias.get("approved", False):
                raise UnapprovedMappingError(
                    f"urgency {urgency!r} has no approved problem-statement alias"
                )
            return alias["to"]
        raise UnapprovedMappingError(f"unknown vocabulary {vocabulary!r}")


def load_label_adapter() -> LabelAdapter:
    cfg = load_yaml("label_adapter.yaml")
    approved = frozenset(
        name
        for name, fields in cfg["approved_sources"].items()
        if all(f.get("approved", False) for f in fields.values())
    )
    # The YAML list is documentation; the code constant is authoritative. They must agree.
    for entry in cfg.get("forbidden_transforms", []):
        if (entry["source"], entry["field"]) not in FORBIDDEN_TRANSFORMS:
            raise TaxonomyError(f"config lists a forbidden transform missing from code: {entry}")
    return LabelAdapter(
        taxonomy=load_taxonomy(),
        mapping_version=cfg["mapping_version"],
        approved_sources=approved,
        urgency_aliases=cfg.get("problem_statement_urgency_aliases", {}),
    )
