import hashlib
import json
import os
import time
from datetime import datetime

class TaoTzcivEEngine:
    def __init__(self, case_id=None):
        self.case_id = case_id or f"CASE-{int(time.time())}"
        self.vault_path = f"/home/ubuntu/vault/{self.case_id}"
        os.makedirs(self.vault_path, exist_ok=True)
        self.evidence_log = []

    def vault_evidence(self, source, content, url=None):
        """Hashes, timestamps, and archives evidence."""
        timestamp = datetime.now().isoformat()
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        filename = f"{source}_{content_hash[:10]}.txt"
        filepath = os.path.join(self.vault_path, filename)
        
        with open(filepath, "w") as f:
            f.write(content)
            
        entry = {
            "source": source,
            "url": url,
            "timestamp": timestamp,
            "hash": content_hash,
            "path": filepath
        }
        self.evidence_log.append(entry)
        return entry

    def detect_anomalies(self, subject_data):
        """Programmatically flags contradictions in subject data."""
        anomalies = []
        dod = subject_data.get("dod")
        gazette_date = subject_data.get("gazette_date")
        
        if dod and gazette_date:
            d1 = datetime.strptime(dod, "%Y-%m-%d")
            d2 = datetime.strptime(gazette_date, "%Y-%m-%d")
            delta = (d2 - d1).days
            if delta > 180:
                anomalies.append(f"CRITICAL: Estate Suppression Flag - {delta} days gap between death and notice.")
        
        for event in subject_data.get("timeline", []):
            event_date = datetime.strptime(event["date"], "%Y-%m-%d")
            if dod and event_date > datetime.strptime(dod, "%Y-%m-%d"):
                anomalies.append(f"CRITICAL: Post-Mortem Activity Detected - {event['type']} on {event['date']}.")
                
        return anomalies

    def generate_brief(self, subject_data, anomalies):
        """Generates a formal intelligence brief."""
        brief = f"""# [CONFIDENTIAL] TAOTZCIVE CIVIL INTELLIGENCE BRIEF
**CASE ID**: {self.case_id}
**DATE**: {datetime.now().strftime('%Y-%m-%d')}
**SUBJECT**: {subject_data.get('name')}
**ID NUMBER**: {subject_data.get('id')}

## 1. TRIANGULATED EVIDENCE LOG
"""
        for entry in self.evidence_log:
            brief += f"- **{entry['source']}**: {entry['url']} (Hash: {entry['hash'][:8]})\n"
            
        brief += "\n## 2. ANOMALY DETECTION & RED FLAGS\n"
        for anomaly in anomalies:
            brief += f"- {anomaly}\n"
            
        brief += "\n## 3. NEXT MOVE\n1. Subpoena L&D account from relevant Master's Office.\n2. Formal DHA identity verification."
        
        report_path = os.path.join(self.vault_path, "intelligence_brief.md")
        with open(report_path, "w") as f:
            f.write(brief)
        return report_path

if __name__ == "__main__":
    # Example usage for the engine
    engine = TaoTzcivEEngine()
    
    # Mock data for Jan Pauls
    subject = {
        "name": "Jan Pauls",
        "id": "6407305107089",
        "dod": "2020-06-28",
        "gazette_date": "2021-04-23",
        "timeline": [
            {"date": "2021-05-05", "type": "Director Appointment"}
        ]
    }
    
    engine.vault_evidence("GovGazette", "Deceased Estate Notice for Jan Pauls...", "https://gpwonline.co.za")
    anomalies = engine.detect_anomalies(subject)
    report = engine.generate_brief(subject, anomalies)
    print(f"Investigation complete. Report saved to: {report}")
