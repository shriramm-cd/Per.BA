from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.api.schemas import AuditLogResponse
from backend.api.middleware import verify_api_key
from backend.db.postgres import get_db_session
from backend.db.models import AuditLog
from backend.shared.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/audit", tags=["Audit"])

@router.get("/logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    job_id: Optional[str] = Query(None, description="Filter logs by a specific Job transaction ID"),
    limit: int = Query(50, description="Maximum number of log entries to retrieve"),
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_api_key)
):
    """
    Retrieves execution histories, node statuses, and quality parameters from the audit trail database.
    """
    logger.info("Retrieving pipeline audit logs...")
    
    stmt = select(AuditLog)
    if job_id:
        stmt = stmt.where(AuditLog.job_id == job_id)
        
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    logs = res.scalars().all()

    return [
        AuditLogResponse(
            id=log.id,
            node_name=log.node_name,
            status=log.status,
            message=log.message,
            payload=log.payload,
            created_at=log.created_at
        )
        for log in logs
    ]

# INTEGRATION NOTE
# Audit trails are populated automatically by graph.py node executors.
# Logs are sorted by descending creation time (latest executions first).
