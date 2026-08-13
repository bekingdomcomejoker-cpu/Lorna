from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import CensusEngine


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


if __name__ == "__main__":
    main()
