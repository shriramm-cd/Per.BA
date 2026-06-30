from typing import Dict, Any, List
from datetime import datetime
from functools import wraps
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.orchestrator.state import GraphState
from backend.shared.logger import get_logger
from backend.orchestrator.router import route_after_agent1, route_after_validation
from backend.orchestrator.retry_handler import RetryHandler

logger = get_logger(__name__)

def _to_dict(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, list):
        return [_to_dict(item) for item in val]
    if isinstance(val, dict):
        return {k: _to_dict(v) for k, v in val.items()}
    if hasattr(val, "model_dump"):
        return val.model_dump()
    return val

pipeline_debug_state: Dict[str, Dict[str, Any]] = {}


def _append_debug_entry(job_id: str, node_name: str, status: str, output: Dict[str, Any] = None, message: str = None) -> None:
    if job_id not in pipeline_debug_state:
        pipeline_debug_state[job_id] = {
            "job_id": job_id,
            "nodes": [],
            "latest_status": "PENDING",
            "error_message": None,
        }

    entry = {
        "node": node_name,
        "status": status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "output": output or {},
    }
    if message:
        entry["message"] = message

    pipeline_debug_state[job_id]["nodes"].append(entry)
    pipeline_debug_state[job_id]["latest_status"] = status
    if status == "FAILED":
        pipeline_debug_state[job_id]["error_message"] = message


def reset_pipeline_debug_state(job_id: str) -> None:
    pipeline_debug_state[job_id] = {
        "job_id": job_id,
        "nodes": [],
        "latest_status": "PENDING",
        "error_message": None,
    }


def get_pipeline_debug_state(job_id: str) -> Dict[str, Any]:
    return pipeline_debug_state.get(job_id, {
        "job_id": job_id,
        "nodes": [],
        "latest_status": "UNKNOWN",
        "error_message": None,
    })


