from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import CensusEngine, DEFAULT_DATA_DIR
from .review import DEFAULT_REVIEW_STATE, export_reviewed, review_interactive, review_status


def main() -> None:
    parser = argparse.ArgumentParser(description="CENSUS civic witness engine")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("manifest", help="Print engine and data manifest")

    report_p = sub.add_parser("report", help="Generate markdown witness report")
    report_p.add_argument("--out", default="out/CENSUS_ENGINE_REPORT.md")

    list_p = sub.add_parser("list", help="List records from a bucket")
    list_p.add_argument("--bucket", default="canon_core")
    list_p.add_argument("--limit", type=int, default=10)
    list_p.add_argument("--offset", type=int, default=0)

    review_p = sub.add_parser("review", help="Human-in-the-loop terminal review")
    review_p.add_argument("--bucket", default="canon_core")
    review_p.add_argument("--limit", type=int, default=None)
    review_p.add_argument("--offset", type=int, default=0)
    review_p.add_argument("--state", default=str(DEFAULT_REVIEW_STATE))
    review_p.add_argument("--reviewer", default="local_operator")
    review_p.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))

    status_p = sub.add_parser("review-status", help="Show human review state counts")
    status_p.add_argument("--state", default=str(DEFAULT_REVIEW_STATE))
    status_p.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))

    export_p = sub.add_parser("export-reviewed", help="Export human-reviewed records")
    export_p.add_argument("--state", default=str(DEFAULT_REVIEW_STATE))
    export_p.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    export_p.add_argument("--include", default="canon", help="comma-separated decisions, e.g. canon,witness")
    export_p.add_argument("--out", default="out/human_reviewed_canon.jsonl")

    args = parser.parse_args()
    engine = CensusEngine()

    if args.command == "manifest":
        print(json.dumps(engine.manifest(), indent=2, ensure_ascii=False))
        return

    if args.command == "report":
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(engine.render_markdown_report(), encoding="utf-8")
        print(f"Wrote {out}")
        return

    if args.command == "list":
        records = engine.load_bucket(args.bucket, limit=args.limit, offset=args.offset)
        for r in records:
            print(json.dumps(r.model_dump(), ensure_ascii=False))
        return

    if args.command == "review":
        review_interactive(
            bucket=args.bucket,
            data_dir=Path(args.data_dir),
            state_path=Path(args.state),
            reviewer=args.reviewer,
            limit=args.limit,
            offset=args.offset,
        )
        return

    if args.command == "review-status":
        print(json.dumps(review_status(data_dir=Path(args.data_dir), state_path=Path(args.state)), indent=2, ensure_ascii=False))
        return

    if args.command == "export-reviewed":
        out = Path(args.out)
        count = export_reviewed(data_dir=Path(args.data_dir), state_path=Path(args.state), out_path=out, include=args.include)
        print(f"Wrote {count} records to {out}")
        return


if __name__ == "__main__":
    main()
