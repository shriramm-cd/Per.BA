from typing import List, Dict, Any
from backend.validation_export.validators.base import BaseValidator
from backend.validation_export.schemas import ValidationContext, ValidationFinding, Severity
from backend.shared.jinja_renderer import JinjaRenderer
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class HallucinationValidator(BaseValidator):
    def __init__(self):
        super().__init__("hallucination_validator")
        self.renderer = JinjaRenderer()
        self.llm = LLMClient()

    async def _validate_logic(self, context: ValidationContext) -> List[ValidationFinding]:
        findings = []

        # Map requirements by ID for quick lookup
        req_map = {r.get("id") or r.get("trace_id"): r for r in context.requirements}

        for story in context.stories:
            story_id = story.get("id")
            title = story.get("title") or "Unnamed Story"
            trace_mappings = story.get("trace_mappings", [])

            # Filter requirements mapped to this story
            mapped_reqs = [req_map[r_id] for r_id in trace_mappings if r_id in req_map]
            
            # If no mappings, map all as fallback to check broadly
            if not mapped_reqs:
                mapped_reqs = context.requirements

            if not mapped_reqs:
                continue

            prompt = self.renderer.render(
                "hallucination.jinja2",
                {
                    "requirements": mapped_reqs,
                    "title": title,
                    "user_story_text": story.get("user_story_text", ""),
                    "acceptance_criteria": story.get("acceptance_criteria", [])
                }
            )

            system_prompt = "You are a requirements compliance auditor. Detect developer hallucinations. Output raw JSON."

            try:
                response_json = await self.llm.generate_json(prompt=prompt, system_prompt=system_prompt)
                
                if response_json.get("has_hallucinations", False):
                    unsupported = response_json.get("unsupported_elements", [])
                    feedback = response_json.get("feedback", "Features unsupported by source requirements.")
                    
                    findings.append(
                        ValidationFinding(
                            id=f"HALLUCINATION-{story_id}",
                            validator_name=self.name,
                            title="Hallucinated Content Detected",
                            description=(
                                f"Story '{title}' contains elements not grounded in the source requirements. "
                                f"Unsupported elements: {', '.join(unsupported)}. Feedback: {feedback}"
                            ),
                            severity=Severity.CRITICAL,
                            field="user_story_text",
                            mitigation="Remove or revise the unsupported features to align strictly with the source requirements."
                        )
                    )
            except Exception as e:
                logger.error(f"Hallucination check failed for story {story_id}: {str(e)}")
                # Do not fail the whole execution, add an info finding
                findings.append(
                    ValidationFinding(
                        id=f"HALLUCINATION-ERR-{story_id}",
                        validator_name=self.name,
                        title="Hallucination Check Failed",
                        description=f"Could not complete LLM hallucination check: {str(e)}",
                        severity=Severity.MINOR,
                        field="user_story_text",
                        mitigation="Audit the story manually for ungrounded details."
                    )
                )

        return findings
