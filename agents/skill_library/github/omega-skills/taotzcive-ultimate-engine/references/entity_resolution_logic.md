# Entity Resolution & Anomaly Detection Logic

This logic defines how the engine resolves identities and flags contradictions across disparate data sources.

## 1. Entity Resolution (ER) Rules

| Check | Logic | Confidence Impact |
| :--- | :--- | :--- |
| **ID Number Match** | Exact 13-digit match across sources | **High (+50%)** |
| **Name Variant** | "Jan Pauls" vs "Johnny Pauls" with matching address | **Medium (+25%)** |
| **Spouse Link** | Matching spouse name/ID in Gazette and DHA | **High (+40%)** |
| **Attorney Collision** | Same law firm appearing in unrelated cases | **Flag (Anomaly)** |

## 2. Timeline Anomaly Flags

| Anomaly | Description | Risk Level |
| :--- | :--- | :--- |
| **Post-Mortem Director** | Subject listed as an "Active" director after DOD | **Critical (Identity Theft)** |
| **Estate Suppression** | >6 month gap between DOD and Gazette notice | **High (Asset Stripping)** |
| **Marriage After Death** | Marriage registration date > DOD | **Critical (Fraud)** |
| **Inquest Avoidance** | Unnatural death without a corresponding court docket | **High (Legal Bypass)** |

## 3. Network Node Analysis

*   **Node 1: The Fountain of Praise / Gerhard Dryer Nexus**: Private registry firewalls used to obscure asset movements.
*   **Node 2: The Kingsley / Standerton Nexus**: Drug manufacturing and cross-border money movement.
*   **Node 3: The Attorney Collision**: Law firms acting as facilitators for "ghost" estate registrations.
