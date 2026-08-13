from __future__ import annotations
import re
from typing import Dict, List

PERSONISH = re.compile(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){1,3}\b")
URL_RE = re.compile(r"https?://[^\s\]\)<>]+")
DATE_RE = re.compile(r"\b(?:20\d{2}|19\d{2})[-/\.](?:0?[1-9]|1[0-2])[-/\.](?:0?[1-9]|[12]\d|3[01])\b")

def extract_entities(text: str) -> Dict[str, List[str]]:
    text = text or ""
    people = sorted(set(PERSONISH.findall(text)))[:25]
    urls = sorted(set(URL_RE.findall(text)))[:25]
    dates = sorted(set(DATE_RE.findall(text)))[:25]
    return {"names": people, "urls": urls, "dates": dates}
