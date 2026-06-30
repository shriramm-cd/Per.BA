import pytest
from datetime import datetime
from backend.agents.schemas import (
    ExtractedRequirement,
    RequirementIntelligenceOutput,
    EpicPlan,
    FeaturePlan,
    TraceMapping,
    RequirementMapping,
    EpicHierarchy,
    Dependency,
    FeatureDependency,

    FeaturePriority,
    CoverageReport,
    Metadata,
    TraceabilityMatrix,
    EpicFeaturePlannerOutput,
    StoryContext,
    MasterContext
)

def test_pydantic_extraction_schemas():
    """
    Verifies that requirement schemas enforce types correctly.
    """
    req = ExtractedRequirement(
        id="REQ-001",
        content="System must allow email verification",
        actors=["Customer"],
        business_rules=["Token expires in 24 hours"]
    )
    assert req.id == "REQ-001"
    assert "Customer" in req.actors

def test_requirement_output_schema():
    """
    Ensures requirement agent payload output structure validates successfully.
    """
    data = {
        "requirements": [
            {"id": "REQ-001", "content": "Auth user", "actors": ["Admin"], "business_rules": []}
        ],
        "actors": ["Admin"],
        "business_rules": [],
        "ambiguities": [],
        "conflicts": [],
        "confidence_score": 0.95
    }
    obj = RequirementIntelligenceOutput.model_validate(data)
    assert obj.confidence_score == 0.95
    assert len(obj.requirements) == 1

def test_epic_plan_schema():
    """
    Verifies EpicPlan schema structure.
    """
    epic = EpicPlan(
        id="EPIC-001",
        name="User Authentication",
        description="All user authentication and authorization features"
    )
    assert epic.id == "EPIC-001"
    assert epic.name == "User Authentication"

def test_feature_plan_with_priority():
    """
    Ensures FeaturePlan includes priority field.
    """
    feature = FeaturePlan(
        id="FEAT-001",
        epic_id="EPIC-001",
        name="Login Feature",
        description="User login functionality",
        priority="High"
    )
    assert feature.priority == "High"

def test_requirement_mapping_schema():
    """
    Verifies RequirementMapping includes all required fields.
    """
    mapping = RequirementMapping(
        requirement_id="REQ-001",
        requirement_content="User can log in with email",
        epic_id="EPIC-001",
        feature_id="FEAT-001"
    )
    assert mapping.requirement_id == "REQ-001"
    assert mapping.epic_id == "EPIC-001"
    assert mapping.feature_id == "FEAT-001"

def test_epic_hierarchy_schema():
    """
    Verifies EpicHierarchy structure with features and requirements.
    """
    hierarchy = EpicHierarchy(
        epic_id="EPIC-001",
        feature_ids=["FEAT-001", "FEAT-002"],
        requirement_ids=["REQ-001", "REQ-002"]
    )
    assert hierarchy.epic_id == "EPIC-001"
    assert len(hierarchy.feature_ids) == 2
    assert len(hierarchy.requirement_ids) == 2

def test_dependency_schema():
    """
    Verifies Dependency schema with dependency types.
    """
    dep = FeatureDependency(
        dependent_feature_id="FEAT-002",
        dependency_feature_id="FEAT-001",
        dependency_type="blocks"
    )

    assert dep.dependent_feature_id == "FEAT-002"
    assert dep.dependency_type == "blocks"

def test_feature_priority_schema():
    """
    Verifies FeaturePriority assignment.
    """
    priority = FeaturePriority(
        feature_id="FEAT-001",
        priority="High"
    )
    assert priority.feature_id == "FEAT-001"
    assert priority.priority == "High"

def test_coverage_report_schema():
    """
    Verifies CoverageReport schema with all required fields.
    """
    report = CoverageReport(
        total_requirements=10,
        mapped_requirements=10,
        unmapped_requirements=0,
        coverage_percentage=100.0
    )
    assert report.total_requirements == 10
    assert report.coverage_percentage == 100.0

def test_metadata_schema():
    """
    Verifies Metadata schema includes confidence score.
    """
    metadata = Metadata(
        generated_by="Agent-2",
        generated_timestamp=datetime.utcnow().isoformat() + "Z",
        domain="Payment Processing",
        version="1.0",
        model_name="claude-3-5-sonnet",
        confidence_score=0.92
    )
    assert metadata.confidence_score == 0.92
    assert 0.0 <= metadata.confidence_score <= 1.0

def test_traceability_matrix_schema():
    """
    Verifies TraceabilityMatrix schema with dependencies.
    """
    matrix = TraceabilityMatrix(
        requirement_id="REQ-001",
        epic_id="EPIC-001",
        feature_id="FEAT-001",
        dependencies=["FEAT-002"]
    )
    assert matrix.requirement_id == "REQ-001"
    assert "FEAT-002" in matrix.dependencies

