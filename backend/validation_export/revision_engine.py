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

    @staticmethod
    def generate_story_revision_packages(
        job_id: str,
        stories: List[Dict[str, Any]],
        findings: List[ValidationFinding],
        ba_comments_dict: Dict[str, str]
    ) -> List[Any]:
        """
        Generates a list of per-story revision packages for stories requiring rework.
        """
        from backend.validation_export.schemas import StoryRevisionPackage, Severity
        
        packages = []
        for story in stories:
            story_id = story.get("id")
            if not story_id:
                continue
                
            # Filter findings for this story
            story_findings = [
                f for f in findings 
                if (f.field and story_id in f.field) or (f.id and story_id in f.id)
            ]
            
            ba_comment = ba_comments_dict.get(story_id, "")
            
            # A story needs rework if it has findings or BA feedback/rejection
            if not story_findings and not ba_comment:
                continue
                
            failed_validators = list({f.validator_name for f in story_findings})
            
            # Identify failed ACs
            failed_ac = [
                f.description for f in story_findings 
                if "acceptance_criteria" in str(f.field) or "AC-" in f.id
            ]
            
            # Extract actor from story text
            story_text = story.get("user_story", "")
            actor = "User"
            lower_text = story_text.lower()
            if "i want" in lower_text:
                prefix = ""
                if "as a " in lower_text:
                    prefix = "as a "
                elif "as an " in lower_text:
                    prefix = "as an "
                
                if prefix:
                    try:
                        idx = lower_text.find(prefix)
                        end_idx = lower_text.find("i want")
                        actor = story_text[idx + len(prefix):end_idx].strip().rstrip(",")
                    except Exception:
                        pass
            elif story.get("actor"):
                actor = story.get("actor")


            # Structure Preserve Section
            preserve = {
                "story_title": story.get("title", ""),
                "actor": actor,
                "approved_business_rules": story.get("business_rules", []),
                "traceability_links": story.get("trace_mappings", []),
                "approved_acceptance_criteria": [
                    ac.get("statement") if isinstance(ac, dict) else str(ac)
                    for ac in story.get("acceptance_criteria", [])
                    if (ac.get("statement") if isinstance(ac, dict) else str(ac)) not in failed_ac
                ]
            }
            
            # Structure Modify Section
            modify = {
                "missing_requirements": [f.description for f in story_findings if "COV-" in f.id],
                "failed_acceptance_criteria": failed_ac,
                "validator_findings": [f.description for f in story_findings],
                "ba_feedback": [ba_comment] if ba_comment else [],
                "missing_business_rules": [f.description for f in story_findings if "BR-" in f.id],
                "wording_issues": [
                    f.description for f in story_findings 
                    if f.severity == Severity.MINOR and "wording" in f.description.lower()
                ]
            }
            
            packages.append(
                StoryRevisionPackage(
                    story_id=story_id,
                    current_story=story,
                    failed_validators=failed_validators,
                    validation_findings=[
                        {
                            "id": f.id,
                            "validator_name": f.validator_name,
                            "title": f.title,
                            "description": f.description,
                            "severity": f.severity.value,
                            "field": f.field,
                            "mitigation": f.mitigation
                        }
                        for f in story_findings
                    ],
                    ba_comments=[ba_comment] if ba_comment else [],
                    preserve_section=preserve,
                    modify_section=modify
                )
            )
            
        return packages

