from __future__ import annotations
import string

AXES = {
    "A": "Anchor / identity / beginning",
    "B": "Boundary / body / place",
    "C": "Conflict / change / contact",
    "D": "Debt / duty / document",
    "E": "Evidence / event / emergence",
    "F": "Family / finance / friction",
    "G": "Government / ground / gate",
    "H": "Household / health / home",
    "I": "Identity / ingress / incident",
    "J": "Judgment / justice / jurisdiction",
    "K": "Kingdom / kinship / known actor",
    "L": "Location / law / ledger",
    "M": "Memory / money / movement",
    "N": "Network / name / node",
    "O": "Origin / obligation / office",
    "P": "Pressure / pattern / presence",
    "Q": "Question / query / qualification",
    "R": "Relationship / record / route",
    "S": "Service / signal / sensor",
    "T": "Time / testimony / transfer",
    "U": "Unknown / unresolved / upload",
    "V": "Verification / value / vector",
    "W": "Witness / work / warning",
    "X": "Cross-link / contradiction / extraction",
    "Y": "Yield / year / yes-no decision",
    "Z": "Zone / zero / closure"
}

KEYWORDS = {
    "A": ["account", "access", "anchor", "authority"],
    "B": ["birth", "body", "boundary", "bank"],
    "C": ["court", "case", "conflict", "connection"],
    "D": ["debt", "document", "drive", "download"],
    "E": ["evidence", "event", "email", "export"],
    "F": ["family", "finance", "fraud", "farm"],
    "G": ["government", "gov", "gate", "guardian"],
    "H": ["home", "house", "health", "housing"],
    "I": ["identity", "incident", "ingest", "input"],
    "J": ["justice", "judge", "jurisdiction"],
    "K": ["kingsley", "kin", "kingdom"],
    "L": ["location", "law", "ledger", "login"],
    "M": ["memory", "money", "movement", "mikrotik"],
    "N": ["network", "name", "node", "number"],
    "O": ["omega", "origin", "office"],
    "P": ["pressure", "pattern", "presence", "phone"],
    "Q": ["query", "question"],
    "R": ["relationship", "record", "route", "report"],
    "S": ["service", "sensor", "source", "security"],
    "T": ["time", "timeline", "testimony", "termux"],
    "U": ["unknown", "upload", "unresolved"],
    "V": ["verify", "verification", "value"],
    "W": ["witness", "warning", "work"],
    "X": ["cross", "contradiction", "extract"],
    "Y": ["year", "yield"],
    "Z": ["zone", "zero", "zip"]
}

def classify_axis(text: str) -> str:
    low = (text or "").lower()
    scores = {k: 0 for k in AXES}
    for axis, words in KEYWORDS.items():
        for w in words:
            if w in low:
                scores[axis] += 1
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] else "U"

def pressure_score(text: str) -> float:
    low = (text or "").lower()
    pressure_words = [
        "urgent", "risk", "threat", "court", "fraud", "crime", "missing",
        "blocked", "denied", "error", "warning", "incident", "escalate",
        "security", "access", "lock", "password", "login"
    ]
    return min(1.0, sum(1 for w in pressure_words if w in low) / 5.0)
