import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.validation_export.revision_engine import RevisionEngine
from backend.validation_export.schemas import ValidationFinding, Severity
from backend.agents.agent3_user_story_generator import UserStoryGenerator
from backend.agents.schemas import StoryContext

def test_generate_story_revision_packages():
    """
    Verifies that generate_story_revision_packages correctly identifies rejected stories
    and builds the preserve/modify sections as expected.
    """
    stories = [
        {
            "id": "US-001",
            "epic": "Epic 1",
            "feature": "Feature 1",
            "title": "Submit leave request",
            "user_story": "As an Employee, I want to submit a leave request so that I can take time off.",
            "acceptance_criteria": [
                {"statement": "Given I am logged in"},
                {"statement": "When I click submit"}
            ],
            "trace_mappings": ["REQ-001"]
        },
        {
            "id": "US-002",
            "epic": "Epic 1",
            "feature": "Feature 1",
            "title": "Approve leave request",
            "user_story": "As a Manager, I want to approve requests so that employees can take leave.",
            "acceptance_criteria": [
                {"statement": "Given I am logged in"},
                {"statement": "When I approve a request"}
            ],
            "trace_mappings": ["REQ-002"]
        }
    ]

    findings = [
        ValidationFinding(
            id="AC-US-001-FAIL",
            validator_name="AcceptanceCriteriaValidator",
            title="Invalid AC",
            description="When I click submit is incomplete",
            severity=Severity.MAJOR,
            field="US-001.acceptance_criteria"
        )
    ]

    ba_comments = {"US-002": "Please add validation rules for managers."}

    packages = RevisionEngine.generate_story_revision_packages(
        job_id="test-job",
        stories=stories,
        findings=findings,
        ba_comments_dict=ba_comments
    )

    assert len(packages) == 2
    
    # Story US-001 has validation findings
    pkg1 = next(p for p in packages if p.story_id == "US-001")
    assert "AcceptanceCriteriaValidator" in pkg1.failed_validators
    assert pkg1.preserve_section["story_title"] == "Submit leave request"
    assert pkg1.preserve_section["actor"] == "Employee"
    assert any("When I click submit" in ac for ac in pkg1.modify_section["failed_acceptance_criteria"])

    # Story US-002 has BA comments
    pkg2 = next(p for p in packages if p.story_id == "US-002")
    assert pkg2.ba_comments == ["Please add validation rules for managers."]
    assert pkg2.preserve_section["story_title"] == "Approve leave request"
    assert pkg2.preserve_section["actor"] == "Manager"


@pytest.mark.asyncio
async def test_agent3_preserves_approved_stories():
    """
    Verifies that Agent 3 preserves approved stories exactly as-is without calling the LLM.
    """
    generator = UserStoryGenerator()
    
    story_contexts = [
        StoryContext(
            story_context_id="ctx-1",
            story_id="US-001",
            requirement_id="REQ-001",
            requirement={"id": "REQ-001", "text": "Submit request"},
            epic={"id": "EPIC-1", "name": "Epic 1"},
            feature={"id": "FEAT-1", "name": "Feature 1"},
            actor="Employee"
        ),
        StoryContext(
            story_context_id="ctx-2",
            story_id="US-002",
            requirement_id="REQ-002",
            requirement={"id": "REQ-002", "text": "Approve request"},
            epic={"id": "EPIC-1", "name": "Epic 1"},
            feature={"id": "FEAT-1", "name": "Feature 1"},
            actor="Manager"
        )
    ]

    approved_stories = [
        {
            "id": "US-001",
            "epic": "Epic 1",
            "feature": "Feature 1",
            "title": "Submit leave request",
            "user_story": "As an Employee, I want to submit a leave request so that I can take time off.",
            "acceptance_criteria": [
                {"statement": "Given I am logged in"},
                {"statement": "When I click submit"}
            ],
            "trace_mappings": ["REQ-001"]
        }
    ]

    # US-002 is rejected and has a revision package
    revision_packages = [
        {
            "story_id": "US-002",
            "current_story": {
                "id": "US-002",
                "epic": "Epic 1",
                "feature": "Feature 1",
                "title": "Approve leave request",
                "user_story": "As a Manager, I want to approve requests so that employees can take leave.",
                "acceptance_criteria": [
                    {"statement": "Given I am logged in"},
                    {"statement": "When I approve a request"}
                ],
                "trace_mappings": ["REQ-002"]
            },
            "failed_validators": ["AcceptanceCriteriaValidator"],
            "validation_findings": [],
            "ba_comments": ["Please add validation rules for managers."],
            "preserve_section": {
                "story_title": "Approve leave request",
                "actor": "Manager",
                "approved_business_rules": [],
                "traceability_links": ["REQ-002"],
                "approved_acceptance_criteria": []
            },
            "modify_section": {}
        }
    ]

    # Mock the LLM call for the reworked story US-002
    mock_response = {
        "story_id": "US-002",
        "epic": "Epic 1",
        "feature": "Feature 1",
        "user_story": {
            "actor": "Manager",
            "goal": "approve requests with validation",
            "benefit": "employees can take leave"
        },
        "acceptance_criteria": [
            "Given I am logged in",
            "When I approve a request with sufficient balance",
            "Then the request is approved"
        ],
        "definition_of_done": [],
        "summary": "Approve leave request",
        "priority": "Medium",
        "version": 2
    }

    with patch.object(generator.llm_client, "generate_json", AsyncMock(return_value=mock_response)) as mock_generate:
        result = await generator.generate({
            "story_contexts": [ctx.model_dump() for ctx in story_contexts],
            "revision_packages": revision_packages,
            "approved_stories": approved_stories
        })

        # We should only have 1 LLM call (for US-002)
        assert mock_generate.call_count == 1
        
        # We should have 2 stories in the result
        assert len(result) == 2
        
        # US-001 (approved) is preserved as-is
        us1 = next(s for s in result if s.story_id == "US-001")
        assert us1.summary == "Submit leave request"
        assert us1.metadata.generated_by == "Agent-3-Preserved"

        # US-002 (rejected) is regenerated and version incremented
        us2 = next(s for s in result if s.story_id == "US-002")
        assert us2.version == 2
        assert "When I approve a request with sufficient balance" in us2.acceptance_criteria
