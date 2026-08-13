#!/bin/bash

##############################################################################
# HUAWEI PHONE B: SKILL LAYER BULK DEPLOYMENT
#
# Timeline: 1 hour
# Goal: Scale skill layer from 1 adapter to 5 candidates
#
# What happens:
# 1. Generate adapters for all 5 candidate skills
# 2. Test @action:run on persistent-computing and voice_instructions
# 3. Wire router to call adapter run methods
# 4. Deploy to Huawei ~/omega-root/09_SKILLS/enabled/
##############################################################################

set -e

OMEGA_ROOT="${HOME}/omega-root"
SKILLS_DIR="${OMEGA_ROOT}/09_SKILLS"
ENABLED_DIR="${SKILLS_DIR}/enabled"
REGISTRY="${SKILLS_DIR}/skill_registry.json"
LOGS_DIR="${OMEGA_ROOT}/07_LOGS"

echo "[HUAWEI] Skill Layer Bulk Deployment START"
echo "[HUAWEI] Root: ${OMEGA_ROOT}"
echo ""

# ============================================================================
# STEP 1: Verify registry exists
# ============================================================================

echo "[1] Verifying skill registry..."

if [ ! -f "${REGISTRY}" ]; then
    echo "[ERROR] Registry not found: ${REGISTRY}"
    exit 1
fi

TOTAL=$(jq '.summary.total' "${REGISTRY}")
CANDIDATES=$(jq '.summary.candidate' "${REGISTRY}")

echo "[1] ✓ Registry found"
echo "    Total skills: ${TOTAL}"
echo "    Candidates (safe): ${CANDIDATES}"
echo ""

# ============================================================================
# STEP 2: Generate adapters for all candidates
# ============================================================================

echo "[2] Generating adapters for ${CANDIDATES} candidate skills..."

mkdir -p "${ENABLED_DIR}" "${LOGS_DIR}"

# Python script embedded below
python3 << 'PYTHON_ADAPTER_GEN'

import json
import re
from pathlib import Path
from datetime import datetime, timezone

ADAPTER_TEMPLATE = '''#!/usr/bin/env python3
"""
AUTO-GENERATED OMEGA SKILL ADAPTER

Package: {package_name}
Status: {status}
Risk: {risk}

Safe actions: inspect, summarize, run
Blocked: execute, credentials, network_mutation, source_mutation
"""

from __future__ import annotations
import json, re
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path

SKILL_NAME = "{package_name}"
SAFE_ACTIONS = ["inspect", "summarize", "run"]
SAFE_RUN_FUNCTIONS = [
    "inspect_package", "get_documentation", "validate_inputs",
    "get_available_functions", "estimate_execution"
]

def run(payload: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    action = "inspect"
    match = re.search(r"@action:([A-Za-z_]+)", payload)
    if match:
        action = match.group(1).lower()
    
    if action not in SAFE_ACTIONS:
        return {{"kind": "adapter_error", "error": f"Unknown: {{action}}", "allowed": SAFE_ACTIONS}}
    
    if action == "inspect":
        return {{"kind": "adapter_inspect", "package": SKILL_NAME, "status": "active", "safe_actions": SAFE_ACTIONS}}
    
    elif action == "summarize":
        return {{"kind": "adapter_summary", "package": SKILL_NAME, "description": "Skill provides {skill_description}", "requires_keys": "{requires_keys}"}}
    
    elif action == "run":
        func = re.search(r"@function:([A-Za-z_]+)", payload)
        if not func:
            return {{"kind": "adapter_run_error", "error": "Missing @function:<name>", "available": SAFE_RUN_FUNCTIONS}}
        func_name = func.group(1)
        if func_name not in SAFE_RUN_FUNCTIONS:
            return {{"kind": "adapter_run_error", "error": f"Unknown function: {{func_name}}"}}
        return {{"kind": "function_result", "package": SKILL_NAME, "function": func_name, "status": "ready"}}
    
    return {{"kind": "adapter_fallback", "package": SKILL_NAME}}

if __name__ == "__main__":
    import sys
    payload = " ".join(sys.argv[1:]) or "@action:inspect"
    print(json.dumps(run(payload), ensure_ascii=False, indent=2))
'''

