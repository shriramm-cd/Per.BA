from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from backend.agents.schemas import (
    AcceptanceCriteria,
    GeneratedUserStory,
    Metadata,
    Response,
    StoryContext,
    UserStory,
    UserStoryGeneratorOutput,
)
from backend.shared.jinja_renderer import JinjaRenderer
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger


class UserStoryGenerator:
    """Generates one grounded user story per story context."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        renderer: Optional[JinjaRenderer] = None,
        logger: Optional[Any] = None,
    ) -> None:
        self.llm_client = llm_client or LLMClient()
        self.renderer = renderer or JinjaRenderer()
        self.logger = logger or get_logger(__name__)

    def validate_input(self, orchestrated_payload: dict[str, Any]) -> list[StoryContext]:
        """Validates the orchestrated payload and returns normalized story contexts."""
        if not isinstance(orchestrated_payload, dict):
            raise TypeError("Input payload must be a dictionary.")

        raw_contexts = orchestrated_payload.get("story_contexts", [])
        if not isinstance(raw_contexts, list) or not raw_contexts:
            raise ValueError("At least one story_context is required.")

        contexts: list[StoryContext] = []
        for raw_context in raw_contexts:
            contexts.append(StoryContext.model_validate(raw_context))
        return contexts

    def build_grounded_context(self, story_context: StoryContext) -> dict[str, Any]:
        """Builds the minimal context needed for one story prompt."""
        requirement = self._normalize_value(story_context.requirement, "text")
        epic = self._normalize_value(story_context.epic, "name")
        feature = self._normalize_value(story_context.feature, "name")

        return {
            "story_context": story_context.model_dump(),
            "requirement": requirement,
            "epic": epic,
            "feature": feature,
            "actor": story_context.actor or "User",
            "business_rules": story_context.business_rules,
            "priority": story_context.priority,
            "traceability": story_context.traceability or {},
        }

    def render_prompt(self, grounded_context: dict[str, Any]) -> str:
        """Renders the Agent 3 prompt with grounded context."""
        return self.renderer.render("agent3.jinja2", grounded_context)

    async def generate_story(self, story_context: StoryContext) -> GeneratedUserStory:
        """Generates one user story from a single story context."""
        grounded_context = self.build_grounded_context(story_context)
        prompt = self.render_prompt(grounded_context)
        system_prompt = (
            "You are a senior Business Analyst and Product Owner. "
            "Create one grounded Agile user story using only the supplied context."
        )
        response_json = await self.llm_client.generate_json(prompt=prompt, system_prompt=system_prompt)
        return self.parse_response(response_json, story_context)

    def parse_response(self, response: dict[str, Any], story_context: StoryContext) -> GeneratedUserStory:
        """Parses and validates an LLM response into a GeneratedUserStory."""
        if not isinstance(response, dict):
            raise ValueError("LLM response must be a JSON object.")

        traceability = response.get("traceability", {})
        if not isinstance(traceability, dict):
            raise ValueError("Traceability must be a JSON object.")

        metadata = Metadata(
            generated_by="Agent-3",
            generated_timestamp=datetime.now(timezone.utc).isoformat(),
            domain=str(self._normalize_value(story_context.epic, "name")),
            version="1.0",
            confidence_score=0.9,
            source_story_count=1,
        )

        user_story_payload = response.get("user_story", {})
        if not isinstance(user_story_payload, dict):
            user_story_payload = {}

        return GeneratedUserStory(
            story_id=str(response.get("story_id") or response.get("id") or "US-001"),
            traceability={
                "requirement_id": str(traceability.get("requirement_id") or story_context.requirement_id),
                "epic_id": str(traceability.get("epic_id") or self._safe_id(story_context.epic, "id")),
                "feature_id": str(traceability.get("feature_id") or self._safe_id(story_context.feature, "id")),
            },
            epic=str(response.get("epic") or self._normalize_value(story_context.epic, "name")),
            feature=str(response.get("feature") or self._normalize_value(story_context.feature, "name")),
            user_story={
                "actor": str(user_story_payload.get("actor") or story_context.actor or "User"),
                "goal": str(user_story_payload.get("goal") or "complete the requested task"),
                "benefit": str(user_story_payload.get("benefit") or "deliver business value"),
            },
            acceptance_criteria=[str(item) for item in response.get("acceptance_criteria", [])],
            definition_of_done=[str(item) for item in response.get("definition_of_done", [])],
            summary=str(response.get("summary") or "Generated from the supplied story context."),
            priority=str(response.get("priority") or story_context.priority or "Medium"),
            version=int(response.get("version") or 1),
            metadata=metadata,
        )

    async def generate(self, orchestrated_payload: dict[str, Any]) -> list[GeneratedUserStory]:
        """Generates user stories for every provided story context."""
        story_contexts = self.validate_input(orchestrated_payload)
        generated: list[GeneratedUserStory] = []
        for story_context in story_contexts:
            generated_story = await self.generate_story(story_context)
            generated.append(generated_story)
        return generated

    def _normalize_value(self, value: Any, key: str) -> str:
        """Normalizes a nested context value into a readable string."""
        if isinstance(value, dict):
            return str(value.get(key) or "")
        if hasattr(value, "model_dump"):
            return str(getattr(value, key, "") or "")
        return str(value or "")

    def _safe_id(self, value: Any, key: str) -> str:
        """Safely extracts an ID field from a context object."""
        if isinstance(value, dict):
            return str(value.get(key) or "")
        if hasattr(value, "model_dump"):
            return str(getattr(value, key, "") or "")
        return str(value or "")


async def run(input_data: dict[str, Any], config: Optional[dict[str, Any]] = None) -> UserStoryGeneratorOutput:
    """Compatibility wrapper used by the orchestrator and API layers."""
    generator = UserStoryGenerator()
    generated_stories = await generator.generate({"story_contexts": input_data.get("story_contexts", [])})

    legacy_stories: list[UserStory] = []
    for story in generated_stories:
        acceptance_criteria = [
            AcceptanceCriteria(statement=item) for item in story.acceptance_criteria
        ]
        legacy_stories.append(
            UserStory(
                id=story.story_id,
                epic_id=story.traceability.epic_id,
                feature_id=story.traceability.feature_id,
                title=story.summary,
                user_story_text=(
                    f"As a {story.user_story.actor or 'user'}, "
                    f"I want {story.user_story.goal or 'the requested capability'}, "
                    f"so that {story.user_story.benefit or 'business value is delivered'}"
                ),
                acceptance_criteria=acceptance_criteria,
                trace_mappings=[story.traceability.requirement_id],
            )
        )


    response = Response(stories=generated_stories, summary="Generated grounded stories from story contexts.")
    generator.logger.info("Agent 3 completed generation for %s story contexts.", len(generated_stories))
    return UserStoryGeneratorOutput(
        user_stories=legacy_stories,
        plain_text_summary=response.summary,
    )
