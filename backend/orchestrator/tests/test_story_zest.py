import pytest
from unittest.mock import patch, AsyncMock
from backend.orchestrator.story_zest import StoryZestGenerator

@pytest.mark.anyio
async def test_generate_zest_success():
    stories = [
        {"epic": "HRMS-101", "feature": "FEAT-01", "title": "Apply for Leave", "user_story": "As an employee..."},
        {"epic": "HRMS-101", "feature": "FEAT-02", "title": "Approve Leave", "user_story": "As a manager..."}
    ]
    
    mock_response = {
        "business_goal": "Automate leave management processes.",
        "scope_summary": "Allows employees to apply and managers to approve leave requests.",
        "actors": ["Employee", "Manager"],
        "key_features": ["Leave Application", "Leave Approval"],
        "dependencies": ["Notification System"],
        "risks": ["Delay in approvals"],
        "coverage_metrics": {
            "coverage_percentage": 100
        }
    }
    
    generator = StoryZestGenerator()
    with patch.object(generator.llm_client, "generate_json", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_response
        zest = await generator.generate_zest(stories, is_final=False)
        
        assert zest["business_goal"] == "Automate leave management processes."
        assert zest["coverage_metrics"]["total_stories"] == 2
        assert zest["coverage_metrics"]["total_epics"] == 1
        assert zest["coverage_metrics"]["total_features"] == 2
        assert "Employee" in zest["actors"]
