from __future__ import annotations
import argparse
import os
from pathlib import Path
from .ledger import list_events, status_counts, update_review, DEFAULT_DB

def clear():
    print("\033[2J\033[H", end="")

def review(limit=25, status="candidate", db_path=DEFAULT_DB):
    rows = list_events(status=status, limit=limit, db_path=db_path)
    if not rows:
        print("[✓] No pending events.")
        print(status_counts(db_path))
        return
    changed = 0
    for i, ev in enumerate(rows, 1):
        clear()
        print(f"=== CENSUS HUMAN REVIEW | {status} | {i}/{len(rows)} ===")
        print(f"Record ID:     {ev.get('id')}")
        print(f"Date:          {ev.get('event_date')}")
        print(f"Type:          {ev.get('event_type')}")
        print(f"Speaker:       {ev.get('speaker')}")
        print(f"Source:        {ev.get('source_path')}:L{ev.get('line_start')}-L{ev.get('line_end')}")
        print(f"Axis:          {ev.get('mpam_axis')} | Pressure: {ev.get('pressure_score')}")
        print("-" * 72)
        print(ev.get("text") or ev.get("excerpt") or "")
        print("-" * 72)
        choice = input("[c] canon  [w] witness  [r] reject  [p] private  [s] skip  [q] save & quit\nDecision: ").strip().lower()
        if choice == "q":
            break
        mapping = {"c":"canon","w":"witness","r":"rejected","p":"private"}
        if choice in mapping:
            update_review(ev["id"], mapping[choice], db_path=db_path)
            changed += 1
    print(f"\n[✓] Review complete. Saved {changed} decisions.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--status", default="candidate")
    ap.add_argument("--ledger", default=str(DEFAULT_DB))
    args = ap.parse_args()
    review(args.limit, args.status, Path(args.ledger).expanduser())
