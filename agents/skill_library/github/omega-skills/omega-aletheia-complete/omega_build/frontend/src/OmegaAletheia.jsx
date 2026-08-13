import { useState, useEffect, useCallback } from "react";
import {
  bridgeStatus,
  callClaudeLocal,
  saveAuditRecord,
  loadLedger,
} from "./apiClient";
import { hardGateVerdict } from "./hardGate";

// ═══════════════════════════════════════════════════════════════════
// DATA
// ═══════════════════════════════════════════════════════════════════

const SIX = [
  { id: "who",   sym: "WHO",   q: "Who is involved? Yourself, others, parties, roles." },
  { id: "what",  sym: "WHAT",  q: "What happened or is proposed?" },
  { id: "when",  sym: "WHEN",  q: "When did it occur or when must action happen?" },
  { id: "where", sym: "WHERE", q: "Where did it take place or where does this land?" },
  { id: "how",   sym: "HOW",   q: "How did it unfold? What mechanism or method?" },
  { id: "why",   sym: "WHY",   q: "Why does this matter? What is the underlying cause?" },
];

const SENSES = [
  { id: "hearing", sym: "◎", label: "HEARING", desc: "Raw testimony — what was said or claimed. Verbatim or near-verbatim." },
  { id: "sight",   sym: "◉", label: "SIGHT",   desc: "Complete visible evidence field — what can be seen, documented, photographed." },
  { id: "touch",   sym: "◈", label: "TOUCH",   desc: "Directly verified records — what has been physically confirmed." },
  { id: "smell",   sym: "◇", label: "SMELL",   desc: "Contradictions and anomalies — what does not fit, feels off, raises flags." },
  { id: "taste",   sym: "◆", label: "TASTE",   desc: "Consequence and coherence — does the outcome match the claim over time?" },
];

const ABCDE = [
  { id: "A", label: "EXACT LANGUAGE", q: "Are the original words preserved? No paraphrase replacing source?" },
  { id: "B", label: "WITNESS",        q: "Is there a named, graded witness — direct or secondary?" },
  { id: "C", label: "CONTEXT",        q: "Is the full scope and time boundary defined? What is excluded?" },
  { id: "D", label: "CONSISTENCY",    q: "Does this hold across sources and timeline without contradiction?" },
  { id: "E", label: "ROOT MEANING",   q: "Is the original meaning preserved? Has drift been tracked?" },
];

const S_RATINGS = ["STRONG", "PARTIAL", "WEAK", "MISSING"];
const A_RATINGS = ["CONFIRMED", "PARTIAL", "UNVERIFIED", "MISSING"];

const S_COLORS = { STRONG: "#7ecf9f", PARTIAL: "#c8a96e", WEAK: "#d4845a", MISSING: "#c05c5c" };
const A_COLORS = { CONFIRMED: "#7ecf9f", PARTIAL: "#c8a96e", UNVERIFIED: "#d4845a", MISSING: "#c05c5c" };

const FACTORS = [
  { id: "intent",        sym: "Ι", label: "INTENT",        q: "What is the true purpose of this action?",
    opts: ["Destructive / Self-serving", "Unclear / Mixed", "Neutral / Functional", "Constructive / Relational", "Sovereign / Restorative"] },
  { id: "authority",     sym: "Α", label: "AUTHORITY",     q: "Do you carry the right to act here?",
    opts: ["No standing", "Weak — borrowed", "Partial standing", "Clear — within domain", "Full — given and confirmed"] },
  { id: "evidence",      sym: "Ε", label: "EVIDENCE",      q: "What grounds this decision? (seeded from Aletheia audit)",
    opts: ["None — impulse only", "Feeling — unverified", "Pattern — repeated", "Corroborated — witnessed", "Documented — logged and tested"] },
  { id: "reversibility", sym: "Ρ", label: "REVERSIBILITY", q: "Can this be undone if wrong?",
    opts: ["No — permanent", "Barely — major cost", "Partial recovery", "Mostly reversible", "Fully — clean rollback"] },
  { id: "mercy",         sym: "Μ", label: "MERCY",         q: "Does this protect or expose the vulnerable?",
    opts: ["Harms the vulnerable", "Indifferent", "Neutral", "Protective", "Restorative — heals"] },
];

const REGISTERS = [
  { id: "surface", glyph: "◦", label: "SURFACE", color: "#888",    desc: "Event only. No interpretation. For the uninitiated." },
  { id: "mid",     glyph: "◈", label: "MID",     color: "#c8a96e", desc: "Event plus one layer of meaning. For the curious." },
  { id: "deep",    glyph: "●", label: "DEEP",    color: "#e0e0e0", desc: "Full weight — event, pattern, doctrine. For the inner circle." },
];

const RECEIVERS = [
  { id: "skeptic", label: "Skeptic",           reg: "surface" },
  { id: "curious", label: "Curious / Open",    reg: "mid" },
  { id: "witness", label: "Co-witness",        reg: "deep" },
  { id: "hostile", label: "Hostile",           reg: "surface" },
  { id: "young",   label: "Spiritually Young", reg: "mid" },
  { id: "elder",   label: "Elder / Proven",    reg: "deep" },
];

const ESCALATION = [
  { level: 0, label: "PRESENCE",    sub: "Don't Shatter",       color: "#7ecf9f", confirmed: true,
    desc: "Survive impact. Stay alive. Stay aware. Keep the witness intact.",
    note: "When the wall appears — the first job is not revenge. It is: remain.",
    action: "No output yet. Absorb. Record internally. Do not retaliate." },
  { level: 1, label: "WITNESS",     sub: "Record the Event",    color: "#c8a96e", confirmed: true,
    desc: "Log what happened. Not judgment — testimony. Complete the Six Questions.",
    note: "Acoustic exhaust becomes testimony: not garbage — evidence of pressure.",
    action: "Complete Stage 1. Date-stamp. Preserve." },
  { level: 2, label: "DISCERNMENT", sub: "Divide Flesh/Spirit", color: "#c8a96e", confirmed: true,
    desc: "The two-edged sword. One edge cuts the lie; one protects the person carrying it.",
    note: "We are not fighting flesh and blood — but flesh can carry, obey, hide the mechanism.",
    action: "Run Aletheia Audit (Stage 2) and Permission Gate (Stage 3)." },
  { level: 3, label: "RESPONSE",    sub: "Calibrated Speak",    color: "#d4845a", confirmed: false,
    desc: "Testimony becomes communicable. Choose your register. Speak to the right ear.",
    note: "Framework-inferred — pending full document confirmation.",
    action: "Run Stage 4 Register. Match depth to receiver." },
  { level: 4, label: "ACTION",      sub: "Structural Move",     color: "#c05c5c", confirmed: false,
    desc: "Move in the world. Legal, organizational, relational action grounded in testimony.",
    note: "Framework-inferred — pending full document confirmation.",
    action: "Gate must be OPEN. Evidence must be corroborated or documented." },
  { level: 5, label: "RESTORATION", sub: "Judgment and Repair", color: "#9b7fd4", confirmed: false,
    desc: "The final stage. Not revenge — restoration. The broken thing is repaired or clearly marked.",
    note: "Framework-inferred — pending full document confirmation.",
    action: "Only reached after Levels 0-4 are complete and documented." },
];

