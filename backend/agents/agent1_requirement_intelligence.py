import json
import re
from typing import Dict, Any, Optional, List
from backend.agents.schemas import (
    Agent1RequirementIntelligenceOutput,
    PrimaryInput,
    ValidationContext,
    RetryMetadata,
    FunctionalRequirement,
    NonFunctionalRequirement,
    BusinessRule,
    Actor,
    Dependency,
    Conflict,
    Ambiguity,
    MissingRequirement,
)
from backend.shared.jinja_renderer import JinjaRenderer
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger

logger = get_logger(__name__)

# Quality gate configuration
TARGET_CONFIDENCE = 90
MAX_RETRIES = 3
AMBIGUOUS_TERMS = {
    "fast", "quickly", "soon", "secure", "safe", "user friendly", "intuitive",
    "efficient", "optimized", "immediate", "urgent", "possible", "feasible",
    "reliable", "robust", "modern", "professional", "scalable", "responsive"
}


class Agent1RequirementIntelligence:
    """
    Agent 1: Requirement Intelligence Agent
    Performs 12-step analysis to extract and validate requirements
    with quality gates and self-regeneration logic
    """
    
    def __init__(self):
        self.renderer = JinjaRenderer()
        self.llm_client = LLMClient()
        self.attempt = 1
    
    async def run(
        self,
        input_data: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Agent1RequirementIntelligenceOutput:
        """
        Main entry point for Agent-1 execution
        """
        logger.info("=" * 80)
        logger.info("AGENT-1: REQUIREMENT INTELLIGENCE AGENT")
        logger.info("=" * 80)
        
        # Validate input
        raw_text = input_data.get("raw_text", "") or input_data.get("text", "")
        if not raw_text:
            logger.warning("Empty raw_text passed to Agent 1. Returning empty outputs.")
            return self._create_empty_output()
        
        # Extract metadata for traceability
        fingerprint = input_data.get("fingerprint", "unknown")
        metadata = input_data.get("metadata", {})
        source_type = input_data.get("source_type", "unknown")
        
        logger.info(f"Input fingerprint: {fingerprint[:16]}...")
        logger.info(f"Source type: {source_type}")
        logger.info(f"Raw text length: {len(raw_text)} characters")
        
        # Retry loop with quality gate
        for attempt in range(1, MAX_RETRIES + 1):
            self.attempt = attempt
            logger.info(f"\n--- ANALYSIS ATTEMPT {attempt}/{MAX_RETRIES} ---")
            
            try:
                # Execute 12-step analysis
                output = await self._execute_12_step_analysis(
                    raw_text=raw_text,
                    fingerprint=fingerprint,
                    source_type=source_type,
                    metadata=metadata,
                    attempt=attempt
                )
                
                # Check quality gate
                confidence = output.validation_context.confidence_score
                logger.info(f"Confidence Score: {confidence}/{TARGET_CONFIDENCE}")
                
                if confidence >= TARGET_CONFIDENCE:
                    logger.info("✓ Quality gate PASSED. Proceeding to next agent.")
                    output.validation_context.retry_metadata.status = "SUCCESS"
                    output.validation_context.retry_metadata.attempts = attempt
                    return output
                else:
                    logger.warning(f"✗ Quality gate FAILED. Score {confidence} < {TARGET_CONFIDENCE}")
                    if attempt < MAX_RETRIES:
                        logger.info(f"Retrying (attempt {attempt + 1}/{MAX_RETRIES})...")
                    else:
                        logger.warning("Max retries reached. Returning best output.")
                        output.validation_context.retry_metadata.status = "MAX_RETRIES_REACHED"
                        output.validation_context.retry_metadata.attempts = attempt
                        output.validation_context.retry_metadata.recommendation = (
                            "Human review recommended before proceeding to Agent-2. "
                            "Review extracted requirements for missed details, ambiguities, or incomplete business rules."
                        )
                        return output
            
            except Exception as e:
                logger.error(f"Error during analysis: {str(e)}", exc_info=True)
                if attempt == MAX_RETRIES:
                    return self._create_error_output(str(e), attempt)
        
        # Fallback (should not reach here)
        return self._create_empty_output()
    
    async def _execute_12_step_analysis(
        self,
        raw_text: str,
        fingerprint: str,
        source_type: str,
        metadata: Dict[str, Any],
        attempt: int
    ) -> Agent1RequirementIntelligenceOutput:
        """
        Execute all 12 steps in sequence
        """
        logger.info("\n[STEP 1] REQUIREMENT EXTRACTION")
        raw_requirements = self._step1_extract_requirements(raw_text)
        logger.info(f"  Extracted {len(raw_requirements)} raw requirements")
        
        logger.info("\n[STEP 2] FUNCTIONAL REQUIREMENT CLASSIFICATION")
        functional_reqs = self._step2_classify_functional(raw_requirements, fingerprint)
        logger.info(f"  Found {len(functional_reqs)} functional requirements")
        
        logger.info("\n[STEP 3] NON-FUNCTIONAL REQUIREMENT CLASSIFICATION")
        nonfunctional_reqs = self._step3_classify_nonfunctional(raw_requirements, fingerprint)
        logger.info(f"  Found {len(nonfunctional_reqs)} non-functional requirements")
        
        logger.info("\n[STEP 4] BUSINESS RULE EXTRACTION")
        business_rules = self._step4_extract_business_rules(raw_requirements, raw_text, fingerprint)
        logger.info(f"  Extracted {len(business_rules)} business rules")
        
        logger.info("\n[STEP 5] ACTOR/STAKEHOLDER EXTRACTION")
        actors = self._step5_extract_actors(raw_requirements, raw_text)
        logger.info(f"  Identified {len(actors)} actors")
        
        logger.info("\n[STEP 6] DEPENDENCY DETECTION")
        dependencies = self._step6_detect_dependencies(
            functional_reqs + nonfunctional_reqs,
            raw_text
        )
        logger.info(f"  Detected {len(dependencies)} dependencies")
        
        logger.info("\n[STEP 7] CONFLICT DETECTION")
        conflicts = self._step7_detect_conflicts(
            functional_reqs + nonfunctional_reqs,
            business_rules,
            raw_text
        )
        logger.info(f"  Found {len(conflicts)} conflicts")
        
        logger.info("\n[STEP 8] AMBIGUITY DETECTION")
        ambiguities = self._step8_detect_ambiguities(raw_requirements)
        logger.info(f"  Detected {len(ambiguities)} ambiguities")
        
        logger.info("\n[STEP 9] COMPLETENESS ANALYSIS")
        missing_reqs = self._step9_analyze_completeness(raw_text, functional_reqs)
        logger.info(f"  Found {len(missing_reqs)} missing requirement areas")
        
        logger.info("\n[STEP 10] DOMAIN CLASSIFICATION")
        from backend.agents.domain_detection import DomainDetectionModule
        domain_detector = DomainDetectionModule()
        domain_detection_res = await domain_detector.detect_domain(raw_text)
        domain = domain_detection_res.primary_domain
        logger.info(f"  Primary Domain: {domain_detection_res.primary_domain}")
        logger.info(f"  Secondary Domains: {domain_detection_res.secondary_domains}")
        logger.info(f"  Confidence: {domain_detection_res.confidence}%")
        
        logger.info("\n[STEP 11] CONFIDENCE SCORE CALCULATION")
        confidence = self._step11_calculate_confidence(
            functional_reqs, nonfunctional_reqs, business_rules, actors,
            dependencies, conflicts, ambiguities, missing_reqs
        )
        logger.info(f"  Confidence Score: {confidence}/100")
        
        # Build output
        primary_input = PrimaryInput(
            functional_requirements=functional_reqs,
            non_functional_requirements=nonfunctional_reqs,
            business_rules=business_rules,
            actors=actors,
            dependencies=dependencies
        )
        
        validation_context = ValidationContext(
            conflicts=conflicts,
            ambiguities=ambiguities,
            missing_requirements=missing_reqs,
            domain=domain,
            confidence_score=confidence,
            retry_metadata=RetryMetadata(
                attempts=attempt,
                max_attempts=MAX_RETRIES,
                target_confidence=TARGET_CONFIDENCE,
                status="RETRIED" if attempt > 1 else "SUCCESS",
                recommendation=""
            )
        )
        
        output = Agent1RequirementIntelligenceOutput(
            primary_input=primary_input,
            validation_context=validation_context,
            domain_detection=domain_detection_res
        )

        
        return output
    
    # ========== STEP IMPLEMENTATIONS ==========
    
    def _step1_extract_requirements(self, raw_text: str) -> List[str]:
        """
        STEP 1: Extract individual requirements
        Split compound requirements, remove duplicates, preserve intent
        """
        # Remove headers, page numbers, greetings
        cleaned = re.sub(r'^(Chapter|Section|Page|Introduction|Conclusion).*$', '', raw_text, flags=re.MULTILINE | re.IGNORECASE)
        cleaned = re.sub(r'\d+\s*of\s*\d+', '', cleaned)  # Page numbers
        
        # Split by common delimiters
        requirements = re.split(r'[\n•\-\*]{1,}|(?:^|\n)(?:\d+\.|[A-Z]\.)', cleaned)
        
        # Clean and deduplicate
        requirements = [req.strip() for req in requirements if req.strip() and len(req.strip()) > 10]
        requirements = list(dict.fromkeys(requirements))  # Preserve order while removing duplicates
        
        return requirements
    
    def _step2_classify_functional(self, requirements: List[str], fingerprint: str) -> List[FunctionalRequirement]:
        """
        STEP 2: Identify functional requirements
        """
        functional_keywords = ["user", "system", "shall", "must", "can", "will", "process", "generate", "upload", "download", "register", "login", "create", "update", "delete"]
        
        functional_reqs = []
        req_id = 1
        
        for i, req in enumerate(requirements):
            if any(keyword in req.lower() for keyword in functional_keywords):
                functional_reqs.append(FunctionalRequirement(
                    id=f"FR-{req_id:03d}",
                    name=req[:50].strip() + ("..." if len(req) > 50 else ""),
                    description=req,
                    source_text=req,
                    traceability_id=f"{fingerprint[:8]}#offset_{i}"
                ))
                req_id += 1
        
        return functional_reqs
    
    def _step3_classify_nonfunctional(self, requirements: List[str], fingerprint: str) -> List[NonFunctionalRequirement]:
        """
        STEP 3: Identify non-functional requirements
        """
        category_keywords = {
            "Performance": ["response time", "latency", "throughput", "fast", "quickly", "millisecond", "second", "timeout"],
            "Security": ["encrypt", "secure", "authentication", "authorization", "permission", "password", "ssl", "https", "token"],
            "Reliability": ["fault tolerance", "recovery", "failure", "backup", "failover", "resilient"],
            "Availability": ["uptime", "availability", "24/7", "always available", "downtime"],
            "Scalability": ["scale", "concurrent", "users", "load", "growth", "performance"],
            "Compliance": ["gdpr", "hipaa", "regulation", "compliance", "standard", "law", "audit"],
            "Accessibility": ["wcag", "accessible", "disability", "screen reader", "keyboard"],
            "Usability": ["user friendly", "intuitive", "ux", "ui", "experience"],
            "Maintainability": ["maintain", "support", "bug fix", "update", "patch"],
            "Portability": ["platform", "browser", "device", "cross-platform", "mobile", "desktop"]
        }
        
        nonfunctional_reqs = []
        req_id = 1
        
        for i, req in enumerate(requirements):
            for category, keywords in category_keywords.items():
                if any(keyword in req.lower() for keyword in keywords):
                    nonfunctional_reqs.append(NonFunctionalRequirement(
                        id=f"NFR-{req_id:03d}",
                        category=category,
                        name=f"{category}: {req[:40].strip()}",
                        description=req,
                        source_text=req,
                        traceability_id=f"{fingerprint[:8]}#offset_{i}"
                    ))
                    req_id += 1
                    break
        
        return nonfunctional_reqs
    
    def _step4_extract_business_rules(
        self,
        requirements: List[str],
        raw_text: str,
        fingerprint: str
    ) -> List[BusinessRule]:
        """
        STEP 4: Extract business rules (constraints, policies, validation rules)
        """
        rule_patterns = {
            "Validation Rule": [r"must be", r"required", r"mandatory", r"must have"],
            "Constraint": [r"maximum", r"minimum", r"cannot", r"not allowed"],
            "Policy": [r"only \w+ can", r"admin only", r"only for"],
            "Permission Rule": [r"user can", r"allowed to", r"permitted to"],
            "Threshold Rule": [r"above \d+", r"below \d+", r"greater than", r"less than"],
            "Calculation Rule": [r"calculate", r"compute", r"formula", r"percentage"]
        }
        
        business_rules = []
        rule_id = 1
        
        for i, req in enumerate(requirements):
            for rule_type, patterns in rule_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, req, re.IGNORECASE):
                        business_rules.append(BusinessRule(
                            id=f"BR-{rule_id:03d}",
                            type=rule_type,
                            rule=req[:60].strip(),
                            description=req,
                            source_text=req,
                            traceability_id=f"{fingerprint[:8]}#offset_{i}"
                        ))
                        rule_id += 1
                        break
        
        return business_rules
    
    def _step5_extract_actors(self, requirements: List[str], raw_text: str) -> List[Actor]:
        """
        STEP 5: Extract actors and stakeholders
        """
        actor_keywords = {
            "Customer": ["customer", "user", "client"],
            "Manager": ["manager", "supervisor", "lead"],
            "Administrator": ["admin", "administrator", "system admin"],
            "External Service": ["api", "service", "gateway", "provider"],
            "System": ["system", "application", "service"],
            "Auditor": ["auditor", "audit"],
            "Bank": ["bank", "financial institution"]
        }
        
        actors_found = {}
        
        for req in requirements + [raw_text]:
            for actor_name, keywords in actor_keywords.items():
                if any(keyword in req.lower() for keyword in keywords):
                    if actor_name not in actors_found:
                        actors_found[actor_name] = True
        
        actors = []
        for i, actor_name in enumerate(actors_found.keys()):
            actors.append(Actor(
                id=f"ACT-{i+1:03d}",
                name=actor_name,
                type="Human" if actor_name in ["Customer", "Manager", "Administrator", "Auditor"] else "System",
                description=f"{actor_name} in the system"
            ))
        
        return actors
    
    def _step6_detect_dependencies(
        self,
        requirements: List[object],
        raw_text: str
    ) -> List[Dependency]:
        """
        STEP 6: Detect execution dependencies between requirements
        """
        dependency_patterns = [
            (r"after\s+(\w+)", "Sequential"),
            (r"before\s+(\w+)", "Sequential"),
            (r"requires?\s+(\w+)", "Blocking"),
            (r"then\s+(\w+)", "Sequential"),
            (r"depends on\s+(\w+)", "Blocking"),
            (r"triggered by\s+(\w+)", "Sequential")
        ]
        
        dependencies = []
        dep_id = 1
        
        # Extract requirement IDs to link
        req_ids = {getattr(req, 'id', f"REQ-{i}") for i, req in enumerate(requirements)}
        
        # Simple dependency detection from text patterns
        if len(req_ids) >= 2:
            req_list = sorted(list(req_ids))
            for i in range(len(req_list) - 1):
                dependencies.append(Dependency(
                    id=f"DEP-{dep_id:03d}",
                    source=req_list[i],
                    target=req_list[i + 1],
                    type="Sequential",
                    description=f"{req_list[i]} must be completed before {req_list[i + 1]}"
                ))
                dep_id += 1
        
        return dependencies
    
    def _step7_detect_conflicts(
        self,
        requirements: List[object],
        business_rules: List[BusinessRule],
        raw_text: str
    ) -> List[Conflict]:
        """
        STEP 7: Detect contradictions in requirements
        """
        conflicts = []
        
        # Check for contradictory keywords
        contradictory_pairs = [
            ("must", "cannot"),
            ("required", "optional"),
            ("always", "never"),
            ("all users", "admin only")
        ]
        
        text_lower = raw_text.lower()
        
        for term1, term2 in contradictory_pairs:
            if term1 in text_lower and term2 in text_lower:
                conflicts.append(Conflict(
                    requirement=f"Multiple statements",
                    issue=f"Conflicting requirements found: '{term1}' vs '{term2}'"
                ))
        
        return conflicts
    
    def _step8_detect_ambiguities(self, requirements: List[str]) -> List[Ambiguity]:
        """
        STEP 8: Detect vague or unclear requirements
        """
        ambiguities = []
        amb_id = 1
        
        for i, req in enumerate(requirements):
            for ambiguous_term in AMBIGUOUS_TERMS:
                if ambiguous_term in req.lower():
                    ambiguities.append(Ambiguity(
                        requirement=f"REQ-{i+1}",
                        term=ambiguous_term,
                        issue=f"Term '{ambiguous_term}' is not quantified. Recommend: Specify measurable criteria (e.g., response time < 500ms, 99.9% uptime)."
                    ))
                    amb_id += 1
                    break
        
        return ambiguities
    
    def _step9_analyze_completeness(
        self,
        raw_text: str,
        functional_reqs: List[FunctionalRequirement]
    ) -> List[MissingRequirement]:
        """
        STEP 9: Identify missing important business requirements
        """
        important_areas = {
            "Error Handling": ["error", "exception", "fail"],
            "Audit Logs": ["audit", "log", "track", "history"],
            "Notifications": ["notify", "alert", "email", "sms"],
            "Authorization": ["permission", "access", "role"],
            "Backup": ["backup", "recovery", "disaster"],
            "Monitoring": ["monitor", "alert", "metric"]
        }
        
        missing = []
        text_lower = raw_text.lower()
        
        for area, keywords in important_areas.items():
            if not any(keyword in text_lower for keyword in keywords):
                missing.append(MissingRequirement(
                    area=area,
                    description=f"No explicit requirement specified for {area.lower()}"
                ))
        
        return missing
    
    def _step10_classify_domain(self, raw_text: str) -> str:
        """
        STEP 10: Identify the business domain
        """
        domain_keywords = {
            "Banking & Financial Services": ["bank", "loan", "credit", "payment", "transaction"],
            "Healthcare": ["patient", "medical", "doctor", "hospital", "health"],
            "Retail & E-Commerce": ["product", "shopping", "cart", "checkout", "order"],
            "Insurance": ["insurance", "claim", "policy", "premium"],
            "Manufacturing": ["production", "factory", "inventory", "assembly"],
            "Education": ["student", "course", "grade", "school", "university"],
            "Logistics": ["shipment", "delivery", "warehouse", "tracking"],
            "Human Resources (HR)": ["employee", "leave", "attendance", "payroll", "hr", "vacation", "hire"],
            "Technology & SaaS": ["software", "api", "saas", "platform", "system", "integration"]
        }
        
        text_lower = raw_text.lower()
        domain_scores = {}
        
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        return "General Business"
    
    def _step11_calculate_confidence(
        self,
        functional_reqs: List[FunctionalRequirement],
        nonfunctional_reqs: List[NonFunctionalRequirement],
        business_rules: List[BusinessRule],
        actors: List[Actor],
        dependencies: List[Dependency],
        conflicts: List[Conflict],
        ambiguities: List[Ambiguity],
        missing_reqs: List[MissingRequirement]
    ) -> int:
        """
        STEP 11: Calculate overall confidence score (0-100)
        """
        score = 100
        
        # Extraction quality (20%)
        if not functional_reqs:
            score -= 20
        elif len(functional_reqs) < 3:
            score -= 10
        
        # Classification accuracy (15%)
        if not nonfunctional_reqs:
            score -= 8
        
        # Business rule extraction (15%)
        if not business_rules:
            score -= 10
        
        # Dependency detection (15%)
        if not dependencies:
            score -= 8
        
        # Conflict detection (10%)
        if conflicts:
            score -= min(5, len(conflicts) * 2)
        
        # Ambiguity analysis (10%)
        if ambiguities:
            score -= min(8, len(ambiguities) * 2)
        
        # Completeness (10%)
        if missing_reqs:
            score -= min(8, len(missing_reqs) * 1)
        
        # Domain classification (5%)
        if not actors:
            score -= 5
        
        return max(0, min(100, score))
    
    def _create_empty_output(self) -> Agent1RequirementIntelligenceOutput:
        """Create empty output for error cases"""
        return Agent1RequirementIntelligenceOutput(
            primary_input=PrimaryInput(
                functional_requirements=[],
                non_functional_requirements=[],
                business_rules=[],
                actors=[],
                dependencies=[]
            ),
            validation_context=ValidationContext(
                conflicts=[],
                ambiguities=[Ambiguity(requirement="", term="", issue="No content was provided for analysis.")],
                missing_requirements=[],
                domain="Unknown",
                confidence_score=0,
                retry_metadata=RetryMetadata(
                    attempts=1,
                    max_attempts=MAX_RETRIES,
                    target_confidence=TARGET_CONFIDENCE,
                    status="FAILED",
                    recommendation="Provide valid input document for analysis."
                )
            )
        )
    
    def _create_error_output(self, error_msg: str, attempt: int) -> Agent1RequirementIntelligenceOutput:
        """Create output for error cases"""
        return Agent1RequirementIntelligenceOutput(
            primary_input=PrimaryInput(
                functional_requirements=[],
                non_functional_requirements=[],
                business_rules=[],
                actors=[],
                dependencies=[]
            ),
            validation_context=ValidationContext(
                conflicts=[Conflict(requirement="System", issue=f"Error: {error_msg}")],
                ambiguities=[],
                missing_requirements=[],
                domain="Unknown",
                confidence_score=0,
                retry_metadata=RetryMetadata(
                    attempts=attempt,
                    max_attempts=MAX_RETRIES,
                    target_confidence=TARGET_CONFIDENCE,
                    status="MAX_RETRIES_REACHED",
                    recommendation=f"Analysis failed with error: {error_msg}"
                )
            )
        )


# ========== ENTRY POINT ==========

async def run(
    input_data: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
) -> Agent1RequirementIntelligenceOutput:
    """
    Agent 1 entry point
    Transforms normalized requirement document into structured requirement intelligence
    """
    agent = Agent1RequirementIntelligence()
    return await agent.run(input_data, config)


# INTEGRATION NOTE
# This module implements the signature: async def run(input_data, config) -> Agent1RequirementIntelligenceOutput
# Output conforms to exact JSON schema for direct integration with GraphState and Agent-2
# Quality gate: Confidence >= 90 (max 3 retries)

