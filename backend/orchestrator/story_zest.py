from typing import List, Dict, Any, Optional
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class StoryZestGenerator:
    """
    Generates a high-level Business Executive Summary (Story Zest) from generated user stories.
    Supports both Draft and Final versions.
    """
    def __init__(self):
        self.llm_client = LLMClient()

    async def generate_zest(
        self, 
        stories: List[Dict[str, Any]], 
        is_final: bool = False
    ) -> Dict[str, Any]:
        """
        Summarizes the user stories into a structured executive summary.
        """
        logger.info(f"Generating {'Final' if is_final else 'Draft'} Story Zest for {len(stories)} stories...")
        
        if not stories:
            return {
                "business_goal": "No stories generated yet.",
                "scope_summary": "Empty scope.",
                "actors": [],
                "key_features": [],
                "dependencies": [],
                "risks": [],
                "coverage_metrics": {"total_stories": 0}
            }

        # Calculate basic metrics
        epics = list(set(s.get("epic", "General") for s in stories))
        features = list(set(s.get("feature", "General") for s in stories))
        
        prompt = (
            f"You are a Principal Business Analyst. Summarize the following user stories into a high-level Business Executive Summary (Story Zest).\n\n"
            f"Stories:\n"
        )
        for i, s in enumerate(stories):
            prompt += f"- [{s.get('epic')} -> {s.get('feature')}] {s.get('title')}: {s.get('user_story')}\n"

        prompt += (
            f"\nProvide a structured JSON response with the following keys:\n"
            f"- \"business_goal\": Clear, concise statement of the business objective this package achieves.\n"
            f"- \"scope_summary\": A 2-3 sentence summary of the functional scope covered by these stories.\n"
            f"- \"actors\": List of key users or systems interacting with these features.\n"
            f"- \"key_features\": List of the most critical features or capabilities delivered.\n"
            f"- \"dependencies\": List of external systems, third-party APIs, or cross-feature dependencies.\n"
            f"- \"risks\": List of business, technical, or delivery risks identified from the stories.\n"
            f"- \"coverage_metrics\": A dictionary containing:\n"
            f"    - \"total_stories\": {len(stories)}\n"
            f"    - \"total_epics\": {len(epics)}\n"
            f"    - \"total_features\": {len(features)}\n"
            f"    - \"coverage_percentage\": 100 (or estimated coverage percentage)\n"
        )

        system_prompt = (
            "You are an expert Business Analyst. You write concise, professional executive summaries of software requirements. "
            "You must return ONLY a valid JSON object matching the requested schema. Do not include any conversational text or markdown formatting outside of the JSON."
        )

        try:
            zest_json = await self.llm_client.generate_json(prompt, system_prompt)
            # Ensure all keys exist
            for key in ["business_goal", "scope_summary", "actors", "key_features", "dependencies", "risks", "coverage_metrics"]:
                if key not in zest_json:
                    zest_json[key] = [] if key in ["actors", "key_features", "dependencies", "risks"] else ""
            
            # Inject metrics if LLM didn't fill them
            if not zest_json.get("coverage_metrics"):
                zest_json["coverage_metrics"] = {}
            zest_json["coverage_metrics"]["total_stories"] = len(stories)
            zest_json["coverage_metrics"]["total_epics"] = len(epics)
            zest_json["coverage_metrics"]["total_features"] = len(features)
            
            return zest_json
        except Exception as e:
            logger.error(f"Failed to generate Story Zest via LLM: {str(e)}")
            # Return fallback
            return {
                "business_goal": "Objective of the stories package.",
                "scope_summary": f"Functional scope containing {len(stories)} stories across {len(epics)} epics and {len(features)} features.",
                "actors": ["User"],
                "key_features": features[:5],
                "dependencies": [],
                "risks": [],
                "coverage_metrics": {
                    "total_stories": len(stories),
                    "total_epics": len(epics),
                    "total_features": len(features),
                    "coverage_percentage": 100
                }
            }
