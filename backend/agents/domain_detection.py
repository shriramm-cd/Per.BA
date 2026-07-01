import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger
from backend.agents.schemas import BusinessDomainDetection

logger = get_logger(__name__)

SUPPORTED_DOMAINS = [
    "Healthcare", "Banking", "Insurance", "E-Commerce", "Retail", 
    "Telecom", "Education", "Manufacturing", "Logistics", "Travel", 
    "SaaS", "FinTech", "Government", "HRMS", "CRM", "ERP"
]

class DomainDetectionModule:
    """
    LLM-based Business Domain Detection Module.
    Classifies requirements documents into primary and secondary domains.
    """
    def __init__(self):
        self.llm_client = LLMClient()

    async def detect_domain(self, raw_text: str) -> BusinessDomainDetection:
        """
        Classifies the raw text of the BRD into one or more of the 16 supported domains.
        """
        logger.info("Running LLM-based Business Domain Detection...")
        
        system_prompt = (
            "You are an expert Enterprise Architect and Business Analyst.\n"
            "Analyze the provided Business Requirements Document (BRD) and identify its business domain.\n"
            "You MUST classify the document into one or more of the following 16 supported domains:\n"
            f"{', '.join(SUPPORTED_DOMAINS)}\n\n"
            "Determine the 'primary_domain', any relevant 'secondary_domains' (can be empty if only one domain applies), "
            "and your 'confidence' score as an integer between 0 and 100.\n\n"
            "You MUST respond with a JSON object matching this exact schema:\n"
            "{\n"
            "  \"primary_domain\": \"string (one of the 16 supported domains)\",\n"
            "  \"secondary_domains\": [\"list of strings (from the 16 supported domains)\"],\n"
            "  \"confidence\": integer (0-100)\n"
            "}"
        )

        prompt = (
            f"Analyze the following requirements document and detect its business domains:\n\n"
            f"--- REQUIREMENTS START ---\n"
            f"{raw_text[:8000]}\n"
            f"--- REQUIREMENTS END ---\n"
        )

        try:
            result_json = await self.llm_client.generate_json(
                prompt=prompt,
                system_prompt=system_prompt
            )
            
            # Validate and clean the output
            primary = result_json.get("primary_domain", "").strip()
            # Normalize to match case exactly
            matched_primary = next((d for d in SUPPORTED_DOMAINS if d.lower() == primary.lower()), "General Business")
            
            secondaries = result_json.get("secondary_domains", [])
            matched_secondaries = []
            if isinstance(secondaries, list):
                for sec in secondaries:
                    if isinstance(sec, str):
                        m = next((d for d in SUPPORTED_DOMAINS if d.lower() == sec.strip().lower()), None)
                        if m and m != matched_primary:
                            matched_secondaries.append(m)
                            
            confidence = result_json.get("confidence", 85)
            if not isinstance(confidence, int):
                try:
                    confidence = int(confidence)
                except Exception:
                    confidence = 85
            confidence = max(0, min(100, confidence))
            reasoning = result_json.get("reasoning", "").strip() or "Detected via LLM classification."

            return BusinessDomainDetection(
                primary_domain=matched_primary,
                secondary_domains=matched_secondaries,
                confidence=confidence,
                reasoning=reasoning
            )

        except Exception as e:
            logger.error(f"LLM Domain Detection failed: {str(e)}. Falling back to keyword heuristics.")
            return self._fallback_keyword_detection(raw_text)

    def _fallback_keyword_detection(self, raw_text: str) -> BusinessDomainDetection:
        """
        Fallback keyword heuristic classifier in case the LLM fails.
        """
        domain_keywords = {
            "Banking": ["bank", "loan", "credit", "payment", "transaction"],
            "FinTech": ["payment", "transaction", "ledger", "stripe", "wallet", "invoice"],
            "Healthcare": ["patient", "medical", "doctor", "hospital", "health", "clinical"],
            "Insurance": ["insurance", "claim", "policy", "premium"],
            "Manufacturing": ["production", "factory", "inventory", "assembly"],
            "Education": ["student", "course", "grade", "school", "university"],
            "Logistics": ["shipment", "delivery", "warehouse", "tracking", "cargo"],
            "E-Commerce": ["shopping", "cart", "checkout", "order", "product", "store"],
            "Retail": ["pos", "store", "product", "inventory", "retail"],
            "HRMS": ["employee", "leave", "attendance", "payroll", "hr", "vacation", "hire"],
            "CRM": ["customer", "lead", "opportunity", "sales", "contact"],
            "ERP": ["resource", "planning", "supply", "finance", "billing"]
        }
        
        text_lower = raw_text.lower()
        domain_scores = {}
        
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                domain_scores[domain] = score
                
        if domain_scores:
            primary = max(domain_scores, key=domain_scores.get)
            # Remove primary from potential secondaries
            domain_scores.pop(primary)
            secondaries = [d for d, s in domain_scores.items() if s >= 2]
            return BusinessDomainDetection(
                primary_domain=primary,
                secondary_domains=secondaries,
                confidence=80,
                reasoning=f"Matched keywords for primary domain '{primary}'."
            )
            
        default_domain = "HRMS" if "leave" in text_lower or "employee" in text_lower else "SaaS"
        return BusinessDomainDetection(
            primary_domain=default_domain,
            secondary_domains=[],
            confidence=70,
            reasoning=f"Defaulted to domain '{default_domain}' due to low keyword matches."
        )
