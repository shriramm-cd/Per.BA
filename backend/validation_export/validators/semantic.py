from typing import List
from backend.validation_export.validators.base import BaseValidator
from backend.validation_export.schemas import ValidationContext, ValidationFinding, Severity
from backend.validation_export.services.embedding_service import EmbeddingService
from backend.validation_export import validation_settings

class SemanticValidator(BaseValidator):
    def __init__(self):
        super().__init__("semantic_validator")
        self.embedding_service = EmbeddingService()

    async def _validate_logic(self, context: ValidationContext) -> List[ValidationFinding]:
        findings = []

        # Map requirements by ID
        req_map = {}
        for req in context.requirements:
            req_id = req.get("id") or req.get("trace_id")
            if req_id:
                req_map[req_id] = req.get("content", "")

        for story in context.stories:
            story_id = story.get("id")
            title = story.get("title") or "Unnamed Story"
            story_text = story.get("user_story_text") or ""
            
            trace_mappings = story.get("trace_mappings", [])
            if not trace_mappings:
                continue

            for req_id in trace_mappings:
                if req_id in req_map:
                    req_content = req_map[req_id]
                    if not req_content:
                        continue

                    similarity = await self.embedding_service.calculate_similarity(story_text, req_content)
                    if similarity < validation_settings.CONSISTENCY_THRESHOLD:
                        findings.append(
                            ValidationFinding(
                                id=f"SEM-DRIFT-{req_id}-{story_id}",
                                validator_name=self.name,
                                title="Semantic Drift Detected",
                                description=(
                                    f"Story '{title}' has low semantic similarity ({similarity:.2f}) "
                                    f"with its mapped requirement '{req_id}'. Threshold is {validation_settings.CONSISTENCY_THRESHOLD}."
                                ),
                                severity=Severity.MINOR,
                                field="user_story_text",
                                mitigation=(
                                    "Review the story content to ensure it accurately represents "
                                    "the business intent of the source requirement."
                                )
                            )
                        )

        return findings
