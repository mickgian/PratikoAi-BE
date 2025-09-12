# RAG STEP 44 — Use default SYSTEM_PROMPT (RAG.prompting.use.default.system.prompt)

**Type:** process  
**Category:** prompting  
**Node ID:** `DefaultSysPrompt`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DefaultSysPrompt` (Use default SYSTEM_PROMPT).

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
  `RAG STEP 44 (RAG.prompting.use.default.system.prompt): Use default SYSTEM_PROMPT | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.25

Top candidates:
1) app/models/user.py:50 — app.models.user.User.verify_password (score 0.25)
   Evidence: Score 0.25, Verify if the provided password matches the hash.
2) app/models/user.py:55 — app.models.user.User.hash_password (score 0.25)
   Evidence: Score 0.25, Hash a password using bcrypt.
3) app/models/user.py:60 — app.models.user.User.set_refresh_token_hash (score 0.25)
   Evidence: Score 0.25, Set the hash of the refresh token.

Stores a bcrypt hash of the refresh token fo...
4) app/models/user.py:72 — app.models.user.User.verify_refresh_token (score 0.25)
   Evidence: Score 0.25, Verify if the provided refresh token matches the stored hash.

Args:
    refresh...
5) app/models/user.py:85 — app.models.user.User.revoke_refresh_token (score 0.25)
   Evidence: Score 0.25, Revoke the current refresh token by clearing its hash.

This effectively invalid...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for DefaultSysPrompt
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->