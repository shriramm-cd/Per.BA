import os
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
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

async def run_rework_pipeline(job_id: str, edits: Dict[str, Any], comments: str):
    from backend.db.postgres import AsyncSessionLocal
    from backend.db.models import Job, Story, Requirement
    from backend.validation_export.db_models import ValidationResultDB, ValidationFindingDB
    from backend.validation_export.schemas import ValidationFinding, Severity
    from backend.validation_export.revision_engine import RevisionEngine
    from backend.agents.agent3_user_story_generator import run as run_agent3
    from backend.validation_export.agent4_validation_engine import run as run_agent4
    from sqlalchemy import select, delete
    
    from backend.shared.logger import get_logger
    logger = get_logger(__name__)
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. Get Job and increment retry_count
            stmt_job = select(Job).where(Job.id == job_id)
            res_job = await session.execute(stmt_job)
            job = res_job.scalar_one_or_none()
            if not job:
                logger.error(f"Job {job_id} not found for rework.")
                return
                
            meta = dict(job.meta_info or {})
            retry_count = meta.get("retry_count", 0) + 1
            meta["retry_count"] = retry_count
            job.meta_info = meta
            
            if retry_count > 3:
                logger.warning(f"Job {job_id} reached max retry attempts. Status set to MANUAL_RESOLUTION_REQUIRED.")
                job.status = "MANUAL_RESOLUTION_REQUIRED"
                await session.commit()
                return
                
            job.status = "RUNNING"
            await session.commit()
            
            # 2. Get all stories
            stmt_stories = select(Story).where(Story.job_id == job_id)
            res_stories = await session.execute(stmt_stories)
            stories = res_stories.scalars().all()
            
            # 3. Get latest validation findings
            stmt_val = select(ValidationResultDB).where(ValidationResultDB.job_id == job_id).order_by(ValidationResultDB.created_at.desc())
            res_val = await session.execute(stmt_val)
            val_result = res_val.scalars().first()
            
            findings = []
            if val_result:
                stmt_f = select(ValidationFindingDB).where(ValidationFindingDB.validation_result_id == val_result.id)
                res_f = await session.execute(stmt_f)
                db_findings = res_f.scalars().all()
                for f in db_findings:
                    findings.append(ValidationFinding(
                        id=f.id,
                        validator_name=f.validator_name,
                        title=f.title,
                        description=f.description,
                        severity=Severity(f.severity),
                        field=f.field,
                        mitigation=f.mitigation
                    ))
            
            # 4. Separate approved and rejected stories
            rejected_stories = []
            approved_stories = []
            ba_comments_dict = {}
            
            stories_list = []
            for s in stories:
                s_dict = {
                    "id": s.id,
                    "epic": s.epic,
                    "feature": s.feature,
                    "title": s.title,
                    "user_story": s.user_story,
                    "acceptance_criteria": s.acceptance_criteria,
                    "trace_mappings": s.trace_mappings,
                    "definition_of_done": s.validation_results.get("definition_of_done", []) if s.validation_results else []
                }
                stories_list.append(s_dict)
                
                story_id = s.id
                ba_status = edits.get(story_id, {}).get("status")
                ba_feedback = edits.get(story_id, {}).get("feedback")
                if ba_feedback:
                    ba_comments_dict[story_id] = ba_feedback
                    
                has_findings = any((f.field and story_id in f.field) or (f.id and story_id in f.id) for f in findings)
                
                if ba_status == "REJECTED" or ba_feedback or has_findings:
                    rejected_stories.append(s_dict)
                else:
                    approved_stories.append(s_dict)
                    
            # 5. Generate story revision packages
            revision_packages = RevisionEngine.generate_story_revision_packages(
                job_id=job_id,
                stories=stories_list,
                findings=findings,
                ba_comments_dict=ba_comments_dict
            )
            
            # 6. Reconstruct story contexts
            stmt_reqs = select(Requirement).where(Requirement.job_id == job_id)
            res_reqs = await session.execute(stmt_reqs)
            db_reqs = res_reqs.scalars().all()
            req_map = {r.trace_id: r for r in db_reqs}
            
            story_contexts = []
            for s in stories:
                req_id = s.trace_mappings[0] if s.trace_mappings else ""
                req_obj = req_map.get(req_id)
                
                ctx = {
                    "story_id": s.id,
                    "requirement_id": req_id,
                    "requirement": {"id": req_id, "text": req_obj.content if req_obj else ""},
                    "epic": {"id": s.epic, "name": s.epic},
                    "feature": {"id": s.feature, "name": s.feature},
                    "actor": s.user_story.split("I want")[0].replace("As a ", "").strip() if "I want" in s.user_story else "User",
                    "business_rules": s.acceptance_criteria,
                    "dependencies": [],
                    "priority": "Medium",
                    "validation": {},
                    "traceability": {}
                }
                story_contexts.append(ctx)
                
            # 7. Run Agent 3 to regenerate only rejected stories
            agent3_output = await run_agent3({
                "story_contexts": story_contexts,
                "revision_packages": [rp.model_dump() for rp in revision_packages],
                "approved_stories": approved_stories
            })
            
            # 8. Save updated stories to DB
            await session.execute(delete(Story).where(Story.job_id == job_id))
            for us in agent3_output.user_stories:
                story_model = Story(
                    id=us.id,
                    job_id=job_id,
                    epic=us.epic_id,
                    feature=us.feature_id,
                    title=us.title,
                    user_story=us.user_story_text,
                    acceptance_criteria=[ac.model_dump() for ac in us.acceptance_criteria],
                    trace_mappings=us.trace_mappings,
                    validation_results=None,
                    plain_text_summary=agent3_output.plain_text_summary
                )
                session.add(story_model)
            await session.commit()
            
            # 9. Re-run Agent 4 (Validation Engine)
            state_data = {
                "job_id": job_id,
                "retry_count": retry_count,
                "user_stories": [
                    {
                        "id": s.id,
                        "epic": s.epic_id,
                        "feature": s.feature_id,
                        "title": s.title,
                        "user_story": s.user_story_text,
                        "acceptance_criteria": [ac.model_dump() for ac in s.acceptance_criteria],
                        "trace_mappings": s.trace_mappings
                    }
                    for s in agent3_output.user_stories
                ],
                "requirements": [
                    {
                        "id": r.trace_id,
                        "content": r.content,
                        "actors": r.actors,
                        "business_rules": r.business_rules
                    }
                    for r in db_reqs
                ],
                "epics": meta.get("epics", []),
                "features": meta.get("features", []),
                "business_rules": meta.get("business_rules", []),
                "actors": meta.get("actors", []),
                "domain_detection": meta.get("domain_detection", None)
            }
            
            validation_output = await run_agent4(state_data)
            
            # 10. Update job status to HUMAN_REVIEW so BA can review again
            stmt_job = select(Job).where(Job.id == job_id)
            res_job = await session.execute(stmt_job)
            job = res_job.scalar_one_or_none()
            if job:
                job.status = "HUMAN_REVIEW"
                await session.commit()
                
            logger.info(f"Rework pipeline completed successfully for job: {job_id}")
            
        except Exception as e:
            logger.error(f"Rework pipeline failed for job {job_id}: {str(e)}")
            try:
                stmt_job = select(Job).where(Job.id == job_id)
                res_job = await session.execute(stmt_job)
                job = res_job.scalar_one_or_none()
                if job:
                    job.status = "FAILED"
                    job.error_message = str(e)
                    await session.commit()
            except Exception as db_ex:
                logger.error(f"Failed to set job status to FAILED: {db_ex}")

