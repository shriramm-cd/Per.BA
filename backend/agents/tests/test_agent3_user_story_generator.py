import asyncio

from backend.agents.agent3_user_story_generator import UserStoryGenerator
from backend.agents.schemas import GeneratedUserStory


class StubLLMClient:
    async def generate_json(self, prompt: str, system_prompt: str | None = None) -> dict:
        return {
            "story_id": "US-001",
            "traceability": {
                "requirement_id": "FR-001",
                "epic_id": "EP-01",
                "feature_id": "FT-01",
            },
            "epic": "Authentication",
            "feature": "Email Login",
            "user_story": {
                "actor": "Customer",
                "goal": "Login using email and password",
                "benefit": "Securely access banking services",
            },
            "acceptance_criteria": [
                "Given a registered customer, when they enter valid credentials, then they are authenticated."
            ],
            "definition_of_done": [
                "The story is implemented and reviewed.",
                "The login flow is tested end-to-end."
            ],
            "summary": "Allows registered customers to log in securely.",
            "priority": "High",
            "version": 1,
        }


class StubRenderer:
    def render(self, template_name: str, context: dict) -> str:
        return f"prompt:{template_name}"


def test_generate_creates_story_from_story_context() -> None:
    generator = UserStoryGenerator(
        llm_client=StubLLMClient(),
        renderer=StubRenderer(),
    )

    story_contexts = [
        {
            "story_context_id": "CTX-001",
            "requirement": {"id": "FR-001", "text": "Customer can login using email and password."},
            "actor": "Customer",
            "epic": {"id": "EP-01", "name": "Authentication"},
            "feature": {"id": "FT-01", "name": "Email Login"},
            "business_rules": ["Account should be active"],
            "priority": "High",
        }
    ]

    stories = asyncio.run(generator.generate({"story_contexts": story_contexts}))

    assert len(stories) == 1
    assert isinstance(stories[0], GeneratedUserStory)
    assert stories[0].story_id == "US-001"
    assert stories[0].user_story.goal == "Login using email and password"
