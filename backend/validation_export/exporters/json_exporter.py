import json
import asyncio
from typing import List, Dict, Any
from backend.shared.exceptions import ExportError
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class JSONExporter:
    """
    Exports validation and generated user story schemas as clean structured JSON files.
    """
    async def export(
        self, 
        stories: List[Dict[str, Any]], 
        validation_results: Dict[str, Any], 
        output_path: str
    ) -> None:
        """
        Dumps story data and compliance metrics to standard JSON.
        """
        logger.info(f"Dumping pipeline outputs to JSON structure at {output_path}...")
        
        try:
            def serialize_and_save():
                payload = {
                    "user_stories": stories,
                    "validation_report": validation_results
                }
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                logger.info("JSON file generated successfully.")

            await asyncio.to_thread(serialize_and_save)
        except Exception as e:
            logger.error(f"JSON export failure: {str(e)}")
            raise ExportError(f"JSON export failed: {str(e)}")

# INTEGRATION NOTE
# JSONExporter creates human-readable output files. Keep format clean for API routing ingestion.
