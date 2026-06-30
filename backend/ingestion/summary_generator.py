import json
from typing import Dict, Any
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class InputSummaryGenerator:
    """
    Generates a structured, concise BRD summary from raw ingested text
    prior to Agent 1 execution.
    """
    def __init__(self):
        self.llm = LLMClient()

    async def generate_summary(self, raw_text: str) -> Dict[str, Any]:
        """
        Calls the LLM to generate the BRD summary matching the required JSON schema.
        """
        system_prompt = (
            "You are an expert Business Analyst. Analyze the provided requirement text and "
            "generate a structured summary. You must return ONLY a valid JSON object with the "
            "exact keys listed below. Do not include any explanations or markdown formatting.\n\n"
            "Required JSON Schema:\n"
            "{\n"
            "  \"business_objective\": \"Short description of the business goal/objective.\",\n"
            "  \"functional_requirements\": [\"List of key functional requirements.\"],\n"
            "  \"non_functional_requirements\": [\"List of key non-functional requirements (security, performance, etc.).\"],\n"
            "  \"business_rules\": [\"List of key business rules and constraints.\"],\n"
            "  \"actors\": [\"List of primary actors and user roles.\"],\n"
            "  \"systems\": [\"List of external or internal systems mentioned.\"],\n"
            "  \"detected_domain\": \"Primary industry domain (e.g., Healthcare, E-Commerce).\",\n"
            "  \"summary\": \"A high-level 2-3 sentence narrative summary of the document.\"\n"
            "}"
        )
        
        prompt = (
            f"Please analyze the following requirement text and generate the JSON summary:\n\n"
            f"{raw_text}"
        )

        try:
            summary_dict = await self.llm.generate_json(prompt=prompt, system_prompt=system_prompt)
            # Ensure all required keys are present
            required_keys = [
                "business_objective", "functional_requirements", "non_functional_requirements",
                "business_rules", "actors", "systems", "detected_domain", "summary"
            ]
            for key in required_keys:
                if key not in summary_dict:
                    if key in ["functional_requirements", "non_functional_requirements", "business_rules", "actors", "systems"]:
                        summary_dict[key] = []
                    else:
                        summary_dict[key] = ""
            return summary_dict
        except Exception as e:
            logger.error(f"Failed to generate input summary: {e}")
            # Graceful fallback
            return {
                "business_objective": "Unable to generate summary due to an error.",
                "functional_requirements": [],
                "non_functional_requirements": [],
                "business_rules": [],
                "actors": [],
                "systems": [],
                "detected_domain": "Unknown",
                "summary": "Error generating summary."
            }
