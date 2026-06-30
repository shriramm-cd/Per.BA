import uuid
from typing import List, Dict, Any
from backend.validation_export.validators.base import BaseValidator
from backend.validation_export.schemas import ValidationContext, ValidationFinding, Severity

class StructuralValidator(BaseValidator):
    def __init__(self):
        super().__init__("structural_validator")

    async def _validate_logic(self, context: ValidationContext) -> List[ValidationFinding]:
        findings = []
        mandatory_fields = ["title", "user_story_text", "acceptance_criteria", "epic_id", "feature_id", "trace_mappings"]

        for idx, story in enumerate(context.stories):
            story_id = story.get("id") or f"STORY-TEMP-{idx}"
            title = story.get("title") or "Unnamed Story"

            # 1. Check mandatory fields
            for field in mandatory_fields:
                if not story.get(field):
                    findings.append(
                        ValidationFinding(
                            id=f"STRUC-MISSING-{field.upper()}-{story_id}",
                            validator_name=self.name,
                            title="Missing Mandatory Field",
                            description=f"Story '{title}' is missing the mandatory field '{field}'.",
                            severity=Severity.CRITICAL,
                            field=field,
                            mitigation=f"Add the missing '{field}' field to the story."
                        )
                    )

            # 2. Check Story Format (As a... I want... So that...)
            story_text = story.get("user_story_text") or ""
            if story_text:
                lower_text = story_text.lower()
                if "as a" not in lower_text or "i want" not in lower_text or "so that" not in lower_text:
                    findings.append(
                        ValidationFinding(
                            id=f"STRUC-FORMAT-{story_id}",
                            validator_name=self.name,
                            title="Incorrect Story Format",
                            description=f"Story '{title}' does not follow the standard 'As a... I want... So that...' template.",
                            severity=Severity.MAJOR,
                            field="user_story_text",
                            mitigation="Rephrase the user story text to follow the standard Agile format: 'As a [user], I want [feature] so that [value]'."
                        )
                    )

            # 3. Check Acceptance Criteria presence and format
            ac_list = story.get("acceptance_criteria") or []
            if not ac_list:
                findings.append(
                    ValidationFinding(
                        id=f"STRUC-NO-AC-{story_id}",
                        validator_name=self.name,
                        title="No Acceptance Criteria",
                        description=f"Story '{title}' does not have any acceptance criteria defined.",
                        severity=Severity.CRITICAL,
                        field="acceptance_criteria",
                        mitigation="Define at least one acceptance criterion for the story."
                    )
                )

            # 4. Check Definition of Done (DoD) alignment
            dod = context.definition_of_done or {}
            # For example, DoD might require "unit_tests", "documentation", "security_scan"
            # Verify if story mentions or conforms to these (can be a simple info check)
            for criteria, req_desc in dod.items():
                # Check if the story mentions the DoD criteria in its text or AC
                found_in_story = criteria.lower() in story_text.lower() or any(
                    criteria.lower() in str(ac).lower() for ac in ac_list
                )
                if not found_in_story:
                    findings.append(
                        ValidationFinding(
                            id=f"STRUC-DOD-WARN-{criteria.upper()}-{story_id}",
                            validator_name=self.name,
                            title="Definition of Done Gap",
                            description=f"Story '{title}' does not explicitly address the DoD criteria '{criteria}' ({req_desc}).",
                            severity=Severity.INFO,
                            field="definition_of_done",
                            mitigation=f"Review if the story should explicitly address the DoD requirement: '{req_desc}'."
                        )
                    )

        return findings
