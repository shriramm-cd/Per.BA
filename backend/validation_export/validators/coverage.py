from typing import List, Set
from backend.validation_export.validators.base import BaseValidator
from backend.validation_export.schemas import ValidationContext, ValidationFinding, Severity

class CoverageValidator(BaseValidator):
    def __init__(self):
        super().__init__("coverage_validator")

    async def _validate_logic(self, context: ValidationContext) -> List[ValidationFinding]:
        findings = []

        # 1. Collect all mapped requirements
        mapped_reqs: Set[str] = set()
        for story in context.stories:
            for mapping in story.get("trace_mappings", []):
                mapped_reqs.add(mapping)

        # 2. Check Requirement Coverage (FR and NFR)
        for req in context.requirements:
            req_id = req.get("trace_id") or req.get("id")
            if not req_id:
                continue

            if req_id not in mapped_reqs:
                req_type = req.get("type", "Functional").upper()
                severity = Severity.CRITICAL if req_type == "FUNCTIONAL" else Severity.MAJOR
                findings.append(
                    ValidationFinding(
                        id=f"COV-UNCOVERED-REQ-{req_id}",
                        validator_name=self.name,
                        title=f"Uncovered {req_type} Requirement",
                        description=f"Source requirement '{req_id}' ({req.get('content', '')[:60]}...) has no stories mapped to it.",
                        severity=severity,
                        field="trace_mappings",
                        mitigation="Create a user story or map an existing story to cover this requirement."
                    )
                )

        # 3. Check Business Rule Coverage
        # Combine all business rules from requirements and context
        all_rules = list(context.business_rules)
        for req in context.requirements:
            for br in req.get("business_rules", []):
                if br not in all_rules:
                    all_rules.append(br)

        mapped_rules: Set[str] = set()
        for story in context.stories:
            # Look for business rule IDs in the story's business rules list
            for br in story.get("business_rules", []):
                mapped_rules.add(br.get("id") if isinstance(br, dict) else str(br))

        for rule in all_rules:
            rule_id = rule.get("id") if isinstance(rule, dict) else str(rule)
            rule_desc = rule.get("description") if isinstance(rule, dict) else str(rule)
            if rule_id and rule_id not in mapped_rules:
                findings.append(
                    ValidationFinding(
                        id=f"COV-UNCOVERED-BR-{rule_id}",
                        validator_name=self.name,
                        title="Uncovered Business Rule",
                        description=f"Business Rule '{rule_id}' ('{rule_desc[:60]}...') is not covered by any user story.",
                        severity=Severity.MAJOR,
                        field="business_rules",
                        mitigation="Link this business rule to a user story or create a new story to implement it."
                    )
                )

        # 4. Check Actor Coverage
        mapped_actors: Set[str] = set()
        for story in context.stories:
            actor = story.get("actor")
            if actor:
                mapped_actors.add(actor.lower())

        for actor in context.actors:
            actor_name = actor.get("name") or actor.get("id")
            if actor_name and actor_name.lower() not in mapped_actors:
                findings.append(
                    ValidationFinding(
                        id=f"COV-UNCOVERED-ACTOR-{actor_name.upper()}",
                        validator_name=self.name,
                        title="Unused/Uncovered Actor",
                        description=f"Actor '{actor_name}' is defined in the requirements but never used as the primary persona of any user story.",
                        severity=Severity.MINOR,
                        field="actors",
                        mitigation="Verify if there should be user stories written from the perspective of this actor."
                    )
                )

        return findings
