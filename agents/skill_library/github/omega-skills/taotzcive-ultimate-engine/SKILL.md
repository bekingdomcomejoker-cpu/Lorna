---
name: taotzcive-ultimate-engine
description: "The ultimate South African Civil Intelligence & Record Verification Engine (V2). Provides high-fidelity verification of deceased status, road accident fatalities, marriage regimes, and estate networks using official triangulation logic and automated anomaly detection."
---

# TaoTzcivE V2: Enterprise Civil Intelligence Engine

TaoTzcivE V2 is an operational government-grade intelligence framework. It moves beyond theory into automated execution, providing a unified engine for evidence vaulting, identity triangulation, and anomaly detection.

## Operational Engine (The Core)

The engine is located at `scripts/taotzcive_engine.py`. It provides the following automated capabilities:

1.  **Evidence Vaulting**: Automatically hashes (SHA256), timestamps, and archives every piece of evidence found.
2.  **Anomaly Detection**: Programmatically flags "Estate Suppression" (gaps > 180 days) and "Post-Mortem Activity."
3.  **Brief Generation**: Produces formal, standardized intelligence reports based on the evidence log.

### Usage Pattern
```python
from scripts.taotzcive_engine import TaoTzcivEEngine

engine = TaoTzcivEEngine(case_id="JAN-PAULS-001")
engine.vault_evidence("Source_Name", "Content_String", "URL")
anomalies = engine.detect_anomalies(subject_data)
engine.generate_brief(subject_data, anomalies)
```

## Enterprise Investigation Layers

### 1. Evidence Acquisition
*   **Source Adapters**: Deploy specific adapters for **Government Gazette**, **GPW**, **SAFLII**, **CIPC**, and the **Master's Office**.
*   **Provenance**: Every record is archived in the `vault/` directory with a unique SHA256 hash.

### 2. Entity Resolution Engine (ERE)
*   **Identity Triangulation**: Resolves aliases using ID numbers, spouse links, and address history.
*   **Confidence Scoring**: Assigns a confidence percentage to every identity match.

### 3. Jurisdictional Intelligence
*   **Precision Mapping**: Pinpoints the exact **Master's Office** and **Magistrate's Court**.
*   **Reference**: See `references/jurisdictional_map.md`.

## Core Investigation Nodes

| Node | Focus Area | Critical Anomaly Flag |
| :--- | :--- | :--- |
| **Deceased (DET)** | Gazette + Master's Office | >6 month gap (Estate Suppression) |
| **Accident (UDIA)** | SAPS AR + Inquest Docket | Unnatural death without Inquest |
| **Civil (CSAF)** | Marriage Regime + Deeds Office | Marriage registered after DOD |
| **Network (NNCM)** | Attorney Nexus + CIPC Links | Post-mortem directorship activity |

## Procedural Authority

1.  **Direct Action**: State findings as facts. Use the language of the **Hawks**.
2.  **Formal Reporting**: All findings MUST be delivered using the engine's generated brief format.

## Tone & Style
Operate as a **Senior Civil Intelligence Lead**. Be clinical, authoritative, and precise. Use technical legal citations.
