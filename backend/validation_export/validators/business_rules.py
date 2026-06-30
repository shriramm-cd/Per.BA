import json
from typing import List, Dict, Any
from backend.validation_export.validators.base import BaseValidator
from backend.validation_export.schemas import ValidationContext, ValidationFinding, Severity
from backend.shared.jinja_renderer import JinjaRenderer
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class BusinessRulesValidator(BaseValidator):
    def __init__(self):
        super().__init__("business_rules_validator")
        self.renderer = JinjaRenderer()
        self.llm = LLMClient()

    async def _validate_logic(self, context: ValidationContext) -> List[ValidationFinding]:
        findings = []
        
        # Collect all business rules in the context for mapping
        all_rules = {r.get("id"): r for r in context.business_rules if r.get("id")}
        for req in context.requirements:
            for br in req.get("business_rules", []):
                if isinstance(br, dict) and br.get("id"):
                    all_rules[br.get("id")] = br

        for story in context.stories:
            story_id = story.get("id")
            title = story.get("title") or "Unnamed Story"
            
            # Map business rules associated with this story
            story_br_links = story.get("business_rules", [])
            story_brs = []
            for link in story_br_links:
                link_id = link.get("id") if isinstance(link, dict) else str(link)
                if link_id in all_rules:
                    story_brs.append(all_rules[link_id])
                else:
                    # Fallback/raw description if not in global list
                    story_brs.append({"id": link_id, "description": link.get("description") if isinstance(link, dict) else link_id})

            if not story_brs:
                # No business rules mapped, skip LLM check
                continue

            prompt = self.renderer.render(
                "business_rules.jinja2",
                {
                    "title": title,
                    "user_story_text": story.get("user_story_text", ""),
                    "acceptance_criteria": story.get("acceptance_criteria", []),
                    "business_rules": story_brs
                }
            )

            system_prompt = "You are a business rules compliance auditor. Analyze the story and output raw JSON."
            
            try:
                response_json = await self.llm.generate_json(prompt=prompt, system_prompt=system_prompt)
                
                # Check for violations in response
                violations = response_json.get("violations", [])
                for v in violations:
                    severity_map = {
                        "CRITICAL": Severity.CRITICAL,
                        "MAJOR": Severity.MAJOR,
                        "MINOR": Severity.MINOR
                    }
                    severity = severity_map.get(v.get("severity", "MAJOR"), Severity.MAJOR)
                    
                    findings.append(
                        ValidationFinding(
                            id=f"BR-VIOLATION-{v.get('rule_id')}-{story_id}",
                            validator_name=self.name,
                            title=f"Business Rule Violation: {v.get('rule_id')}",
                            description=v.get("description", "The user story violates the business rule."),
                            severity=severity,
                            field="business_rules",
                            mitigation=f"Modify the story or acceptance criteria to comply with business rule {v.get('rule_id')}."
                        )
                    )
            except Exception as e:
                logger.error(f"Business Rules validation failed for story {story_id}: {str(e)}")
                # Do not fail the whole execution, add an info finding
                findings.append(
                    ValidationFinding(
                        id=f"BR-ERR-{story_id}",
                        validator_name=self.name,
                        title="Business Rules Check Failed",
                        description=f"Could not complete LLM business rule validation: {str(e)}",
                        severity=Severity.MINOR,
                        field="business_rules",
                        mitigation="Verify business rule compliance manually."
                    )
                )

        return findings
