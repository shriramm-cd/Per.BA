import pytest
from backend.orchestrator.router import route_after_agent1, route_after_validation
from backend.orchestrator.retry_handler import RetryHandler
from backend.shared.exceptions import MaxRetriesError

def test_router_confidence_pass():
    """
    Asserts that acceptable confidence scores route directly to epic planning.
    """
    state = {
        "confidence_score": 0.85,
        "retry_count": 0,
        "max_retries": 3
    }
    next_node = route_after_agent1(state)
    assert next_node == "agent2_node"

def test_router_confidence_fail():
    """
    Asserts that confidence scores below 0.75 trigger retry node.
    """
    state = {
        "confidence_score": 0.60,
        "retry_count": 0,
        "max_retries": 3
    }
    next_node = route_after_agent1(state)
    assert next_node == "retry_node"

def test_retry_count_exhaustion():
    """
    Checks that the retry handler stops when limit is reached.
    """
    state = {
        "confidence_score": 0.60,
        "retry_count": 3,
        "max_retries": 3
    }
    with pytest.raises(MaxRetriesError):
        RetryHandler.inspect_and_increment(state)

# INTEGRATION NOTE
# Graph edges rely on router outputs. Ensure target node strings match.