def debug_node(node_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(state: GraphState) -> Dict[str, Any]:
            job_id = state.get("job_id", "")
            logger.info(f"[graph] {node_name} node started for job {job_id}")
            _append_debug_entry(job_id, node_name, "STARTED")
            try:
                output = await func(state)
                _append_debug_entry(job_id, node_name, "COMPLETED", output=output)
                return output
            except Exception as exc:
                _append_debug_entry(job_id, node_name, "FAILED", output={}, message=str(exc))
                raise
        return wrapper
    return decorator


@debug_node("ingest")
async def ingest_node(state: GraphState) -> Dict[str, Any]:
    from backend.ingestion.summary_generator import InputSummaryGenerator
    summary_gen = InputSummaryGenerator()
    summary = await summary_gen.generate_summary(state.get("raw_text", ""))
    
    # Save input_summary to the Job's meta_info in the DB
    from backend.db.postgres import AsyncSessionLocal
    from backend.db.models import Job
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        try:
            stmt_job = select(Job).where(Job.id == state["job_id"])
            res_job = await session.execute(stmt_job)
            job = res_job.scalar_one_or_none()
            if job:
                meta = dict(job.meta_info or {})
                meta["input_summary"] = summary
                job.meta_info = meta
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to save input_summary to Job meta_info: {e}")
            
    return {"status": "RUNNING", "input_summary": summary}



@debug_node("requirement_repository")
async def requirement_repository_node(state: GraphState) -> Dict[str, Any]:
    return {"requirement_package": {"package_id": f"pkg-{state.get('fingerprint','')}", "fingerprint": state.get('fingerprint'), "source_type": state.get('source_type')}}


@debug_node("requirement_package_builder")
async def requirement_package_builder_node(state: GraphState) -> Dict[str, Any]:
    return {
        "requirement_package": {
            "package_id": f"pkg-{state.get('fingerprint','')}",
            "job_id": state.get("job_id"),
            "fingerprint": state.get("fingerprint"),
            "source_type": state.get("source_type"),
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
    }


@debug_node("agent1")
async def agent1_node(state: GraphState) -> Dict[str, Any]:
    from backend.agents.agent1_requirement_intelligence import Agent1RequirementIntelligence
    agent1 = Agent1RequirementIntelligence()
    output = await agent1.run(state)
    
    # Map output to GraphState keys
    requirements = []
    for fr in output.primary_input.functional_requirements:
        requirements.append({
            "id": fr.id,
            "content": fr.description,
            "actors": [],
            "business_rules": [],
            "traceability_id": fr.traceability_id
        })
    for nfr in output.primary_input.non_functional_requirements:
        requirements.append({
            "id": nfr.id,
            "content": nfr.description,
            "actors": [],
            "business_rules": [],
            "traceability_id": nfr.traceability_id
        })
        
    actors = [a.name for a in output.primary_input.actors]
    business_rules = [br.rule for br in output.primary_input.business_rules]
    
    domain_detection = _to_dict(output.domain_detection) if output.domain_detection else None
    
    # Save requirements to database
    from backend.db.postgres import AsyncSessionLocal
    from backend.db.models import Requirement, Job
    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy import delete, select
            await session.execute(delete(Requirement).where(Requirement.job_id == state["job_id"]))
            
            for r in requirements:
                req_model = Requirement(
                    id=r["id"],
                    job_id=state["job_id"],
                    content=r["content"],
                    actors=None,
                    business_rules=None,
                    ambiguities=None,
                    conflicts=None,
                    confidence_score=output.validation_context.confidence_score / 100.0,
                    trace_id=r["traceability_id"]
                )
                session.add(req_model)
                
            # Update Job meta_info
            stmt_job = select(Job).where(Job.id == state["job_id"])
            res_job = await session.execute(stmt_job)
            job = res_job.scalar_one_or_none()
            if job:
                meta = dict(job.meta_info or {})
                meta["domain_detection"] = domain_detection
                job.meta_info = meta
                
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to save requirements to DB: {e}")
            
    return {
        "agent1_output": _to_dict(output),
        "requirements": requirements,
        "actors": actors,
        "business_rules": business_rules,
        "domain": output.validation_context.domain,
        "domain_detection": domain_detection,
        "ambiguities": _to_dict(output.validation_context.ambiguities),
        "conflicts": _to_dict(output.validation_context.conflicts),
        "confidence_score": output.validation_context.confidence_score / 100.0
    }




@debug_node("agent2")
async def agent2_node(state: GraphState) -> Dict[str, Any]:
    from backend.agents.agent2_epic_feature_planner import run as run_agent2
    output = await run_agent2(state)
    
    return {
        "agent2_output": _to_dict(output),
        "epics": _to_dict(output.epics),
        "features": _to_dict(output.features),
        "hierarchy": _to_dict(output.hierarchy),
        "requirement_mapping": _to_dict(output.requirement_mapping),
        "epic_hierarchy": _to_dict(output.epic_hierarchy),
        "dependencies": _to_dict(output.dependencies),
        "priority": _to_dict(output.priority),
        "coverage_report": _to_dict(output.coverage_report),
        "metadata": _to_dict(output.metadata),
        "traceability_matrix": _to_dict(output.traceability_matrix)
    }


@debug_node("traceability_matrix_builder")
async def traceability_matrix_builder_node(state: GraphState) -> Dict[str, Any]:
    return {"traceability_matrix": state.get("traceability_matrix", [])}


def build_story_contexts(state: GraphState) -> List[Dict[str, Any]]:
    requirements = state.get("requirements", [])
    epics = state.get("epics", [])
    features = state.get("features", [])
    traceability_matrix = state.get("traceability_matrix", [])
    
    req_map = {r["id"]: r for r in requirements}
    epic_map = {e["id"]: e for e in epics}
    feat_map = {f["id"]: f for f in features}
    
    story_contexts = []
    for tm in traceability_matrix:
        req_id = tm.get("requirement_id")
        epic_id = tm.get("epic_id")
        feat_id = tm.get("feature_id")
        
        req = req_map.get(req_id, {})
        epic = epic_map.get(epic_id, {})
        feature = feat_map.get(feat_id, {})
        
        priority = feature.get("priority", "Medium")
        deps = tm.get("dependencies", [])
        
        brs = req.get("business_rules", [])
        if not brs and "business_rules" in state:
            brs = state["business_rules"]
            
        ctx = {
            "story_context_id": f"ctx-{req_id}-{feat_id}",
            "story_id": f"story-{req_id}-{feat_id}",
            "requirement_id": req_id,
            "requirement": {"id": req_id, "text": req.get("content", "")},
            "epic": {"id": epic_id, "name": epic.get("name", "")},
            "feature": {"id": feat_id, "name": feature.get("name", ""), "priority": priority} if feat_id else {},
            "actor": req.get("actors", ["User"])[0] if req.get("actors") else "User",
            "business_rules": brs,
            "dependencies": deps,
            "priority": priority,
            "validation": {},
            "traceability": {
                "requirement_id": req_id,
                "epic_id": epic_id,
                "feature_id": feat_id
            }
        }
        story_contexts.append(ctx)
    return story_contexts


@debug_node("agent3")
async def agent3_node(state: GraphState) -> Dict[str, Any]:
    from backend.agents.agent3_user_story_generator import run as run_agent3
    
    story_contexts = build_story_contexts(state)
    output = await run_agent3({"story_contexts": story_contexts})
    
    # Save stories to DB
    from backend.db.postgres import AsyncSessionLocal
    from backend.db.models import Story
    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy import delete
            await session.execute(delete(Story).where(Story.job_id == state["job_id"]))
            
            for us in output.user_stories:
                epic_name = ""
                for e in state.get("epics", []):
                    if e.get("id") == us.epic_id:
                        epic_name = e.get("name", "")
                        break
                feature_name = ""
                for f in state.get("features", []):
                    if f.get("id") == us.feature_id:
                        feature_name = f.get("name", "")
                        break
                        
                story_model = Story(
                    id=us.id,
                    job_id=state["job_id"],
                    epic=epic_name or us.epic_id,
                    feature=feature_name or us.feature_id,
                    title=us.title,
                    user_story=us.user_story_text,
                    acceptance_criteria=_to_dict(us.acceptance_criteria),
                    trace_mappings=us.trace_mappings,
                    validation_results=None,
                    plain_text_summary=output.plain_text_summary
                )
                session.add(story_model)
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to save stories to DB: {e}")
            
    return {
        "user_stories": _to_dict(output.user_stories),
        "plain_text_summary": output.plain_text_summary,
        "story_contexts": story_contexts
    }


@debug_node("agent4")
async def agent4_node(state: GraphState) -> Dict[str, Any]:
    from backend.validation_export.agent4_validation_engine import run as run_agent4
    output = await run_agent4(state)
    
    # Save validation_results to the Job's meta_info in the DB
    from backend.db.postgres import AsyncSessionLocal
    from backend.db.models import Job
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        try:
            stmt_job = select(Job).where(Job.id == state["job_id"])
            res_job = await session.execute(stmt_job)
            job = res_job.scalar_one_or_none()
            if job:
                meta = dict(job.meta_info or {})
                meta["validation_results"] = _to_dict(output)
                job.meta_info = meta
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to save validation_results to Job meta_info: {e}")
            
    return {
        "validation_results": _to_dict(output),
        "quality_score": output.quality_score,
        "is_approved": output.is_approved
    }



@debug_node("export")
async def export_node(state: GraphState) -> Dict[str, Any]:
    return {"status": "COMPLETED"}


@debug_node("retry_node")
async def retry_node(state: GraphState) -> Dict[str, Any]:
    new_state = RetryHandler.inspect_and_increment(dict(state))
    return {"retry_count": new_state.get("retry_count", 0), "status": new_state.get("status")}


@debug_node("fail_node")
async def fail_node(state: GraphState) -> Dict[str, Any]:
    return {"status": "FAILED", "error_message": "Failed to generate requirements with sufficient confidence."}


@debug_node("human_review_node")
async def human_review_node(state: GraphState) -> Dict[str, Any]:
    return {"status": "HUMAN_REVIEW"}


workflow = StateGraph(GraphState)
workflow.add_node("ingest", ingest_node)
workflow.add_node("requirement_repository", requirement_repository_node)
workflow.add_node("requirement_package_builder", requirement_package_builder_node)
workflow.add_node("agent1", agent1_node)
workflow.add_node("agent2", agent2_node)
workflow.add_node("traceability_matrix_builder", traceability_matrix_builder_node)
workflow.add_node("agent3", agent3_node)
workflow.add_node("agent4", agent4_node)
workflow.add_node("export", export_node)
workflow.add_node("retry_node", retry_node)
workflow.add_node("fail_node", fail_node)
workflow.add_node("human_review_node", human_review_node)

workflow.set_entry_point("ingest")
workflow.add_edge("ingest", "requirement_repository")
workflow.add_edge("requirement_repository", "requirement_package_builder")
workflow.add_edge("requirement_package_builder", "agent1")

# Add conditional routing after agent1
workflow.add_conditional_edges(
    "agent1",
    route_after_agent1,
    {
        "retry_node": "retry_node",
        "fail_node": "fail_node",
        "agent2_node": "agent2"
    }
)

# If retry, go back to agent1
workflow.add_edge("retry_node", "agent1")
workflow.add_edge("fail_node", END)

workflow.add_edge("agent2", "traceability_matrix_builder")
workflow.add_edge("traceability_matrix_builder", "agent3")
workflow.add_edge("agent3", "agent4")

# Add conditional routing after validation (agent4)
workflow.add_conditional_edges(
    "agent4",
    route_after_validation,
    {
        "export_node": "export",
        "human_review_node": "human_review_node"
    }
)

workflow.add_edge("export", END)
workflow.add_edge("human_review_node", END)

memory_store = MemorySaver()
pipeline_graph = workflow.compile(checkpointer=memory_store)

