from backend.validation_export.schemas import ValidationExecutionSummary, DecisionOutcome
from backend.validation_export import validation_settings

class DecisionRulesEngine:
    def __init__(self, config: dict = None):
        self.config = config or {
            "min_coverage_pct": validation_settings.MIN_COVERAGE_PCT,
            "max_retries": validation_settings.MAX_RETRIES
        }

    def evaluate(
        self,
        summary: ValidationExecutionSummary,
        coverage_pct: float,
        retry_count: int
    ) -> DecisionOutcome:
        """
        Executes the rule-based quality gates as defined in the architecture.
        """
        # 1. Escalate to MANUAL_REVIEW if retry limit reached
        if retry_count >= self.config["max_retries"]:
            return DecisionOutcome.MANUAL_REVIEW

        # 2. Check validator-specific gates
        hallucination_failed = "hallucination_validator" in summary.validators_failed
        traceability_failed = "traceability_validator" in summary.validators_failed
        business_rule_failed = "business_rules_validator" in summary.validators_failed
        acceptance_criteria_failed = "acceptance_criteria_validator" in summary.validators_failed

        if hallucination_failed:
            return DecisionOutcome.REWORK

        if traceability_failed:
            return DecisionOutcome.REWORK

        if business_rule_failed:
            return DecisionOutcome.REWORK

        if acceptance_criteria_failed:
            return DecisionOutcome.REWORK

        # 3. Check coverage threshold
        if coverage_pct < self.config["min_coverage_pct"]:
            return DecisionOutcome.REWORK

        # 4. Check for any Critical findings
        if summary.critical_count > 0:
            return DecisionOutcome.REWORK

        return DecisionOutcome.PASS