@router.post("/review", response_model=Dict[str, Any])
async def submit_ba_review(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    user_info: Dict[str, Any] = Depends(SecurityService.authenticate)
):
    """
    Saves a BA manual review decision, generates Final Story Zest on approval,
    and logs audit events.
    """
    SecurityService.authorize(user_info, ["BA", "ADMIN"])
    
    job_id = payload.get("job_id")
    reviewer = payload.get("reviewer") or user_info.get("user", "BA_USER")
    decision = payload.get("decision")  # APPROVE, REWORK, REJECT
    comments = payload.get("comments", "")
    edits = payload.get("edits", {})

    if not job_id or not decision:
        raise HTTPException(status_code=400, detail="Missing job_id or decision")

    import uuid
    from backend.db.models import Job, Story, StoryZest
    from backend.validation_export.db_models import BAReviewDB, ValidatedStoryPackageDB
    from sqlalchemy import select, delete

    async with AsyncSessionLocal() as session:
        # Get Job
        stmt_job = select(Job).where(Job.id == job_id)
        res_job = await session.execute(stmt_job)
        job = res_job.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        version_number = job.version_number
        execution_id = job.execution_id
        pipeline_run_id = job.pipeline_run_id

        # Save BAReviewDB record
        db_review = BAReviewDB(
            id=str(uuid.uuid4()),
            job_id=job_id,
            reviewer=reviewer,
            decision=decision,
            comments=comments,
            edits=edits,
            version_number=version_number,
            execution_id=execution_id,
            pipeline_run_id=pipeline_run_id,
            status="COMPLETED"
        )
        session.add(db_review)

        if decision == "APPROVE":
            job.status = "COMPLETED"
            
            # Fetch stories
            stmt_stories = select(Story).where(Story.job_id == job_id)
            res_stories = await session.execute(stmt_stories)
            stories = res_stories.scalars().all()
            stories_list = [
                {
                    "id": s.id,
                    "epic": s.epic,
                    "feature": s.feature,
                    "title": s.title,
                    "user_story": s.user_story,
                    "acceptance_criteria": s.acceptance_criteria,
                    "trace_mappings": s.trace_mappings
                }
                for s in stories
            ]

            # Generate Final Story Zest
            from backend.orchestrator.story_zest import StoryZestGenerator
            zest_gen = StoryZestGenerator()
            final_zest = await zest_gen.generate_zest(stories_list, is_final=True)

            # Save Final Story Zest
            await session.execute(delete(StoryZest).where(
                (StoryZest.job_id == job_id) & (StoryZest.type == "FINAL")
            ))
            zest_model = StoryZest(
                job_id=job_id,
                type="FINAL",
                business_goal=final_zest.get("business_goal", ""),
                scope_summary=final_zest.get("scope_summary", ""),
                actors=final_zest.get("actors", []),
                key_features=final_zest.get("key_features", []),
                dependencies=final_zest.get("dependencies", []),
                risks=final_zest.get("risks", []),
                coverage_metrics=final_zest.get("coverage_metrics", {}),
                version_number=version_number,
                execution_id=execution_id,
                pipeline_run_id=pipeline_run_id,
                status="COMPLETED"
            )
            session.add(zest_model)

            # Save ValidatedStoryPackageDB
            await session.execute(delete(ValidatedStoryPackageDB).where(ValidatedStoryPackageDB.job_id == job_id))
            db_package = ValidatedStoryPackageDB(
                package_id=str(uuid.uuid4()),
                job_id=job_id,
                stories=stories_list,
                traceability_links=[s.get("trace_mappings", []) for s in stories_list],
                coverage_metrics=final_zest.get("coverage_metrics", {}),
                quality_metrics={"approved_stories": len(stories_list)},
                approval_status="APPROVED",
                audit_metadata={"approved_by": reviewer, "approved_at": datetime.utcnow().isoformat() + "Z"},
                final_story_zest=str(final_zest),
                version_number=version_number,
                execution_id=execution_id,
                pipeline_run_id=pipeline_run_id,
                status="COMPLETED"
            )
            session.add(db_package)

        elif decision == "REWORK":
            job.status = "RUNNING"
        else:
            job.status = "MANUAL_RESOLUTION_REQUIRED"
            
        await session.commit()

    # Log audit event
    event_type = f"BA_{decision.upper()}"
    await AuditService.log_event(job_id, event_type, {"reviewer": reviewer, "comments": comments})

    if decision == "REWORK":
        background_tasks.add_task(run_rework_pipeline, job_id, edits, comments)
        return {"status": "success", "next_state": "REWORK", "message": "Rework pipeline started in background."}

    return {"status": "success", "next_state": "PUBLISHED" if decision == "APPROVE" else "REWORK" if decision == "REWORK" else "MANUAL_RESOLUTION_REQUIRED"}