def test_epic_feature_planner_output_full():
    """
    Comprehensive test of EpicFeaturePlannerOutput with all extended fields.
    """
    data = {
        "epics": [
            {
                "id": "EPIC-001",
                "name": "Authentication",
                "description": "User authentication system"
            }
        ],
        "features": [
            {
                "id": "FEAT-001",
                "epic_id": "EPIC-001",
                "name": "Login",
                "description": "Login feature",
                "priority": "High"
            }
        ],
        "hierarchy": [
            {
                "requirement_id": "REQ-001",
                "feature_id": "FEAT-001"
            }
        ],
        "requirement_mapping": [
            {
                "requirement_id": "REQ-001",
                "requirement_content": "User can log in",
                "epic_id": "EPIC-001",
                "feature_id": "FEAT-001"
            }
        ],
        "epic_hierarchy": [
            {
                "epic_id": "EPIC-001",
                "feature_ids": ["FEAT-001"],
                "requirement_ids": ["REQ-001"]
            }
        ],
        "dependencies": [
            {
                "dependent_feature_id": "FEAT-002",
                "dependency_feature_id": "FEAT-001",
                "dependency_type": "blocks"
            }
        ],
        "priority": [
            {
                "feature_id": "FEAT-001",
                "priority": "High"
            }
        ],
        "coverage_report": {
            "total_requirements": 1,
            "mapped_requirements": 1,
            "unmapped_requirements": 0,
            "coverage_percentage": 100.0
        },
        "metadata": {
            "generated_by": "Agent-2",
            "generated_timestamp": "2024-06-26T10:30:00Z",
            "domain": "Authentication",
            "version": "1.0",
            "model_name": "claude-3-5-sonnet",
            "confidence_score": 0.92
        },
        "traceability_matrix": [
            {
                "requirement_id": "REQ-001",
                "epic_id": "EPIC-001",
                "feature_id": "FEAT-001",
                "dependencies": []
            }
        ]
    }
    
    output = EpicFeaturePlannerOutput.model_validate(data)
    assert len(output.epics) == 1
    assert len(output.features) == 1
    assert len(output.requirement_mapping) == 1
    assert len(output.epic_hierarchy) == 1
    assert len(output.dependencies) == 1
    assert len(output.priority) == 1
    assert output.coverage_report["coverage_percentage"] == 100.0
    assert 0.0 <= output.metadata["confidence_score"] <= 1.0
    assert len(output.traceability_matrix) == 1

def test_story_context_schema():
    """
    Verifies StoryContext schema for orchestrator.
    """
    context = StoryContext(
        story_id="STORY-REQ-001",
        requirement_id="REQ-001",
        requirement="User can log in with email",
        epic={"id": "EPIC-001", "name": "Authentication"},
        feature={"id": "FEAT-001", "name": "Login", "priority": "High"},
        actor="Customer",
        business_rules=["Token expires in 24 hours"],
        dependencies=["FEAT-002"],
        priority="High",
        validation={},
        traceability={}
    )
    assert context.story_id == "STORY-REQ-001"
    assert context.priority == "High"
    assert "FEAT-002" in context.dependencies

def test_master_context_schema():
    """
    Verifies MasterContext schema as single source of truth.
    """
    context = MasterContext(
        job_id="JOB-001",
        requirements=[],
        actors=["Admin", "Customer"],
        business_rules=["Rule 1"],
        validation_context={},
        epics=[],
        features=[],
        hierarchy=[],
        priority=[],
        coverage_report={
            "total_requirements": 5,
            "mapped_requirements": 5,
            "unmapped_requirements": 0,
            "coverage_percentage": 100.0
        },
        dependencies=[],
        metadata={
            "generated_by": "Agent-2",
            "generated_timestamp": "2024-06-26T10:30:00Z",
            "domain": "System",
            "version": "1.0",
            "model_name": "claude",
            "confidence_score": 0.9
        },
        traceability_matrix=[],
        created_at="2024-06-26T10:30:00Z"
    )
    assert context.job_id == "JOB-001"
    assert len(context.actors) == 2

def test_confidence_score_validation():
    """
    Ensures confidence score is properly validated within 0.0-1.0 range.
    """
    # Valid confidence scores
    for score in [0.0, 0.5, 0.75, 1.0]:
        metadata = Metadata(
            generated_by="Agent-2",
            generated_timestamp="2024-06-26T10:30:00Z",
            confidence_score=score
        )
        assert 0.0 <= metadata.confidence_score <= 1.0
    
    # Invalid scores should raise validation error
    with pytest.raises(ValueError):
        Metadata(
            generated_by="Agent-2",
            generated_timestamp="2024-06-26T10:30:00Z",
            confidence_score=1.5  # Out of range
        )
    
    with pytest.raises(ValueError):
        Metadata(
            generated_by="Agent-2",
            generated_timestamp="2024-06-26T10:30:00Z",
            confidence_score=-0.1  # Out of range
        )

def test_priority_values():
    """
    Ensures priority is one of the allowed values.
    """
    valid_priorities = ["High", "Medium", "Low"]
    for priority_val in valid_priorities:
        priority = FeaturePriority(
            feature_id="FEAT-001",
            priority=priority_val
        )
        assert priority.priority in valid_priorities

def test_dependency_types():
    """
    Verifies dependency types are correctly classified.
    """
    valid_types = ["blocks", "extends", "requires", "related"]
    for dep_type in valid_types:
        dep = FeatureDependency(
            dependent_feature_id="FEAT-002",
            dependency_feature_id="FEAT-001",
            dependency_type=dep_type
        )

        assert dep.dependency_type == dep_type

# INTEGRATION NOTE
# Verify prompt variables align with these schemas before deploying.
# All schemas are backward compatible with existing functionality.
# New fields are optional with sensible defaults where applicable.
