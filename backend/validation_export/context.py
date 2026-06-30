from typing import Dict, Any
from backend.validation_export.schemas import ValidationContext

class ValidationContextBuilder:
    @staticmethod
    def build(input_data: Dict[str, Any]) -> ValidationContext:
        """
        Extracts and structures all necessary architectural elements from the raw input data
        to build the unified ValidationContext.
        """
        stories = input_data.get("user_stories", [])
        requirements = input_data.get("requirements", [])
        
        # Extrapolate Epics and Features from input if present
        epics = input_data.get("epics", [])
        features = input_data.get("features", [])
        
        # If Epics/Features are not explicitly provided, extract them from stories to populate the context
        if not epics:
            seen_epics = set()
            for story in stories:
                epic_id = story.get("epic_id") or story.get("epic")
                if epic_id and epic_id not in seen_epics:
                    seen_epics.add(epic_id)
                    epics.append({"id": epic_id, "name": epic_id})
                    
        if not features:
            seen_features = set()
            for story in stories:
                feature_id = story.get("feature_id") or story.get("feature")
                if feature_id and feature_id not in seen_features:
                    seen_features.add(feature_id)
                    features.append({
                        "id": feature_id, 
                        "name": feature_id,
                        "epic_id": story.get("epic_id") or story.get("epic")
                    })

        # Extract Business Rules
        raw_brs = input_data.get("business_rules", [])
        business_rules = []
        if raw_brs:
            for idx, br in enumerate(raw_brs):
                if isinstance(br, dict):
                    business_rules.append(br)
                else:
                    business_rules.append({"id": f"BR-{idx+1:03d}", "description": str(br)})
        else:
            # Fallback: Extract from requirements
            seen_brs = set()
            for req in requirements:
                for br in req.get("business_rules", []):
                    br_id = br.get("id") if isinstance(br, dict) else str(br)
                    if br_id and br_id not in seen_brs:
                        seen_brs.add(br_id)
                        if isinstance(br, dict):
                            business_rules.append(br)
                        else:
                            business_rules.append({"id": br_id, "description": br_id})


        # Extract Acceptance Criteria
        acceptance_criteria = []
        for story in stories:
            story_id = story.get("id")
            for ac in story.get("acceptance_criteria", []):
                if isinstance(ac, dict):
                    ac_copy = ac.copy()
                    ac_copy["story_id"] = story_id
                    if "id" not in ac_copy:
                        ac_copy["id"] = f"AC-{story_id}-{len(acceptance_criteria)}"
                    acceptance_criteria.append(ac_copy)
                else:
                    acceptance_criteria.append({
                        "id": f"AC-{story_id}-{len(acceptance_criteria)}",
                        "story_id": story_id,
                        "description": str(ac)
                    })

        # Default Definition of Done
        definition_of_done = input_data.get("definition_of_done") or {
            "unit_tests": "Unit tests must be written and passing.",
            "documentation": "User documentation must be updated.",
            "security_scan": "Security scans must be run and pass with zero critical vulnerabilities.",
            "code_review": "Code must be reviewed by at least one peer."
        }

        # Extract Dependencies
        dependencies = []
        for story in stories:
            story_id = story.get("id")
            for dep in story.get("dependencies", []):
                dep_id = dep.get("story_id") or dep.get("id") if isinstance(dep, dict) else str(dep)
                dependencies.append({
                    "story_id": story_id,
                    "depends_on_story_id": dep_id
                })

        # Extract Actors & Systems
        raw_actors = input_data.get("actors", [])
        actors = []
        if raw_actors:
            for actor in raw_actors:
                if isinstance(actor, dict):
                    actors.append(actor)
                else:
                    actors.append({"id": str(actor), "name": str(actor)})
        else:
            seen_actors = set()
            for req in requirements:
                for actor in req.get("actors", []):
                    if actor and actor not in seen_actors:
                        seen_actors.add(actor)
                        actors.append({"id": actor, "name": actor})


        systems = input_data.get("systems", [])
        if not systems:
            seen_systems = set()
            for story in stories:
                for sys in story.get("systems", []):
                    if sys and sys not in seen_systems:
                        seen_systems.add(sys)
                        systems.append({"id": sys, "name": sys})

        metadata = input_data.get("metadata", {})
        if "job_id" not in metadata and input_data.get("job_id"):
            metadata["job_id"] = input_data["job_id"]

        return ValidationContext(
            requirements=requirements,
            epics=epics,
            features=features,
            stories=stories,
            business_rules=business_rules,
            acceptance_criteria=acceptance_criteria,
            definition_of_done=definition_of_done,
            dependencies=dependencies,
            actors=actors,
            systems=systems,
            metadata=metadata
        )
