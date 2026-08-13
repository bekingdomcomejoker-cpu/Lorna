import re, html
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

DATE_RE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{4})\b", re.I)
CASE_RE = re.compile(r"\b(?:RC|CAS|CCMA|CIPC|K)\s*[-:/]?\s*[A-Z0-9/.-]{3,}\b", re.I)
URL_RE = re.compile(r"https?://[^\s<>()\"']+")
ORG_HINT_RE = re.compile(r"\b(?:Commission|Court|Police|SAPS|Group|Holdings|Investments|Motors|Nissan|Honda|Subaru|Bank|Finance|NPO|Church|Ministry|Department|Pty|Ltd|Limited|CCMA|CIPC|SAFLII|Motus)\b", re.I)
PERSON_RE = re.compile(r"\b[A-Z][a-zA-Z'’.-]+(?:\s+\"[A-Za-z0-9'’.-]+\")?(?:\s+[A-Z][a-zA-Z'’.-]+){1,3}\b")
PLACE_HINT_RE = re.compile(r"\b(?:Pretoria|Centurion|Midrand|Roodepoort|Standerton|Gauteng|Benoni|Pinetown|Johannesburg|Durban|Cape Town|South Africa|Mpumalanga|Free State)\b", re.I)

class LinkTextParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links = []
        self.parts = []
        self.title = ""
        self._in_title = False
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip = True
        if tag == "title":
            self._in_title = True
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(urljoin(self.base_url, href))

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = False
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._skip:
            return
        data = html.unescape(data)
        if self._in_title:
            self.title += data.strip()
        if data.strip():
            self.parts.append(data.strip())

    def text(self):
        return "\n".join(self.parts)

def parse_html(raw, base_url):
    parser = LinkTextParser(base_url)
    try:
        parser.feed(raw)
    except Exception:
        pass
    return parser.title.strip(), parser.text(), clean_links(parser.links)

def clean_links(links):
    out = []
    seen = set()
    for link in links:
        p = urlparse(link)
        if p.scheme not in ("http", "https"):
            continue
        clean = p._replace(fragment="").geturl()
        if clean not in seen:
            seen.add(clean)
            out.append(clean)
    return out

def same_domain(url, root):
    return urlparse(url).netloc.lower() == urlparse(root).netloc.lower()

def dedupe(seq):
    seen = set()
    out = []
    for item in seq:
        key = tuple(str(x).lower() for x in item)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out

def extract_entities(text):
    entities = []
    for m in PERSON_RE.finditer(text):
        val = m.group(0).strip()
        if len(val) >= 5:
            entities.append(("PERSON_OR_TITLE", val))
    for m in PLACE_HINT_RE.finditer(text):
        entities.append(("PLACE", m.group(0).strip()))
    for line in text.splitlines():
        if ORG_HINT_RE.search(line):
            phrase = " ".join(line.split())
            if 3 <= len(phrase) <= 180:
                entities.append(("ORG_OR_INSTITUTION", phrase))
    for m in CASE_RE.finditer(text):
        entities.append(("CASE_REF", m.group(0).strip()))
    for m in URL_RE.finditer(text):
        entities.append(("URL", m.group(0).strip()))
    return dedupe(entities)

def extract_claims(text, max_claims=300):
    claims = []
    keywords = re.compile(r"\b(?:arrest|court|case|commission|fraud|tender|contract|vehicle|dealer|motors|police|SAPS|investigation|alleged|charged|convicted|acquired|sold|owned|director|finance|bank|CCMA|CIPC|Nissan|Honda|Subaru|Matlala|Cronje|Atlantis)\b", re.I)
    for line in text.splitlines():
        line = " ".join(line.split())
        if len(line) < 35 or len(line) > 500:
            continue
        if keywords.search(line) or DATE_RE.search(line) or CASE_RE.search(line):
            claims.append(line)
        if len(claims) >= max_claims:
            break
    return claims

def extract_events(text, max_events=150):
    events = []
    for line in text.splitlines():
        line = " ".join(line.split())
        if len(line) < 25 or len(line) > 500:
            continue
        dm = DATE_RE.search(line)
        if dm:
            events.append((dm.group(0), line))
        if len(events) >= max_events:
            break
    return events
