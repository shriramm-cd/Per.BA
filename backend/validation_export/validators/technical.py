import re
from typing import List
from backend.validation_export.validators.base import BaseValidator
from backend.validation_export.schemas import ValidationContext, ValidationFinding, Severity

class TechnicalValidator(BaseValidator):
    def __init__(self):
        super().__init__("technical_validator")

    async def _validate_logic(self, context: ValidationContext) -> List[ValidationFinding]:
        findings = []

        for idx, story in enumerate(context.stories):
            story_id = story.get("id") or f"STORY-TEMP-{idx}"
            title = story.get("title") or "Unnamed Story"
            story_text = story.get("user_story_text") or ""
            ac_list = story.get("acceptance_criteria") or []

            combined_text = (story_text + " " + " ".join(str(ac) for ac in ac_list)).lower()

            # 1. API Integration Check
            # If "api" or "endpoint" or "integrate" is mentioned, ensure request/response or schema is referenced
            if any(term in combined_text for term in ["api", "endpoint", "webhook", "integration", "rest service"]):
                if not any(term in combined_text for term in ["request", "response", "payload", "schema", "headers", "json", "xml", "documentation"]):
                    findings.append(
                        ValidationFinding(
                            id=f"TECH-API-DETAILS-{story_id}",
                            validator_name=self.name,
                            title="Technical: Missing API Specifications",
                            description=f"Story '{title}' mentions API/Integration but does not specify the request/response payloads, schemas, or endpoint details.",
                            severity=Severity.MAJOR,
                            field="acceptance_criteria",
                            mitigation="Add acceptance criteria specifying the API endpoint, request/response payload, or link to API documentation."
                        )
                    )

            # 2. Security Check
            # If login, password, token, credit card, payment, sensitive data is mentioned, ensure SSL/TLS, encryption, or hashing is mentioned
            if any(term in combined_text for term in ["password", "login", "auth", "token", "credit card", "payment", "ssn", "sensitive"]):
                if not any(term in combined_text for term in ["ssl", "tls", "encrypt", "hash", "secure", "https", "oauth", "jwt", "rbac", "token-based"]):
                    findings.append(
                        ValidationFinding(
                            id=f"TECH-SECURITY-{story_id}",
                            validator_name=self.name,
                            title="Technical: Missing Security NFRs",
                            description=f"Story '{title}' handles authentication or sensitive data but does not specify security NFRs (e.g., encryption, HTTPS, OAuth).",
                            severity=Severity.CRITICAL,
                            field="acceptance_criteria",
                            mitigation="Add acceptance criteria specifying the security protocols, encryption standards, or authentication mechanisms."
                        )
                    )

            # 3. Performance Check
            # If load, response time, concurrent, database query, search is mentioned, ensure latency/response time thresholds are specified
            if any(term in combined_text for term in ["response time", "load", "concurrent", "latency", "search", "database", "query"]):
                if not any(re.search(r'\b(seconds|ms|milliseconds|seconds|threshold|perf|s)\b', combined_text) for ac in ac_list):
                    findings.append(
                        ValidationFinding(
                            id=f"TECH-PERFORMANCE-{story_id}",
                            validator_name=self.name,
                            title="Technical: Missing Performance Thresholds",
                            description=f"Story '{title}' involves database or performance-sensitive operations but does not specify latency or response time thresholds.",
                            severity=Severity.MINOR,
                            field="acceptance_criteria",
                            mitigation="Add acceptance criteria specifying the maximum acceptable response time or throughput (e.g., response time under 2 seconds)."
                        )
                    )

        return findings