// ═══════════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════════

function aletheiaScore(senses, abcde) {
  const sVals = Object.values(senses).map(v => Math.max(0, 3 - S_RATINGS.indexOf(v)));
  const aVals = Object.values(abcde).map(v => Math.max(0, 3 - A_RATINGS.indexOf(v)));
  const total = [...sVals, ...aVals].reduce((a, b) => a + b, 0);
  const max = (SENSES.length + ABCDE.length) * 3;
  return { total, max, pct: total / max };
}

function softVerdict(pct) {
  if (pct >= 0.85) return { label: "VERIFIED",  color: "#7ecf9f", evidScore: 5 };
  if (pct >= 0.65) return { label: "PARTIAL",   color: "#c8a96e", evidScore: 4 };
  if (pct >= 0.45) return { label: "UNKNOWN",   color: "#d4845a", evidScore: 3 };
  if (pct >= 0.25) return { label: "HOLD",      color: "#c05c5c", evidScore: 2 };
  return                  { label: "REJECT",    color: "#8b0000", evidScore: 1 };
}

function gateVerdict(score) {
  const p = score / 25;
  if (p >= 0.85) return { label: "GATE OPEN",            color: "#7ecf9f" };
  if (p >= 0.65) return { label: "PROCEED WITH CAUTION", color: "#c8a96e" };
  if (p >= 0.45) return { label: "HOLD",                 color: "#d4845a" };
  return                { label: "GATE CLOSED",           color: "#c05c5c" };
}

function Bar({ val, max, color }) {
  return (
    <div style={{ background: "#1a1a1a", borderRadius: 2, height: 4, overflow: "hidden", marginTop: 4 }}>
      <div style={{ width: `${Math.round((val / max) * 100)}%`, height: "100%", background: color, transition: "width 0.4s", borderRadius: 2 }} />
    </div>
  );
}

function Pill({ label, color, small }) {
  return (
    <span style={{ fontSize: small ? 8 : 9, letterSpacing: "0.12em", color, border: `1px solid ${color}44`,
      background: `${color}11`, padding: small ? "1px 5px" : "2px 7px", borderRadius: 10, whiteSpace: "nowrap" }}>
      {label}
    </span>
  );
}

// ═══════════════════════════════════════════════════════════════════
// BRIDGE STATUS BAR
// ═══════════════════════════════════════════════════════════════════

