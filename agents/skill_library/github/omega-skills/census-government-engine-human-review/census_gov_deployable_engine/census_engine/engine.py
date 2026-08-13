from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .schema import CensusRecord, WitnessReport, GovernanceBoundary

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = Path(os.environ.get("CENSUS_DATA_DIR", PACKAGE_ROOT / "data"))

BUCKET_FILES = {
    "canon_core": "canon_core_357.redacted.jsonl",
    "source_filename_date_witness": "source_filename_date_witness_1392.redacted.jsonl",
    "date_repair_required": "date_repair_required_428.redacted.jsonl",
    "unconfirmed_review": "unconfirmed_review_26.redacted.jsonl",
}

EXPECTED_COUNTS = {
    "canon_core": 357,
    "source_filename_date_witness": 1392,
    "date_repair_required": 428,
    "private_canon_candidate": 26,
    "private_only_sensitive": 24,
    "unconfirmed_review": 15,
    "noise_or_log_review": 8,
    "line_evidence_missing": 7,
    "fuzzy_witness_only": 3,
}


def iter_jsonl(path: Path) -> Iterable[dict]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


class CensusEngine:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir or DEFAULT_DATA_DIR)

    def manifest(self) -> Dict[str, object]:
        files = {}
        for bucket, filename in BUCKET_FILES.items():
            path = self.data_dir / filename
            files[bucket] = {
                "filename": filename,
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
                "records": sum(1 for _ in iter_jsonl(path)) if path.exists() else 0,
            }
        return {
            "engine": "CENSUS civic witness engine",
            "version": "1.0.0-gov-handoff",
            "data_dir": str(self.data_dir),
            "expected_counts": EXPECTED_COUNTS,
            "bucket_files": files,
            "boundary": GovernanceBoundary().model_dump(),
        }

    def load_bucket(self, bucket: str, limit: int = 100, offset: int = 0) -> List[CensusRecord]:
        if bucket not in BUCKET_FILES:
            raise KeyError(f"Unknown bucket: {bucket}")
        path = self.data_dir / BUCKET_FILES[bucket]
        out = []
        for i, obj in enumerate(iter_jsonl(path)):
            if i < offset:
                continue
            out.append(CensusRecord.from_json(obj))
            if len(out) >= limit:
                break
        return out

    def build_report(self) -> WitnessReport:
        bucket_counts = Counter()
        event_type_counts = Counter()
        date_quality_counts = Counter()
        speaker_counts = Counter()
        risk_flags = Counter()

        for bucket, filename in BUCKET_FILES.items():
            path = self.data_dir / filename
            for obj in iter_jsonl(path):
                bucket_counts[bucket] += 1
                event_type_counts[obj.get("event_type_v2") or obj.get("event_type") or "unknown"] += 1
                date_quality_counts[obj.get("date_lock_strength_v5") or obj.get("event_date_provenance_v5") or "unknown"] += 1
                speaker_counts[obj.get("speaker_role_v4") or obj.get("speaker_role_guess") or "unknown"] += 1
                if obj.get("sensitive_review_v5"):
                    risk_flags["sensitive_review"] += 1
                if obj.get("speaker_review_required_v5"):
                    risk_flags["speaker_review_required"] += 1
                if not obj.get("line_evidence_ok_v5", True):
                    risk_flags["line_evidence_missing"] += 1
                if obj.get("date_review_required_v5"):
                    risk_flags["date_review_required"] += 1

        total = sum(bucket_counts.values())
        conclusion = (
            "The deployable engine is ready for civic-witness review and voluntary pilot use. "
            "It is not cleared for coercive individual prediction, secret citizen scoring, or automated adverse decisions. "
            "The strongest current working canon is the canon_core bucket; all other buckets remain labeled witness/repair queues."
        )
        return WitnessReport(
            title="CENSUS Government Handoff Witness Report",
            total_records=total,
            bucket_counts=dict(bucket_counts),
            event_type_counts=dict(event_type_counts),
            date_quality_counts=dict(date_quality_counts),
            speaker_counts=dict(speaker_counts),
            risk_flags=dict(risk_flags),
            conclusion=conclusion,
        )

    def render_markdown_report(self) -> str:
        report = self.build_report()
        lines = [
            f"# {report.title}",
            "",
            f"Total loaded records: **{report.total_records}**",
            "",
            "## Bucket Counts",
        ]
        for k, v in sorted(report.bucket_counts.items()):
            lines.append(f"- `{k}`: {v}")
        lines += ["", "## Event Type Counts"]
        for k, v in sorted(report.event_type_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"- `{k}`: {v}")
        lines += ["", "## Date Quality Counts"]
        for k, v in sorted(report.date_quality_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"- `{k}`: {v}")
        lines += ["", "## Speaker Counts"]
        for k, v in sorted(report.speaker_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"- `{k}`: {v}")
        lines += ["", "## Risk Flags"]
        if report.risk_flags:
            for k, v in sorted(report.risk_flags.items(), key=lambda kv: (-kv[1], kv[0])):
                lines.append(f"- `{k}`: {v}")
        else:
            lines.append("- none")
        lines += [
            "",
            "## Governance Boundary",
            "",
            "Allowed uses:",
        ]
        for item in report.governance_boundary.allowed_uses:
            lines.append(f"- {item}")
        lines += ["", "Prohibited uses:"]
        for item in report.governance_boundary.prohibited_uses:
            lines.append(f"- {item}")
        lines += ["", "## Conclusion", "", report.conclusion, ""]
        return "\n".join(lines)
