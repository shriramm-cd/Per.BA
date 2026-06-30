from typing import Dict, Any, Optional, List
from datetime import datetime
from backend.agents.schemas import EpicFeaturePlannerOutput
from backend.shared.jinja_renderer import JinjaRenderer
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger

logger = get_logger(__name__)

def _calculate_confidence_score(
    total_requirements: int,
    mapped_requirements: int,
    epics_count: int,
    features_count: int,
    dependencies_count: int,
    has_ambiguities: bool = False
) -> float:
    """
    Calculate overall confidence score considering multiple factors.
    Returns value between 0.0 and 1.0.
    """
    if total_requirements == 0:
        return 0.0
    
    # Coverage score (0.0 to 1.0)
    coverage_score = mapped_requirements / total_requirements
    
    # Granularity score: features per epic should be 2-5 (optimal)
    avg_features_per_epic = features_count / epics_count if epics_count > 0 else 1
    granularity_penalty = 0.0
    if avg_features_per_epic < 1.5 or avg_features_per_epic > 6:
        granularity_penalty = 0.15
    
    # Dependency complexity: some dependencies are good, too many might indicate poor decomposition
    dependency_factor = 1.0
    if dependencies_count > features_count * 0.5:
        dependency_factor = 0.85
    
    # Ambiguity penalty
    ambiguity_penalty = 0.2 if has_ambiguities else 0.0
    
    # Final confidence calculation
    confidence = coverage_score * dependency_factor * (1.0 - granularity_penalty) * (1.0 - ambiguity_penalty)
    
    # Clamp to valid range
    return max(0.0, min(1.0, confidence))

