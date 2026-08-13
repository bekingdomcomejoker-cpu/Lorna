const BLOCKING = new Set(["MISSING"]);
const UNRESOLVED = new Set(["UNVERIFIED", "MISSING"]);

export function hardGateVerdict({ senses = {}, abcde = {}, contradictions = [] }) {
  const abcdeValues = Object.values(abcde);
  const senseValues = Object.values(senses);

  if (abcdeValues.some((value) => BLOCKING.has(value))) {
    return {
      label: "HOLD",
      movement: "DRY_RUN_ONLY",
      reason: "At least one required ABCDE gate is missing.",
    };
  }

  if (contradictions.length > 0) {
    return {
      label: "HOLD",
      movement: "DRY_RUN_ONLY",
      reason: "Contradictions remain unresolved.",
    };
  }

  if (abcdeValues.some((value) => UNRESOLVED.has(value))) {
    return {
      label: "UNKNOWN",
      movement: "NO_IRREVERSIBLE_ACTION",
      reason: "One or more ABCDE gates remain unresolved.",
    };
  }

  if (senseValues.includes("MISSING")) {
    return {
      label: "PARTIAL",
      movement: "REVERSIBLE_ONLY",
      reason: "A sensory evidence channel is missing.",
    };
  }

  return {
    label: "VERIFIED",
    movement: "GATE_ELIGIBLE",
    reason: "All required gates are confirmed and no contradiction is open.",
  };
}
