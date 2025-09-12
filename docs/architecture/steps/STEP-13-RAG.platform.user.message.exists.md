# RAG STEP 13 — User message exists? (RAG.platform.user.message.exists)

**Type:** decision  
**Category:** platform  
**Node ID:** `MessageExists`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `MessageExists` (User message exists?).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ❓ Pending review (✅ Implemented / 🟡 Partial / ❌ Missing / 🔌 Not wired)
- **Behavior notes:** _TBD_

## Differences (Blueprint vs Current)
- _TBD_

## Risks / Impact
- _TBD_

## TDD Task List
- [ ] Unit tests (list specific cases)
- [ ] Integration tests (list cases)
- [ ] Implementation changes (bullets)
- [ ] Observability: add structured log line  
  `RAG STEP 13 (RAG.platform.user.message.exists): User message exists? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) app/models/user.py:50 — app.models.user.User.verify_password (score 0.31)
   Evidence: Score 0.31, Verify if the provided password matches the hash.
2) app/models/user.py:55 — app.models.user.User.hash_password (score 0.31)
   Evidence: Score 0.31, Hash a password using bcrypt.
3) app/models/user.py:60 — app.models.user.User.set_refresh_token_hash (score 0.31)
   Evidence: Score 0.31, Set the hash of the refresh token.

Stores a bcrypt hash of the refresh token fo...
4) app/models/user.py:72 — app.models.user.User.verify_refresh_token (score 0.31)
   Evidence: Score 0.31, Verify if the provided refresh token matches the stored hash.

Args:
    refresh...
5) app/models/user.py:85 — app.models.user.User.revoke_refresh_token (score 0.31)
   Evidence: Score 0.31, Revoke the current refresh token by clearing its hash.

This effectively invalid...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->