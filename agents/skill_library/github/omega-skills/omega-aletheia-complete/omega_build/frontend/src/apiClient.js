const DEFAULT_BASE = "";

async function parseResponse(response) {
  let payload;
  try {
    payload = await response.json();
  } catch {
    payload = { ok: false, error: `HTTP ${response.status}` };
  }

  if (!response.ok || payload.ok === false) {
    const error = new Error(payload.error || `HTTP ${response.status}`);
    error.payload = payload;
    throw error;
  }
  return payload;
}

export async function bridgeStatus() {
  const response = await fetch(`${DEFAULT_BASE}/api/status`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  return parseResponse(response);
}

export async function callClaudeLocal({
  prompt,
  stage,
  context = {},
  system = "",
  maxTokens = 1200,
}) {
  const response = await fetch(`${DEFAULT_BASE}/api/claude`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      stage,
      context,
      system,
      max_tokens: maxTokens,
    }),
  });

  const payload = await parseResponse(response);
  return payload.text;
}

export async function saveAuditRecord(record) {
  const response = await fetch(`${DEFAULT_BASE}/api/records`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(record),
  });
  return parseResponse(response);
}

export async function loadLedger(limit = 50) {
  const response = await fetch(
    `${DEFAULT_BASE}/api/ledger?limit=${encodeURIComponent(limit)}`,
    { headers: { Accept: "application/json" } }
  );
  return parseResponse(response);
}
