from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .pipeline import ingest_path, ingest_text
from .ledger import Ledger
from .connectors.public_url import PublicURLFetcher
from .exports.report import make_report
from .exports.graph import export_json, export_graphml
from .verify_chain import verify
from .resolve import candidates
from .guardian.scraper import read_url_list, guardian_run

DEFAULT_DB = 'census_v4_2.sqlite'


def _db(args):
    return getattr(args, 'db', None) or DEFAULT_DB


def cmd_init(args):
    db = _db(args)
    Path(db).parent.mkdir(parents=True, exist_ok=True) if Path(db).parent != Path('.') else None
    Ledger(db).close()
    print(f"initialized {db}")


def cmd_ingest(args):
    sources, claims = ingest_path(_db(args), args.path)
    print(json.dumps({"sources": sources, "claims": claims}, indent=2))


def cmd_fetch(args):
    data = PublicURLFetcher().fetch(args.url)
    l = Ledger(_db(args))
    sid, count = ingest_text(l, data['text'], args.label or args.url, args.url, 'url')
    l.close()
    print(json.dumps({"source_id": sid, "claims": count, "sha256": data['sha256']}, indent=2))


def cmd_fetch_list(args):
    url_file = Path(args.url_file)
    if not url_file.exists():
        raise SystemExit(f"URL file not found: {url_file}")
    results = []
    for line in url_file.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # format: URL | optional label
        if '|' in line:
            url, label = [x.strip() for x in line.split('|', 1)]
        else:
            url, label = line, line
        try:
            data = PublicURLFetcher().fetch(url)
            l = Ledger(_db(args))
            sid, count = ingest_text(l, data['text'], label, url, 'url')
            l.close()
            results.append({"url": url, "label": label, "source_id": sid, "claims": count, "sha256": data['sha256'], "ok": True})
        except Exception as e:
            results.append({"url": url, "label": label, "ok": False, "error": str(e)})
    print(json.dumps(results, indent=2))



def cmd_guardian(args):
    urls = read_url_list(args.url_file)
    summary, records, texts = guardian_run(
        urls,
        outdir=args.out,
        timeout=args.timeout,
        delay=args.delay,
        depth=args.depth,
        max_pages=args.max_pages,
        same_domain_only=not args.cross_domain,
        user_agent=args.user_agent,
    )
    l = Ledger(_db(args))
    ingested = []
    for rec, label, text in texts:
        if rec.status != 'ok' or not text:
            continue
        sid, count = ingest_text(l, text, label or rec.url, rec.final_url or rec.url, 'guardian_url')
        # also preserve the raw source hash and guardian file paths as a source record
        l.add_task(None, 'guardian_raw_saved', rec.url, rec.meta_path)
        ingested.append({'url': rec.url, 'source_id': sid, 'claims': count, 'html_sha256': rec.html_sha256, 'text_path': rec.text_path})
    l.close()
    summary['ingested'] = ingested
    print(json.dumps(summary, indent=2, default=str))

def cmd_report(args):
    Path(args.out).parent.mkdir(parents=True, exist_ok=True) if Path(args.out).parent != Path('.') else None
    print(make_report(_db(args), args.out, not args.no_redact))


def cmd_graph(args):
    Path(args.out).parent.mkdir(parents=True, exist_ok=True) if Path(args.out).parent != Path('.') else None
    if args.format == 'json':
        print(export_json(_db(args), args.out))
    else:
        print(export_graphml(_db(args), args.out))


def cmd_verify(args):
    print(json.dumps(verify(_db(args)), indent=2, default=str))


def cmd_resolve(args):
    print(json.dumps(candidates(_db(args), args.threshold), indent=2))


def cmd_list(args):
    l = Ledger(_db(args))
    for row in l.rows(f"SELECT * FROM {args.table} LIMIT ?", (args.limit,)):
        print(json.dumps(row, ensure_ascii=False, default=str))
    l.close()


