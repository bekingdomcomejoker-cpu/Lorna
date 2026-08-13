from __future__ import annotations
import urllib.request, re
from urllib.parse import urlparse
from html import unescape
from ..util import sha256_bytes

class PublicURLFetcher:
    def __init__(self, user_agent="CensusEngine/4.1 lawful public-record fetcher"):
        self.user_agent=user_agent
    def fetch(self,url:str,timeout=25,max_bytes=3_000_000):
        p=urlparse(url)
        if p.scheme not in {"http","https"}: raise ValueError("Only http/https URLs")
        req=urllib.request.Request(url,headers={"User-Agent":self.user_agent})
        with urllib.request.urlopen(req,timeout=timeout) as r:
            data=r.read(max_bytes); ctype=r.headers.get("content-type","")
        text=data.decode("utf-8",errors="replace")
        if "html" in ctype.lower() or "<html" in text[:500].lower():
            text=re.sub(r"(?is)<script.*?</script>|<style.*?</style>"," ",text)
            text=re.sub(r"(?s)<[^>]+>"," ",text)
            text=unescape(re.sub(r"\s+"," ",text))
        return {"url":url,"content_type":ctype,"sha256":sha256_bytes(data),"text":text}
