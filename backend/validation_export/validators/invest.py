import re
from typing import List, Dict, Any
from backend.validation_export.validators.base import BaseValidator
from backend.validation_export.schemas import ValidationContext, ValidationFinding, Severity
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class InvestValidator(BaseValidator):
    def __init__(self):
        super().__init__("invest_validator")
        self.llm = LLMClient()

    async def _validate_logic(self, context: ValidationContext) -> List[ValidationFinding]:
        findings = []

        for idx, story in enumerate(context.stories):
            story_id = story.get("id") or f"STORY-TEMP-{idx}"
            title = story.get("title") or "Unnamed Story"
            story_text = story.get("user_story_text") or ""
            ac_list = story.get("acceptance_criteria") or []

            # --- 1. Deterministic Checks ---
            
            # Independent: Check if story text or AC references other stories (e.g. "STORY-123", "depends on ST-12")
            # We exclude self-references.
            independent = True
            other_story_refs = re.findall(r'\b(STORY-\d+|ST-\d+)\b', story_text + " " + " ".join(str(ac) for ac in ac_list))
            other_story_refs = [ref for ref in other_story_refs if ref != story_id]
            if other_story_refs:
                independent = False
                findings.append(
                    ValidationFinding(
                        id=f"INVEST-INDEPENDENT-{story_id}",
                        validator_name=self.name,
                        title="INVEST: Story is not Independent",
                        description=f"Story '{title}' references other stories ({', '.join(other_story_refs)}), indicating tight coupling.",
                        severity=Severity.MINOR,
                        field="user_story_text",
                        mitigation="Refactor the story to reduce dependencies on other stories, or merge them if they cannot be separated."
                    )
                )

            # Small: Check if number of ACs <= 6 and word count <= 250
            small = True
            word_count = len(story_text.split())
            if len(ac_list) > 6 or word_count > 250:
                small = False
                findings.append(
                    ValidationFinding(
                        id=f"INVEST-SMALL-{story_id}",
                        validator_name=self.name,
                        title="INVEST: Story is too Large",
                        description=f"Story '{title}' has {len(ac_list)} ACs and {word_count} words. It may be too large for a single sprint.",
                        severity=Severity.MINOR,
                        field="user_story_text",
                        mitigation="Split the story into smaller, more manageable vertical slices of value."
                    )
                )

            # Testable: Check if ACs contain Given/When/Then Gherkin syntax
            testable = True
            ac_str = " ".join(str(ac).lower() for ac in ac_list)
            if "given" not in ac_str or "when" not in ac_str or "then" not in ac_str:
                testable = False
                findings.append(
                    ValidationFinding(
                        id=f"INVEST-TESTABLE-{story_id}",
                        validator_name=self.name,
                        title="INVEST: Story is not Testable",
                        description=f"Story '{title}' lacks clear Given-When-Then Gherkin acceptance criteria, making it hard to verify.",
                        severity=Severity.MINOR,
                        field="acceptance_criteria",
                        mitigation="Add structured Gherkin scenarios to make the story testable."
                    )
                )

            # --- 2. LLM Reasoning Checks (Negotiable, Valuable, Estimable) ---
            
            prompt = f"""
You are an Agile Quality Coach. Evaluate the following user story against three specific INVEST principles:
- Negotiable: Does it avoid over-specifying implementation details and leave room for discussion?
- Valuable: Is the benefit to the end user or business clear and explicit?
- Estimable: Is there enough context and clarity for developers to estimate the effort?

User Story Details:
Title: {title}
Story: {story_text}
Acceptance Criteria:
{json.dumps(ac_list, indent=2)}

Evaluate each of the three principles as true or false. Provide brief explanation feedback for any false flags.
Output must be in JSON format matching this structure:
{{
  "negotiable": true,
  "valuable": true,
  "estimable": true,
  "feedback": "Critique feedback on failure points, or empty if valid."
}}
IMPORTANT: Return ONLY the raw JSON object. Do not include markdown code block wrapper backticks or extra text.
"""
            system_prompt = "You are an Agile coach. Evaluate user story quality. Output raw JSON."

            try:
                response_json = await self.llm.generate_json(prompt=prompt, system_prompt=system_prompt)
                
                # Process LLM findings
                if not response_json.get("negotiable", True):
                    findings.append(
                        ValidationFinding(
                            id=f"INVEST-NEGOTIABLE-{story_id}",
                            validator_name=self.name,
                            title="INVEST: Story is not Negotiable",
                            description=f"Story '{title}' is over-specified: {response_json.get('feedback')}",
                            severity=Severity.MINOR,
                            field="user_story_text",
                            mitigation="Remove technical implementation details to allow for team discussion."
                        )
                    )
                if not response_json.get("valuable", True):
                    findings.append(
                        ValidationFinding(
                            id=f"INVEST-VALUABLE-{story_id}",
                            validator_name=self.name,
                            title="INVEST: Story has Low Value",
                            description=f"Story '{title}' does not express clear business or user value: {response_json.get('feedback')}",
                            severity=Severity.MINOR,
                            field="user_story_text",
                            mitigation="Refine the 'So that...' clause to clearly articulate the business or user benefit."
                        )
                    )
                if not response_json.get("estimable", True):
                    findings.append(
                        ValidationFinding(
                            id=f"INVEST-ESTIMABLE-{story_id}",
                            validator_name=self.name,
                            title="INVEST: Story is not Estimable",
                            description=f"Story '{title}' lacks sufficient clarity/context for estimation: {response_json.get('feedback')}",
                            severity=Severity.MINOR,
                            field="user_story_text",
                            mitigation="Clarify the requirements, assumptions, and scope of the story."
                        )
                    )
            except Exception as e:
                logger.error(f"INVEST LLM check failed for story {story_id}: {str(e)}")
                # Add a minor warning finding
                findings.append(
                    ValidationFinding(
                        id=f"INVEST-LLM-ERR-{story_id}",
                        validator_name=self.name,
                        title="INVEST Reasoning Check Failed",
                        description=f"Could not complete LLM reasoning evaluation: {str(e)}",
                        severity=Severity.MINOR,
                        field="user_story_text",
                        mitigation="Evaluate Negotiable, Valuable, and Estimable principles manually."
                    )
                )

        return findings
