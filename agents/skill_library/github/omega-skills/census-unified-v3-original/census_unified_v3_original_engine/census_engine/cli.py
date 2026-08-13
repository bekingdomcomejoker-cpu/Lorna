from __future__ import annotations
import argparse
from pathlib import Path

from .ledger import init_db, export_events, status_counts, DEFAULT_DB
from .history_extractor import extract
from .guardian import main as guardian_main
from .review import review
from .report import write_report

def main():
    ap = argparse.ArgumentParser(prog="census")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    p = sub.add_parser("extract")
    p.add_argument("--input", required=True)
    p.add_argument("--out", default="~/.omega/census/history_events.jsonl")

    g = sub.add_parser("guardian")
    g.add_argument("--input")
    g.add_argument("--target", action="append")
    g.add_argument("--out", default="~/.omega/census/guardian_events.jsonl")

    r = sub.add_parser("review")
    r.add_argument("--limit", type=int, default=25)
    r.add_argument("--status", default="candidate")
    r.add_argument("--ledger", default=str(DEFAULT_DB))

    sub.add_parser("status")

    e = sub.add_parser("export")
    e.add_argument("--include", action="append", default=["canon"])
    e.add_argument("--out", default="~/.omega/census/canon_export.jsonl")

    rep = sub.add_parser("report")
    rep.add_argument("--out", default="~/.omega/census/CENSUS_REPORT.md")

    args = ap.parse_args()

    if args.cmd == "init":
        init_db()
        print(f"[✓] Initialized {DEFAULT_DB}")
    elif args.cmd == "extract":
        n = extract(Path(args.input).expanduser(), Path(args.out).expanduser())
        print(f"[✓] Extracted {n} events")
    elif args.cmd == "guardian":
        # Re-run argument parser in guardian module by translating args.
        import sys
        sys.argv = ["omega_guardian_engine.py"]
        if args.input:
            sys.argv += ["--input", args.input]
        for t in args.target or []:
            sys.argv += ["--target", t]
        sys.argv += ["--out", args.out]
        guardian_main()
    elif args.cmd == "review":
        review(args.limit, args.status, Path(args.ledger).expanduser())
    elif args.cmd == "status":
        init_db()
        print(status_counts())
    elif args.cmd == "export":
        export_events(Path(args.out).expanduser(), statuses=args.include)
        print(f"[✓] Exported {args.include} to {Path(args.out).expanduser()}")
    elif args.cmd == "report":
        out = write_report(Path(args.out).expanduser())
        print(f"[✓] Wrote {out}")

if __name__ == "__main__":
    main()
