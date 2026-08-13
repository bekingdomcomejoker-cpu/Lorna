from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BucketName(str, Enum):
    canon_core = "canon_core"
    source_filename_date_witness = "source_filename_date_witness"
    date_repair_required = "date_repair_required"
    unconfirmed_review = "unconfirmed_review"


class GovernanceBoundary(BaseModel):
    allowed_uses: List[str] = Field(default_factory=lambda: [
        "service-delivery planning",
        "record reconciliation",
        "citizen-facing transparency reports",
        "evidence/witness packet generation",
        "oversight-reviewed voluntary pilot analysis",
    ])
    prohibited_uses: List[str] = Field(default_factory=lambda: [
        "automated denial of rights, benefits, housing, employment, credit, education, or healthcare",
        "policing/enforcement targeting without independent lawful process",
        "secret citizen scoring",
        "coercive surveillance",
        "unreviewable prediction or profiling",
        "deployment without appeal, correction, and audit routes",
    ])


class CensusRecord(BaseModel):
    text: str = ""
    event_type_v2: Optional[str] = None
    promotion_tier_v5: Optional[str] = None
    event_date_v5: Optional[str] = None
    event_date_provenance_v5: Optional[str] = None
    date_lock_strength_v5: Optional[str] = None
    source_line_citation_v5: Optional[str] = None
    speaker_role_v4: Optional[str] = None
    speaker_review_required_v5: Optional[bool] = None
    sensitive_review_v5: Optional[bool] = None
    line_evidence_ok_v5: Optional[bool] = None
    confidence: Optional[float] = None
    source_match_score: Optional[float] = None
    raw: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_json(cls, obj: Dict[str, Any]) -> "CensusRecord":
        known = {
            "text": obj.get("text", ""),
            "event_type_v2": obj.get("event_type_v2"),
            "promotion_tier_v5": obj.get("promotion_tier_v5"),
            "event_date_v5": obj.get("event_date_v5"),
            "event_date_provenance_v5": obj.get("event_date_provenance_v5"),
            "date_lock_strength_v5": obj.get("date_lock_strength_v5"),
            "source_line_citation_v5": obj.get("source_line_citation_v5"),
            "speaker_role_v4": obj.get("speaker_role_v4"),
            "speaker_review_required_v5": obj.get("speaker_review_required_v5"),
            "sensitive_review_v5": obj.get("sensitive_review_v5"),
            "line_evidence_ok_v5": obj.get("line_evidence_ok_v5"),
            "confidence": obj.get("confidence"),
            "source_match_score": obj.get("source_match_score"),
            "raw": obj,
        }
        return cls(**known)


class WitnessReport(BaseModel):
    title: str
    total_records: int
    bucket_counts: Dict[str, int]
    event_type_counts: Dict[str, int]
    date_quality_counts: Dict[str, int]
    speaker_counts: Dict[str, int]
    risk_flags: Dict[str, int]
    governance_boundary: GovernanceBoundary = Field(default_factory=GovernanceBoundary)
    conclusion: str
