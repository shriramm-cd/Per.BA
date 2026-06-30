from typing import List
from backend.validation_export.validators.base import BaseValidator
from backend.validation_export.schemas import ValidationContext, ValidationFinding, Severity
from backend.validation_export.services.graph_engine import GraphEngine

class TraceabilityValidator(BaseValidator):
    def __init__(self):
        super().__init__("traceability_validator")

    async def _validate_logic(self, context: ValidationContext) -> List[ValidationFinding]:
        findings = []
        
        # 1. Build the Graph
        graph = GraphEngine()
        graph.build_from_context(context)

        # 2. Verify trace for every story and its ACs
        for story in context.stories:
            story_id = story.get("id")
            title = story.get("title") or "Unnamed Story"

            if not story_id:
                continue

            # Verify Story -> Feature -> Epic -> Requirement
            parents = graph.incoming_edges.get(story_id, set())
            has_feature = False
            for p in parents:
                if graph.nodes[p].node_type == "Feature":
                    has_feature = True
                    feature_node = graph.nodes[p]
                    # Check Feature -> Epic
                    epic_parents = graph.incoming_edges.get(feature_node.node_id, set())
                    has_epic = False
                    for ep in epic_parents:
                        if graph.nodes[ep].node_type == "Epic":
                            has_epic = True
                            epic_node = graph.nodes[ep]
                            # Check Epic -> Requirement
                            req_parents = graph.incoming_edges.get(epic_node.node_id, set())
                            has_req = False
                            for rp in req_parents:
                                if graph.nodes[rp].node_type == "Requirement":
                                    has_req = True
                                    req_node = graph.nodes[rp]
                                    # Check Requirement -> Actor
                                    actor_parents = graph.incoming_edges.get(req_node.node_id, set())
                                    has_actor = any(graph.nodes[ap].node_type == "Actor" for ap in actor_parents)
                                    if not has_actor:
                                        findings.append(
                                            ValidationFinding(
                                                id=f"TRACE-NO-ACTOR-{story_id}",
                                                validator_name=self.name,
                                                title="Broken Traceability: Missing Actor Link",
                                                description=f"Story '{title}' traces back to Requirement '{req_node.node_id}', but the requirement is not linked to any Actor.",
                                                severity=Severity.MAJOR,
                                                field="trace_mappings",
                                                mitigation="Link the source requirement to a business or system actor."
                                            )
                                        )
                            if not has_req:
                                findings.append(
                                    ValidationFinding(
                                        id=f"TRACE-NO-REQ-{story_id}",
                                        validator_name=self.name,
                                        title="Broken Traceability: Missing Requirement Link",
                                        description=f"Story '{title}' traces to Epic '{epic_node.node_id}', but the epic is not mapped to any source requirement.",
                                        severity=Severity.CRITICAL,
                                        field="trace_mappings",
                                        mitigation="Establish a trace mapping between the Epic and a source requirement."
                                    )
                                )
                    if not has_epic:
                        findings.append(
                            ValidationFinding(
                                id=f"TRACE-NO-EPIC-{story_id}",
                                validator_name=self.name,
                                title="Broken Traceability: Missing Epic Link",
                                description=f"Story '{title}' traces to Feature '{feature_node.node_id}', but the feature is not mapped to an Epic.",
                                severity=Severity.CRITICAL,
                                field="feature_id",
                                mitigation="Link the feature to its parent Epic."
                            )
                        )
            if not has_feature:
                findings.append(
                    ValidationFinding(
                        id=f"TRACE-NO-FEAT-{story_id}",
                        validator_name=self.name,
                        title="Broken Traceability: Missing Feature Link",
                        description=f"Story '{title}' is not linked to any planned Feature.",
                        severity=Severity.CRITICAL,
                        field="feature_id",
                        mitigation="Link the user story to a planned feature."
                    )
                )

        return findings
