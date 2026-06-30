from typing import List, Dict, Any, Tuple
from backend.shared.logger import get_logger

logger = get_logger(__name__)


def validate_traceability_matrix(traceability_matrix: List[Dict[str, Any]], requirements: List[Dict[str, Any]], epics: List[Dict[str, Any]], features: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Validate that traceability entries reference existing requirement/epic/feature ids.
    Returns (normalized_matrix, issues)
    """
    issues: List[str] = []
    req_ids = {r.get("id") for r in requirements}
    epic_ids = {e.get("id") for e in epics}
    feat_ids = {f.get("id") for f in features}

    normalized = []
    for entry in traceability_matrix:
        rid = entry.get("requirement_id")
        eid = entry.get("epic_id")
        fid = entry.get("feature_id")

        if rid not in req_ids:
            issues.append(f"Missing requirement id in traceability: {rid}")
        if eid and eid not in epic_ids:
            issues.append(f"Missing epic id in traceability: {eid}")
        if fid and fid not in feat_ids:
            issues.append(f"Missing feature id in traceability: {fid}")

        # Ensure dependencies key exists
        deps = entry.get("dependencies") or []
        normalized.append({
            "requirement_id": rid,
            "epic_id": eid,
            "feature_id": fid,
            "dependencies": deps
        })

    if issues:
        logger.warning("Traceability matrix validation found issues: %s", issues)

    return normalized, issues


def validate_agent_outputs(agent1_output: Dict[str, Any], agent2_output: Dict[str, Any]) -> List[str]:
    """Quick validation checks on agent outputs. Returns list of issues found.
    """
    issues: List[str] = []

    if not agent1_output:
        issues.append("Agent-1 output missing")
    else:
        if "primary_input" not in agent1_output:
            issues.append("Agent-1 primary_input missing")
        if "validation_context" not in agent1_output:
            issues.append("Agent-1 validation_context missing")

    if not agent2_output:
        issues.append("Agent-2 output missing")
    else:
        if "epics" not in agent2_output:
            issues.append("Agent-2 epics missing")
        if "features" not in agent2_output:
            issues.append("Agent-2 features missing")

    if issues:
        logger.warning("Agent outputs validation issues: %s", issues)

    return issues
