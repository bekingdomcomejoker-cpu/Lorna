from __future__ import annotations
PUBLIC=["saflii","court","commission","cipc","ccma","gazette","government","judgment","tribunal"]
PRESS=["daily maverick","amabhungane","news24","sabc","enca","reuters","groundup","ama bhungane"]
PERSONAL=["my ","i ","we ","he told","she said","i saw","my mom","wife","ex wife"]
SENSITIVE=["id number","phone","address","minor","mother","wife","ex wife","child"]

def grade(text:str, source_label:str=""):
    low=(text+" "+source_label).lower()
    if any(x in low for x in SENSITIVE): return ("sensitive_witness","witness",0.35,"high","Verify from owned/legal docs; keep redacted working copy")
    if any(x in low for x in PUBLIC): return ("public_record_claim","factual",0.70,"normal","Verify against original public record PDF/page and archive locator")
    if any(x in low for x in PRESS): return ("press_report_claim","factual",0.60,"normal","Verify article, date, author, and independent second source")
    if any(x in low for x in PERSONAL): return ("personal_witness_claim","witness",0.45,"sensitive","Attach witness statement or supporting document")
    return ("unverified","factual",0.40,"normal","Needs source and independent verification")