def _build_requirement_mapping(
    requirements: List[Dict[str, Any]],
    hierarchy: List[Dict[str, Any]],
    epics: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Build detailed requirement mappings with full context.
    """
    mappings = []
    for mapping in hierarchy:
        req_id = mapping.get("requirement_id")
        feat_id = mapping.get("feature_id")
        
        # Find requirement content
        req_content = ""
        for req in requirements:
            if req.get("id") == req_id:
                req_content = req.get("content", "")
                break
        
        # Find epic for this feature
        epic_id = ""
        for epic in epics:
            if epic.get("id") == feat_id:
                epic_id = epic.get("epic_id", "")
                break
        
        mappings.append({
            "requirement_id": req_id,
            "requirement_content": req_content,
            "epic_id": epic_id,
            "feature_id": feat_id
        })
    
    return mappings

def _build_epic_hierarchy(
    epics: List[Dict[str, Any]],
    features: List[Dict[str, Any]],
    hierarchy: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Build epic-level hierarchy showing feature and requirement groupings.
    """
    epic_map = {}
    
    # Initialize epic entries
    for epic in epics:
        epic_id = epic.get("id")
        epic_map[epic_id] = {
            "epic_id": epic_id,
            "feature_ids": [],
            "requirement_ids": []
        }
    
    # Map features and requirements to epics
    for feature in features:
        epic_id = feature.get("epic_id")
        feat_id = feature.get("id")
        if epic_id in epic_map:
            epic_map[epic_id]["feature_ids"].append(feat_id)
    
    # Map requirements through hierarchy
    for mapping in hierarchy:
        feat_id = mapping.get("feature_id")
        req_id = mapping.get("requirement_id")
        
        # Find which epic this feature belongs to
        for feature in features:
            if feature.get("id") == feat_id:
                epic_id = feature.get("epic_id")
                if epic_id in epic_map:
                    epic_map[epic_id]["requirement_ids"].append(req_id)
                break
    
    return list(epic_map.values())

def _extract_domain_context(requirements: List[Dict[str, Any]]) -> str:
    """
    Extract domain context from requirements.
    """
    # Simple heuristic: look for domain keywords in requirement content
    all_content = " ".join([req.get("content", "") for req in requirements])
    
    keywords_map = {
        "payment": "Payment Processing",
        "user": "User Management",
        "report": "Reporting",
        "authentication": "Security & Authentication",
        "notification": "Notifications",
        "integration": "System Integration",
        "workflow": "Workflow Management",
        "analytics": "Analytics & Monitoring"
    }
    
    for keyword, domain in keywords_map.items():
        if keyword.lower() in all_content.lower():
            return domain
    
    return "General Business System"

async def run(input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> EpicFeaturePlannerOutput:
    """
    Agent 2: Epic & Feature Planner.
    Groups validated requirements into Epics, Features, with full traceability, dependencies, priority, and confidence scoring.
    """
    from backend.agents.schemas import CoverageReport, Metadata
    
    logger.info("Executing Agent 2 (Epic & Feature Planner)...")
    
    # Support two input shapes:
    # - { "requirements": [...] } (legacy)
    # - { "primary_input": { "functional_requirements": [...], "non_functional_requirements": [...] } } (Agent-1 output)
    requirements = []
    if input_data.get("requirements"):
        requirements = input_data.get("requirements", [])
    elif input_data.get("primary_input"):
        primary = input_data.get("primary_input", {})
        # convert PrimaryInput functional and non-functional requirements into unified requirement dicts
        for fr in primary.get("functional_requirements", []):
            # fr may be a Pydantic object or dict
            frd = fr.model_dump() if hasattr(fr, "model_dump") else fr
            requirements.append({
                "id": frd.get("id"),
                "content": frd.get("description") or frd.get("name") or "",
                "traceability_id": frd.get("traceability_id"),
                "source_type": input_data.get("source_type", "")
            })
        for nfr in primary.get("non_functional_requirements", []):
            nfrd = nfr.model_dump() if hasattr(nfr, "model_dump") else nfr
            requirements.append({
                "id": nfrd.get("id"),
                "content": nfrd.get("description") or nfrd.get("name") or "",
                "traceability_id": nfrd.get("traceability_id"),
                "category": nfrd.get("category"),
                "source_type": input_data.get("source_type", "")
            })

    if not requirements:
        logger.warning("Empty requirements list passed to Agent 2. Returning empty plan.")
        empty_coverage = CoverageReport(
            total_requirements=0,
            mapped_requirements=0,
            unmapped_requirements=0,
            coverage_percentage=0.0
        )
        empty_metadata = Metadata(
            generated_by="Agent-2",
            generated_timestamp=datetime.utcnow().isoformat() + "Z",
            domain="",
            version="1.0",
            model_name="",
            confidence_score=0.0
        )
        return EpicFeaturePlannerOutput(
            epics=[],
            features=[],
            hierarchy=[],
            requirement_mapping=[],
            epic_hierarchy=[],
            dependencies=[],
            priority=[],
            coverage_report=empty_coverage,
            metadata=empty_metadata,
            traceability_matrix=[]
        )

    # Convert Pydantic objects to list of dicts if needed
    serializable_requirements = []
    for req in requirements:
        if hasattr(req, "model_dump"):
            serializable_requirements.append(req.model_dump())
        else:
            serializable_requirements.append(req)

    # 1. Render template prompt
    renderer = JinjaRenderer()
    prompt = renderer.render("agent2.jinja2", {"requirements": serializable_requirements})
    
    system_prompt = """You are an expert Enterprise Agile Architect. 
    Organize requirements into a structured Epic & Feature hierarchy with complete traceability.
    Include dependency mapping, priority classification, and confidence assessment.
    Output ONLY valid JSON matching the specified schema.
    Do not include any text outside the JSON."""

    # 2. Invoke LLM client
    llm = LLMClient()
    response_json = await llm.generate_json(prompt=prompt, system_prompt=system_prompt)
    
    # 3. Cast to Pydantic structure
    output = EpicFeaturePlannerOutput.model_validate(response_json)
    
    # 4. Post-processing and enrichment
    total_requirements = len(serializable_requirements)
    mapped_requirements = len(output.hierarchy)
    unmapped_requirements = total_requirements - mapped_requirements
    coverage_percentage = (mapped_requirements / total_requirements * 100) if total_requirements > 0 else 0.0
    
    # Update coverage report with Pydantic model
    from backend.agents.schemas import CoverageReport
    output.coverage_report = CoverageReport(
        total_requirements=total_requirements,
        mapped_requirements=mapped_requirements,
        unmapped_requirements=unmapped_requirements,
        coverage_percentage=coverage_percentage
    )
    
    # Extract domain context
    domain_context = _extract_domain_context(serializable_requirements)
    
    # Calculate confidence score
    confidence_score = _calculate_confidence_score(
        total_requirements=total_requirements,
        mapped_requirements=mapped_requirements,
        epics_count=len(output.epics),
        features_count=len(output.features),
        dependencies_count=len(output.dependencies),
        has_ambiguities=False
    )
    
    # Update metadata with Pydantic model
    from backend.agents.schemas import Metadata
    output.metadata = Metadata(
        generated_by="Agent-2",
        generated_timestamp=datetime.utcnow().isoformat() + "Z",
        domain=domain_context,
        version="1.0",
        model_name=llm.model_name if hasattr(llm, "model_name") else "unknown",
        confidence_score=confidence_score
    )
    
    # Build requirement mapping if not provided by LLM
    if not output.requirement_mapping or len(output.requirement_mapping) == 0:
        output.requirement_mapping = _build_requirement_mapping(
            serializable_requirements,
            output.hierarchy,
            output.features
        )
    
    # Build epic hierarchy if not provided by LLM
    if not output.epic_hierarchy or len(output.epic_hierarchy) == 0:
        output.epic_hierarchy = _build_epic_hierarchy(
            output.epics,
            output.features,
            output.hierarchy
        )
    
    # Build traceability matrix if not provided
    if not output.traceability_matrix or len(output.traceability_matrix) == 0:
        traceability = []
        for req_map in output.requirement_mapping:
            trace_entry = {
                "requirement_id": req_map.get("requirement_id"),
                "epic_id": req_map.get("epic_id"),
                "feature_id": req_map.get("feature_id"),
                "dependencies": []
            }
            
            # Find dependencies for this feature
            feat_id = req_map.get("feature_id")
            for dep in output.dependencies:
                if dep.get("dependent_feature_id") == feat_id:
                    trace_entry["dependencies"].append(dep.get("dependency_feature_id"))
            
            traceability.append(trace_entry)
        
        output.traceability_matrix = traceability
    
    logger.info(
        f"Agent 2 run completed. Structured {len(output.epics)} epics, "
        f"{len(output.features)} features. Mapped {mapped_requirements}/{total_requirements} requirements. "
        f"Confidence: {confidence_score:.2f}"
    )
    
    return output

# INTEGRATION NOTE
# Epic Feature Planner output aligns requirements with feature boundaries.
# Maintain target signatures so Orchestrator state updates function smoothly.

