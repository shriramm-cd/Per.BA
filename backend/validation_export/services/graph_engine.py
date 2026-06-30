from typing import Dict, List, Set, Any, Optional

class GraphNode:
    def __init__(self, node_id: str, node_type: str, data: Dict[str, Any] = None):
        self.node_id = node_id
        self.node_type = node_type  # Actor, System, Requirement, Epic, Feature, Story, AcceptanceCriteria
        self.data = data or {}

class GraphEngine:
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, Set[str]] = {}  # adjacency list: node_id -> set of target_node_ids
        self.incoming_edges: Dict[str, Set[str]] = {}  # target_node_id -> set of source_node_ids

    def add_node(self, node_id: str, node_type: str, data: Dict[str, Any] = None) -> None:
        if node_id not in self.nodes:
            self.nodes[node_id] = GraphNode(node_id, node_type, data)
            self.edges[node_id] = set()
            self.incoming_edges[node_id] = set()

    def add_edge(self, source_id: str, target_id: str) -> None:
        if source_id in self.nodes and target_id in self.nodes:
            self.edges[source_id].add(target_id)
            self.incoming_edges[target_id].add(source_id)

    def has_cycle(self) -> bool:
        """
        Detects if there is any directed cycle in the graph using DFS.
        """
        visited = set()
        rec_stack = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in self.edges.get(node_id, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False

    def find_cycles(self) -> List[List[str]]:
        """
        Finds and returns all simple directed cycles in the graph.
        """
        cycles = []
        visited = set()
        path = []

        def dfs(node_id: str) -> None:
            visited.add(node_id)
            path.append(node_id)

            for neighbor in self.edges.get(node_id, set()):
                if neighbor in path:
                    # Cycle detected
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
                elif neighbor not in visited:
                    dfs(neighbor)

            path.pop()

        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id)
        return cycles

    def verify_traceability_chain(self, ac_id: str) -> List[str]:
        """
        Verifies and returns the tracing path back from an Acceptance Criteria to an Actor:
        AC -> Story -> Feature -> Epic -> Requirement -> Actor
        """
        if ac_id not in self.nodes or self.nodes[ac_id].node_type != "AcceptanceCriteria":
            return []

        path = [ac_id]
        curr = ac_id
        
        # We traverse backwards using incoming edges
        # We need a chain: AC -> Story -> Feature -> Epic -> Requirement -> Actor
        expected_chain_types = ["Story", "Feature", "Epic", "Requirement", "Actor"]
        
        for next_type in expected_chain_types:
            parents = self.incoming_edges.get(curr, set())
            found = False
            for p in parents:
                if self.nodes[p].node_type == next_type:
                    path.append(p)
                    curr = p
                    found = True
                    break
            if not found:
                break
                
        return path

    def verify_system_trace(self, story_id: str) -> List[str]:
        """
        Verifies if the story is linked to any System node.
        """
        if story_id not in self.nodes or self.nodes[story_id].node_type != "Story":
            return []
            
        parents = self.incoming_edges.get(story_id, set())
        systems = [p for p in parents if self.nodes[p].node_type == "System"]
        return systems

    def build_from_context(self, context: Any) -> None:
        """
        Builds the graph from a ValidationContext object.
        """
        # 1. Add Actor nodes
        for actor in context.actors:
            actor_id = actor.get("id") or actor.get("name")
            if actor_id:
                self.add_node(actor_id, "Actor", actor)

        # 2. Add System nodes
        for system in context.systems:
            system_id = system.get("id") or system.get("name")
            if system_id:
                self.add_node(system_id, "System", system)

        # 3. Add Requirement nodes and link to Actors
        for req in context.requirements:
            req_id = req.get("id") or req.get("trace_id")
            if req_id:
                self.add_node(req_id, "Requirement", req)
                # Link to actors if specified
                req_actors = req.get("actors") or []
                for actor_name in req_actors:
                    if actor_name in self.nodes:
                        self.add_edge(actor_name, req_id)

        # 4. Add Epic nodes and link to Requirements
        for epic in context.epics:
            epic_id = epic.get("id")
            if epic_id:
                self.add_node(epic_id, "Epic", epic)
                # Link Requirement -> Epic
                req_id = epic.get("requirement_id") or epic.get("trace_mappings", [None])[0]
                if req_id and req_id in self.nodes:
                    self.add_edge(req_id, epic_id)

        # 5. Add Feature nodes and link to Epics
        for feature in context.features:
            feature_id = feature.get("id")
            if feature_id:
                self.add_node(feature_id, "Feature", feature)
                epic_id = feature.get("epic_id")
                if epic_id and epic_id in self.nodes:
                    self.add_edge(epic_id, feature_id)

        # 6. Add Story nodes and link to Features & Systems
        for story in context.stories:
            story_id = story.get("id")
            if story_id:
                self.add_node(story_id, "Story", story)
                feature_id = story.get("feature_id") or story.get("feature")
                if feature_id and feature_id in self.nodes:
                    self.add_edge(feature_id, story_id)
                # Link story dependencies (Story -> Story)
                for dep in story.get("dependencies", []):
                    # We add dependency edges. Note: Story depends on Dep_Story.
                    # Add node for dependency story if not exists (safeguard)
                    dep_id = dep.get("story_id") or dep.get("id")
                    if dep_id:
                        if dep_id not in self.nodes:
                            self.add_node(dep_id, "Story")
                        self.add_edge(dep_id, story_id)  # dep_id must happen before story_id
                # Link System -> Story
                systems_mapped = story.get("systems") or []
                for sys_name in systems_mapped:
                    if sys_name in self.nodes:
                        self.add_edge(sys_name, story_id)

        # 7. Add Acceptance Criteria nodes and link to Stories
        for ac in context.acceptance_criteria:
            ac_id = ac.get("id")
            if ac_id:
                self.add_node(ac_id, "AcceptanceCriteria", ac)
                story_id = ac.get("story_id")
                if story_id and story_id in self.nodes:
                    self.add_edge(story_id, ac_id)
