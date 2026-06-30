from typing import List
from backend.validation_export.validators.base import BaseValidator
from backend.validation_export.schemas import ValidationContext, ValidationFinding, Severity
from backend.validation_export.services.embedding_service import EmbeddingService
from backend.validation_export import validation_settings

class DuplicateValidator(BaseValidator):
    def __init__(self):
        super().__init__("duplicate_validator")
        self.embedding_service = EmbeddingService()

    async def _validate_logic(self, context: ValidationContext) -> List[ValidationFinding]:
        findings = []

        if len(context.stories) <= 1:
            return findings

        # Find duplicates using the embedding service
        duplicates = await self.embedding_service.find_duplicates(context.stories)

        for id1, id2, similarity in duplicates:
            # Find story titles for better descriptions
            title1 = next((s.get("title", "Story 1") for s in context.stories if s.get("id") == id1), id1)
            title2 = next((s.get("title", "Story 2") for s in context.stories if s.get("id") == id2), id2)

            findings.append(
                ValidationFinding(
                    id=f"DUP-DETECTED-{id1}-{id2}",
                    validator_name=self.name,
                    title="Duplicate Story Detected",
                    description=(
                        f"Story '{title1}' ({id1}) and Story '{title2}' ({id2}) are near-duplicates "
                        f"with a semantic similarity of {similarity:.2f} (Threshold: {validation_settings.DUPLICATE_THRESHOLD})."
                    ),
                    severity=Severity.MAJOR,
                    field="user_story_text",
                    mitigation="Consolidate the duplicate stories or differentiate their scope."
                )
            )

        return findings