@router.get("/jobs/{job_id}/report", response_model=Dict[str, Any])
async def get_validation_report(
    job_id: str,
    user_info: Dict[str, Any] = Depends(SecurityService.authenticate)
):
    """
    Retrieves the latest validation result and findings for a job.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(ValidationResultDB).where(ValidationResultDB.job_id == job_id).order_by(ValidationResultDB.created_at.desc())
        res = await session.execute(stmt)
        result = res.scalars().first()
        
        if not result:
            raise HTTPException(status_code=404, detail="No validation report found for this job ID.")
            
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


@router.get("/jobs/{job_id}/history", response_model=Dict[str, Any])
async def get_job_history(
    job_id: str,
    user_info: Dict[str, Any] = Depends(SecurityService.authenticate)
):
    """
    Lists all version history, rework cycles, and decisions for a job.
    """
    async with AsyncSessionLocal() as session:
        # Fetch all validation results ordered by version
        stmt_val = select(ValidationResultDB).where(ValidationResultDB.job_id == job_id).order_by(ValidationResultDB.version_number.asc())
        res_val = await session.execute(stmt_val)
        val_results = res_val.scalars().all()

        # Fetch all BA reviews
        stmt_rev = select(BAReviewDB).where(BAReviewDB.job_id == job_id).order_by(BAReviewDB.version_number.asc())
        res_rev = await session.execute(stmt_rev)
        reviews = res_rev.scalars().all()

        versions = []
        for val in val_results:
            # Find matching review for this version
            review = next((r for r in reviews if r.version_number == val.version_number), None)
            
            versions.append({
                "version_number": val.version_number,
                "created_at": val.created_at.isoformat() + "Z",
                "quality_score": val.quality_score,
                "coverage_score": val.coverage_score,
                "traceability_score": val.traceability_score,
                "validation_decision": val.decision,
                "ba_decision": review.decision if review else None,
                "ba_reviewer": review.reviewer if review else None,
                "ba_comments": review.comments if review else None,
                "retry_count": val.retry_count
            })

        return {
            "job_id": job_id,
            "versions": versions
        }


@router.get("/jobs/{job_id}/version/{version_number}", response_model=Dict[str, Any])
async def get_job_version(
    job_id: str,
    version_number: int,
    user_info: Dict[str, Any] = Depends(SecurityService.authenticate)
):
    """
    Retrieves all requirements, stories, and validation results for a specific version.
    """
    from backend.db.models import Requirement, Story, StoryZest
    async with AsyncSessionLocal() as session:
        # Fetch requirements for this version
        stmt_reqs = select(Requirement).where(
            (Requirement.job_id == job_id) & (Requirement.version_number == version_number)
        )
        res_reqs = await session.execute(stmt_reqs)
        reqs = res_reqs.scalars().all()

        # Fetch stories
        stmt_stories = select(Story).where(
            (Story.job_id == job_id) & (Story.version_number == version_number)
        )
        res_stories = await session.execute(stmt_stories)
        stories = res_stories.scalars().all()

        # Fetch validation result
        stmt_val = select(ValidationResultDB).where(
            (ValidationResultDB.job_id == job_id) & (ValidationResultDB.version_number == version_number)
        )
        res_val = await session.execute(stmt_val)
        val = res_val.scalars().first()

        findings = []
        if val:
            stmt_f = select(ValidationFindingDB).where(ValidationFindingDB.validation_result_id == val.id)
            res_f = await session.execute(stmt_f)
            findings = res_f.scalars().all()

        # Fetch story zest
        stmt_zest = select(StoryZest).where(
            (StoryZest.job_id == job_id) & (StoryZest.version_number == version_number)
        )
        res_zest = await session.execute(stmt_zest)
        zests = res_zest.scalars().all()
        draft_zest = next((z for z in zests if z.type == "DRAFT"), None)
        final_zest = next((z if z.type == "FINAL" else None for z in zests), None)

        return {
            "job_id": job_id,
            "version_number": version_number,
            "requirements": [
                {
                    "id": r.id,
                    "content": r.content,
                    "actors": r.actors,
                    "business_rules": r.business_rules,
                    "confidence_score": r.confidence_score,
                    "trace_id": r.trace_id
                }
                for r in reqs
            ],
            "stories": [
                {
                    "id": s.id,
                    "epic": s.epic,
                    "feature": s.feature,
                    "title": s.title,
                    "user_story": s.user_story,
                    "acceptance_criteria": s.acceptance_criteria,
                    "trace_mappings": s.trace_mappings
                }
                for s in stories
            ],
            "validation": {
                "quality_score": val.quality_score if val else None,
                "coverage_score": val.coverage_score if val else None,
                "traceability_score": val.traceability_score if val else None,
                "decision": val.decision if val else None,
                "findings": [
                    {
                        "id": f.id,
                        "validator_name": f.validator_name,
                        "title": f.title,
                        "description": f.description,
                        "severity": f.severity
                    }
                    for f in findings
                ]
            } if val else None,
            "draft_story_zest": {
                "business_goal": draft_zest.business_goal,
                "scope_summary": draft_zest.scope_summary,
                "actors": draft_zest.actors,
                "key_features": draft_zest.key_features,
                "dependencies": draft_zest.dependencies,
                "risks": draft_zest.risks,
                "coverage_metrics": draft_zest.coverage_metrics
            } if draft_zest else None,
            "final_story_zest": {
                "business_goal": final_zest.business_goal,
                "scope_summary": final_zest.scope_summary,
                "actors": final_zest.actors,
                "key_features": final_zest.key_features,
                "dependencies": final_zest.dependencies,
                "risks": final_zest.risks,
                "coverage_metrics": final_zest.coverage_metrics
            } if final_zest else None
        }


@router.post("/jobs/{job_id}/restore/{version_number}", response_model=Dict[str, Any])
async def restore_job_version(
    job_id: str,
    version_number: int,
    user_info: Dict[str, Any] = Depends(SecurityService.authenticate)
):
    """
    Restores a specific historical version as a new active version.
    """
    SecurityService.authorize(user_info, ["BA", "ADMIN"])

    from backend.db.models import Job, Requirement, Story, MasterContext, StoryContextPacket, StoryZest, ValidationContextModel
    from sqlalchemy import update
    
    async with AsyncSessionLocal() as session:
        # Get Job
        stmt_job = select(Job).where(Job.id == job_id)
        res_job = await session.execute(stmt_job)
        job = res_job.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        current_active_version = job.version_number
        new_active_version = current_active_version + 1
        new_execution_id = str(uuid.uuid4())

        # Fetch historical requirements
        stmt_reqs = select(Requirement).where(
            (Requirement.job_id == job_id) & (Requirement.version_number == version_number)
        )
        res_reqs = await session.execute(stmt_reqs)
        historical_reqs = res_reqs.scalars().all()

        # Duplicate requirements for new version
        for r in historical_reqs:
            new_r = Requirement(
                id=str(uuid.uuid4()),
                job_id=job_id,
                content=r.content,
                actors=r.actors,
                business_rules=r.business_rules,
                ambiguities=r.ambiguities,
                conflicts=r.conflicts,
                confidence_score=r.confidence_score,
                trace_id=r.trace_id,
                version_number=new_active_version,
                execution_id=new_execution_id,
                pipeline_run_id=job.pipeline_run_id,
                status="COMPLETED"
            )
            session.add(new_r)

        # Fetch and duplicate stories
        stmt_stories = select(Story).where(
            (Story.job_id == job_id) & (Story.version_number == version_number)
        )
        res_stories = await session.execute(stmt_stories)
        historical_stories = res_stories.scalars().all()

        for s in historical_stories:
            new_s = Story(
                id=str(uuid.uuid4()),
                job_id=job_id,
                epic=s.epic,
                feature=s.feature,
                title=s.title,
                user_story=s.user_story,
                acceptance_criteria=s.acceptance_criteria,
                trace_mappings=s.trace_mappings,
                validation_results=s.validation_results,
                plain_text_summary=s.plain_text_summary,
                version_number=new_active_version,
                execution_id=new_execution_id,
                pipeline_run_id=job.pipeline_run_id,
                status="COMPLETED"
            )
            session.add(new_s)

        # Fetch and duplicate master contexts
        stmt_mc = select(MasterContext).where(
            (MasterContext.job_id == job_id) & (MasterContext.version_number == version_number)
        )
        res_mc = await session.execute(stmt_mc)
        historical_mcs = res_mc.scalars().all()
        for mc in historical_mcs:
            new_mc = MasterContext(
                id=str(uuid.uuid4()),
                job_id=job_id,
                requirements=mc.requirements,
                actors=mc.actors,
                business_rules=mc.business_rules,
                validation_context=mc.validation_context,
                epics=mc.epics,
                features=mc.features,
                hierarchy=mc.hierarchy,
                priority=mc.priority,
                coverage_report=mc.coverage_report,
                dependencies=mc.dependencies,
                orchestrator_metadata=mc.orchestrator_metadata,
                traceability_matrix=mc.traceability_matrix,
                version_number=new_active_version,
                execution_id=new_execution_id,
                pipeline_run_id=job.pipeline_run_id,
                status="COMPLETED"
            )
            session.add(new_mc)

        # Fetch and duplicate story context packets
        stmt_scp = select(StoryContextPacket).where(
            (StoryContextPacket.job_id == job_id) & (StoryContextPacket.version_number == version_number)
        )
        res_scp = await session.execute(stmt_scp)
        historical_scps = res_scp.scalars().all()
        for scp in historical_scps:
            new_scp = StoryContextPacket(
                id=str(uuid.uuid4()),
                job_id=job_id,
                story_id=scp.story_id,
                requirement_id=scp.requirement_id,
                requirement=scp.requirement,
                epic=scp.epic,
                feature=scp.feature,
                actor=scp.actor,
                business_rules=scp.business_rules,
                dependencies=scp.dependencies,
                priority=scp.priority,
                validation=scp.validation,
                traceability=scp.traceability,
                version_number=new_active_version,
                execution_id=new_execution_id,
                pipeline_run_id=job.pipeline_run_id,
                status="COMPLETED"
            )
            session.add(new_scp)

        # Fetch and duplicate zests
        stmt_z = select(StoryZest).where(
            (StoryZest.job_id == job_id) & (StoryZest.version_number == version_number)
        )
        res_z = await session.execute(stmt_z)
        historical_zs = res_z.scalars().all()
        for z in historical_zs:
            new_z = StoryZest(
                id=str(uuid.uuid4()),
                job_id=job_id,
                type=z.type,
                business_goal=z.business_goal,
                scope_summary=z.scope_summary,
                actors=z.actors,
                key_features=z.key_features,
                dependencies=z.dependencies,
                risks=z.risks,
                coverage_metrics=z.coverage_metrics,
                version_number=new_active_version,
                execution_id=new_execution_id,
                pipeline_run_id=job.pipeline_run_id,
                status="COMPLETED"
            )
            session.add(new_z)

        # Update Job
        job.version_number = new_active_version
        job.execution_id = new_execution_id
        job.status = "HUMAN_REVIEW"
        await session.commit()

    await AuditService.log_event(
        job_id, 
        "VERSION_RESTORED", 
        {"from_version": version_number, "to_version": new_active_version}
    )

    return {
        "status": "success",
        "message": f"Version {version_number} restored successfully as Version {new_active_version}.",
        "active_version": new_active_version
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

