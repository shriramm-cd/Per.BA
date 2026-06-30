import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from typing import Dict, Any, List
from backend.validation_export.schemas import (
    ValidationContext, 
    ValidationExecutionSummary, 
    DecisionOutcome, 
    RevisionPackage,
    ValidatedStoryPackage
)
from backend.validation_export.context import ValidationContextBuilder
from backend.validation_export.decision_rules import DecisionRulesEngine
from backend.validation_export.revision_engine import RevisionEngine
from backend.validation_export.reporting import ReportingEngine
from backend.validation_export.services.security_service import SecurityService
from backend.validation_export.services.audit_service import AuditService

# Validators
from backend.validation_export.validators import (
    StructuralValidator, TraceabilityValidator, CoverageValidator,
    BusinessRulesValidator, DependencyValidator, AcceptanceCriteriaValidator,
    InvestValidator, SemanticValidator, HallucinationValidator,
    ConsistencyValidator, DuplicateValidator, TechnicalValidator
)

# Database
from backend.db.postgres import AsyncSessionLocal
from backend.validation_export.db_models import (
    ValidationResultDB, ValidationFindingDB, BAReviewDB, 
    ValidatedStoryPackageDB, RevisionPackageDB
)
from sqlalchemy import select

router = APIRouter(prefix="/api/v1/validation", tags=["Validation"])

@router.post("/validate", response_model=Dict[str, Any])
async def validate_story_package(
    payload: Dict[str, Any],
    user_info: Dict[str, Any] = Depends(SecurityService.authenticate)
):
    """
    Executes all 12 validators in parallel, evaluates decision rules,
    and records audit events and results.
    """
    job_id = payload.get("job_id") or "DEV-JOB-123"
    retry_count = payload.get("retry_count", 0)
    
    await AuditService.log_event(job_id, "VALIDATION_STARTED", {"retry_count": retry_count})
    
    # 1. Build context
    context = ValidationContextBuilder.build(payload)

    # 2. Instantiate validators
    validators = [
        StructuralValidator(), TraceabilityValidator(), CoverageValidator(),
        BusinessRulesValidator(), DependencyValidator(), AcceptanceCriteriaValidator(),
        InvestValidator(), SemanticValidator(), HallucinationValidator(),
        ConsistencyValidator(), DuplicateValidator(), TechnicalValidator()
    ]

    # 3. Parallel Execution using asyncio.gather
    import asyncio
    import time
    
    start_time = time.perf_counter()
    results = await asyncio.gather(*[v.validate(context) for v in validators])
    total_time = (time.perf_counter() - start_time) * 1000.0

    # 4. Aggregate Findings
    findings = []
    validators_passed = []
    validators_failed = []
    critical_count = 0
    major_count = 0
    minor_count = 0
    info_count = 0

    for r in results:
        findings.extend(r.findings)
        if r.status == "PASSED":
            validators_passed.append(r.validator_name)
        else:
            validators_failed.append(r.validator_name)
            
        critical_count += r.severity_summary.get("CRITICAL", 0)
        major_count += r.severity_summary.get("MAJOR", 0)
        minor_count += r.severity_summary.get("MINOR", 0)
        info_count += r.severity_summary.get("INFO", 0)

    # Calculate Coverage Score
    total_reqs = len(context.requirements)
    uncovered_req_ids = {f.id.split("-")[-1] for f in findings if "COV-UNCOVERED-REQ" in f.id}
    coverage_pct = ((total_reqs - len(uncovered_req_ids)) / total_reqs * 100.0) if total_reqs > 0 else 100.0

    # 5. Build Execution Summary
    summary = ValidationExecutionSummary(
        job_id=job_id,
        validators_passed=validators_passed,
        validators_failed=validators_failed,
        critical_count=critical_count,
        major_count=major_count,
        minor_count=minor_count,
        info_count=info_count,
        execution_time=round(total_time, 2),
        decision=DecisionOutcome.PASS  # placeholder
    )

    # 6. Evaluate Decision Rules
    engine = DecisionRulesEngine()
    decision = engine.evaluate(summary, coverage_pct, retry_count)
    summary.decision = decision

    # 7. Persist Results and Findings
    async with AsyncSessionLocal() as session:
        # Create validation result record
        db_result = ValidationResultDB(
            id=str(uuid_id := os.urandom(16).hex()),
            job_id=job_id,
            quality_score=round(100.0 - (critical_count * 25 + major_count * 10 + minor_count * 3), 2),
            coverage_score=round(coverage_pct, 2),
            traceability_score=round(100.0 - (len([f for f in findings if "TRACE-" in f.id]) * 15), 2),
            decision=decision.value,
            retry_count=retry_count
        )
        session.add(db_result)
        
        # Add findings
        for f in findings:
            db_finding = ValidationFindingDB(
                id=f.id,
                validation_result_id=uuid_id,
                validator_name=f.validator_name,
                title=f.title,
                description=f.description,
                severity=f.severity.value,
                field=f.field,
                mitigation=f.mitigation
            )
            session.add(db_finding)
            
        await session.commit()

    # 8. Generate Reports
    reports = ReportingEngine.generate_all_reports(context, summary, findings)

    await AuditService.log_event(
        job_id, 
        "VALIDATION_COMPLETED", 
        {"decision": decision.value, "failed_validators": validators_failed}
    )

    return {
        "job_id": job_id,
        "decision": decision.value,
        "summary": summary.model_dump(),
        "findings": [f.model_dump() for f in findings],
        "reports": reports
    }

