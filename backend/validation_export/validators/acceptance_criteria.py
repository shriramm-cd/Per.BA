import re
from typing import List
from backend.validation_export.validators.base import BaseValidator
from backend.validation_export.schemas import ValidationContext, ValidationFinding, Severity

class AcceptanceCriteriaValidator(BaseValidator):
    def __init__(self):
        super().__init__("acceptance_criteria_validator")

    async def _validate_logic(self, context: ValidationContext) -> List[ValidationFinding]:
        findings = []

        for idx, story in enumerate(context.stories):
            story_id = story.get("id") or f"STORY-TEMP-{idx}"
            title = story.get("title") or "Unnamed Story"
            ac_list = story.get("acceptance_criteria") or []

            if not ac_list:
                # Handled by structural validator, but skip here
                continue

            has_gherkin = False
            has_positive = False
            has_negative = False

            for ac in ac_list:
                ac_text = ac.get("description", "") if isinstance(ac, dict) else str(ac)
                ac_text_lower = ac_text.lower()

                # 1. Check Gherkin keywords
                if "given" in ac_text_lower and "when" in ac_text_lower and "then" in ac_text_lower:
                    has_gherkin = True
                
                # 2. Check Positive scenarios
                # Any scenario describing normal/success flow
                if any(kw in ac_text_lower for kw in ["success", "valid", "positive", "successful", "allow", "enable", "confirm"]):
                    has_positive = True

                # 3. Check Negative scenarios
                # Any scenario describing error handling, validation, or exceptions
                if any(kw in ac_text_lower for kw in ["error", "fail", "invalid", "negative", "exception", "reject", "deny", "cannot", "prevent"]):
                    has_negative = True

            # 4. Add findings based on checks
            if not has_gherkin:
                findings.append(
                    ValidationFinding(
                        id=f"AC-GHERKIN-{story_id}",
                        validator_name=self.name,
                        title="Acceptance Criteria: Non-Gherkin Format",
                        description=f"Story '{title}' has acceptance criteria that do not follow the Given-When-Then format.",
                        severity=Severity.MAJOR,
                        field="acceptance_criteria",
                        mitigation="Rephrase acceptance criteria using the Given-When-Then Gherkin format."
                    )
                )

            if not has_positive:
                findings.append(
                    ValidationFinding(
                        id=f"AC-NO-POSITIVE-{story_id}",
                        validator_name=self.name,
                        title="Acceptance Criteria: Missing Positive Scenario",
                        description=f"Story '{title}' does not explicitly define a positive/happy path scenario.",
                        severity=Severity.MAJOR,
                        field="acceptance_criteria",
                        mitigation="Add at least one positive scenario confirming successful execution."
                    )
                )

            if not has_negative:
                findings.append(
                    ValidationFinding(
                        id=f"AC-NO-NEGATIVE-{story_id}",
                        validator_name=self.name,
                        title="Acceptance Criteria: Missing Negative Scenario",
                        description=f"Story '{title}' does not define any negative/error-handling scenario.",
                        severity=Severity.MAJOR,
                        field="acceptance_criteria",
                        mitigation="Add a negative scenario detailing how the system handles invalid input or failure states."
                    )
                )

        return findings
