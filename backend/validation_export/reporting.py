from typing import Dict, Any, List
from backend.validation_export.schemas import ValidationContext, ValidationExecutionSummary, ValidationFinding

class ReportingEngine:
    """
    Reporting Engine responsible for generating the 7 required architectural reports.
    """
    @staticmethod
    def generate_all_reports(
        context: ValidationContext,
        summary: ValidationExecutionSummary,
        findings: List[ValidationFinding]
    ) -> Dict[str, Any]:
        """
        Compiles and returns all 7 reports in a unified structure.
        """
        return {
            "validation_report": ReportingEngine.generate_validation_report(summary, findings),
            "coverage_report": ReportingEngine.generate_coverage_report(context, findings),
            "traceability_report": ReportingEngine.generate_traceability_report(context, findings),
            "hallucination_report": ReportingEngine.generate_hallucination_report(findings),
            "validator_report": ReportingEngine.generate_validator_report(summary),
            "quality_score_report": ReportingEngine.generate_quality_score_report(summary),
            "rework_report": ReportingEngine.generate_rework_report(summary, findings)
        }

    @staticmethod
    def generate_validation_report(summary: ValidationExecutionSummary, findings: List[ValidationFinding]) -> Dict[str, Any]:
        return {
            "report_name": "Validation Report",
            "job_id": summary.job_id,
            "decision": summary.decision.value,
            "total_findings": len(findings),
            "critical_count": summary.critical_count,
            "major_count": summary.major_count,
            "minor_count": summary.minor_count,
            "info_count": summary.info_count,
            "findings": [f.model_dump() for f in findings]
        }

    @staticmethod
    def generate_coverage_report(context: ValidationContext, findings: List[ValidationFinding]) -> Dict[str, Any]:
        total_reqs = len(context.requirements)
        uncovered_reqs = [f.id.split("-")[-1] for f in findings if "COV-UNCOVERED-REQ" in f.id]
        covered_count = total_reqs - len(uncovered_reqs)
        coverage_pct = (covered_count / total_reqs * 100.0) if total_reqs > 0 else 100.0

        return {
            "report_name": "Coverage Report",
            "total_requirements": total_reqs,
            "covered_requirements_count": covered_count,
            "uncovered_requirements_count": len(uncovered_reqs),
            "coverage_percentage": round(coverage_pct, 2),
            "uncovered_requirement_details": uncovered_reqs
        }

    @staticmethod
    def generate_traceability_report(context: ValidationContext, findings: List[ValidationFinding]) -> Dict[str, Any]:
        broken_traces = [f for f in findings if "TRACE-" in f.id]
        total_stories = len(context.stories)
        traceability_pct = ((total_stories - len(broken_traces)) / total_stories * 100.0) if total_stories > 0 else 100.0

        return {
            "report_name": "Traceability Report",
            "total_stories_checked": total_stories,
            "broken_traceability_count": len(broken_traces),
            "traceability_score": round(traceability_pct, 2),
            "broken_traceability_details": [bt.model_dump() for bt in broken_traces]
        }

    @staticmethod
    def generate_hallucination_report(findings: List[ValidationFinding]) -> Dict[str, Any]:
        hallucinations = [f for f in findings if "HALLUCINATION-" in f.id]
        return {
            "report_name": "Hallucination Report",
            "hallucinations_detected": len(hallucinations),
            "hallucination_details": [h.model_dump() for h in hallucinations]
        }

    @staticmethod
    def generate_validator_report(summary: ValidationExecutionSummary) -> Dict[str, Any]:
        return {
            "report_name": "Validator Report",
            "validators_passed": summary.validators_passed,
            "validators_failed": summary.validators_failed,
            "execution_time_ms": summary.execution_time
        }

    @staticmethod
    def generate_quality_score_report(summary: ValidationExecutionSummary) -> Dict[str, Any]:
        # Formulate an informational score based on finding weights
        penalty = (
            (summary.critical_count * 25) + 
            (summary.major_count * 10) + 
            (summary.minor_count * 3) + 
            (summary.info_count * 1)
        )
        quality_score = max(0, 100 - penalty)

        return {
            "report_name": "Quality Score Report",
            "raw_quality_score": quality_score,
            "grade": "A" if quality_score >= 90 else "B" if quality_score >= 80 else "C" if quality_score >= 70 else "F",
            "is_approved_by_rules": summary.decision == "PASS"
        }

    @staticmethod
    def generate_rework_report(summary: ValidationExecutionSummary, findings: List[ValidationFinding]) -> Dict[str, Any]:
        rework_needed = summary.decision == "REWORK"
        rework_items = [f.model_dump() for f in findings if f.severity in [Severity.CRITICAL, Severity.MAJOR]]
        
        return {
            "report_name": "Rework Report",
            "rework_required": rework_needed,
            "total_rework_items": len(rework_items),
            "rework_items": rework_items
        }
