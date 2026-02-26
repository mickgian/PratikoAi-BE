# ADR-035: Notification-Only Delivery for Proactive Suggestions (FR-004)

## Status
Accepted

## Date
2026-02-26

## Context

FR-004 (Proactive Suggestions & Communications) originally specified two delivery
mechanisms for informing professionals about client-normative matches:

1. **In-chat flow** (PRATIKO_2.0_REFERENCE.md §3.4.3 Step 2): After the user asks a
   normative question, the RAG pipeline would simultaneously run client matching and
   append a suggestion card inline in the chat response ("La rottamazione quinquies
   potrebbe interessare 7 dei tuoi clienti. Vuoi che ti prepari un messaggio?").

2. **Notification system** (Phase 13, DEV-422 to DEV-427): Background notifications
   triggered by RSS ingestion or matching events, displayed in a bell icon dropdown.

### Problems with the in-chat flow

#### 1. RAG context pollution

The chat history is the RAG pipeline's primary memory. Injecting client match results,
suggestion cards, and action buttons (Sì/No/Mostra lista) into the conversation history
means every subsequent normative question carries CRM data in its context window. Client
names, match counts, and channel preferences are irrelevant to answering fiscal questions
and degrade retrieval quality over time.

#### 2. Mixed responsibilities in a single LLM call

The in-chat flow requires the LLM to simultaneously:
- Answer a normative question (its core job — knowledge retrieval)
- Present client match results (a CRM concern)
- Offer interactive action buttons (a workflow concern)
- If the user accepts, switch to communication drafting mode (a completely different task)

This creates fragile prompt engineering and unpredictable output formatting.

#### 3. Synchronous coupling adds latency and failure risk

DEV-323 (LangGraph Matching Node) was designed to insert a synchronous node after
step 35 in the 134-step RAG pipeline. Even with a <100ms target, this:
- Adds a hard dependency on the client database during every chat query
- If the matching query is slow or fails, it **blocks the normative response** the
  user actually asked for
- The user didn't ask "which clients does this affect?" — they asked about the regulation

#### 4. UX complexity crammed into chat

The full FR-004 workflow (message editor, recipient selection table, channel picker,
WhatsApp modals) is too complex for inline chat bubbles. The GestioneComunicazioniPage
already provides a dedicated, full-featured UI for this workflow.

#### 5. Architectural opposition, not complementarity

The in-chat flow and notification system serve the same purpose (inform about matches)
through contradictory mechanisms. Having both creates confusion about where the user
should manage their proactive suggestions.

## Decision

### Remove the in-chat suggestion flow; use notification-only delivery

All proactive suggestion delivery happens through the **notification system** (DEV-422
to DEV-427), never inline in the chat response.

### How it works

```
User asks: "Spiegami la rottamazione quinquies"
    ↓
RAG pipeline runs normally (NO matching node, NO modification)
    ↓
Normative response delivered to user (clean, fast)
    ↓
ASYNC (fire-and-forget, after response):
    ↓
Background matching job detects: topic="rottamazione" + studio clients
    ↓
Creates ClientMatch records + ProactiveSuggestion records
    ↓
Creates MATCH notification: "La rottamazione quinquies potrebbe
    interessare 7 dei tuoi clienti"
    ↓
Bell icon badge updates (unread count +1)
    ↓
User clicks notification → navigates to Comunicazioni page
    ↓
Full workflow on dedicated page: draft → edit → select recipients → send
```

### What changes

| Before (in-chat) | After (notification-only) |
|-------------------|--------------------------|
| Inline suggestion card in chat bubble | MATCH notification in bell dropdown |
| "Sì/No/Mostra lista" buttons in chat | Notification links to Comunicazioni page |
| Message editor inline in chat | Full editor on GestioneComunicazioniPage |
| Recipient table in chat | Recipient management on dedicated page |
| Matching node synchronous in RAG pipeline | Matching runs async after response delivery |

### What stays the same

- **NormativeMatchingService** (DEV-320): Same matching logic, same rules engine
- **Background Matching Job** (DEV-325): Already designed as async — becomes the
  primary delivery path
- **CommunicationService** (DEV-330): Same draft/approve/send workflow
- **GestioneComunicazioniPage**: Already designed with full editor, recipient
  selection, channel picker
- **NotificationsDropdown** (DEV-426): Already shows MATCH type notifications
- **WhatsApp integration** (DEV-334): Same wa.me modal flow

### Trigger mechanisms

Matching is triggered by two events:

1. **User query (async)**: After a normative response is delivered, a lightweight
   background task checks if the topic has matching rules. If clients match,
   a MATCH notification is created. No impact on response latency.

2. **RSS/KB ingestion (async)**: When new regulations are ingested, the background
   matching job (DEV-325) scans all studio clients. Same as originally designed.

### Tasks affected

| Task | Change |
|------|--------|
| **DEV-323** (LangGraph Matching Node) | **REMOVED** — No longer inserting a node into the RAG pipeline |
| **DEV-337** (Response Formatter with Suggestions) | **REMOVED** — Response formatter stays unmodified |
| **DEV-325** (Background Matching Job) | **EXPANDED** — Now also triggered after chat queries (async), not just RSS ingestion |
| **DEV-425** (Notification Creation Triggers) | **EXPANDED** — MATCH notifications are now the primary delivery for chat-triggered matches |

### Acceptance criteria updates

| Old (in-chat) | New (notification) |
|----------------|-------------------|
| AC-004.1: Suggestion appears within 2s of response | AC-004.1: MATCH notification created within 5s of response delivery |
| AC-003.1: Matching in parallel, no delay | AC-003.1: Matching async after response, zero added latency |
| AC-003.2: Suggestion appears only if count > 0 | AC-003.2: Notification created only if count > 0 |

## Consequences

### Positive

- **Zero impact on RAG pipeline**: No new nodes, no state modifications, no latency
- **Failure isolation**: If matching fails, the user still gets their normative answer
- **Clean separation of concerns**: RAG does knowledge, matching does CRM, notifications
  do delivery
- **Simpler LangGraph**: No modification to the 134-step pipeline (eliminates HIGH RISK
  flag from DEV-323)
- **Better UX for complex workflows**: Message editing, recipient selection, and channel
  picking happen on a dedicated page designed for that purpose
- **Fewer tasks**: DEV-323 and DEV-337 are removed, reducing implementation scope
- **Chat history stays clean**: No CRM data in conversation context

### Negative

- **Less "magical" UX**: The user doesn't see the suggestion immediately in the chat.
  They need to notice the bell icon badge.
- **Extra click**: User must click the notification to reach the Comunicazioni page,
  rather than acting directly in chat.

### Mitigation for UX trade-off

- Bell icon badge pulsing animation on new MATCH notifications (visual cue)
- Toast/snackbar notification: "Trovati 7 clienti interessati alla rottamazione
  quinquies" (appears briefly after response, dismisses automatically)
- MATCH notifications are HIGH priority (sorted to top of notification list)

## Alternatives Considered

### 1. Keep both systems (in-chat + notification)

Rejected. Having two parallel delivery systems for the same information creates
confusion and doubles implementation effort. Users wouldn't know where to manage
their matches.

### 2. In-chat only (no notifications)

Rejected. Background matching (RSS ingestion trigger) requires a notification
system anyway. Having in-chat only would miss matches discovered outside of
active chat sessions.

### 3. Lightweight in-chat banner (no full workflow)

Considered: show a minimal, non-interactive banner in chat ("7 clienti interessati —
vedi notifiche") without action buttons. Rejected because it still requires the
synchronous matching node in the RAG pipeline, and the banner adds no value over
the notification badge that would appear simultaneously.

## References

- FR-003: Matching Normativo Automatico (PRATIKO_2.0_REFERENCE.md §3.3)
- FR-004: Suggerimenti Proattivi e Generazione Comunicazioni (PRATIKO_2.0_REFERENCE.md §3.4)
- ADR-004: LangGraph for RAG pipeline
- ADR-018: Normative Matching Engine
- ADR-019: Communication Generation
- DEV-422 to DEV-427: Notification System (Phase 13)
- DEV-320 to DEV-328: Matching Engine (Phase 2)
