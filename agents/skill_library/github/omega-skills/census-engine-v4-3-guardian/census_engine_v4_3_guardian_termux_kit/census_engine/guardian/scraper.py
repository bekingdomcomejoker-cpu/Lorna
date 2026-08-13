from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

DEFAULT_UA = "CensusEngineGuardian/4.3 (+local evidence preservation; explicit operator URLs)"

class TextAndLinkExtractor(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.text_parts: list[str] = []
        self.links: list[str] = []
        self._skip_depth = 0
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                u = urljoin(self.base_url, href)
                u, _ = urldefrag(u)
                if u.startswith(("http://", "https://")):
                    self.links.append(u)
        if tag in {"p","br","div","section","article","li","tr","h1","h2","h3","h4","h5"}:
            self.text_parts.append("\n")
    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"p","div","section","article","li","tr","h1","h2","h3","h4","h5"}:
            self.text_parts.append("\n")
    def handle_data(self, data):
        if not self._skip_depth:
            s = data.strip()
            if s:
                self.text_parts.append(s + " ")
    def text(self) -> str:
        raw = html.unescape("".join(self.text_parts))
        raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()

@dataclass
class GuardianRecord:
    source_id: str
    url: str
    final_url: str
    status: str
    http_status: int | None
    fetched_at: float
    elapsed_ms: int
    html_sha256: str
    text_sha256: str
    html_path: str
    text_path: str
    meta_path: str
    title_guess: str
    bytes: int
    text_chars: int
    discovered_links: int
    error: str = ""

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()

def safe_name(url: str, index: int) -> str:
    p = urlparse(url)
    host = re.sub(r"[^a-zA-Z0-9_.-]+", "_", p.netloc)[:80] or "source"
    path = re.sub(r"[^a-zA-Z0-9_.-]+", "_", p.path.strip("/"))[:80] or "root"
    return f"{index:04d}_{host}_{path}"

def read_url_list(path: str | Path) -> list[tuple[str,str]]:
    out=[]
    for line in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
        line=line.strip()
        if not line or line.startswith("#"): continue
        if "|" in line:
            url,label=[x.strip() for x in line.split("|",1)]
        else:
            url,label=line,line
        out.append((url,label))
    return out

def same_domain(a: str, b: str) -> bool:
    return urlparse(a).netloc.lower() == urlparse(b).netloc.lower()

def fetch_one(url: str, label: str, outdir: Path, index: int, timeout: int, user_agent: str) -> tuple[GuardianRecord, str, list[str]]:
    started=time.time(); base=safe_name(url,index)
    html_path=outdir/"html"/(base+".html")
    text_path=outdir/"text"/(base+".txt")
    meta_path=outdir/"meta"/(base+".json")
    html_path.parent.mkdir(parents=True, exist_ok=True); text_path.parent.mkdir(parents=True, exist_ok=True); meta_path.parent.mkdir(parents=True, exist_ok=True)
    req=Request(url,headers={"User-Agent":user_agent,"Accept":"text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.2"})
    try:
        with urlopen(req,timeout=timeout) as r:
            final=r.geturl(); code=getattr(r,"status",None) or 200; raw=r.read()
        # store exact bytes; decode only for extracted text
        html_path.write_bytes(raw)
        decoded=raw.decode("utf-8",errors="replace")
        parser=TextAndLinkExtractor(final)
        try: parser.feed(decoded)
        except Exception: pass
        text=parser.text() or decoded[:100000]
        text_path.write_text(text,encoding="utf-8",errors="ignore")
        title=""
        m=re.search(r"<title[^>]*>(.*?)</title>", decoded, flags=re.I|re.S)
        if m: title=re.sub(r"\s+"," ",html.unescape(m.group(1))).strip()[:240]
        rec=GuardianRecord(
            source_id=base,url=url,final_url=final,status="ok",http_status=code,fetched_at=time.time(),elapsed_ms=int((time.time()-started)*1000),
            html_sha256=sha256_bytes(raw),text_sha256=sha256_text(text),html_path=str(html_path),text_path=str(text_path),meta_path=str(meta_path),
            title_guess=title or label,bytes=len(raw),text_chars=len(text),discovered_links=len(parser.links),error="")
        meta={**asdict(rec),"label":label,"links":parser.links[:500]}
        meta_path.write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding="utf-8")
        return rec,text,parser.links
    except Exception as e:
        rec=GuardianRecord(source_id=base,url=url,final_url="",status="error",http_status=None,fetched_at=time.time(),elapsed_ms=int((time.time()-started)*1000),html_sha256="",text_sha256="",html_path=str(html_path),text_path=str(text_path),meta_path=str(meta_path),title_guess=label,bytes=0,text_chars=0,discovered_links=0,error=repr(e))
        meta_path.write_text(json.dumps({**asdict(rec),"label":label},indent=2,ensure_ascii=False),encoding="utf-8")
        return rec,"",[]

def guardian_run(urls: list[tuple[str,str]], outdir: str|Path="guardian_raw", timeout:int=20, delay:float=0.5, depth:int=0, max_pages:int=50, same_domain_only:bool=True, user_agent:str=DEFAULT_UA):
    outdir=Path(outdir); outdir.mkdir(parents=True,exist_ok=True)
    manifest_path=outdir/"guardian_manifest.jsonl"
    queue=[]; seen=set(); seed_domains={urlparse(u).netloc.lower() for u,_ in urls}
    for u,l in urls: queue.append((u,l,0,u))
    records=[]; texts=[]; i=0
    with manifest_path.open("a",encoding="utf-8") as mf:
        while queue and len(records)<max_pages:
            url,label,d,seed=queue.pop(0)
            url,_=urldefrag(url)
            if url in seen or not url.startswith(("http://","https://")): continue
            if same_domain_only and d>0 and urlparse(url).netloc.lower() not in seed_domains: continue
            seen.add(url); i+=1
            rec,text,links=fetch_one(url,label,outdir,i,timeout,user_agent)
            records.append(rec); texts.append((rec,label,text))
            mf.write(json.dumps(asdict(rec),ensure_ascii=False)+"\n"); mf.flush()
            if rec.status=="ok" and d<depth:
                for link in links:
                    if link not in seen and len(queue)+len(records)<max_pages*3:
                        if not same_domain_only or same_domain(link, seed):
                            queue.append((link, f"discovered from {url}", d+1, seed))
            if delay: time.sleep(delay)
    summary={
        "count": len(records), "ok": sum(1 for r in records if r.status=="ok"), "errors": sum(1 for r in records if r.status!="ok"),
        "outdir": str(outdir), "manifest": str(manifest_path), "depth": depth, "max_pages": max_pages
    }
    (outdir/"guardian_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    return summary, records, texts

if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("url_file")
    ap.add_argument("--out",default="guardian_raw")
    ap.add_argument("--timeout",type=int,default=20)
    ap.add_argument("--delay",type=float,default=0.5)
    ap.add_argument("--depth",type=int,default=0)
    ap.add_argument("--max-pages",type=int,default=50)
    ap.add_argument("--cross-domain",action="store_true")
    ap.add_argument("--user-agent",default=DEFAULT_UA)
    ns=ap.parse_args()
    urls=read_url_list(ns.url_file)
    summary,_,_=guardian_run(urls, ns.out, ns.timeout, ns.delay, ns.depth, ns.max_pages, not ns.cross_domain, ns.user_agent)
    print(json.dumps(summary,indent=2))
