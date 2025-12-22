# ADR-021: Interactive Questions Architecture

## Status
**ACCEPTED** - Implemented in PRATIKO 1.5

## Context

### The Problem
Users often submit incomplete queries lacking essential parameters:
- "Calcola le tasse" (missing: income amount, taxpayer type)
- "Quanto devo pagare?" (missing: tax type, period, amounts)
- "Aiutami con la dichiarazione" (missing: declaration type, year)

The AI must either:
1. Ask clarifying questions (better UX, slower)
2. Make assumptions (faster, potentially wrong)
3. Provide generic answers (safe but unhelpful)

### Requirements
1. **Non-Blocking**: Questions should not interrupt the conversation flow
2. **Contextual**: Questions must be relevant to the user's query
3. **Skippable**: Users can proceed without answering
4. **Multi-Step Support**: Complex scenarios may need multiple questions
5. **Keyboard Accessible**: Full keyboard navigation support

### Alternatives Considered

#### Option 1: Modal Dialog Questions
- **Pros**: Clear separation, focused attention
- **Cons**: Interrupts flow, jarring UX
- **Rejected**: Poor mobile experience, breaks conversation context

#### Option 2: Separate Clarification Page
- **Pros**: Comprehensive data collection
- **Cons**: Navigation overhead, context loss
- **Rejected**: Too heavy for simple clarifications

#### Option 3: Inline Questions (Claude Code Style) (CHOSEN)
- **Pros**: Non-blocking, preserves context, familiar pattern
- **Cons**: Limited screen real estate
- **Selected**: Best balance of UX and functionality

## Decision

### Architecture Overview

We adopt an **Inline Interactive Questions** approach inspired by Claude Code's question interface:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Chat Interface                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────┐                 │
│  │ AI Message                                  │                 │
│  │ "Per aiutarti meglio, ho bisogno di        │                 │
│  │  sapere alcune informazioni..."            │                 │
│  └────────────────────────────────────────────┘                 │
│                                                                  │
│  ┌────────────────────────────────────────────┐                 │
│  │ InteractiveQuestionInline                  │                 │
│  │ ┌──────────────────────────────────────┐   │                 │
│  │ │ "Che tipo di contribuente sei?"      │   │                 │
│  │ └──────────────────────────────────────┘   │                 │
│  │                                            │                 │
│  │ ┌──────────┐ ┌──────────┐ ┌──────────┐   │                 │
│  │ │1. Persona│ │2. Azienda│ │3. Profes-│   │                 │
│  │ │   fisica │ │          │ │  sionista│   │                 │
│  │ └──────────┘ └──────────┘ └──────────┘   │                 │
│  │                                            │                 │
│  │ [________________] Altro: scrivi...        │                 │
│  │                                            │                 │
│  │ Premi Esc per saltare • Usa 1-3 per        │                 │
│  │ selezione rapida                           │                 │
│  └────────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

### Question Template Schema

```yaml
# app/templates/questions/tax_clarifications.yaml
questions:
  - id: "taxpayer-type"
    text: "Che tipo di contribuente sei?"
    question_type: "single_choice"
    domain: "tax"
    options:
      - id: "persona-fisica"
        label: "Persona fisica"
        leads_to: "income-range"  # Multi-step flow
      - id: "azienda"
        label: "Azienda"
        leads_to: "company-size"
      - id: "professionista"
        label: "Professionista"
        requires_input: false
    allow_custom_input: true
    custom_input_placeholder: "Specifica tipo..."
```

### Question Types

| Type | Description | Example |
|------|-------------|---------|
| `single_choice` | Select one option | Taxpayer type |
| `multi_choice` | Select multiple | Applicable deductions |
| `text_input` | Free text | Specific amount |
| `date_range` | Date selection | Tax period |

