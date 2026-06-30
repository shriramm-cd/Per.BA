from typing import Dict, Any
from backend.shared.exceptions import MaxRetriesError
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class RetryHandler:
    """
    Manages low confidence retry logic loops inside LangGraph flow.
    """
    @staticmethod
    def inspect_and_increment(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Increments retry count if confidence score falls below required threshold.
        Raises MaxRetriesError if max retries threshold is breached.
        """
        confidence = state.get("confidence_score", 1.0)
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)

        logger.info(f"Checking quality limits: confidence={confidence}, retry={retry_count}/{max_retries}")

        if confidence < 0.75:
            if retry_count >= max_retries:
                logger.error(f"Execution halted. Confidence ({confidence}) below 0.75 after {retry_count} retries.")
                raise MaxRetriesError(f"Failed to generate requirements with sufficient confidence after {retry_count} retries.")
            
            # Increment retry counter
            new_retry_count = retry_count + 1
            logger.warning(f"Confidence score {confidence} is below threshold (0.75). Incrementing retry counter to {new_retry_count}.")
            state["retry_count"] = new_retry_count
            state["status"] = "RETRY"
        else:
            state["status"] = "VERIFIED"

        return state

# INTEGRATION NOTE
# High level routing components invoke RetryHandler helper methods.
# Keep retry state increments saved inside GraphState.
