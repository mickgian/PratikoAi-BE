# RAG STEP 110 — Send DONE frame (RAG.platform.send.done.frame)

**Type:** process  
**Category:** platform  
**Node ID:** `SendDone`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `SendDone` (Send DONE frame).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/platform.py:2891` - `step_110__send_done()`
- **Status:** ✅ Implemented
- **Behavior notes:** Orchestrator sending DONE frame to complete streaming response. Signals end of response stream and finalizes connection.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 110 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.30

Top candidates:
1) app/orchestrators/platform.py:2891 — app.orchestrators.platform.step_110__send_done (score 0.30)
   Evidence: Score 0.30, RAG STEP 110 — Send DONE frame
ID: RAG.platform.send.done.frame
Type: process | ...
2) app/api/v1/metrics.py:200 — app.api.v1.metrics.send_email_report (score 0.26)
   Evidence: Score 0.26, Send metrics report via email.
3) app/services/ccnl_notification_service.py:248 — app.services.ccnl_notification_service.CCNLNotificationService.send_notification (score 0.26)
   Evidence: Score 0.26, Send notification through specified channels.
4) app/services/scheduler_service.py:249 — app.services.scheduler_service.send_metrics_report_task (score 0.26)
   Evidence: Score 0.26, Scheduled task to send metrics reports.
5) app/services/scrapers/cassazione_scheduler.py:559 — app.services.scrapers.cassazione_scheduler.CassazioneScheduler._should_send_notification (score 0.26)
   Evidence: Score 0.26, Check if notification should be sent (with throttling).

Args:
    job: Schedule...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for SendDone
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->