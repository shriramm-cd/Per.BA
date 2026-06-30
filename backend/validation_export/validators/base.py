import time
from abc import ABC, abstractmethod
from typing import List, Dict
from backend.validation_export.schemas import ValidationContext, ValidatorResult, ValidationFinding, Severity

class BaseValidator(ABC):
    """
    Abstract base class for all 12 validators.
    """
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def _validate_logic(self, context: ValidationContext) -> List[ValidationFinding]:
        """
        Specific validation logic to be implemented by child classes.
        """
        pass

    async def validate(self, context: ValidationContext) -> ValidatorResult:
        """
        Orchestrates validation, measures execution time, and structures the result.
        """
        start_time = time.perf_counter()
        findings: List[ValidationFinding] = []
        status = "PASSED"

        try:
            findings = await self._validate_logic(context)
            # If there are any CRITICAL or MAJOR findings, mark as FAILED
            if any(f.severity in [Severity.CRITICAL, Severity.MAJOR] for f in findings):
                status = "FAILED"
        except Exception as e:
            status = "FAILED"
            findings.append(
                ValidationFinding(
                    id=f"{self.name.upper()}-EXEC-ERR",
                    validator_name=self.name,
                    title="Validator Execution Error",
                    description=f"An unexpected error occurred during execution: {str(e)}",
                    severity=Severity.CRITICAL,
                    mitigation="Check system logs and retry the validation."
                )
            )

        execution_time = (time.perf_counter() - start_time) * 1000.0  # in milliseconds

        # Calculate severity summary
        severity_summary = {
            Severity.CRITICAL.value: 0,
            Severity.MAJOR.value: 0,
            Severity.MINOR.value: 0,
            Severity.INFO.value: 0
        }
        for f in findings:
            severity_summary[f.severity.value] = severity_summary.get(f.severity.value, 0) + 1

        return ValidatorResult(
            validator_name=self.name,
            status=status,
            findings=findings,
            execution_time=round(execution_time, 2),
            severity_summary=severity_summary
        )
