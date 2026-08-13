from __future__ import annotations
import argparse, json
from pathlib import Path
from .pipeline import ingest_path, ingest_text
from .ledger import Ledger
from .connectors.public_url import PublicURLFetcher
from .exports.report import make_report
from .exports.graph import export_json, export_graphml
from .verify_chain import verify
from .resolve import candidates


def cmd_init(args):
    Ledger(args.db).close(); print(f"initialized {args.db}")

def cmd_ingest(args):
    sources, claims=ingest_path(args.db,args.path); print(json.dumps({"sources":sources,"claims":claims},indent=2))

def cmd_fetch(args):
    data=PublicURLFetcher().fetch(args.url)
    l=Ledger(args.db)
    sid,count=ingest_text(l,data['text'],args.label or args.url,args.url,'url')
    l.close(); print(json.dumps({"source_id":sid,"claims":count,"sha256":data['sha256']},indent=2))

def cmd_report(args):
    print(make_report(args.db,args.out,not args.no_redact))

def cmd_graph(args):
    if args.format=='json': print(export_json(args.db,args.out))
    else: print(export_graphml(args.db,args.out))

def cmd_verify(args): print(json.dumps(verify(args.db),indent=2,default=str))

def cmd_resolve(args): print(json.dumps(candidates(args.db,args.threshold),indent=2))

def cmd_list(args):
    l=Ledger(args.db)
    for row in l.rows(f"SELECT * FROM {args.table} LIMIT ?",(args.limit,)): print(json.dumps(row,ensure_ascii=False))
    l.close()

def main(argv=None):
    p=argparse.ArgumentParser(prog='census-engine',description='Census Engine v4.1 evidence ledger')
    p.add_argument('--db',default='census_v4_1.sqlite')
    sub=p.add_subparsers(required=True)
    s=sub.add_parser('init'); s.set_defaults(func=cmd_init)
    s=sub.add_parser('ingest'); s.add_argument('path'); s.set_defaults(func=cmd_ingest)
    s=sub.add_parser('fetch-url'); s.add_argument('url'); s.add_argument('--label'); s.set_defaults(func=cmd_fetch)
    s=sub.add_parser('report'); s.add_argument('--out',default='reports/evidence_report.md'); s.add_argument('--no-redact',action='store_true'); s.set_defaults(func=cmd_report)
    s=sub.add_parser('graph'); s.add_argument('--out',default='reports/graph.json'); s.add_argument('--format',choices=['json','graphml'],default='json'); s.set_defaults(func=cmd_graph)
    s=sub.add_parser('verify-chain'); s.set_defaults(func=cmd_verify)
    s=sub.add_parser('resolve'); s.add_argument('--threshold',type=float,default=0.84); s.set_defaults(func=cmd_resolve)
    s=sub.add_parser('list'); s.add_argument('table',choices=['sources','entities','claims','events','relations','verification_tasks','chain']); s.add_argument('--limit',type=int,default=50); s.set_defaults(func=cmd_list)
    args=p.parse_args(argv); args.func(args)
if __name__=='__main__': main()
