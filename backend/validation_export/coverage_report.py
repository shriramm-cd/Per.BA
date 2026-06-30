from typing import Dict, Any, List, Set
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class CoverageReporter:
    """
    Computes trace-coverage metrics mapping source requirements to generated user stories.
    """
    @staticmethod
    def calculate_coverage(stories: List[Dict[str, Any]], requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extracts mapped requirement IDs from all stories and matches them against source requirement IDs.
        """
        # Collect all requirement identifiers in the system
        # Support both 'id' (extracted schema format) and 'trace_id' (DB format)
        source_req_ids: Set[str] = set()
        for r in requirements:
            if "id" in r:
                source_req_ids.add(r["id"])
            if "trace_id" in r:
                source_req_ids.add(r["trace_id"])

        if not source_req_ids:
            logger.warning("No source requirements found. Coverage defaults to 0%.")
            return {
                "requirements_covered": [],
                "requirements_uncovered": [],
                "coverage_percentage": 0.0
            }

        # Collect all mapped requirement IDs from generated stories
        mapped_req_ids: Set[str] = set()
        for story in stories:
            for trace in story.get("trace_mappings", []):
                mapped_req_ids.add(trace)

        # Intersect keys to verify real coverage
        covered = source_req_ids.intersection(mapped_req_ids)
        uncovered = source_req_ids.difference(mapped_req_ids)

        coverage_pct = (len(covered) / len(source_req_ids)) * 100.0
        
        logger.info(f"Trace Coverage check: {len(covered)}/{len(source_req_ids)} requirements covered ({coverage_pct:.2f}%)")

        return {
            "requirements_covered": list(covered),
            "requirements_uncovered": list(uncovered),
            "coverage_percentage": round(coverage_pct, 2)
        }

# INTEGRATION NOTE
# CoverageReporter runs purely algorithmically without LLM calls.
# It provides instant structural audit indicators of completeness.