def cmd_run(args):
    db = _db(args)
    Ledger(db).close()
    summary = {"db": db, "ingested_sources": 0, "ingested_claims": 0, "fetched": [], "reports": []}
    input_path = Path(args.input)
    if input_path.exists():
        s, c = ingest_path(db, str(input_path))
        summary["ingested_sources"] += s
        summary["ingested_claims"] += c
    else:
        summary["input_warning"] = f"Input path not found: {input_path}"
    if args.urls and Path(args.urls).exists():
        # Reuse fetch-list logic but keep compact summary
        for line in Path(args.urls).read_text(encoding='utf-8', errors='ignore').splitlines():
            line=line.strip()
            if not line or line.startswith('#'): continue
            url,label=(line.split('|',1)+[None])[:2] if '|' in line else (line,line)
            url=url.strip(); label=(label or url).strip()
            try:
                data=PublicURLFetcher().fetch(url)
                l=Ledger(db); sid,count=ingest_text(l,data['text'],label,url,'url'); l.close()
                summary["fetched"].append({"url":url,"source_id":sid,"claims":count,"ok":True})
            except Exception as e:
                summary["fetched"].append({"url":url,"ok":False,"error":str(e)})
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    summary["reports"].append(make_report(db, str(outdir / 'evidence_report.md'), not args.no_redact))
    summary["reports"].append(export_json(db, str(outdir / 'evidence_graph.json')))
    summary["reports"].append(export_graphml(db, str(outdir / 'evidence_graph.graphml')))
    summary["chain"] = verify(db)
    print(json.dumps(summary, indent=2, default=str))


def main(argv=None):
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument('--db', default=DEFAULT_DB, help='SQLite ledger path')

    p = argparse.ArgumentParser(prog='census-engine', description='Census Engine v4.3 Guardian terminal evidence ledger')
    p.add_argument('--db', default=DEFAULT_DB, help='SQLite ledger path; may also be used after a subcommand')
    sub = p.add_subparsers(required=True)

    s = sub.add_parser('init', parents=[parent]); s.set_defaults(func=cmd_init)
    s = sub.add_parser('ingest', parents=[parent]); s.add_argument('path'); s.set_defaults(func=cmd_ingest)
    s = sub.add_parser('fetch-url', parents=[parent]); s.add_argument('url'); s.add_argument('--label'); s.set_defaults(func=cmd_fetch)
    s = sub.add_parser('fetch-list', parents=[parent]); s.add_argument('url_file'); s.set_defaults(func=cmd_fetch_list)
    s = sub.add_parser('guardian', parents=[parent], help='Guardian public-source scraper: fetch URL list, preserve raw HTML/text/hash manifest, ingest extracted text')
    s.add_argument('url_file')
    s.add_argument('--out', default='guardian_raw')
    s.add_argument('--timeout', type=int, default=20)
    s.add_argument('--delay', type=float, default=0.5)
    s.add_argument('--depth', type=int, default=0, help='crawl link depth from seed URLs; 0 = seeds only')
    s.add_argument('--max-pages', type=int, default=50)
    s.add_argument('--cross-domain', action='store_true', help='allow discovered links outside seed domains')
    s.add_argument('--user-agent', default='CensusEngineGuardian/4.3 (+local evidence preservation; explicit operator URLs)')
    s.set_defaults(func=cmd_guardian)
    s = sub.add_parser('report', parents=[parent]); s.add_argument('--out', default='reports/evidence_report.md'); s.add_argument('--no-redact', action='store_true'); s.set_defaults(func=cmd_report)
    s = sub.add_parser('graph', parents=[parent]); s.add_argument('--out', default='reports/graph.json'); s.add_argument('--format', choices=['json','graphml'], default='json'); s.set_defaults(func=cmd_graph)
    s = sub.add_parser('verify-chain', parents=[parent]); s.set_defaults(func=cmd_verify)
    s = sub.add_parser('resolve', parents=[parent]); s.add_argument('--threshold', type=float, default=0.84); s.set_defaults(func=cmd_resolve)
    s = sub.add_parser('list', parents=[parent]); s.add_argument('table', choices=['sources','entities','claims','events','relations','verification_tasks','chain']); s.add_argument('--limit', type=int, default=50); s.set_defaults(func=cmd_list)
    s = sub.add_parser('run', parents=[parent]); s.add_argument('--input', default='evidence_inbox'); s.add_argument('--urls', default='urls.txt'); s.add_argument('--outdir', default='reports'); s.add_argument('--no-redact', action='store_true'); s.set_defaults(func=cmd_run)

    args = p.parse_args(argv)
    args.func(args)

if __name__ == '__main__':
    main()