@router.post("/rework", response_model=RevisionPackage)
async def generate_rework_package(
    payload: Dict[str, Any],
    user_info: Dict[str, Any] = Depends(SecurityService.authenticate)
):
    """
    Generates and persists a RevisionPackage for Agent 3.
    """
    job_id = payload.get("job_id")
    if not job_id:
        raise HTTPException(status_code=400, detail="Missing job_id")
        
    stories = payload.get("user_stories", [])
    findings_raw = payload.get("findings", [])
    retry_count = payload.get("retry_count", 0)
    ba_comments = payload.get("ba_comments", "")

    from backend.validation_export.schemas import ValidationFinding, Severity
    findings = []
    for f in findings_raw:
        findings.append(ValidationFinding(
            id=f.get("id"),
            validator_name=f.get("validator_name"),
            title=f.get("title"),
            description=f.get("description"),
            severity=Severity(f.get("severity", "MAJOR")),
            field=f.get("field"),
            mitigation=f.get("mitigation")
        ))

    package = await RevisionEngine.generate_package(
        job_id=job_id,
        stories=stories,
        findings=findings,
        retry_count=retry_count,
        ba_comments=ba_comments
    )
    
    await AuditService.log_event(job_id, "REWORK_CREATED", {"package_id": package.package_id})
    return package

@router.post("/review", response_model=Dict[str, Any])
async def submit_ba_review(
    payload: Dict[str, Any],
    user_info: Dict[str, Any] = Depends(SecurityService.authenticate)
):
    """
    Saves a BA manual review decision and logs audit events.
    """
    SecurityService.authorize(user_info, ["BA", "ADMIN"])
    
    job_id = payload.get("job_id")
    reviewer = payload.get("reviewer") or user_info.get("user", "BA_USER")
    decision = payload.get("decision")  # APPROVE, REWORK, REJECT
    comments = payload.get("comments", "")
    edits = payload.get("edits", {})

    if not job_id or not decision:
        raise HTTPException(status_code=400, detail="Missing job_id or decision")

    # Persist review
    import uuid
    async with AsyncSessionLocal() as session:
        db_review = BAReviewDB(
            id=str(uuid.uuid4()),
            job_id=job_id,
            reviewer=reviewer,
            decision=decision,
            comments=comments,
            edits=edits
        )
        session.add(db_review)
        await session.commit()

    # Log audit event
    event_type = f"BA_{decision.upper()}"
    await AuditService.log_event(job_id, event_type, {"reviewer": reviewer, "comments": comments})

    return {"status": "success", "next_state": "PUBLISHED" if decision == "APPROVE" else "REWORK" if decision == "REWORK" else "FAILED"}

@router.get("/jobs/{job_id}/report", response_model=Dict[str, Any])
async def get_validation_report(
    job_id: str,
    user_info: Dict[str, Any] = Depends(SecurityService.authenticate)
):
    """
    Retrieves the latest validation result and findings for a job.
    """
    async with AsyncSessionLocal() as session:
        # Get latest validation result
        stmt = select(ValidationResultDB).where(ValidationResultDB.job_id == job_id).order_by(ValidationResultDB.created_at.desc())
        res = await session.execute(stmt)
        result = res.scalars().first()
        
        if not result:
            raise HTTPException(status_code=404, detail="No validation report found for this job ID.")
            
        # Get findings
        stmt_f = select(ValidationFindingDB).where(ValidationFindingDB.validation_result_id == result.id)
        res_f = await session.execute(stmt_f)
        findings = res_f.scalars().all()

        return {
            "job_id": job_id,
            "quality_score": result.quality_score,
            "coverage_score": result.coverage_score,
            "traceability_score": result.traceability_score,
            "decision": result.decision,
            "retry_count": result.retry_count,
            "created_at": result.created_at.isoformat(),
            "findings": [{
                "id": f.id,
                "validator_name": f.validator_name,
                "title": f.title,
                "description": f.description,
                "severity": f.severity,
                "field": f.field,
                "mitigation": f.mitigation
            } for f in findings]
        }

@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """
    Serves the high-fidelity glassmorphic UI dashboard.
    """
    dashboard_path = os.path.join(os.path.dirname(__file__), "ui", "dashboard.html")
    if not os.path.exists(dashboard_path):
        raise HTTPException(status_code=404, detail="Dashboard UI file not found.")
        
    with open(dashboard_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return html_content
