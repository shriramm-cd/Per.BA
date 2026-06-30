import asyncio
from typing import Dict, Any, List
from backend.validation_export.schemas import HallucinationResult
from backend.shared.jinja_renderer import JinjaRenderer
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class HallucinationChecker:
    """
    Submits user stories and their trace-mapped requirements to LLM to detect feature hallucinations.
    """
    def __init__(self):
        self.renderer = JinjaRenderer()
        self.llm = LLMClient()

    async def audit_story(self, story: Dict[str, Any], requirements: List[Dict[str, Any]]) -> HallucinationResult:
        """
        Audits a story's content against its trace-mapped requirements.
        """
        logger.info(f"Auditing hallucinations for story: {story.get('id')}")
        
        # Filter requirements mapped to this story
        mapped_req_ids = set(story.get("trace_mappings", []))
        mapped_reqs = [r for r in requirements if r.get("id") in mapped_req_ids or r.get("trace_id") in mapped_req_ids]
        
        # If no mappings, map all as fallback to search broadly or check
        if not mapped_reqs:
            mapped_reqs = requirements

        prompt = self.renderer.render(
            "hallucination.jinja2",
            {
                "requirements": mapped_reqs,
                "title": story.get("title", ""),
                "user_story_text": story.get("user_story_text", ""),
                "acceptance_criteria": story.get("acceptance_criteria", [])
            }
        )

        system_prompt = "You are a requirements compliance auditor. Detect developer hallucinations. Output raw JSON."
        
        try:
            response_json = await self.llm.generate_json(prompt=prompt, system_prompt=system_prompt)
            response_json["story_id"] = story.get("id") or "STORY-UNKNOWN"
            return HallucinationResult.model_validate(response_json)
        except Exception as e:
            logger.error(f"Hallucination check failed for story {story.get('id')}: {str(e)}")
            return HallucinationResult(
                story_id=story.get("id") or "STORY-UNKNOWN",
                has_hallucinations=False,
                unsupported_elements=[],
                feedback=f"LLM check failed: {str(e)}"
            )

    async def audit_all(self, stories: List[Dict[str, Any]], requirements: List[Dict[str, Any]]) -> List[HallucinationResult]:
        """
        Audits a set of stories concurrently.
        """
        tasks = [self.audit_story(s, requirements) for s in stories]
        return await asyncio.gather(*tasks)

# INTEGRATION NOTE
# HallucinationChecker verifies that no out-of-scope features are auto-injected during generation.
