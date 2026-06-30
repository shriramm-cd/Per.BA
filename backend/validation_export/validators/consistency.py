import json
from typing import List, Dict, Any
from backend.validation_export.validators.base import BaseValidator
from backend.validation_export.schemas import ValidationContext, ValidationFinding, Severity
from backend.shared.jinja_renderer import JinjaRenderer
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class ConsistencyValidator(BaseValidator):
    def __init__(self):
        super().__init__("consistency_validator")
        self.renderer = JinjaRenderer()
        self.llm = LLMClient()

    async def _validate_logic(self, context: ValidationContext) -> List[ValidationFinding]:
        findings = []

        if len(context.stories) <= 1:
            return findings

        # Render all stories into the consistency prompt
        prompt = self.renderer.render(
            "consistency.jinja2",
            {
                "stories": context.stories
            }
        )

        system_prompt = "You are an enterprise consistency auditor. Detect story contradictions. Output raw JSON."

        try:
            response_json = await self.llm.generate_json(prompt=prompt, system_prompt=system_prompt)
            
            if not response_json.get("consistent", True):
                conflicts = response_json.get("conflicts", [])
                for idx, c in enumerate(conflicts):
                    story_ids = c.get("story_ids", [])
                    severity_map = {
                        "CRITICAL": Severity.CRITICAL,
                        "MAJOR": Severity.MAJOR,
                        "MINOR": Severity.MINOR
                    }
                    severity = severity_map.get(c.get("severity", "MAJOR"), Severity.MAJOR)
                    
                    findings.append(
                        ValidationFinding(
                            id=f"CONSISTENCY-CONFLICT-{idx}",
                            validator_name=self.name,
                            title=f"Story Contradiction Detected: {c.get('conflict_type')}",
                            description=f"Conflict between stories {', '.join(story_ids)}: {c.get('description')}",
                            severity=severity,
                            field="user_story_text",
                            mitigation="Review the conflicting stories and align their requirements and business logic."
                        )
                    )
        except Exception as e:
            logger.error(f"Consistency check failed: {str(e)}")
            findings.append(
                ValidationFinding(
                    id="CONSISTENCY-ERR",
                    validator_name=self.name,
                    title="Consistency Check Failed",
                    description=f"Could not complete LLM consistency validation: {str(e)}",
                    severity=Severity.MINOR,
                    field="user_story_text",
                    mitigation="Review consistency across stories manually."
                )
            )

        return findings
