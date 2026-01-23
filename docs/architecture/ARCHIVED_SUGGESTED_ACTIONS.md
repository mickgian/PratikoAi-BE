# Archived: Suggested Actions Feature (Azioni Suggerite)

**Status:** REMOVED (January 23, 2026)
**Removal Reason:** User feedback - actions were generic, not contextually relevant, felt like filler content
**Removal Ticket:** DEV-245 Phase 5.15

---

## Overview

The "Suggested Actions" (Azioni Suggerite) feature displayed actionable buttons after AI responses. It was designed to guide users toward common follow-up actions but was removed due to poor user reception.

### What It Looked Like

```
[AI Response about rottamazione quinquies...]

Azioni suggerite:
1. Compila modulo di domanda
2. Controlla documenti
3. Invia domanda online
```

---

## Why It Was Built

1. **User Engagement:** Encourage users to take next steps
2. **Reduced Typing:** Pre-built prompts for common follow-ups
3. **Feature Differentiation:** Distinguish from basic chatbots

---

## Why It Was Removed

User feedback revealed:
1. **Generic Actions:** "Compila modulo" appeared for every query, regardless of context
2. **Not Contextually Relevant:** Actions often didn't relate to the actual question
3. **Filler Content Feel:** Felt like padding rather than genuine assistance
4. **"Chatbot Checklist" Effect:** Undermined the expert assistant persona

---

## Architecture (For Historical Reference)

### Data Flow

```
User Query → LLM Router → LLM generates response with XML tags:
<answer>...</answer>
<suggested_actions>[{"id":"1","label":"...","prompt":"..."}]</suggested_actions>
    ↓
parse_llm_response() extracts answer + actions
    ↓
Step 100: ActionValidator checks label/prompt length, topic relevance
    ↓
If <2 valid actions: ActionRegenerator asks LLM for better ones
    ↓
SSE event "suggested_actions" sent to frontend
    ↓
SuggestedActionsBar renders numbered list (1., 2., 3.)
    ↓
User clicks → action.prompt_template sent as new query
```

### Decision Tree

1. Is query a CALCULABLE_INTENT (IRPEF, IVA, etc.) + missing params? → Interactive Question (KEPT)
2. Is document recognized (fattura, F24, bilancio)? → Template Actions (REMOVED)
3. Otherwise → LLM generates actions (REMOVED)

---

## Backend Files (Deleted)

| File | Purpose |
|------|---------|
| `app/core/prompts/suggested_actions.md` | LLM prompt for action generation |
| `app/services/action_validator.py` | Validates action quality (label length, topic relevance) |
| `app/services/action_regenerator.py` | Regenerates bad actions via LLM |
| `app/services/action_quality_metrics.py` | Quality metrics for actions |

### Test Files (Deleted)

| File | Purpose |
|------|---------|
| `tests/core/prompts/test_suggested_actions_prompt.py` | Prompt tests |
| `tests/unit/services/test_action_validator.py` | Validator tests |
| `tests/unit/services/test_action_regenerator.py` | Regenerator tests |
| `tests/unit/services/test_action_quality_metrics.py` | Metrics tests |
| `tests/unit/prompts/test_action_regeneration.py` | Regeneration tests |
| `tests/api/test_chatbot_actions.py` | API integration tests |

---

## Backend Files (Modified)

### `app/services/llm_response_parser.py`

**Before:**
```python
ANSWER_PATTERN = re.compile(r"<answer>(.*?)</answer>", re.DOTALL)
ACTIONS_PATTERN = re.compile(r"<suggested_actions>\s*(\[.*?\])\s*</suggested_actions>", re.DOTALL)

class ParsedLLMResponse(BaseModel):
    answer: str
    suggested_actions: list[SuggestedAction]
```

**After:**
```python
ANSWER_PATTERN = re.compile(r"<answer>(.*?)</answer>", re.DOTALL)
# ACTIONS_PATTERN removed

class ParsedLLMResponse(BaseModel):
    answer: str
    # suggested_actions field removed
```

### `app/core/langgraph/nodes/step_100__post_proactivity.py`

**Removed:**
- Import of `ActionValidator`, `ActionRegenerator`
- `_build_proactivity_update()` function
- `_build_topic_context()` function
- `_extract_previous_action_labels()` function
- Action validation/regeneration logic

