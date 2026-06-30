# Agent-2: Epic & Feature Planner - Enterprise Architecture

## Overview

Agent-2 is an enterprise-grade Epic & Feature Planner that transforms validated requirements from Agent-1 into a structured, hierarchical product backlog. It is **not** a simple User Story Generator, but rather a sophisticated planning agent responsible for:

1. **Epic & Feature Decomposition** - Organizing requirements into logical business capabilities
2. **Complete Traceability** - Mapping every requirement through the hierarchy
3. **Dependency Management** - Identifying and tracking feature-to-feature dependencies
4. **Priority Classification** - Assigning strategic priorities based on business impact
5. **Coverage Analysis** - Ensuring complete requirement mapping with detailed reports
6. **Confidence Scoring** - Generating quality metrics for orchestrator decision-making

## Responsibilities

### 1. Epic Identification
- Groups related functional requirements into logical, independently deployable Epics
- Each Epic represents a major business capability or system module
- Example: "User Authentication & Authorization" (EPIC-001)

### 2. Feature Identification
- Breaks each Epic into distinct Features implementable within a sprint
- Features are building blocks that compose Epics
- Example: "User Login" (FEAT-001), "User Registration" (FEAT-002)

### 3. Requirement Mapping
- Creates explicit Requirement → Epic → Feature mappings
- **Every functional requirement MUST map to exactly one Feature**
- No unmapped or multi-mapped requirements
- Handles ambiguous requirements by finding closest match

### 4. Hierarchy Creation
```
Epic (EPIC-001)
  ├── Feature (FEAT-001)
  │   ├── Requirement (REQ-001)
  │   └── Requirement (REQ-002)
  └── Feature (FEAT-002)
      ├── Requirement (REQ-003)
      └── Requirement (REQ-004)
```

### 5. Dependency Mapping
- Identifies Feature-to-Feature dependencies with types:
  - `blocks` - Feature X blocks Feature Y (must complete X before Y)
  - `extends` - Feature X extends Feature Y (builds upon)
  - `requires` - Feature X requires Feature Y (depends on)
  - `related` - Features are semantically related

### 6. Coverage Planning
Generates comprehensive coverage metrics:
```json
{
  "coverage_report": {
    "total_requirements": 12,
    "mapped_requirements": 12,
    "unmapped_requirements": 0,
    "coverage_percentage": 100.0
  }
}
```

### 7. Priority Classification
Assigns strategic priority (High/Medium/Low) based on:
- Business rule criticality
- Dependency importance
- Approval workflow positioning
- Critical business operations impact

### 8. Domain Context Alignment
- Preserves domain information from Agent-1 requirements
- Includes business context in metadata
- Example: "Payment Processing & User Management"

### 9. Metadata & Tagging
Comprehensive metadata including:
- `generated_by` - Source component identifier
- `generated_timestamp` - ISO 8601 generation time
- `domain` - Business domain classification
- `version` - Output schema version
- `model_name` - LLM model identifier
- `confidence_score` - Quality confidence (0.0-1.0)

### 10. Confidence Scoring
Generates quality confidence score considering:
- **Coverage Score** (primary): `mapped_requirements / total_requirements`
- **Granularity Quality**: Features per epic should be 2-5 (optimal)
- **Dependency Complexity**: Some dependencies good, excessive indicates poor decomposition
- **Ambiguity Presence**: Penalties for unclear mappings
- **Validation Issues**: Inherited from Agent-1

#### Confidence Formula:
```
confidence = coverage_score × dependency_factor × (1 - granularity_penalty) × (1 - ambiguity_penalty)
Constraints: 0.0 <= confidence_score <= 1.0
```

#### Confidence Interpretation:
- **0.9-1.0** - Excellent: Complete mapping, clear hierarchy, no conflicts
- **0.75-0.89** - Good: Minor ambiguities, some overlaps
- **0.5-0.74** - Fair: Moderate issues, weak grouping
- **< 0.50** - Low: Major mapping issues, insufficient coverage

## Output Structure

### Extended EpicFeaturePlannerOutput Schema

```json
{
  "epics": [
    {
      "id": "EPIC-001",
      "name": "Epic Title",
      "description": "Scope and goals"
    }
  ],
  "features": [
    {
      "id": "FEAT-001",
      "epic_id": "EPIC-001",
      "name": "Feature Title",
      "description": "Feature scope",
      "priority": "High"
    }
  ],
  "hierarchy": [
    {
      "requirement_id": "REQ-001",
      "feature_id": "FEAT-001"
    }
  ],
  "requirement_mapping": [
    {
      "requirement_id": "REQ-001",
      "requirement_content": "Original requirement",
      "epic_id": "EPIC-001",
      "feature_id": "FEAT-001"
    }
  ],
  "epic_hierarchy": [
    {
      "epic_id": "EPIC-001",
      "feature_ids": ["FEAT-001", "FEAT-002"],
      "requirement_ids": ["REQ-001", "REQ-002"]
    }
  ],
  "dependencies": [
    {
      "dependent_feature_id": "FEAT-002",
      "dependency_feature_id": "FEAT-001",
      "dependency_type": "blocks"
    }
  ],
  "priority": [
    {
      "feature_id": "FEAT-001",
      "priority": "High"
    }
  ],
  "coverage_report": {
    "total_requirements": 12,
    "mapped_requirements": 12,
    "unmapped_requirements": 0,
    "coverage_percentage": 100.0
  },
  "metadata": {
    "generated_by": "Agent-2",
    "generated_timestamp": "2024-06-26T10:30:00Z",
    "domain": "Payment Processing",
    "version": "1.0",
    "model_name": "claude-3-5-sonnet",
    "confidence_score": 0.92
  },
  "traceability_matrix": [
    {
      "requirement_id": "REQ-001",
      "epic_id": "EPIC-001",
      "feature_id": "FEAT-001",
      "dependencies": ["FEAT-002"]
    }
  ]
}
```

