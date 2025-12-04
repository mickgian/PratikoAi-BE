# Frontend Session Management Fix Requirements

**Created:** 2025-11-26
**Status:** TODO
**Priority:** HIGH
**Related Backend Fix:** DEV-BE-91 (Chat Deduplication - COMPLETED)

---

## Issue #1: Chat Deduplication Not Working

### Problem Description
When a user asks the same question multiple times in different sessions, the frontend is not creating a new chat history item. Instead, it appears to be reusing the previous chat history entry.

### Expected Behavior
1. User asks question A in Session 1 → New chat history item created
2. User starts a new chat (clicks "Nuova chat")
3. User asks the same question A in Session 2 → **New separate chat history item should be created**

### Current Behavior
- Question A in Session 2 appears to reuse the chat history item from Session 1
- No new chat history entry is created in the sidebar/chat list

### Backend Fix Status
✅ **COMPLETED** - Backend now generates unique query signatures with microsecond timestamps to prevent collisions across sessions.

**File:** `app/core/langgraph/graph.py`
**Function:** `generate_query_signature(session_id, user_message, include_timestamp=True)`

```python
# Each query now has a unique signature with timestamp
timestamp_us = int(time.time() * 1_000_000)
return f"session_{session_id}_{timestamp_us}_{message_hash}"
```

### Frontend Fix Required
The frontend needs to:

1. **Session Isolation:** Ensure each session (when user clicks "Nuova chat") gets a completely new conversation context
2. **Chat History Management:** When the backend returns a response with a new query_signature, create a new chat history item in the UI
3. **API Integration:** Check if the frontend is properly handling the session_id and query_signature from the backend response

### Investigation Steps for Frontend Team

1. Check how chat history is stored (local state, Redux, Context API?)
2. Verify that session_id changes when user clicks "Nuova chat"
3. Ensure chat history items are keyed by query_signature or session_id + timestamp (not just by message text)
4. Review the API integration to ensure new chat history items are created for each unique query_signature

### Test Cases

**Test Case 1: Same Question, Different Sessions**
1. Start new chat (Session A)
2. Ask: "Di cosa parla la risoluzione 64?"
3. Verify new chat item created in sidebar
4. Click "Nuova chat" (Session B)
5. Ask: "Di cosa parla la risoluzione 64?"
6. **Expected:** Second chat item created in sidebar
7. **Verify:** Two separate items in chat history list

**Test Case 2: Different Questions, Same Session**
1. Start new chat
2. Ask question A
3. Ask question B
4. **Expected:** Both questions appear in same chat history
5. **Verify:** Single chat item with multiple messages

---

## Issue #2: "Nuova Chat" Button Not Clearing Selection

### Problem Description
When the user clicks the "Nuova chat" button, the currently selected chat history item remains visually selected (highlighted/colored differently). The selection state should be cleared.

### Expected Behavior
1. User has Chat Item A selected (highlighted in chat history list)
2. User clicks "Nuova chat" button
3. **Chat Item A should no longer be highlighted**
4. New chat session starts with no history item selected

### Current Behavior
- After clicking "Nuova chat", the previous chat item remains highlighted
- User cannot visually distinguish that they're in a new chat session

### Frontend Fix Required

1. **Clear Selection State:** When "Nuova chat" is clicked, reset the selected chat history item to null/undefined
2. **Visual Feedback:** Ensure no chat items are highlighted when starting a new chat
3. **State Management:** Update the selection state in the chat history component

### Implementation Suggestions

```typescript
// Example pseudocode
function handleNewChatClick() {
  // 1. Clear selected chat item
  setSelectedChatId(null);

  // 2. Generate new session ID
  const newSessionId = generateSessionId();

  // 3. Reset chat messages
  setChatMessages([]);

  // 4. Update UI to show no selection
  // Remove 'selected' class from all chat items
}
```

### Test Cases

**Test Case 1: Clear Selection on New Chat**
1. Click on any existing chat history item (it gets highlighted)
2. Click "Nuova chat" button
3. **Expected:** Previous chat item is no longer highlighted
4. **Verify:** No chat items have selection styling applied

**Test Case 2: Selection After New Chat**
1. Click "Nuova chat"
2. Send a message (creates new chat history item)
3. Click on another existing chat item
4. **Expected:** Only the clicked item is highlighted
5. **Verify:** Single selection, proper highlight

---

## Technical Context

### Backend Session Management

The backend uses a session-based approach where:
- Each chat session has a unique `session_id`
- Each query within a session has a unique `query_signature`
- Format: `session_{session_id}_{timestamp_us}_{message_hash}`

### API Response Format

The backend returns responses with metadata including:
- `session_id`: Current session identifier
- `query_signature`: Unique signature for this specific query
- `conversation_id`: Conversation context (may span multiple sessions)

### Frontend-Backend Contract

The frontend should:
1. Send `session_id` with each API request
2. Generate a new `session_id` when user clicks "Nuova chat"
3. Use the `query_signature` from the response to manage chat history items
4. Never reuse `session_id` across different chat sessions

---

## Acceptance Criteria

### Issue #1 (Chat Deduplication)
- [ ] Each new chat session creates a new chat history item, even for duplicate questions
- [ ] Chat history list shows all sessions separately
- [ ] User can distinguish between different sessions asking the same question
- [ ] Session isolation works correctly (no crosstalk between sessions)

### Issue #2 (Nuova Chat Selection)
- [ ] Clicking "Nuova chat" clears the selected chat item
- [ ] No chat items are highlighted after starting a new chat
- [ ] User can clearly see they're in a new chat session
- [ ] Selection state is properly managed across navigation

---

## Priority & Timeline

**Priority:** HIGH
**Reason:** Core UX issue affecting chat session management

**Estimated Effort:** 2-4 hours
- Issue #1: 1-2 hours (state management + API integration)
- Issue #2: 1-2 hours (UI state reset + styling)

**Dependencies:** None (backend fix already deployed)

---

## Related Files (Backend)

- `app/core/langgraph/graph.py` - Query signature generation (line 309-333)
- `app/api/v1/chat.py` - Chat API endpoints
- `app/models/conversation.py` - Conversation and session models

---

## Testing Notes

### Backend Testing
✅ Backend tests verify unique query signatures:
- `tests/api/test_chat_session_isolation.py`
- `tests/core/test_query_signature_generation.py`

### Frontend Testing Required
- Manual testing with Chrome DevTools (check session_id in API requests)
- Verify chat history state management
- Test "Nuova chat" button behavior
- Cross-browser testing (Chrome, Firefox, Safari)

---

## Questions for Frontend Team

1. How is session_id currently generated on the frontend?
2. Is session_id persisted (localStorage, cookies, or in-memory)?
3. What state management library is used (Redux, Context, Zustand)?
4. Where is the chat history list implemented?
5. What triggers a new chat history item to be created?

---

## Contact

**Backend Lead:** @ezio (backend-expert agent)
**Frontend Lead:** @livia (frontend-expert agent)
**Issue Reporter:** User (manual testing)

**Slack Channel:** #dev-frontend
**Related PR:** TBD (pending frontend implementation)
