import asyncio
from typing import List, Dict, Any
from atlassian import Jira
from backend.config import settings
from backend.shared.exceptions import ExportError
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class JiraExporter:
    """
    Exports generated User Stories and Epics/Features hierarchy directly into Atlassian Jira projects.
    """
    def __init__(self):
        self.url = settings.JIRA_API_URL
        self.username = settings.JIRA_USERNAME
        self.token = settings.JIRA_API_TOKEN

    async def export_stories(self, project_key: str, stories: List[Dict[str, Any]]) -> List[str]:
        """
        Creates issue stories inside the designated Jira project.
        """
        if not self.url or not self.username or not self.token:
            raise ExportError("Jira settings credentials not configured. Export aborted.")

        logger.info(f"Connecting to Jira for export at {self.url}...")
        
        try:
            def create_jira_issues():
                jira = Jira(url=self.url, username=self.username, password=self.token, cloud=True)
                created_keys = []
                
                for story in stories:
                    summary = f"[{story.get('feature_id', 'US')}] {story.get('title')}"
                    
                    description = (
                        f"h3. User Story\n{story.get('user_story_text')}\n\n"
                        f"h3. Acceptance Criteria\n"
                    )
                    for ac in story.get("acceptance_criteria", []):
                        description += f"*Scenario: {ac.get('scenario')}*\n"
                        description += f"** *Given* {ac.get('given')}\n"
                        description += f"** *When* {ac.get('when')}\n"
                        description += f"** *Then* {ac.get('then')}\n\n"

                    description += f"h3. Traceability Mapping\nSource requirements: {', '.join(story.get('trace_mappings', []))}"

                    fields = {
                        "project": {"key": project_key},
                        "summary": summary,
                        "description": description,
                        "issuetype": {"name": "Story"}
                    }
                    
                    logger.info(f"Creating story issue: '{summary}'")
                    res = jira.create_issue(fields=fields)
                    created_keys.append(res.get("key"))
                    
                return created_keys

            return await asyncio.to_thread(create_jira_issues)
        except Exception as e:
            logger.error(f"Jira stories export failure: {str(e)}")
            raise ExportError(f"Jira export failed: {str(e)}")

# INTEGRATION NOTE
# Make sure project_key (e.g. 'PROJ') is valid and the username has permissions to create issues.
