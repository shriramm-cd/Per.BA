import asyncio
from typing import Dict, Any, List
from backend.validation_export.schemas import InvestResult
from backend.shared.jinja_renderer import JinjaRenderer
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class InvestValidator:
    """
    Submits user stories to LLM to audit conformity to INVEST quality standard.
    """
    def __init__(self):
        self.renderer = JinjaRenderer()
        self.llm = LLMClient()

    async def validate_story(self, story: Dict[str, Any]) -> InvestResult:
        """
        Validates an individual user story against INVEST principles.
        """
        logger.info(f"Auditing INVEST rules for story: {story.get('id')}")
        
        prompt = self.renderer.render(
            "invest.jinja2",
            {
                "title": story.get("title", ""),
                "user_story_text": story.get("user_story_text", ""),
                "acceptance_criteria": story.get("acceptance_criteria", [])
            }
        )

        system_prompt = "You are an expert Scrum Master. Evaluate story structure. Output raw JSON."
        
        try:
            response_json = await self.llm.generate_json(prompt=prompt, system_prompt=system_prompt)
            # Add back the story_id into the response JSON
            response_json["story_id"] = story.get("id") or "STORY-UNKNOWN"
            return InvestResult.model_validate(response_json)
        except Exception as e:
            logger.error(f"INVEST check failed for story {story.get('id')}: {str(e)}")
            # Fail-safe fallback: Mark everything as True but flag error in feedback
            return InvestResult(
                story_id=story.get("id") or "STORY-UNKNOWN",
                independent=True,
                negotiable=True,
                valuable=True,
                estimable=True,
                small=True,
                testable=True,
                feedback=f"LLM check failed: {str(e)}"
            )

    async def validate_all(self, stories: List[Dict[str, Any]]) -> List[InvestResult]:
        """
        Validates a list of user stories concurrently.
        """
        tasks = [self.validate_story(s) for s in stories]
        return await asyncio.gather(*tasks)

# INTEGRATION NOTE
# InvestValidator relies on llm_client to execute evaluations.
# Ensure correct Jinja paths search targets config are maintained.
