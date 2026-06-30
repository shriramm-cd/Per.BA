import pytest
from unittest.mock import AsyncMock, patch
from backend.validation_export.schemas import (
    ValidationContext, 
    ValidationExecutionSummary, 
    DecisionOutcome, 
    Severity,
    ValidationFinding
)
from backend.validation_export.services.graph_engine import GraphEngine
from backend.validation_export.services.embedding_service import EmbeddingService
from backend.validation_export.decision_rules import DecisionRulesEngine
from backend.validation_export.revision_engine import RevisionEngine
from backend.validation_export.validators.structural import StructuralValidator
from backend.validation_export.validators.acceptance_criteria import AcceptanceCriteriaValidator
from backend.validation_export.validators.dependency import DependencyValidator

# --- Graph Engine Tests ---

def test_graph_engine_cycle_detection():
    graph = GraphEngine()
    graph.add_node("ST-001", "Story")
    graph.add_node("ST-002", "Story")
    graph.add_node("ST-003", "Story")

    # ST-001 -> ST-002 -> ST-003 -> ST-001 (Cycle)
    graph.add_edge("ST-001", "ST-002")
    graph.add_edge("ST-002", "ST-003")
    graph.add_edge("ST-003", "ST-001")

    assert graph.has_cycle() is True
    cycles = graph.find_cycles()
    assert len(cycles) > 0

def test_graph_engine_traceability_chain():
    graph = GraphEngine()
    graph.add_node("Actor-1", "Actor")
    graph.add_node("REQ-1", "Requirement")
    graph.add_node("EP-1", "Epic")
    graph.add_node("FEAT-1", "Feature")
    graph.add_node("ST-1", "Story")
    graph.add_node("AC-1", "AcceptanceCriteria")

    # Connect them
    graph.add_edge("Actor-1", "REQ-1")
    graph.add_edge("REQ-1", "EP-1")
    graph.add_edge("EP-1", "FEAT-1")
    graph.add_edge("FEAT-1", "ST-1")
    graph.add_edge("ST-1", "AC-1")

    path = graph.verify_traceability_chain("AC-1")
    assert len(path) == 6
    assert path[0] == "AC-1"
    assert path[-1] == "Actor-1"

# --- Embedding Service Tests ---

@pytest.mark.asyncio
async def test_embedding_service_similarity():
    service = EmbeddingService()
    text1 = "Apply for a credit card online"
    text2 = "Submit credit card application through the web portal"
    text3 = "Weather is nice today in San Francisco"

    sim1 = await service.calculate_similarity(text1, text2)
    sim2 = await service.calculate_similarity(text1, text3)

    assert sim1 > sim2
    if service.gemini_available:
        assert sim1 > 0.5
        assert sim2 < 0.3
    else:
        assert sim1 > 0.35
        assert sim2 < 0.3

# --- Decision Rules Engine Tests ---

def test_decision_rules_engine_pass():
    engine = DecisionRulesEngine()
    summary = ValidationExecutionSummary(
        job_id="TEST-JOB",
        validators_passed=["structural_validator", "traceability_validator", "coverage_validator", "business_rules_validator", "dependency_validator", "acceptance_criteria_validator", "invest_validator", "semantic_validator", "hallucination_validator", "consistency_validator", "duplicate_validator", "technical_validator"],
        validators_failed=[],
        critical_count=0,
        major_count=0,
        minor_count=1,
        info_count=1,
        execution_time=100.0,
        decision=DecisionOutcome.PASS
    )
    decision = engine.evaluate(summary, coverage_pct=98.0, retry_count=0)
    assert decision == DecisionOutcome.PASS

def test_decision_rules_engine_rework():
    engine = DecisionRulesEngine()
    # Scenario 1: Hallucination validator failed
    summary_fail = ValidationExecutionSummary(
        job_id="TEST-JOB",
        validators_passed=[],
        validators_failed=["hallucination_validator"],
        critical_count=1,
        major_count=0,
        minor_count=0,
        info_count=0,
        execution_time=100.0,
        decision=DecisionOutcome.PASS
    )
    decision = engine.evaluate(summary_fail, coverage_pct=98.0, retry_count=0)
    assert decision == DecisionOutcome.REWORK

    # Scenario 2: Low coverage
    summary_low_cov = ValidationExecutionSummary(
        job_id="TEST-JOB",
        validators_passed=[],
        validators_failed=[],
        critical_count=0,
        major_count=0,
        minor_count=0,
        info_count=0,
        execution_time=100.0,
        decision=DecisionOutcome.PASS
    )
    decision = engine.evaluate(summary_low_cov, coverage_pct=90.0, retry_count=0)
    assert decision == DecisionOutcome.REWORK

# --- Validator Tests ---

@pytest.mark.asyncio
async def test_structural_validator():
    validator = StructuralValidator()
    
    # Missing title and epic_id
    context = ValidationContext(
        requirements=[], epics=[], features=[],
        stories=[{
            "id": "ST-001",
            "user_story_text": "As a user I want to login so that I can see my dashboard",
            "acceptance_criteria": ["Given user is on login page..."],
            "feature_id": "FEAT-1",
            "trace_mappings": ["REQ-1"]
        }],
        business_rules=[], acceptance_criteria=[], definition_of_done={},
        dependencies=[], actors=[], systems=[], metadata={}
    )
    
    result = await validator.validate(context)
    assert result.status == "FAILED"
    assert any("title" in f.description for f in result.findings)
    assert any("epic_id" in f.description for f in result.findings)

@pytest.mark.asyncio
async def test_acceptance_criteria_validator():
    validator = AcceptanceCriteriaValidator()
    
    # Non-Gherkin and missing negative scenario
    context = ValidationContext(
        requirements=[], epics=[], features=[],
        stories=[{
            "id": "ST-001",
            "title": "Login",
            "user_story_text": "As a user...",
            "acceptance_criteria": ["User logs in successfully"],
            "epic_id": "EP-1",
            "feature_id": "FEAT-1",
            "trace_mappings": ["REQ-1"]
        }],
        business_rules=[], acceptance_criteria=[], definition_of_done={},
        dependencies=[], actors=[], systems=[], metadata={}
    )
    
    result = await validator.validate(context)
    assert result.status == "FAILED"
    assert any("Gherkin" in f.title for f in result.findings)
    assert any("Negative Scenario" in f.title for f in result.findings)
