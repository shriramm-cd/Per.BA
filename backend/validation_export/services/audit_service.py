from typing import Dict, Any
from backend.db.postgres import AsyncSessionLocal
from backend.validation_export.db_models import AuditEventDB
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class AuditService:
    """
    Enterprise Audit Service for registering and persisting pipeline lifecycle events.
    """
    @staticmethod
    async def log_event(job_id: str, event_type: str, payload: Dict[str, Any] = None) -> None:
        """
        Logs an audit event to the console and writes it to the PostgreSQL audit_events table.
        """
        payload = payload or {}
        logger.info(f"[AUDIT EVENT] Job: {job_id} | Type: {event_type} | Details: {payload}")
        
        try:
            async with AsyncSessionLocal() as session:
                try:
                    event = AuditEventDB(
                        job_id=job_id,
                        event_type=event_type,
                        payload=payload
                    )
                    session.add(event)
                    await session.commit()
                except Exception as e:
                    logger.error(f"Failed to persist audit event for job {job_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Audit persistence layer unavailable for job {job_id}: {str(e)}")
