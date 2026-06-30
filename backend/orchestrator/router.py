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
            logger.error("Routing logic: Low confidence, retry limit exceeded. Routing to failure.")
            return "fail_node"
    
    logger.info("Routing logic: Confidence acceptable. Proceeding to Agent 2.")
    return "agent2_node"

def route_after_validation(state: GraphState) -> str:
    """
    Determines if validation results are sufficient to export, or if human review is needed.
    """
    is_approved = state.get("is_approved", False)
    human_approved = state.get("human_approved", False)

    if is_approved or human_approved:
        logger.info("Routing logic: Approved. Directing to Export.")
        return "export_node"
    
    logger.info("Routing logic: Quality threshold not met. Directing to Human Review.")
    return "human_review_node"

# INTEGRATION NOTE
# Conditional edges are mapped to these string identifiers.
# Maintain naming consistency when compiling the StateGraph in graph.py.
