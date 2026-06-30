from typing import List
from backend.validation_export.validators.base import BaseValidator
from backend.validation_export.schemas import ValidationContext, ValidationFinding, Severity
from backend.validation_export.services.graph_engine import GraphEngine

class DependencyValidator(BaseValidator):
    def __init__(self):
        super().__init__("dependency_validator")

    async def _validate_logic(self, context: ValidationContext) -> List[ValidationFinding]:
        findings = []
        
        # 1. Build the Graph
        graph = GraphEngine()
        graph.build_from_context(context)

        # 2. Check for Circular Dependencies
        cycles = graph.find_cycles()
        for cycle in cycles:
            # We only care about cycles that involve Stories (dependencies)
            story_cycle = [node_id for node_id in cycle if graph.nodes[node_id].node_type == "Story"]
            if len(story_cycle) > 1:
                cycle_str = " -> ".join(story_cycle)
                findings.append(
                    ValidationFinding(
                        id=f"DEP-CIRCULAR-{story_cycle[0]}",
                        validator_name=self.name,
                        title="Circular Dependency Detected",
                        description=f"A circular dependency loop was detected among user stories: {cycle_str}.",
                        severity=Severity.CRITICAL,
                        field="dependencies",
                        mitigation="Refactor the user stories to break the circular dependency loop (e.g., merge stories or remove the redundant dependency link)."
                    )
                )

        # 3. Check for Missing Dependencies
        story_ids = {s.get("id") for s in context.stories if s.get("id")}
        for story in context.stories:
            story_id = story.get("id")
            title = story.get("title") or "Unnamed Story"
            
            for dep in story.get("dependencies", []):
                dep_id = dep.get("story_id") or dep.get("id")
                if dep_id and dep_id not in story_ids:
                    findings.append(
                        ValidationFinding(
                            id=f"DEP-MISSING-{dep_id}-{story_id}",
                            validator_name=self.name,
                            title="Missing Dependency Story",
                            description=f"Story '{title}' depends on story '{dep_id}', but this dependent story is not present in the story package.",
                            severity=Severity.MAJOR,
                            field="dependencies",
                            mitigation=f"Add the missing story '{dep_id}' to the package or remove the dependency mapping."
                        )
                    )

        # 4. Check for Invalid Sequencing
        # If Story A depends on Story B, but Story A is ordered before Story B in the execution sequence
        story_order = {s.get("id"): idx for idx, s in enumerate(context.stories) if s.get("id")}
        for story in context.stories:
            story_id = story.get("id")
            title = story.get("title") or "Unnamed Story"
            
            for dep in story.get("dependencies", []):
                dep_id = dep.get("story_id") or dep.get("id")
                if dep_id in story_order and story_id in story_order:
                    if story_order[story_id] < story_order[dep_id]:
                        findings.append(
                            ValidationFinding(
                                id=f"DEP-SEQUENCE-{story_id}",
                                validator_name=self.name,
                                title="Invalid Dependency Sequencing",
                                description=f"Story '{title}' (index {story_order[story_id]}) depends on story '{dep_id}' (index {story_order[dep_id]}), but is positioned before it in the story package sequence.",
                                severity=Severity.MAJOR,
                                field="dependencies",
                                mitigation=f"Reorder the stories so that the prerequisite story '{dep_id}' is positioned before story '{story_id}'."
                            )
                        )

        return findings
