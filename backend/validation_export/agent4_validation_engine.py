import os
import time
import asyncio
import uuid
from typing import Dict, Any, Optional, List
from backend.validation_export.schemas import (
    ValidationEngineOutput, 
    ValidationContext, 
    ValidationExecutionSummary, 
    DecisionOutcome
)
from backend.validation_export.context import ValidationContextBuilder
from backend.validation_export.decision_rules import DecisionRulesEngine
from backend.validation_export.reporting import ReportingEngine
from backend.validation_export.services.audit_service import AuditService

# Import all 12 validators
from backend.validation_export.validators import (
    StructuralValidator, TraceabilityValidator, CoverageValidator,
    BusinessRulesValidator, DependencyValidator, AcceptanceCriteriaValidator,
    InvestValidator, SemanticValidator, HallucinationValidator,
    ConsistencyValidator, DuplicateValidator, TechnicalValidator
)

# Database
from backend.db.postgres import AsyncSessionLocal
from backend.validation_export.db_models import ValidationResultDB, ValidationFindingDB
from backend.shared.logger import get_logger

logger = get_logger(__name__)

async def run(input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> ValidationEngineOutput:
    """
    Agent 4: Validation Engine.
    Executes the 12 validators in parallel, applies the Decision Rules Engine,
    generates validation reports, and determines the routing path.
    """
    job_id = input_data.get("job_id") or "DEV-JOB-123"
    retry_count = input_data.get("retry_count", 0)
    
    logger.info(f"Executing Agent 4 Validation Engine for job: {job_id} (Attempt: {retry_count})...")
    await AuditService.log_event(job_id, "VALIDATION_STARTED", {"retry_count": retry_count})

    stories = input_data.get("user_stories", [])
    requirements = input_data.get("requirements", [])

    # 1. Edge case: empty data
    if not stories:
        logger.warning("No stories passed to Agent 4. Approving default empty dataset.")
        return ValidationEngineOutput(
            invest_results=[],
            hallucination_results=[],
            coverage_verified=[],
            quality_score=0.0,
            is_approved=False,
            summary=None
        )

    # 2. Build Validation Context
    context = ValidationContextBuilder.build(input_data)

    # 3. Instantiate Validators
    validators = [
        StructuralValidator(),
        TraceabilityValidator(),
        CoverageValidator(),
        BusinessRulesValidator(),
        DependencyValidator(),
        AcceptanceCriteriaValidator(),
        InvestValidator(),
        SemanticValidator(),
        HallucinationValidator(),
        ConsistencyValidator(),
        DuplicateValidator(),
        TechnicalValidator()
    ]

    # 4. Execute all 12 validators concurrently
    start_time = time.perf_counter()
    results = await asyncio.gather(*[v.validate(context) for v in validators])
    total_time = (time.perf_counter() - start_time) * 1000.0

    # 5. Aggregate Findings and Statistics
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
    total_reqs = len(requirements)
    uncovered_req_ids = {f.id.replace("COV-UNCOVERED-REQ-", "") for f in findings if "COV-UNCOVERED-REQ-" in f.id}
    coverage_pct = ((total_reqs - len(uncovered_req_ids)) / total_reqs * 100.0) if total_reqs > 0 else 100.0


    # 6. Build Execution Summary
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

    # 7. Evaluate Decision Rules
    decision_engine = DecisionRulesEngine()
    decision = decision_engine.evaluate(summary, coverage_pct, retry_count)
    summary.decision = decision

    is_approved = decision == DecisionOutcome.PASS

    # Calculate Quality Score
    penalty = (critical_count * 25) + (major_count * 10) + (minor_count * 3) + (info_count * 1)
    quality_score = max(0.0, 100.0 - penalty)

    # 8. Persist Results to Database
    version_number = input_data.get("version_number", 1)
    execution_id = input_data.get("execution_id")
    pipeline_run_id = input_data.get("pipeline_run_id")
    status_val = "COMPLETED"

    try:
        async with AsyncSessionLocal() as session:
            try:
                db_result = ValidationResultDB(
                    id=str(uuid_id := uuid.uuid4()),
                    job_id=job_id,
                    quality_score=quality_score,
                    coverage_score=round(coverage_pct, 2),
                    traceability_score=round(100.0 - (len([f for f in findings if "TRACE-" in f.id]) * 15), 2),
                    decision=decision.value,
                    retry_count=retry_count,
                    validators_passed=len(validators_passed),
                    validators_failed=len(validators_failed),
                    critical_count=critical_count,
                    major_count=major_count,
                    minor_count=minor_count,
                    info_count=info_count,
                    version_number=version_number,
                    execution_id=execution_id,
                    pipeline_run_id=pipeline_run_id,
                    status=status_val
                )
                session.add(db_result)
                
                for f in findings:
                    db_finding = ValidationFindingDB(
                        id=str(uuid.uuid4()),
                        validation_result_id=str(uuid_id),
                        validator_name=f.validator_name,
                        title=f.title,
                        description=f.description,
                        severity=f.severity.value,
                        field=f.field,
                        mitigation=f.mitigation,
                        version_number=version_number,
                        execution_id=execution_id,
                        pipeline_run_id=pipeline_run_id,
                        status=status_val
                    )
                    session.add(db_finding)
                    
                await session.commit()
                logger.info(f"Validation result and {len(findings)} findings saved to DB for job: {job_id}")
            except Exception as e:
                logger.error(f"Failed to persist validation results for job {job_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Validation persistence layer unavailable for job {job_id}: {str(e)}")

    # Log completion audit event
    await AuditService.log_event(
        job_id, 
        "VALIDATION_COMPLETED", 
        {"decision": decision.value, "failed_validators": validators_failed, "quality_score": quality_score}
    )

    logger.info(f"Agent 4 execution complete. Decision: {decision.value} | Quality Score: {quality_score}")

    domain_detection = input_data.get("domain_detection")


    return ValidationEngineOutput(
        invest_results=[],  # Deprecated in favor of the unified summary
        hallucination_results=[],  # Deprecated in favor of the unified summary
        coverage_verified=[r.get("id") or r.get("trace_id") for r in requirements if (r.get("id") or r.get("trace_id")) not in uncovered_req_ids] if isinstance(requirements, list) else [],
        quality_score=quality_score,
        is_approved=is_approved,
        summary=summary,
        domain_detection=domain_detection
    )


