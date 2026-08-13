# OMEGA · ALETHEIA
## Perception Integrity · Decision Engine · Escalation Protocol

A human-facing control panel wired to a local Termux bridge for evidence
auditing, permission-gate evaluation, communication calibration, and
two-edged escalation response.

---

## Architecture

```
Browser (React)
    ↓ same-origin HTTP (localhost only)
127.0.0.1:8765 — Python bridge (backend/server.py)
    ↓
Anthropic Claude API  (server-side only — key never in browser)
    ↓
~/cat_eof/state/perception_integrity.jsonl
~/cat_eof/state/cat_eof.db
```

The API key lives in `~/cat_eof/secrets/anthropic.env`.
It is **never** sent to the browser, never stored in localStorage,
never embedded in Vite environment variables.

---

## Five Stages

| Stage | Level | Name | Source |
|-------|-------|------|--------|
| 1 | L1 | Witness — Six Questions | Two-Edged Escalation Model (confirmed) |
| 2 | L2a | Aletheia — Five Senses + ABCDE | Glass-Chess / Aletheia Protocol (confirmed) |
| 3 | L2b | Permission Gate — I·A·E·R·M | Omega Bridge v7 (confirmed) |
| 4 | L3 | Register — Surface / Mid / Deep | Framework-inferred |
| 5 | L0–5 | Escalation ladder | L0–2 confirmed; L3–5 inferred |

---

## Termux Installation

### 1. Extract the project

```bash
cd ~
unzip omega-aletheia-*.zip
cd omega-aletheia
```

### 2. Run the installer

```bash
bash scripts/install-termux.sh
```

This will:
- Copy backend and tools to `~/cat_eof/apps/omega-aletheia-claude-bridge/`
- Install the `omega-claude-bridge` command to `~/cat_eof/tools/`
- Run the persistence smoke test
- Print next steps

### 3. Configure the API key

```bash
cp ~/cat_eof/secrets/anthropic.env.example ~/cat_eof/secrets/anthropic.env
chmod 600 ~/cat_eof/secrets/anthropic.env
# Edit with your preferred editor:
nano ~/cat_eof/secrets/anthropic.env
# Set: ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Start the bridge

```bash
~/cat_eof/tools/omega-claude-bridge start
```

### 5. Serve the frontend

Option A — serve the pre-built dist folder (no Node needed on device):

```bash
cd dist
python3 -m http.server 5173
```

Option B — development mode (Node required):

```bash
cd frontend
npm install
npm run dev
```

Then open `http://127.0.0.1:5173` in your browser.

---

## Stop / Status / Logs

```bash
~/cat_eof/tools/omega-claude-bridge stop
~/cat_eof/tools/omega-claude-bridge status
~/cat_eof/tools/omega-claude-bridge log
```

---

## Offline Mode

The UI works without Claude. When the bridge is running but the API key
is not set, all five stages remain usable:

- Six Questions are recorded
- Five Senses and ABCDE ratings are scored locally
- Hard-gate verdict is computed locally (no API required)
- Permission Gate scores are computed locally
- Register selection is saved
- Escalation level is saved
- Full case packet can be exported as JSON

Claude narrative analysis shows `CLAUDE ANALYSIS UNAVAILABLE` and saves
the local verdict in its place. No operator input is discarded.

---

## Hard Gate Rule

The percentage score is **informational only**.

`VERIFIED` is **impossible** if any ABCDE gate is `MISSING`.
`HOLD` or `DRY_RUN` applies if any contradiction is unresolved.
`UNKNOWN` is a first-class state — it is never overridden by a high score.

Source: `frontend/src/hardGate.js` → `hardGateVerdict()`

---

## Record Types

Every completed stage writes a record to SQLite and JSONL:

| record_type | Written at |
|-------------|-----------|
| `witness_six_questions` | Stage 1 → Stage 2 |
| `aletheia_sensory_audit` | Stage 2 → Stage 3 |
| `permission_gate` | Stage 3 → Stage 4 |
| `discernment_register` | Stage 4 → Stage 5 |
| `escalation_selection` | Stage 5 Save Packet |
| `claude_analysis` | Each Claude API call |

Raw testimony is preserved separately from Claude's generated output.
The packet export (`Export JSON`) includes both layers under distinct keys.

---

## Safety

- Bridge binds to `127.0.0.1` by default
- Set `ALETHEIA_HOST=0.0.0.0` only if you explicitly need LAN access
- API key is loaded from `~/cat_eof/secrets/anthropic.env` at process start
- The installer does not destroy any existing `~/cat_eof` ledger or registry

---

## Build (if modifying frontend)

```bash
cd frontend
npm install
npm run build
# Output → dist/
```

---

## Tests

```bash
python3 tests/smoke_test.py
```

Expected output:
```
CLAUDE BRIDGE SMOKE TEST PASSED
JSONL and SQLite persistence verified
```

---

## Source Distinctions

The Omega Engine marks its doctrinal sources honestly:

- **✓ Confirmed** — from supplied source documents
- **⊙ Inferred** — framework-inferred, pending full document confirmation

Levels 3–5 of the escalation model are marked inferred and will be updated
when the full Two-Edged Escalation Model document is supplied.

---

*Relevant retrieval ≠ complete retrieval.*
*The gate does not decide — it reveals what is already true.*