### State Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Incomplete │────>│   Question  │────>│  Complete   │
│    Query    │     │   Displayed │     │   Response  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
                    v             v
              ┌──────────┐  ┌──────────┐
              │  Answer  │  │   Skip   │
              │ Selected │  │  (Esc)   │
              └────┬─────┘  └────┬─────┘
                   │             │
                   v             v
              ┌──────────┐  ┌──────────┐
              │  Next    │  │  Default │
              │ Question │  │ Response │
              │ or Done  │  │          │
              └──────────┘  └──────────┘
```

### Keyboard Navigation

| Key | Action |
|-----|--------|
| `1-9` | Quick select option by number |
| `↑/↓` | Navigate between options |
| `←/→` | Navigate between options |
| `Enter` | Select focused option |
| `Escape` | Skip question |
| `Tab` | Move to custom input field |

### Parameter Coverage Algorithm

```python
def should_ask_question(
    extraction_result: ParameterExtractionResult
) -> bool:
    """
    Determine if clarifying question is needed.

    Decision Logic:
    - coverage < 0.3: Always ask (insufficient info)
    - coverage 0.3-0.8: Ask based on missing critical params
    - coverage > 0.8: Smart fallback (proceed with defaults)

    Returns False if:
    - can_proceed_with_defaults is True
    - All critical parameters are present
    """
    if extraction_result.can_proceed_with_defaults:
        return False

    if extraction_result.coverage < 0.3:
        return True

    # Check for critical missing params
    critical_missing = [
        p for p in extraction_result.missing_params
        if p in CRITICAL_PARAMS
    ]
    return len(critical_missing) > 0
```

### API Integration

Questions are returned in the `ChatResponse` schema:

```python
class ChatResponse(BaseModel):
    message: str
    interactive_question: Optional[InteractiveQuestion] = None
    extracted_params: Optional[Dict[str, Any]] = None
    # ... other fields
```

For streaming, questions are sent as a separate SSE event:

```
event: interactive_question
data: {"question": {...}}

event: done
data: {}
```

### Answer Endpoint

```python
@router.post("/questions/answer")
async def answer_question(
    request: QuestionAnswerRequest
) -> QuestionAnswerResponse:
    """
    Process user's answer to an interactive question.

    Flow:
    1. Validate question_id and option_id
    2. Check if option leads to next question
    3. If terminal, generate response with collected params
    4. Return next question or final response
    """
```

## Consequences

### Positive
1. **Non-Intrusive UX**: Questions appear inline, not blocking
2. **Context Preservation**: User stays in conversation flow
3. **Accessibility**: Full keyboard navigation support
4. **Mobile-Friendly**: Touch targets ≥ 44px, responsive grid
5. **Skippable**: Users can always proceed without answering

### Negative
1. **State Complexity**: Multi-step flows require state management
2. **Screen Real Estate**: Questions take vertical space
3. **Template Maintenance**: Questions must be curated manually

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Question overload | Max 1 question at a time |
| Stale question templates | Quarterly review |
| Complex multi-step flows | Limit to 3 steps max |
| Mobile keyboard overlap | Scroll into view on focus |

## Implementation Details

### Files Created

**Backend:**
- `app/schemas/proactivity.py` - InteractiveQuestion, Option schemas
- `app/services/proactivity_engine.py` - Question generation logic
- `app/templates/questions/*.yaml` - Question templates
- `app/api/v1/chatbot.py` - /questions/answer endpoint

**Frontend:**
- `InteractiveQuestionInline.tsx` - Question component
- `useKeyboardNavigation.ts` - Keyboard hook
- `AIMessageV2.tsx` - Integration

### Testing

**Backend:**
- 27 unit tests for ProactivityEngine (question logic)
- 21 integration tests for /questions/answer endpoint

**Frontend:**
- 26 unit tests for InteractiveQuestionInline
- 30 unit tests for useKeyboardNavigation
- 13 E2E tests for complete flows

## References
- [PRATIKO 1.5 Specification](../tasks/PRATIKO_1.5.md)
- [FR-002: Interactive Questions](../tasks/PRATIKO_1.5_REFERENCE.md#32-fr-002-domande-interattive-strutturate)
- [Claude Code UI Pattern](https://claude.com/claude-code)
