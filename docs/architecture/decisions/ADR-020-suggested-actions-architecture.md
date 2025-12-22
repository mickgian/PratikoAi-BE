# ADR-020: Suggested Actions Architecture

## Status
**ACCEPTED** - Implemented in PRATIKO 1.5

## Context

### The Problem
After receiving AI responses, users often need to perform follow-up actions such as:
- Calculating specific values (IVA, IRPEF, contributions)
- Searching for related regulations
- Exporting data in different formats
- Verifying information against official sources

Without proactive suggestions, users must:
1. Formulate follow-up queries manually
2. Remember available functionality
3. Navigate away from the conversation context

### Requirements
1. **Contextual Relevance**: Suggestions must be relevant to the current conversation
2. **Performance**: Must not slow down response delivery (< 100ms additional latency)
3. **Extensibility**: Easy to add new action types per domain
4. **Italian Tax Domain Focus**: Optimized for fiscal/labor law scenarios

### Alternatives Considered

#### Option 1: LLM-Generated Actions
- **Pros**: Highly personalized, dynamic
- **Cons**: Slow (500ms+ per generation), inconsistent, expensive
- **Rejected**: Performance and cost concerns

#### Option 2: Rule-Based Hardcoded Actions
- **Pros**: Fast, predictable
- **Cons**: Inflexible, requires code changes
- **Rejected**: Maintenance burden

#### Option 3: Template-Based Selection (CHOSEN)
- **Pros**: Fast (< 50ms), configurable via YAML, domain-specific
- **Cons**: Limited personalization
- **Selected**: Best balance of performance and flexibility

## Decision

### Architecture Overview

We adopt a **Template-Based Action Selection** approach with the following components:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ProactivityEngine                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │ ActionTemplate   │    │ AtomicFacts      │                   │
│  │ Service          │    │ Extractor        │                   │
│  │ (YAML Loading)   │    │ (Parameter       │                   │
│  └────────┬─────────┘    │  Coverage)       │                   │
│           │              └────────┬─────────┘                   │
│           │                       │                              │
│           v                       v                              │
│  ┌────────────────────────────────────────────┐                 │
│  │           Action Selection Logic            │                 │
│  │  - Domain matching                          │                 │
│  │  - Document type matching                   │                 │
│  │  - Coverage-based filtering                 │                 │
│  └────────────────────────────────────────────┘                 │
│                          │                                       │
│                          v                                       │
│  ┌────────────────────────────────────────────┐                 │
│  │         ProactivityResult                   │                 │
│  │  - actions: List[Action]                    │                 │
│  │  - processing_time_ms: float                │                 │
│  └────────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

### Action Template Schema

```yaml
# app/templates/actions/tax_domain.yaml
actions:
  - id: "calc-iva-22"
    label: "Calcola IVA 22%"
    icon: "calculator"
    category: "calculate"
    prompt_template: "Calcola l'IVA al 22% su {{amount}} euro"
    domain: "tax"
    requires_input: true
    input_placeholder: "Inserisci importo..."
    input_type: "number"

  - id: "search-normativa"
    label: "Cerca normativa"
    icon: "search"
    category: "search"
    prompt_template: "Cerca la normativa su {{topic}}"
    domain: "tax"
    requires_input: true
    input_placeholder: "Argomento da cercare..."
```

### Action Categories

| Category | Icon | Use Case |
|----------|------|----------|
| `calculate` | calculator | Tax calculations, rates |
| `search` | search | Regulatory lookups |
| `verify` | check | Fact verification |
| `export` | download | Data export |
| `explain` | help | Detailed explanations |

### Selection Algorithm

```python
def select_actions(
    domain: str,
    document_type: Optional[str],
    extraction_result: ParameterExtractionResult
) -> List[Action]:
    """
    Select relevant actions based on context.

    Priority:
    1. Document-specific actions (if document attached)
    2. Domain-specific actions
    3. General actions (fallback)

    Filtering:
    - Max 4 actions returned
    - Actions requiring missing params are deprioritized
    """
```

### API Integration

Actions are returned in the `ChatResponse` schema:

```python
class ChatResponse(BaseModel):
    message: str
    suggested_actions: Optional[List[Action]] = None
    # ... other fields
```

For streaming, actions are sent as a separate SSE event:

```
event: suggested_actions
data: {"actions": [...]}

event: done
data: {}
```

## Consequences

### Positive
1. **Fast Response**: < 50ms action selection, no LLM call required
2. **Consistent UX**: Same actions for same contexts
3. **Easy Maintenance**: YAML templates editable without code deploy
4. **Domain Expertise**: Templates curated by domain experts
5. **Testable**: Deterministic selection logic

### Negative
1. **Limited Personalization**: Same actions for all users in same context
2. **Manual Curation**: Templates must be maintained manually
3. **Coverage Gaps**: New scenarios require new templates

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Stale templates | Quarterly review cycle |
| Missing domain coverage | Monitor usage analytics, add templates |
| Action overload | Limit to 4 actions max |

## Implementation Details

### Files Created
- `app/schemas/proactivity.py` - Pydantic schemas
- `app/services/action_template_service.py` - YAML loading
- `app/services/proactivity_engine.py` - Selection logic
- `app/templates/actions/*.yaml` - Domain templates

### Testing
- 30 unit tests for ActionTemplateService
- 27 unit tests for ProactivityEngine
- 76 integration tests for API endpoints

## References
- [PRATIKO 1.5 Specification](../tasks/PRATIKO_1.5.md)
- [FR-001: Suggested Actions](../tasks/PRATIKO_1.5_REFERENCE.md#31-fr-001-azioni-suggerite-post-risposta)