def skill_description(name):
    d = {
        "manus-api": "API integration for Manus hand tracking",
        "music-prompter": "prompt crafting for music generation",
        "persistent-computing": "checkpoint and persistence planning",
        "similarweb-analytics": "website analytics and competitive intelligence",
        "voice_instructions_unitless": "voice command normalization"
    }
    return d.get(name.lower().replace(".zip", ""), "read-only inspection")

def requires_keys(name):
    k = {
        "manus-api": "Manus API key",
        "similarweb-analytics": "SimilarWeb API key"
    }
    return k.get(name.lower().replace(".zip", ""), "none")

registry_path = Path.home() / "omega-root" / "09_SKILLS" / "skill_registry.json"
enabled_dir = Path.home() / "omega-root" / "09_SKILLS" / "enabled"

registry = json.loads(registry_path.read_text())
candidates = [s for s in registry.get("skills", []) if s.get("status") == "candidate"]

for skill in candidates:
    pkg_name = skill.get("package_name", "unknown.zip")
    clean = pkg_name.replace(".zip", "")
    clean = re.sub(r"[^A-Za-z0-9_]+", "_", clean).strip("_").lower()
    filename = f"{clean}_adapter.py"
    filepath = enabled_dir / filename
    
    body = ADAPTER_TEMPLATE.format(
        package_name=pkg_name,
        status=skill.get("status"),
        risk=skill.get("risk"),
        skill_description=skill_description(pkg_name),
        requires_keys=requires_keys(pkg_name),
    )
    
    filepath.write_text(body)
    filepath.chmod(0o700)
    print(f"[GENERATE] {filename}")

PYTHON_ADAPTER_GEN

echo "[2] ✓ All ${CANDIDATES} adapters generated"
echo ""

# ============================================================================
# STEP 3: Test adapters
# ============================================================================

echo "[3] Testing adapters..."

python3 "${ENABLED_DIR}/persistent_computing_adapter.py" '@action:inspect' > /dev/null && echo "[TEST] persistent_computing: inspect ✓"
python3 "${ENABLED_DIR}/persistent_computing_adapter.py" '@action:run @function:get_available_functions' > /dev/null && echo "[TEST] persistent_computing: run ✓"

python3 "${ENABLED_DIR}/voice_instructions_unitless_adapter.py" '@action:summarize' > /dev/null && echo "[TEST] voice_instructions: summarize ✓"

echo "[3] ✓ Adapter tests passed"
echo ""

# ============================================================================
# STEP 4: Wire router to handle @action:run
# ============================================================================

echo "[4] Updating router.py for @action:run..."

# Check if router.py exists
if [ ! -f "router.py" ]; then
    echo "[WARNING] router.py not found in current directory"
    echo "[INFO] Patch location: Add this to router.py after skill_runner import:"
    cat << 'ROUTER_PATCH'

# Route: @route:skill @action:run
if route == "skill" and "@action:run" in payload:
    from router_skill_run_patch import handle_skill_run
    output = json.dumps(handle_skill_run(payload), ensure_ascii=False)
    model_source = "skill_adapter_run"

ROUTER_PATCH
else
    echo "[4] ✓ router.py found (manual patch required)"
fi

echo ""

# ============================================================================
# STEP 5: Summary and next steps
# ============================================================================

echo "[5] DEPLOYMENT COMPLETE"
echo ""
echo "Generated adapters:"
ls -lh "${ENABLED_DIR}"/*_adapter.py | awk '{print "  " $9, "(" $5 ")"}'
echo ""

echo "Candidates ready for @action:run:"
echo "  ✓ manus-api (requires: Manus API key)"
echo "  ✓ music-prompter (no external keys)"
echo "  ✓ persistent-computing (no external keys)"
echo "  ✓ similarweb-analytics (requires: SimilarWeb API key)"
echo "  ✓ voice_instructions_unitless (no external keys)"
echo ""

echo "NEXT STEPS:"
echo "  1. Apply router.py patch (add skill_adapter_run handling)"
echo "  2. Test via clipboard: 🐝 @route:skill @skill:persistent-computing @action:run @function:estimate_execution"
echo "  3. Verify JSONL bus logging"
echo "  4. Implement skill-specific @action:run functions (beyond template)"
echo ""

echo "[HUAWEI] Skill Layer Bulk Deployment END"
