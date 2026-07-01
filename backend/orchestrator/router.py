from typing import Dict, Any
from backend.orchestrator.state import GraphState
from backend.shared.logger import get_logger

logger = get_logger(__name__)

def route_after_agent1(state: GraphState) -> str:
    """
    Determines if requirement parsing needs another attempt due to low confidence.
    """
    confidence = state.get("confidence_score", 1.0)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if confidence < 0.75:
        if retry_count < max_retries:
            logger.info(f"Routing logic: Low confidence ({confidence}). Directing to retry loop.")
            return "retry_node"
        else:
            logger.warning("Routing logic: Low confidence, retry limit reached. Proceeding to Agent 2 with warning.")
            return "agent2_node"
    
    logger.info("Routing logic: Confidence acceptable. Proceeding to Agent 2.")
    return "agent2_node"

def route_after_validation(state: GraphState) -> str:
    """
    Determines if validation results are sufficient to export, or if human review is needed,
    or if we should trigger the automatic rework loop.
    """
    is_approved = state.get("is_approved", False)
    human_approved = state.get("human_approved", False)

    if is_approved or human_approved:
        logger.info("Routing logic: Approved. Directing to Export.")
        return "export_node"
    
    validation_results = state.get("validation_results", {})
    decision = None
    if isinstance(validation_results, dict):
        summary = validation_results.get("summary")
        if isinstance(summary, dict):
            decision = summary.get("decision")
        if not decision:
            decision = validation_results.get("decision")
            
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if decision == "REWORK":
        if retry_count < max_retries:
            logger.info(f"Routing logic: Validation failed (REWORK). Attempt {retry_count + 1} of {max_retries}. Directing to automatic rework loop.")
            return "automatic_revision_node"
        else:
            logger.warning(f"Routing logic: Retry limit ({max_retries}) exceeded. Directing to Human Review.")
            return "human_review_node"
    
    logger.info("Routing logic: Directing to Human Review.")
    return "human_review_node"

# INTEGRATION NOTE
# Conditional edges are mapped to these string identifiers.
# Maintain naming consistency when compiling the StateGraph in graph.py.