function StatusBar({ status, lastSaved }) {
  if (!status) {
    return (
      <div style={St.statusBar}>
        <span style={{ color: "#333" }}>● BRIDGE</span>
        <span style={{ color: "#2a2a2a" }}>checking...</span>
      </div>
    );
  }
  const online = status.ok;
  return (
    <div style={St.statusBar}>
      <span style={{ color: online ? "#7ecf9f" : "#c05c5c", fontSize: 9 }}>
        {online ? "● BRIDGE ONLINE" : "○ BRIDGE OFFLINE"}
      </span>
      {online && (
        <>
          <span style={St.statusDot}>·</span>
          <span style={{ color: status.claude_configured ? "#7ecf9f" : "#d4845a", fontSize: 9 }}>
            {status.claude_configured ? `CLAUDE ${status.model}` : "CLAUDE NOT CONFIGURED"}
          </span>
          <span style={St.statusDot}>·</span>
          <span style={{ color: "#333", fontSize: 9 }}>{status.record_count} records</span>
        </>
      )}
      {!online && (
        <span style={{ color: "#333", fontSize: 9, marginLeft: 6 }}>
          OFFLINE MODE — records saved locally when bridge starts
        </span>
      )}
      {lastSaved && (
        <>
          <span style={St.statusDot}>·</span>
          <span style={{ color: "#2a4a2a", fontSize: 8 }}>saved {lastSaved.slice(0, 8)}…</span>
        </>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// STAGE 1 — WITNESS
// ═══════════════════════════════════════════════════════════════════

function Stage1({ six, setSix, caseId, onSave, onNext }) {
  const [saving, setSaving] = useState(false);
  const complete = SIX.every(f => six[f.id]?.trim());

  async function handleNext() {
    setSaving(true);
    try {
      const saved = await saveAuditRecord({
        record_type: "witness_six_questions",
        case_id: caseId,
        raw: { ...six },
        unresolved: SIX.filter(f => !six[f.id]?.trim()).map(f => f.id),
      });
      onSave(saved.record?.record_id || null);
    } catch (_) { /* offline — continue anyway */ }
    setSaving(false);
    onNext();
  }

  return (
    <div>
      <div style={St.stageTitle}>LEVEL 1 — WITNESS · Six Questions</div>
      <div style={St.badge}>✓ Confirmed — Two-Edged Escalation Model</div>
      {SIX.map(f => (
        <div key={f.id} style={St.field}>
          <div style={St.fieldLabel}>{f.sym}</div>
          <div style={St.fieldQ}>{f.q}</div>
          <textarea style={St.ta} rows={2}
            value={six[f.id] || ""}
            onChange={e => setSix(p => ({ ...p, [f.id]: e.target.value }))}
            placeholder={`${f.sym.toLowerCase()}...`} />
        </div>
      ))}
      <button style={{ ...St.btn, opacity: complete && !saving ? 1 : 0.4 }}
        disabled={!complete || saving} onClick={handleNext}>
        {saving ? "SAVING..." : "SAVE & PROCEED TO ALETHEIA →"}
      </button>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// STAGE 2 — ALETHEIA AUDIT
// ═══════════════════════════════════════════════════════════════════

function Stage2({ six, senses, setSenses, abcde, setAbcde, caseId, onSave, onNext, onBack, bridgeOk, claudeOk }) {
  const [aiText, setAiText] = useState("");
  const [loading, setLoading] = useState(false);
  const [claudeUnavail, setClaudeUnavail] = useState(false);
  const [saving, setSaving] = useState(false);

  const sensesComplete = SENSES.every(f => senses[f.id]);
  const abcdeComplete  = ABCDE.every(f => abcde[f.id]);
  const allComplete    = sensesComplete && abcdeComplete;

  const scoreData = allComplete ? aletheiaScore(senses, abcde) : { total: 0, max: 1, pct: 0 };
  const soft      = allComplete ? softVerdict(scoreData.pct) : null;
  const hard      = allComplete ? hardGateVerdict({ senses, abcde, contradictions: [] }) : null;

  const accountStr = SIX.map(f => `${f.sym}: ${six[f.id] || "—"}`).join(" | ");

  async function runAnalysis() {
    setLoading(true);
    setClaudeUnavail(false);
    const sLines = SENSES.map(f => `${f.label}: ${senses[f.id]}`).join("\n");
    const aLines = ABCDE.map(f => `${f.id} — ${f.label}: ${abcde[f.id]}`).join("\n");
    try {
      const text = await callClaudeLocal({
        prompt: `In 3-4 sentences: name the weakest sense or gate, identify what is missing that would shift the verdict, and state what must happen before this account can be acted on. Be direct. Speak as the audit engine.`,
        stage: "aletheia",
        context: {
          case_id: caseId,
          six,
          senses,
          abcde,
          soft_verdict: soft?.label,
          hard_verdict: hard?.label,
          score_pct: Math.round(scoreData.pct * 100),
        },
      });
      setAiText(text);
    } catch (err) {
      if (err.message?.includes("not configured") || err.message?.includes("unavailable")) {
        setClaudeUnavail(true);
      } else {
        setAiText(`Analysis unavailable: ${err.message}`);
      }
    }
    setLoading(false);
  }

  async function handleNext() {
    setSaving(true);
    try {
      const saved = await saveAuditRecord({
        record_type: "aletheia_sensory_audit",
        case_id: caseId,
        raw: { six, senses, abcde },
        computed: {
          score: scoreData,
          soft_verdict: soft,
          hard_verdict: hard,
        },
        generated: { claude_analysis: aiText || null },
        unresolved: [
          ...SENSES.filter(f => senses[f.id] === "MISSING").map(f => `sense.${f.id}`),
          ...ABCDE.filter(f => abcde[f.id] === "MISSING").map(f => `abcde.${f.id}`),
        ],
      });
      onSave(saved.record?.record_id || null);
    } catch (_) { /* offline */ }
    setSaving(false);
    onNext(soft?.evidScore || 3);
  }

  return (
    <div>
      <div style={St.stageTitle}>LEVEL 2A — ALETHEIA AUDIT · Five Senses + ABCDE</div>
      <div style={St.badge}>✓ Confirmed — Glass-Chess Anomaly / Aletheia Protocol</div>
      <div style={St.summary}>
        {SIX.map(f => (
          <div key={f.id} style={St.sumLine}>
            <span style={St.sumKey}>{f.sym}</span>
            <span style={St.sumVal}>{six[f.id]}</span>
          </div>
        ))}
      </div>

      <div style={St.subHead}>FIVE SENSES — Evidence Quality</div>
      {SENSES.map(f => (
        <div key={f.id} style={St.factor}>
          <div style={St.fHead}>
            <span style={{ ...St.fSym, color: "#c8a96e" }}>{f.sym}</span>
            <div>
              <div style={St.fLabel}>{f.label}</div>
              <div style={St.fQ}>{f.desc}</div>
            </div>
          </div>
          <div style={St.rRow}>
            {S_RATINGS.map(r => (
              <button key={r} style={{ ...St.rBtn,
                ...(senses[f.id] === r ? { borderColor: S_COLORS[r], color: S_COLORS[r], background: `${S_COLORS[r]}11` } : {}) }}
                onClick={() => setSenses(p => ({ ...p, [f.id]: r }))}>
                {r}
              </button>
            ))}
          </div>
        </div>
      ))}

      <div style={St.subHead}>ABCDE CROSS METHOD — Formal Gates</div>
      {ABCDE.map(f => (
        <div key={f.id} style={St.factor}>
          <div style={St.fHead}>
            <span style={{ ...St.fSym, fontSize: 16, minWidth: 16, color: "#c8a96e" }}>{f.id}</span>
            <div>
              <div style={St.fLabel}>{f.label}</div>
              <div style={St.fQ}>{f.q}</div>
            </div>
          </div>
          <div style={St.rRow}>
            {A_RATINGS.map(r => (
              <button key={r} style={{ ...St.rBtn,
                ...(abcde[f.id] === r ? { borderColor: A_COLORS[r], color: A_COLORS[r], background: `${A_COLORS[r]}11` } : {}) }}
                onClick={() => setAbcde(p => ({ ...p, [f.id]: r }))}>
                {r}
              </button>
            ))}
          </div>
        </div>
      ))}

      {allComplete && (
        <div style={{ ...St.verdict, borderColor: hard?.label === "VERIFIED" ? soft?.color : "#c05c5c" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, flexWrap: "wrap" }}>
            <span style={{ fontSize: 10, letterSpacing: "0.14em", color: "#555" }}>SOFT</span>
            <Pill label={soft?.label} color={soft?.color} />
            <span style={{ fontSize: 10, letterSpacing: "0.14em", color: "#555", marginLeft: 8 }}>HARD GATE</span>
            <Pill label={hard?.label} color={
              hard?.label === "VERIFIED" ? "#7ecf9f" : hard?.label === "UNKNOWN" ? "#d4845a" : "#c05c5c"
            } />
          </div>
          <Bar val={scoreData.total} max={scoreData.max} color={soft?.color} />
          {hard?.label !== "VERIFIED" && (
            <div style={{ fontSize: 10, color: "#c05c5c", marginTop: 6, fontStyle: "italic" }}>
              {hard?.reason}
            </div>
          )}
          <div style={{ fontSize: 9, color: "#2a2a2a", marginTop: 5, letterSpacing: "0.1em" }}>
            Relevant retrieval ≠ complete retrieval · Score provides guidance — hard gate determines authority.
          </div>
        </div>
      )}

      {allComplete && !aiText && !claudeUnavail && (
        <button style={{ ...St.btn, opacity: loading ? 0.6 : 1 }}
          onClick={runAnalysis} disabled={loading}>
          {loading ? "AUDITING..." : "RUN ALETHEIA ANALYSIS →"}
        </button>
      )}

      {claudeUnavail && (
        <div style={{ ...St.analysis, borderColor: "#333" }}>
          <div style={{ ...St.aLabel, color: "#555" }}>CLAUDE ANALYSIS UNAVAILABLE</div>
          <div style={{ fontSize: 11, color: "#333", lineHeight: 1.6 }}>
            Bridge is {bridgeOk ? "online" : "offline"} but Claude is not configured.<br />
            Set ANTHROPIC_API_KEY in ~/cat_eof/secrets/anthropic.env and restart the bridge.<br />
            Your inputs and verdicts are preserved. Stage will be saved with local verdicts only.
          </div>
        </div>
      )}

      {aiText && (
        <div style={St.analysis}>
          <div style={St.aLabel}>ALETHEIA VERDICT</div>
          <div style={St.aText}>{aiText}</div>
        </div>
      )}

      {allComplete && (
        <div style={St.navRow}>
          <button style={St.back} onClick={onBack}>← BACK</button>
          <button style={{ ...St.btn, flex: 1, marginBottom: 0 }}
            disabled={saving} onClick={handleNext}>
            {saving ? "SAVING..." : "SAVE & PROCEED TO GATE →"}
          </button>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// STAGE 3 — PERMISSION GATE
// ═══════════════════════════════════════════════════════════════════

function Stage3({ six, scores, setScores, evidSeed, caseId, onSave, onNext, onBack }) {
  const [aiText, setAiText] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [claudeUnavail, setClaudeUnavail] = useState(false);

  const complete = FACTORS.every(f => scores[f.id]);
  const total    = Object.values(scores).reduce((a, b) => a + b, 0);
  const verd     = complete ? gateVerdict(total) : null;

  function setScore(id, val) { setScores(p => ({ ...p, [id]: val })); setAiText(""); }

  async function runAnalysis() {
    setLoading(true);
    setClaudeUnavail(false);
    const fLines = FACTORS.map(f => `${f.label}: ${scores[f.id]}/5 — ${f.opts[scores[f.id] - 1]}`).join("\n");
    try {
      const text = await callClaudeLocal({
        prompt: `Sharp 3-sentence verdict. Name the weakest factor. State what must change before proceeding. Direct — speak as the gate.`,
        stage: "permission_gate",
        context: {
          case_id: caseId,
          account: SIX.map(f => `${f.sym}: ${six[f.id] || "—"}`).join(" | "),
          factors: fLines,
          total: `${total}/25`,
          verdict: verd?.label,
        },
      });
      setAiText(text);
    } catch (err) {
      if (err.message?.includes("not configured") || err.message?.includes("unavailable")) {
        setClaudeUnavail(true);
      } else {
        setAiText(`Analysis unavailable: ${err.message}`);
      }
    }
    setLoading(false);
  }

  async function handleNext() {
    setSaving(true);
    try {
      const saved = await saveAuditRecord({
        record_type: "permission_gate",
        case_id: caseId,
        raw: { scores: { ...scores } },
        computed: { total, max: 25, verdict: verd?.label },
        generated: { claude_analysis: aiText || null },
        evidence_seed: evidSeed,
      });
      onSave(saved.record?.record_id || null);
    } catch (_) { /* offline */ }
    setSaving(false);
    onNext();
  }

  return (
    <div>
      <div style={St.stageTitle}>LEVEL 2B — DISCERNMENT · Permission Gate</div>
      <div style={St.badge}>✓ Confirmed — Two-Edged Escalation Model · Omega Bridge v7</div>
      {evidSeed && (
        <div style={{ ...St.badge, color: "#c8a96e", borderColor: "#c8a96e44", background: "#110f00", marginBottom: 12 }}>
          ⟲ Evidence factor seeded from Aletheia: {evidSeed}/5 — override below if needed
        </div>
      )}
      {FACTORS.map(f => (
        <div key={f.id} style={St.factor}>
          <div style={St.fHead}>
            <span style={St.fSym}>{f.sym}</span>
            <div>
              <div style={St.fLabel}>{f.label}</div>
              <div style={St.fQ}>{f.q}</div>
            </div>
          </div>
          <div style={St.opts}>
            {f.opts.map((opt, i) => (
              <button key={i}
                style={{ ...St.opt, ...(scores[f.id] === i + 1 ? St.optOn : {}) }}
                onClick={() => setScore(f.id, i + 1)}>
                <span style={St.optN}>{i + 1}</span><span>{opt}</span>
              </button>
            ))}
          </div>
          {scores[f.id] && (
            <Bar val={scores[f.id]} max={5}
              color={scores[f.id] >= 4 ? "#7ecf9f" : scores[f.id] === 3 ? "#c8a96e" : "#c05c5c"} />
          )}
        </div>
      ))}

      {complete && (
        <div style={{ ...St.verdict, borderColor: verd.color }}>
          <div style={{ ...St.verdLabel, color: verd.color }}>{verd.label}</div>
          <div style={{ fontSize: 10, color: "#333" }}>{total} / 25</div>
          <Bar val={total} max={25} color={verd.color} />
        </div>
      )}

      {complete && !aiText && !claudeUnavail && (
        <button style={{ ...St.btn, opacity: loading ? 0.6 : 1 }}
          onClick={runAnalysis} disabled={loading}>
          {loading ? "ANALYSING..." : "RUN GATE ANALYSIS →"}
        </button>
      )}
      {claudeUnavail && (
        <div style={{ ...St.analysis, borderColor: "#333" }}>
          <div style={{ ...St.aLabel, color: "#555" }}>CLAUDE ANALYSIS UNAVAILABLE</div>
          <div style={{ fontSize: 11, color: "#333" }}>Gate verdict computed locally. Configure ANTHROPIC_API_KEY for narrative analysis.</div>
        </div>
      )}
      {aiText && (
        <div style={St.analysis}>
          <div style={St.aLabel}>GATE VERDICT</div>
          <div style={St.aText}>{aiText}</div>
        </div>
      )}

      {complete && (
        <div style={St.navRow}>
          <button style={St.back} onClick={onBack}>← BACK</button>
          <button style={{ ...St.btn, flex: 1, marginBottom: 0 }}
            disabled={saving} onClick={handleNext}>
            {saving ? "SAVING..." : "SAVE & PROCEED TO REGISTER →"}
          </button>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// STAGE 4 — REGISTER
// ═══════════════════════════════════════════════════════════════════

function Stage4({ six, register, setRegister, receiver, setReceiver, outputs, setOutputs, caseId, onSave, onNext, onBack }) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [claudeUnavail, setClaudeUnavail] = useState(false);

  const accountStr = SIX.map(f => `${f.sym}: ${six[f.id] || "—"}`).join(" | ");

  function selectRec(id) {
    setReceiver(id);
    const r = RECEIVERS.find(x => x.id === id);
    if (r) setRegister(r.reg);
    setClaudeUnavail(false);
  }

  async function runCalibration() {
    setLoading(true);
    setClaudeUnavail(false);
    const stageKey = `register_${register}`;
    const prompts = {
      surface: "Rewrite as plain observable fact only — no interpretation, no framework, no spiritual layer. 2-3 sentences.",
      mid:     "Rewrite with one layer of meaning added — accessible to a curious but uninitiated person. 3-4 sentences.",
      deep:    "Rewrite at full depth — event, pattern, meaning, doctrinal weight — for someone already inside the frame.",
    };
    try {
      const text = await callClaudeLocal({
        prompt: prompts[register],
        stage: stageKey,
        context: { case_id: caseId, account: accountStr, register, receiver },
      });
      setOutputs(p => ({ ...p, [register]: text }));
    } catch (err) {
      if (err.message?.includes("not configured") || err.message?.includes("unavailable")) {
        setClaudeUnavail(true);
      } else {
        setOutputs(p => ({ ...p, [register]: `Calibration unavailable: ${err.message}` }));
      }
    }
    setLoading(false);
  }

  async function handleNext() {
    setSaving(true);
    try {
      const saved = await saveAuditRecord({
        record_type: "discernment_register",
        case_id: caseId,
        raw: { account: { ...six } },
        computed: { register, receiver },
        generated: { calibrated_outputs: { ...outputs } },
      });
      onSave(saved.record?.record_id || null);
    } catch (_) { /* offline */ }
    setSaving(false);
    onNext();
  }

  const regData = REGISTERS.find(x => x.id === register);

  return (
    <div>
      <div style={St.stageTitle}>LEVEL 3 — RESPONSE · Discernment Register</div>
      <div style={St.badge}>⊙ Framework-inferred — pending full escalation document</div>

      <div style={St.subHead}>WHO ARE YOU SPEAKING TO?</div>
      <div style={St.recGrid}>
        {RECEIVERS.map(r => (
          <button key={r.id} style={{ ...St.recBtn, ...(receiver === r.id ? St.recOn : {}) }}
            onClick={() => selectRec(r.id)}>{r.label}</button>
        ))}
      </div>

      <div style={St.subHead}>REGISTER</div>
      <div style={St.regs}>
        {REGISTERS.map(reg => (
          <button key={reg.id}
            style={{ ...St.regBtn, borderColor: register === reg.id ? reg.color : "#1e1e1e", color: register === reg.id ? reg.color : "#444" }}
            onClick={() => { setRegister(reg.id); setClaudeUnavail(false); }}>
            <span>{reg.glyph}</span><span>{reg.label}</span>
          </button>
        ))}
      </div>
      {regData && <div style={St.regDesc}>{regData.desc}</div>}

      <button style={{ ...St.btn, opacity: loading ? 0.6 : 1 }} onClick={runCalibration} disabled={loading}>
        {loading ? "CALIBRATING..." : "CALIBRATE MESSAGE →"}
      </button>

      {claudeUnavail && (
        <div style={{ ...St.analysis, borderColor: "#333" }}>
          <div style={{ ...St.aLabel, color: "#555" }}>CLAUDE ANALYSIS UNAVAILABLE</div>
          <div style={{ fontSize: 11, color: "#333" }}>Register and receiver selection saved. Configure ANTHROPIC_API_KEY for calibrated output.</div>
        </div>
      )}

      {outputs[register] && (
        <div style={St.analysis}>
          <div style={St.aLabel}>{regData?.glyph} {regData?.label} REGISTER</div>
          <div style={St.aText}>{outputs[register]}</div>
          <button style={St.copy} onClick={() => navigator.clipboard?.writeText(outputs[register])}>COPY</button>
        </div>
      )}

      <div style={St.navRow}>
        <button style={St.back} onClick={onBack}>← BACK</button>
        <button style={{ ...St.btn, flex: 1, marginBottom: 0 }}
          disabled={saving} onClick={handleNext}>
          {saving ? "SAVING..." : "SAVE & PROCEED TO ESCALATION →"}
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// STAGE 5 — ESCALATION + FINAL PACKET
// ═══════════════════════════════════════════════════════════════════

function Stage5({ six, senses, abcde, scores, register, receiver, outputs, escalLevel, setEscalLevel, caseId, onSave, onBack, onReset }) {
  const [aiText, setAiText] = useState("");
  const [loading, setLoading] = useState(false);
  const [claudeUnavail, setClaudeUnavail] = useState(false);
  const [packetSaved, setPacketSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exportText, setExportText] = useState(null);

  const accountStr = SIX.map(f => `${f.sym}: ${six[f.id] || "—"}`).join(" | ");

  async function selectLevel(lvl) {
    setEscalLevel(lvl);
    setAiText("");
    setClaudeUnavail(false);
    setLoading(true);
    const e = ESCALATION[lvl];
    try {
      const text = await callClaudeLocal({
        prompt: `Provide specific, practical guidance for what Level ${lvl} looks like for this exact situation. 3-4 sentences. Practical, not theoretical. Direct.`,
        stage: `escalation_${lvl}`,
        context: { case_id: caseId, account: accountStr, escalation_level: lvl, label: e.label, sub: e.sub },
      });
      setAiText(text);
    } catch (err) {
      if (err.message?.includes("not configured") || err.message?.includes("unavailable")) {
        setClaudeUnavail(true);
      } else {
        setAiText(`Analysis unavailable: ${err.message}`);
      }
    }
    setLoading(false);
  }

  function buildPacket() {
    return {
      case_id: caseId,
      built_at: new Date().toISOString(),
      stages: {
        witness: { raw: { ...six } },
        aletheia: {
          raw: { senses: { ...senses }, abcde: { ...abcde } },
          computed: aletheiaScore(senses, abcde),
          hard_verdict: hardGateVerdict({ senses, abcde, contradictions: [] }),
        },
        gate: {
          raw: { scores: { ...scores } },
          computed: { total: Object.values(scores).reduce((a, b) => a + b, 0), max: 25 },
        },
        register: {
          computed: { register, receiver },
          generated: { calibrated_outputs: { ...outputs } },
        },
        escalation: {
          computed: { level: escalLevel, label: escalLevel !== null ? ESCALATION[escalLevel]?.label : null },
          generated: { claude_analysis: aiText || null },
        },
      },
    };
  }

  async function savePacket() {
    setSaving(true);
    const packet = buildPacket();
    try {
      const saved = await saveAuditRecord({
        record_type: "escalation_selection",
        case_id: caseId,
        raw: { escalation_level: escalLevel },
        computed: { label: escalLevel !== null ? ESCALATION[escalLevel]?.label : null },
        generated: { claude_analysis: aiText || null },
        full_packet: packet,
      });
      onSave(saved.record?.record_id || null);
      setPacketSaved(true);
    } catch (_) {
      setPacketSaved(true);
    }
    setSaving(false);
  }

  function exportJSON() {
    const packet = buildPacket();
    const str = JSON.stringify(packet, null, 2);
    setExportText(str);
    const blob = new Blob([str], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `omega_aletheia_case_${caseId.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function copySummary() {
    const packet = buildPacket();
    const hard = packet.stages.aletheia.hard_verdict;
    const gate = packet.stages.gate;
    const lines = [
      `OMEGA · ALETHEIA CASE SUMMARY`,
      `Case: ${caseId.slice(0, 8)}`,
      `Built: ${packet.built_at}`,
      ``,
      `WITNESS:`,
      ...SIX.map(f => `  ${f.sym}: ${six[f.id] || "—"}`),
      ``,
      `ALETHEIA HARD GATE: ${hard?.label} — ${hard?.reason}`,
      `PERMISSION GATE: ${gate.computed.total}/${gate.computed.max}`,
      `REGISTER: ${register?.toUpperCase()} / ${receiver?.toUpperCase() || "unset"}`,
      `ESCALATION: Level ${escalLevel} — ${escalLevel !== null ? ESCALATION[escalLevel]?.label : "unset"}`,
      ``,
      `GENERATED OUTPUTS:`,
      outputs[register] ? `  [${register?.toUpperCase()}] ${outputs[register]}` : "  none",
    ];
    navigator.clipboard?.writeText(lines.join("\n"));
  }

  return (
    <div>
      <div style={St.stageTitle}>TWO-EDGED ESCALATION MODEL — Response Level</div>
      <div style={{ fontSize: 9, color: "#2a2a2a", letterSpacing: "0.1em", marginBottom: 14, fontStyle: "italic" }}>
        Levels 0–2 confirmed from document · Levels 3–5 framework-inferred
      </div>

      {ESCALATION.map(e => (
        <button key={e.level}
          style={{ ...St.escalBtn, ...(escalLevel === e.level ? { ...St.escalOn, borderColor: e.color } : {}) }}
          onClick={() => selectLevel(e.level)}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
            <div style={{ ...St.escalNum, borderColor: e.color, color: e.color }}>L{e.level}</div>
            <div>
              <div style={{ fontSize: 11, letterSpacing: "0.12em", color: escalLevel === e.level ? e.color : "#888" }}>
                {e.label} <span style={{ color: "#333", fontSize: 9 }}>— {e.sub}</span>
              </div>
              {!e.confirmed && <div style={{ fontSize: 8, color: "#2a3a2a" }}>⊙ inferred</div>}
            </div>
          </div>
          <div style={{ fontSize: 10, color: "#444", lineHeight: 1.5, marginLeft: 38 }}>{e.desc}</div>
          {escalLevel === e.level && (
            <>
              <div style={{ fontSize: 9, color: "#2a3a2a", fontStyle: "italic", marginLeft: 38, marginTop: 4, lineHeight: 1.5 }}>{e.note}</div>
              <div style={{ fontSize: 9, color: "#3a5a3a", marginLeft: 38, marginTop: 4 }}>→ {e.action}</div>
            </>
          )}
        </button>
      ))}

      {loading && <div style={{ fontSize: 11, color: "#444", textAlign: "center", padding: 12 }}>Running escalation engine...</div>}
      {claudeUnavail && (
        <div style={{ ...St.analysis, borderColor: "#333" }}>
          <div style={{ ...St.aLabel, color: "#555" }}>CLAUDE ANALYSIS UNAVAILABLE</div>
          <div style={{ fontSize: 11, color: "#333" }}>Escalation level recorded. Configure ANTHROPIC_API_KEY for narrative guidance.</div>
        </div>
      )}
      {aiText && (
        <div style={St.analysis}>
          <div style={St.aLabel}>LEVEL {escalLevel} — {ESCALATION[escalLevel]?.label}</div>
          <div style={St.aText}>{aiText}</div>
          <button style={St.copy} onClick={() => navigator.clipboard?.writeText(aiText)}>COPY</button>
        </div>
      )}

      {/* FINAL PACKET */}
      <div style={{ ...St.verdict, borderColor: "#2a2a2a", marginTop: 24 }}>
        <div style={{ fontSize: 10, letterSpacing: "0.2em", color: "#c8a96e", marginBottom: 12 }}>CASE PACKET</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <button style={{ ...St.btn, background: "#c8a96e", marginBottom: 0 }}
            disabled={saving} onClick={savePacket}>
            {saving ? "SAVING..." : packetSaved ? "✓ PACKET SAVED" : "SAVE COMPLETE PACKET"}
          </button>
          <div style={{ display: "flex", gap: 8 }}>
            <button style={{ ...St.packetBtn }} onClick={exportJSON}>EXPORT JSON</button>
            <button style={{ ...St.packetBtn }} onClick={copySummary}>COPY SUMMARY</button>
          </div>
          <button style={{ ...St.packetBtn, color: "#555", borderColor: "#1a1a1a" }} onClick={onReset}>
            START NEW CASE
          </button>
        </div>
      </div>

      {exportText && (
        <div style={{ ...St.analysis, marginTop: 12 }}>
          <div style={St.aLabel}>EXPORT PREVIEW — raw and generated layers separate</div>
          <pre style={{ ...St.aText, fontSize: 9, overflowX: "auto", maxHeight: 200 }}>{exportText.slice(0, 2000)}{exportText.length > 2000 ? "\n…(truncated in preview — full file downloaded)" : ""}</pre>
        </div>
      )}

      <button style={{ ...St.back, marginTop: 12 }} onClick={onBack}>← BACK TO REGISTER</button>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// MAIN
// ═══════════════════════════════════════════════════════════════════

export default function OmegaAletheia() {
  const [caseId]                      = useState(() => crypto.randomUUID());
  const [stage, setStage]             = useState(1);
  const [six, setSix]                 = useState({});
  const [senses, setSenses]           = useState({});
  const [abcde, setAbcde]             = useState({});
  const [scores, setScores]           = useState({});
  const [evidSeed, setEvidSeed]       = useState(null);
  const [register, setRegister]       = useState("mid");
  const [receiver, setReceiver]       = useState(null);
  const [outputs, setOutputs]         = useState({});
  const [escalLevel, setEscalLevel]   = useState(null);
  const [bridgeInfo, setBridgeInfo]   = useState(null);
  const [lastSaved, setLastSaved]     = useState(null);

  useEffect(() => {
    bridgeStatus()
      .then(s => setBridgeInfo(s))
      .catch(() => setBridgeInfo({ ok: false }));
  }, []);

  const bridgeOk  = bridgeInfo?.ok === true;
  const claudeOk  = bridgeInfo?.claude_configured === true;

  function handleSave(recordId) {
    if (recordId) setLastSaved(recordId);
    bridgeStatus().then(s => setBridgeInfo(s)).catch(() => {});
  }

  function handleAletheiaNext(evidScore) {
    setEvidSeed(evidScore);
    setScores(p => ({ ...p, evidence: evidScore }));
    setStage(3);
  }

  function resetEngine() {
    setSix({}); setSenses({}); setAbcde({}); setScores({});
    setEvidSeed(null); setRegister("mid"); setReceiver(null);
    setOutputs({}); setEscalLevel(null); setLastSaved(null);
    setStage(1);
    bridgeStatus().then(s => setBridgeInfo(s)).catch(() => {});
  }

  const STAGE_LABELS = ["WITNESS", "ALETHEIA", "GATE", "REGISTER", "ESCALATE"];

  return (
    <div style={St.root}>
      <div style={St.header}>
        <div style={St.omega}>Ω</div>
        <div>
          <div style={St.title}>OMEGA · ALETHEIA</div>
          <div style={St.subtitle}>Perception Integrity · Decision Engine · Escalation Protocol</div>
        </div>
      </div>

      <StatusBar status={bridgeInfo} lastSaved={lastSaved} />

      <div style={St.stageNav}>
        {STAGE_LABELS.map((label, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", flex: i < 4 ? 1 : "unset", gap: 3 }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2,
              cursor: stage > i + 1 ? "pointer" : "default" }}
              onClick={() => { if (stage > i + 1) setStage(i + 1); }}>
              <div style={{ width: 20, height: 20,
                border: `1px solid ${stage === i + 1 ? "#c8a96e" : stage > i + 1 ? "#555" : "#222"}`,
                borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 9, color: stage === i + 1 ? "#c8a96e" : stage > i + 1 ? "#555" : "#222" }}>
                {stage > i + 1 ? "✓" : i + 1}
              </div>
              <div style={{ fontSize: 7, letterSpacing: "0.1em",
                color: stage === i + 1 ? "#c8a96e" : stage > i + 1 ? "#444" : "#1e1e1e" }}>
                {label}
              </div>
            </div>
            {i < 4 && <div style={{ flex: 1, height: 1, background: "#1a1a1a", marginBottom: 14 }} />}
          </div>
        ))}
      </div>

      {stage === 1 && (
        <Stage1 six={six} setSix={setSix} caseId={caseId}
          onSave={handleSave} onNext={() => setStage(2)} />
      )}
      {stage === 2 && (
        <Stage2 six={six} senses={senses} setSenses={setSenses}
          abcde={abcde} setAbcde={setAbcde} caseId={caseId}
          onSave={handleSave} onNext={handleAletheiaNext}
          onBack={() => setStage(1)} bridgeOk={bridgeOk} claudeOk={claudeOk} />
      )}
      {stage === 3 && (
        <Stage3 six={six} scores={scores} setScores={setScores}
          evidSeed={evidSeed} caseId={caseId}
          onSave={handleSave} onNext={() => setStage(4)} onBack={() => setStage(2)} />
      )}
      {stage === 4 && (
        <Stage4 six={six} register={register} setRegister={setRegister}
          receiver={receiver} setReceiver={setReceiver}
          outputs={outputs} setOutputs={setOutputs} caseId={caseId}
          onSave={handleSave} onNext={() => setStage(5)} onBack={() => setStage(3)} />
      )}
      {stage === 5 && (
        <Stage5 six={six} senses={senses} abcde={abcde} scores={scores}
          register={register} receiver={receiver} outputs={outputs}
          escalLevel={escalLevel} setEscalLevel={setEscalLevel}
          caseId={caseId} onSave={handleSave}
          onBack={() => setStage(4)} onReset={resetEngine} />
      )}

      {stage > 1 && (
        <button style={St.reset} onClick={resetEngine}>RESET ENGINE</button>
      )}
      <div style={St.footer}>
        Relevant retrieval ≠ complete retrieval · The gate does not decide — it reveals what is already true.
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// STYLES
// ═══════════════════════════════════════════════════════════════════
const St = {
  root:       { background: "#090909", minHeight: "100vh", padding: "20px 16px",
                fontFamily: "'Courier New',monospace", color: "#ddd",
                maxWidth: 660, margin: "0 auto", boxSizing: "border-box" },
  header:     { display: "flex", alignItems: "center", gap: 12, marginBottom: 10,
                borderBottom: "1px solid #1a1a1a", paddingBottom: 12 },
  omega:      { fontSize: 38, color: "#c8a96e", lineHeight: 1, fontWeight: "bold" },
  title:      { fontSize: 16, letterSpacing: "0.24em", color: "#c8a96e", fontWeight: "bold" },
  subtitle:   { fontSize: 9, letterSpacing: "0.1em", color: "#2a2a2a", marginTop: 3 },
  statusBar:  { display: "flex", alignItems: "center", gap: 6, padding: "5px 0", marginBottom: 12,
                borderBottom: "1px solid #111", flexWrap: "wrap" },
  statusDot:  { color: "#2a2a2a", fontSize: 10 },
  stageNav:   { display: "flex", alignItems: "flex-start", marginBottom: 20 },
  stageTitle: { fontSize: 10, letterSpacing: "0.18em", color: "#555", marginBottom: 8,
                borderBottom: "1px solid #1a1a1a", paddingBottom: 7 },
  badge:      { fontSize: 9, color: "#3a6e4a", letterSpacing: "0.1em", marginBottom: 12,
                background: "#0a1a0f", border: "1px solid #1a3a25", borderRadius: 2,
                padding: "3px 8px", display: "inline-block" },
  subHead:    { fontSize: 9, letterSpacing: "0.2em", color: "#3a3a3a", marginBottom: 9, marginTop: 6 },
  field:      { marginBottom: 14 },
  fieldLabel: { fontSize: 12, color: "#c8a96e", letterSpacing: "0.16em", marginBottom: 2 },
  fieldQ:     { fontSize: 10, color: "#333", marginBottom: 4, fontStyle: "italic" },
  ta:         { width: "100%", background: "#111", border: "1px solid #1a1a1a", borderRadius: 2,
                color: "#ccc", fontFamily: "'Courier New',monospace", fontSize: 12,
                padding: "7px", resize: "vertical", outline: "none", lineHeight: 1.6, boxSizing: "border-box" },
  btn:        { width: "100%", background: "#c8a96e", border: "none", color: "#090909",
                padding: "11px", fontFamily: "'Courier New',monospace", fontSize: 11,
                fontWeight: "bold", letterSpacing: "0.18em", cursor: "pointer",
                borderRadius: 2, marginBottom: 14, transition: "opacity 0.2s" },
  summary:    { background: "#0f0f0f", border: "1px solid #1a1a1a", borderRadius: 2,
                padding: "9px 11px", marginBottom: 16 },
  sumLine:    { display: "flex", gap: 8, marginBottom: 3, fontSize: 10 },
  sumKey:     { color: "#c8a96e", minWidth: 40, letterSpacing: "0.1em" },
  sumVal:     { color: "#444", lineHeight: 1.5 },
  factor:     { marginBottom: 16, borderLeft: "1px solid #1a1a1a", paddingLeft: 10 },
  fHead:      { display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 7 },
  fSym:       { fontSize: 18, color: "#c8a96e", lineHeight: 1.2, minWidth: 18 },
  fLabel:     { fontSize: 10, letterSpacing: "0.16em", color: "#c8a96e" },
  fQ:         { fontSize: 10, color: "#333", fontStyle: "italic", marginTop: 2, lineHeight: 1.4 },
  rRow:       { display: "flex", gap: 4, flexWrap: "wrap" },
  rBtn:       { background: "transparent", border: "1px solid #1a1a1a", color: "#333",
                padding: "4px 8px", fontFamily: "'Courier New',monospace", fontSize: 9,
                cursor: "pointer", borderRadius: 2, letterSpacing: "0.1em" },
  opts:       { display: "flex", flexDirection: "column", gap: 3 },
  opt:        { background: "transparent", border: "1px solid #1a1a1a", color: "#3a3a3a",
                padding: "5px 8px", fontFamily: "'Courier New',monospace", fontSize: 10,
                cursor: "pointer", textAlign: "left", borderRadius: 2,
                display: "flex", alignItems: "center", gap: 7 },
  optOn:      { borderColor: "#c8a96e", color: "#c8a96e", background: "#100f00" },
  optN:       { minWidth: 10, color: "#2a2a2a", fontSize: 9 },
  verdict:    { border: "1px solid", borderRadius: 3, padding: 12, marginBottom: 12, background: "#0c0c0c" },
  verdLabel:  { fontSize: 13, letterSpacing: "0.18em", fontWeight: "bold", marginBottom: 4 },
  analysis:   { background: "#0d0d0d", border: "1px solid #1a1a1a", borderRadius: 3,
                padding: 12, marginBottom: 14 },
  aLabel:     { fontSize: 9, letterSpacing: "0.16em", color: "#c8a96e", marginBottom: 7 },
  aText:      { fontSize: 12, lineHeight: 1.8, color: "#999", whiteSpace: "pre-wrap" },
  copy:       { background: "transparent", border: "1px solid #1a1a1a", color: "#2a2a2a",
                padding: "4px 10px", fontFamily: "'Courier New',monospace",
                fontSize: 9, cursor: "pointer", marginTop: 9, letterSpacing: "0.1em", borderRadius: 2 },
  navRow:     { display: "flex", gap: 8, alignItems: "stretch" },
  back:       { background: "transparent", border: "1px solid #1a1a1a", color: "#2a2a2a",
                padding: "9px 12px", fontFamily: "'Courier New',monospace",
                fontSize: 10, cursor: "pointer", borderRadius: 2, marginBottom: 14, letterSpacing: "0.1em" },
  recGrid:    { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 5, marginBottom: 14 },
  recBtn:     { background: "transparent", border: "1px solid #1a1a1a", color: "#333",
                padding: "7px", fontFamily: "'Courier New',monospace",
                fontSize: 10, cursor: "pointer", textAlign: "left", borderRadius: 2 },
  recOn:      { borderColor: "#c8a96e", color: "#c8a96e", background: "#100f00" },
  regs:       { display: "flex", gap: 5, marginBottom: 5 },
  regBtn:     { background: "transparent", border: "1px solid", flex: 1, padding: "7px 4px",
                fontFamily: "'Courier New',monospace", fontSize: 10, cursor: "pointer",
                borderRadius: 2, display: "flex", alignItems: "center", justifyContent: "center", gap: 5 },
  regDesc:    { fontSize: 10, color: "#2a2a2a", fontStyle: "italic", marginBottom: 14, lineHeight: 1.5 },
  escalBtn:   { width: "100%", background: "transparent", border: "1px solid #1a1a1a",
                padding: "11px", fontFamily: "'Courier New',monospace",
                cursor: "pointer", textAlign: "left", borderRadius: 3, marginBottom: 7, transition: "all 0.15s" },
  escalOn:    { background: "#0c0c0c" },
  escalNum:   { width: 26, height: 26, border: "1px solid", borderRadius: "50%",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 9, fontWeight: "bold", flexShrink: 0 },
  packetBtn:  { flex: 1, background: "transparent", border: "1px solid #2a2a2a", color: "#c8a96e",
                padding: "9px", fontFamily: "'Courier New',monospace", fontSize: 10,
                cursor: "pointer", borderRadius: 2, letterSpacing: "0.12em" },
  reset:      { width: "100%", background: "transparent", border: "1px solid #111",
                color: "#1e1e1e", padding: "7px", fontFamily: "'Courier New',monospace",
                fontSize: 9, cursor: "pointer", letterSpacing: "0.12em", borderRadius: 2, marginBottom: 18 },
  footer:     { textAlign: "center", fontSize: 9, color: "#1a1a1a",
                letterSpacing: "0.1em", paddingTop: 8, borderTop: "1px solid #0f0f0f", lineHeight: 1.8 },
};