## Integration with Orchestrator

### Non-LLM Orchestrator Functions

#### 1. Merge Outputs
Merges Agent-1 and Agent-2 outputs into **MasterContext**:
- Combines requirements, actors, business rules from Agent-1
- Adds epics, features, hierarchy, priorities from Agent-2
- Single source of truth for downstream processing

#### 2. Build Story Contexts
Generates one **StoryContext per requirement** from traceability matrix:
```python
{
    "story_id": "STORY-REQ-001",
    "requirement_id": "REQ-001",
    "requirement": "User can log in",
    "epic": {"id": "EPIC-001", "name": "Authentication"},
    "feature": {"id": "FEAT-001", "name": "Login", "priority": "High"},
    "actor": "Customer",
    "business_rules": ["Token expires in 24 hours"],
    "dependencies": ["FEAT-002"],
    "priority": "High",
    "validation": {...},
    "traceability": {...}
}
```

### Enhanced LangGraph Flow

```
START
  ↓
Agent-1 (Requirement Intelligence)
  ↓
Confidence Check (0.75 threshold)
  ↓
  ├→ Retry (if < 0.75 and retries < 3)
  │   ↓ (back to Agent-1)
  │
  └→ Agent-2 (Epic & Feature Planner)
      ↓
    Merge Outputs (Non-LLM orchestrator)
      ↓
    Build Story Contexts (Non-LLM orchestrator)
      ↓
    Agent-3 (receives optimized story contexts)
      ↓
    Agent-4 (Validation)
      ↓
    Human Review (Interrupt point)
      ↓
    Export
      ↓
     END
```

### State Management

**GraphState** includes:
```python
# Agent-2 outputs
epics: List[Dict[str, Any]]
features: List[Dict[str, Any]]
hierarchy: List[Dict[str, Any]]
requirement_mapping: List[Dict[str, Any]]
epic_hierarchy: List[Dict[str, Any]]
dependencies: List[Dict[str, Any]]
priority: List[Dict[str, Any]]
coverage_report: Dict[str, Any]
metadata: Dict[str, Any]
traceability_matrix: List[Dict[str, Any]]

# Orchestrator outputs
master_context: Dict[str, Any]
story_contexts: List[Dict[str, Any]]
```

## Validation Rules

1. ✓ All requirement IDs from Agent-1 MUST appear in hierarchy
2. ✓ All features MUST be under exactly one epic
3. ✓ All requirements MUST map to exactly one feature
4. ✓ No cyclic dependencies allowed
5. ✓ Priority must be one of: High, Medium, Low
6. ✓ coverage_percentage = (mapped / total) × 100
7. ✓ 0.0 ≤ confidence_score ≤ 1.0

## Implementation Details

### Files Modified

1. **agents/schemas.py** - Extended Pydantic models with:
   - RequirementMapping, EpicHierarchy, Dependency, FeaturePriority
   - CoverageReport, Metadata, TraceabilityMatrix
   - StoryContext, MasterContext
   - FeaturePlan now includes `priority` field

2. **agents/agent2_epic_feature_planner.py** - Enhanced with:
   - Confidence score calculation algorithm
   - Coverage report generation
   - Requirement mapping builder
   - Epic hierarchy construction
   - Traceability matrix generation
   - Domain context extraction

3. **agents/prompts/agent2.jinja2** - Comprehensive prompt including:
   - All 10 responsibilities
   - Detailed output schema
   - Validation rules
   - Confidence scoring guidance
   - Dependency type definitions

4. **orchestrator/state.py** - Extended GraphState with:
   - Agent-2 output fields
   - master_context
   - story_contexts
   - approval_status

5. **orchestrator/graph.py** - Enhanced workflow with:
   - Confidence check node
   - Merge outputs node (non-LLM)
   - Build story contexts node (non-LLM)
   - Updated graph flow with confidence routing
   - Human review interrupt point

6. **agents/tests/test_agents.py** - Comprehensive tests for:
   - All new schema fields and validations
   - Confidence score constraints
   - Priority and dependency types
   - Master context and story context creation

## Token Optimization

The orchestrator implements smart token optimization:

1. **Agent-1 Output** → Used for requirement extraction only
2. **Agent-2 Output** → Structured and cached at orchestrator level
3. **Story Contexts** → Individual, lightweight contexts sent to Agent-3
   - Each context contains only relevant information for one requirement
   - No duplication of master context data
   - Optimal token usage per user story

## Backward Compatibility

All changes maintain backward compatibility:
- Existing fields preserved
- New fields use sensible defaults
- Existing code paths continue to work
- No breaking changes to interfaces

## Usage Example

See `sample_agent2_output.json` for a complete example with:
- 3 Epics (Authentication, Payments, Reporting)
- 9 Features with priorities
- 12 Requirements with complete mapping
- 5 Dependencies with types
- 100% coverage
- 0.92 confidence score

## References

- **LangGraph Documentation**: State management, interrupts, routing
- **Pydantic v2**: Type validation, schema extension
- **Python 3.12**: Async/await patterns, type hints