**Kept:**
- Web verification logic (DEV-245)
- Topic keywords preservation

### `app/api/v1/chatbot.py`

**Removed (lines ~1427-1441):**
```python
if graph_proactivity_actions:
    actions_event = StreamResponse(
        content="",
        event_type="suggested_actions",
        suggested_actions=graph_proactivity_actions,
    )
    yield write_sse(None, format_sse_event(actions_event), request_id=request_id)
```

### `app/schemas/proactivity.py`

**Removed:**
- `ActionCategory` enum
- `Action` class
- `ActionSummary` class
- `ActionContext` class

**Kept:**
- `InteractiveQuestion` and related classes

---

## Frontend Files (Deleted)

| File | Purpose |
|------|---------|
| `src/app/chat/components/SuggestedActionsBar.tsx` | Action buttons component |
| `src/app/chat/components/__tests__/SuggestedActionsBar.test.tsx` | Component tests |

---

## Frontend Files (Modified)

### `src/lib/api.ts`

**Removed:**
```typescript
export interface SuggestedAction {
  id: string;
  label: string;
  icon: string;
  category: string;
  prompt_template: string;
  requires_input?: boolean;
  input_placeholder?: string;
  input_type?: string;
}
```

**Removed from SseFrame:**
```typescript
suggested_actions?: SuggestedAction[];
```

---

## Code Snippets (For Reference)

### ActionValidator Logic

```python
class ActionValidator:
    """Validates suggested action quality."""

    MIN_LABEL_LENGTH = 10
    MAX_LABEL_LENGTH = 60
    MIN_PROMPT_LENGTH = 15
    MAX_PROMPT_LENGTH = 200

    def validate_batch_with_topic_context(
        self,
        actions: list[dict],
        response_text: str,
        kb_sources: list[dict],
        topic_context: dict | None,
        previous_actions_used: list[str],
    ) -> BatchValidationResult:
        """Validate actions with topic filtering."""
        # ... validation logic
```

### ActionRegenerator Logic

```python
class ActionRegenerator:
    """Regenerates actions when validation fails."""

    async def regenerate_if_needed(
        self,
        original_actions: list[dict],
        validation_result: BatchValidationResult,
        response_context: ResponseContext,
    ) -> list[dict] | None:
        """Regenerate actions if too few valid."""
        if len(validation_result.validated_actions) >= 2:
            return None  # Enough valid actions

        # Call LLM to generate better actions
        prompt = self._build_regeneration_prompt(response_context)
        # ...
```

### SuggestedActionsBar Component

```tsx
export function SuggestedActionsBar({
  actions,
  onActionClick,
  isLoading = false,
  disabled = false,
}: SuggestedActionsBarProps) {
  // Renders numbered list of actions
  // Keyboard shortcuts (1-9 to select)
  // Input field for requires_input actions
}
```

---

## What Was Preserved

### Interactive Questions

The pre-response clarification questions feature was kept:
- `InteractiveQuestionInline.tsx` component
- `interactive_question` SSE event
- `CALCULABLE_INTENTS` and param detection

Example:
```
User: "Calcola l'IRPEF"
AI: [Interactive Question] "Quale tipo di contribuente?"
  1. Dipendente
  2. Autonomo
  3. Pensionato
```

### Web Verification

DEV-245 web verification was kept:
- Caveats and contradictions detection
- Brave Search integration
- `web_verification` SSE event

---

## Lessons Learned

1. **User feedback is critical:** Features that seem useful to developers may not resonate with users
2. **Context matters:** Generic actions feel unhelpful; highly contextual ones might work
3. **Persona consistency:** "Expert assistant" persona conflicts with "chatbot checklist" UX
4. **Less is more:** Removing clutter can improve perceived quality

---

## Potential Future Alternatives

If revisiting this feature:
1. **Hyper-contextual actions:** Only show when genuinely relevant (e.g., detect specific document types)
2. **User preference:** Let users enable/disable in settings
3. **A/B testing:** Test specific action types before full rollout
4. **Source-grounded actions:** Only suggest actions backed by KB content

---

**Archive Date:** January 23, 2026
**Archived By:** DEV-245 Phase 5.15 Implementation
