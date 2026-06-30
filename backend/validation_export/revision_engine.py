import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.validation_export.schemas import (
    RevisionPackage, 
    PreserveSection, 
    ModifySection, 
    ValidationFinding, 
    Severity
)
from backend.db.postgres import AsyncSessionLocal
from backend.validation_export.db_models import RevisionPackageDB
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class RevisionEngine:
    """
    Revision Engine for generating, persisting, and structuring rework instructions
    for Agent 3 (Story Generator) using the Preserve vs Modify strategy.
    """
    @staticmethod
    async def generate_package(
        job_id: str,
        stories: List[Dict[str, Any]],
        findings: List[ValidationFinding],
        retry_count: int,
        ba_comments: Optional[str] = None
    ) -> RevisionPackage:
        """
        Analyzes findings and generates a structured RevisionPackage.
        """
        # 1. Identify failed validators and categorize issues
        failed_validators = list({f.validator_name for f in findings})
        
        # 2. Build Preserve Section
        # Preserve approved stories, titles, actors, and trace links
        first_story = stories[0] if stories else {}
        title = first_story.get("title", "Story Set")
        actor = first_story.get("actor", "User")
        
        traceability_links = []
        for s in stories:
            traceability_links.extend(s.get("trace_mappings", []))
            
        # Approved business rules are those without violations
        violated_brs = {f.id.split("-")[-2] for f in findings if "BR-VIOLATION" in f.id}
        all_brs = set()
        for s in stories:
            for br in s.get("business_rules", []):
                br_id = br.get("id") if isinstance(br, dict) else str(br)
                all_brs.add(br_id)
        approved_brs = list(all_brs - violated_brs)

        preserve = PreserveSection(
            title=title,
            actor=actor,
            traceability_links=list(set(traceability_links)),
            approved_sections=[s.get("title") for s in stories if s.get("id") not in [f.field for f in findings]],
            approved_business_rules=approved_brs
        )

        # 3. Build Modify Section
        failed_ac = [f.description for f in findings if "acceptance_criteria" in str(f.field) or "AC-" in f.id]
        violated_br_desc = [f.description for f in findings if "business_rules" in str(f.field) or "BR-" in f.id]
        weak_wording = [f.description for f in findings if f.severity == Severity.MINOR and "wording" in f.description.lower()]
        coverage_gaps = [f.description for f in findings if "COV-" in f.id]
        failures = [f.description for f in findings if f.severity in [Severity.CRITICAL, Severity.MAJOR]]

        modify = ModifySection(
            acceptance_criteria=failed_ac,
            missing_business_rules=violated_br_desc,
            wording=weak_wording,
            coverage_gaps=coverage_gaps,
            validator_failures=failures
        )

        # 4. Compile Revision Package
        package = RevisionPackage(
            package_id=str(uuid.uuid4()),
            job_id=job_id,
            retry_count=retry_count,
            failed_validators=failed_validators,
            validation_report={
                "total_findings": len(findings),
                "critical_count": sum(1 for f in findings if f.severity == Severity.CRITICAL),
                "major_count": sum(1 for f in findings if f.severity == Severity.MAJOR),
                "minor_count": sum(1 for f in findings if f.severity == Severity.MINOR),
                "info_count": sum(1 for f in findings if f.severity == Severity.INFO)
            },
            ba_comments=ba_comments,
            preserve_section=preserve,
            modify_section=modify,
            created_at=datetime.utcnow()
        )

        # 5. Persist to Database
        async with AsyncSessionLocal() as session:
            try:
                db_package = RevisionPackageDB(
                    package_id=package.package_id,
                    job_id=package.job_id,
                    retry_count=package.retry_count,
                    failed_validators=package.failed_validators,
                    validation_report=package.validation_report,
                    ba_comments=package.ba_comments,
                    preserve_section=package.preserve_section.model_dump(),
                    modify_section=package.modify_section.model_dump()
                )
                session.add(db_package)
                await session.commit()
                logger.info(f"Revision package {package.package_id} persisted successfully.")
            except Exception as e:
                logger.error(f"Failed to persist revision package {package.package_id}: {str(e)}")

        return package
