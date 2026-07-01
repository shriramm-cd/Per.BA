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

    def _build_rework_prompt(self, story_context: StoryContext, revision_package: Any) -> str:
        import json
        current_story = revision_package.get("current_story", {})
        preserve = revision_package.get("preserve_section", {})
        modify = revision_package.get("modify_section", {})
        ba_comments = revision_package.get("ba_comments", [])
        findings = revision_package.get("validation_findings", [])
        
        prompt = f"""
        You are reworking an existing Agile user story because it failed validation or was rejected by a Business Analyst.
        
        CURRENT USER STORY:
        Story ID: {revision_package.get("story_id")}
        Title: {current_story.get("title")}
        Story Text: {current_story.get("user_story")}
        Acceptance Criteria:
        {json.dumps(current_story.get("acceptance_criteria"), indent=2)}
        
        REVISION OBJECTIVES:
        1. PRESERVE the following sections exactly as they are. Do NOT modify them under any circumstances:
           - Story Title: {preserve.get("story_title")}
           - Actor: {preserve.get("actor")}
           - Approved Business Rules: {json.dumps(preserve.get("approved_business_rules"))}
           - Traceability Links: {json.dumps(preserve.get("traceability_links"))}
           - Approved Acceptance Criteria: {json.dumps(preserve.get("approved_acceptance_criteria"))}
           
        2. MODIFY or ADD the following based on feedback and validation failures:
           - Missing Requirements: {json.dumps(modify.get("missing_requirements"))}
           - Failed Acceptance Criteria: {json.dumps(modify.get("failed_acceptance_criteria"))}
           - Validator Findings: {json.dumps(modify.get("validator_findings"))}
           - BA Feedback: {json.dumps(modify.get("ba_feedback"))}
           - Missing Business Rules: {json.dumps(modify.get("missing_business_rules"))}
           - Wording Issues: {json.dumps(modify.get("wording_issues"))}
           
        BA Comments: {", ".join(ba_comments) if ba_comments else "None"}
        Failed Validations: {", ".join([f.get("description", "") for f in findings]) if findings else "None"}
        
        You must output a valid JSON object matching this exact structure:
        {{
          "story_id": "{revision_package.get("story_id")}",
          "epic": "{current_story.get("epic", "")}",
          "feature": "{current_story.get("feature", "")}",
          "user_story": {{
            "actor": "{preserve.get("actor")}",
            "goal": "reworked goal based on feedback",
            "benefit": "reworked benefit based on feedback"
          }},
          "acceptance_criteria": [
             // Include both the approved acceptance criteria and the reworked/new acceptance criteria
          ],
          "definition_of_done": {json.dumps(current_story.get("definition_of_done", []))},
          "summary": "{preserve.get("story_title")}",
          "priority": "{current_story.get("priority", "Medium")}",
          "version": {int(current_story.get("version", 1)) + 1},
          "traceability": {{
            "requirement_id": "{story_context.requirement_id}",
            "epic_id": "{self._safe_id(story_context.epic, "id")}",
            "feature_id": "{self._safe_id(story_context.feature, "id")}"
          }}
        }}
        """
        return prompt

    async def generate(self, orchestrated_payload: dict[str, Any]) -> list[GeneratedUserStory]:
        """Generates user stories for every provided story context."""
        story_contexts = self.validate_input(orchestrated_payload)
        revision_packages = orchestrated_payload.get("revision_packages", [])
        approved_stories = orchestrated_payload.get("approved_stories", [])
        
        # Map revision packages by story_id
        rev_map = {}
        for rp in revision_packages:
            story_id = rp.get("story_id")
            if story_id:
                rev_map[story_id] = rp
                
        # Map approved stories by story_id
        approved_map = {}
        for s in approved_stories:
            story_id = s.get("id")
            if story_id:
                approved_map[story_id] = s
                
        # Parallel generation using asyncio.Semaphore to limit concurrent API calls
        import asyncio
        sem = asyncio.Semaphore(10)
        
        async def process_context(story_context):
            async with sem:
                story_id = story_context.story_id
                
                if story_id in rev_map:
                    rp = rev_map[story_id]
                    self.logger.info(f"Regenerating rejected story {story_id} using revision package.")
                    
                    prompt = self._build_rework_prompt(story_context, rp)
                    system_prompt = (
                        "You are a senior Business Analyst and Product Owner. "
                        "Rework the existing Agile user story based on the provided revision objectives, preserving the required sections."
                    )
                    response_json = await self.llm_client.generate_json(prompt=prompt, system_prompt=system_prompt)
                    
                    generated_story = self.parse_response(response_json, story_context)
                    generated_story.story_id = story_id
                    generated_story.version = int(rp.get("current_story", {}).get("version", 1)) + 1
                    return generated_story
                    
                elif story_id in approved_map:
                    self.logger.info(f"Preserving approved story {story_id} as-is.")
                    s = approved_map[story_id]
                    
                    from backend.agents.schemas import Traceability, UserStoryContent, Metadata
                    
                    story_text = s.get("user_story", "")
                    goal = ""
                    benefit = ""
                    if "I want" in story_text and "so that" in story_text:
                        try:
                            goal = story_text.split("so that")[0].split("I want")[1].strip()
                            benefit = story_text.split("so that")[1].strip()
                        except Exception:
                            pass
                            
                    ac_list = []
                    for ac in s.get("acceptance_criteria", []):
                        if isinstance(ac, dict):
                            ac_list.append(ac.get("statement", ""))
                        else:
                            ac_list.append(str(ac))
                            
                    gen_story = GeneratedUserStory(
                        story_id=story_id,
                        traceability=Traceability(
                            requirement_id=story_context.requirement_id,
                            epic_id=self._safe_id(story_context.epic, "id"),
                            feature_id=self._safe_id(story_context.feature, "id")
                        ),
                        epic=s.get("epic", ""),
                        feature=s.get("feature", ""),
                        user_story=UserStoryContent(
                            actor=s.get("actor") or "User",
                            goal=goal,
                            benefit=benefit
                        ),
                        acceptance_criteria=ac_list,
                        definition_of_done=s.get("definition_of_done") or [],
                        summary=s.get("title", ""),
                        priority=s.get("priority", "Medium"),
                        version=int(s.get("version", 1)),
                        metadata=Metadata(
                            generated_by="Agent-3-Preserved",
                            generated_timestamp=datetime.now(timezone.utc).isoformat(),
                            domain=s.get("epic", ""),
                            version="1.0",
                            confidence_score=1.0,
                            source_story_count=1
                        )
                    )
                    return gen_story
                else:
                    return await self.generate_story(story_context)

        tasks = [process_context(story_context) for story_context in story_contexts]
        generated = await asyncio.gather(*tasks)
        return list(generated)

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
    generated_stories = await generator.generate({
        "story_contexts": input_data.get("story_contexts", []),
        "revision_packages": input_data.get("revision_packages", []),
        "approved_stories": input_data.get("approved_stories", [])
    })

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

