import argparse, json
from pathlib import Path
from .db import init_db
from .guardian import run_guardian
from .graphsync import sync_graph
from .report import write_report
from .export import export_json, export_graphml
from .resolve import resolve_candidates
from .chain import verify_chain

def main():
    p = argparse.ArgumentParser(prog="census_engine", description="Census Engine v4.4 Graph Sync + Internet Guardian")
    p.add_argument("--db", default="census.sqlite")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    g = sub.add_parser("guardian")
    g.add_argument("url_file")
    g.add_argument("--run-id", default="latest")
    g.add_argument("--out", default="guardian_raw")
    g.add_argument("--depth", type=int, default=0)
    g.add_argument("--max-pages", type=int, default=25)
    g.add_argument("--delay", type=float, default=0.25)

    sg = sub.add_parser("sync-graph")
    sg.add_argument("--run", required=True)
    sg.add_argument("--raw", default=None)
    sg.add_argument("--reports", default=None)

    r = sub.add_parser("report")
    r.add_argument("--run", default=None)
    r.add_argument("--out", default="reports/evidence_report.md")

    gr = sub.add_parser("graph")
    gr.add_argument("--run", default=None)
    gr.add_argument("--format", choices=["json", "graphml"], default="json")
    gr.add_argument("--out", default=None)

    res = sub.add_parser("resolve")
    res.add_argument("--out", default="reports/entity_resolution_candidates.json")

    vc = sub.add_parser("verify-chain")
    vc.add_argument("--out", default=None)

    args = p.parse_args()

    if args.cmd == "init":
        init_db(args.db)
        print(f"initialized: {args.db}")
    elif args.cmd == "guardian":
        print(json.dumps(run_guardian(args.db, args.url_file, args.run_id, args.out, args.depth, args.max_pages, args.delay), indent=2, ensure_ascii=False))
    elif args.cmd == "sync-graph":
        print(json.dumps(sync_graph(args.db, args.run, args.raw, args.reports), indent=2, ensure_ascii=False))
    elif args.cmd == "report":
        print(write_report(args.db, args.out, args.run))
    elif args.cmd == "graph":
        out = args.out or ("reports/evidence_graph.graphml" if args.format == "graphml" else "reports/evidence_graph.json")
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        print(export_graphml(args.db, out, args.run) if args.format == "graphml" else export_json(args.db, out, args.run))
    elif args.cmd == "resolve":
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        print(resolve_candidates(args.db, args.out))
    elif args.cmd == "verify-chain":
        print(json.dumps(verify_chain(args.db, args.out), indent=2, ensure_ascii=False))
