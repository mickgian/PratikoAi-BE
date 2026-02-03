# PratikoAI v1.9 Backlog - Autonomous Workflow Engine

**Version:** 1.9
**Date:** February 2026
**Status:** BACKLOG (moved from v1.8)
**Label:** Pratiko 1.9
**GitHub Issues:** DEV-260 to DEV-273 (CLOSED)

---

## Overview

This document archives the original v1.8 "Autonomous Workflow Engine" plan, which was deprioritized in favor of the Social Campaign Creator feature.

The Italian Tax Workflows feature includes:
- Desktop application (Kotlin Multiplatform + Compose)
- Project-based organization with folder sync
- 4 core workflows: Dichiarazione Redditi, Adempimenti Periodici, Apertura/Chiusura, Pensionamento
- Human-in-the-loop checkpoints
- GDPR-compliant EU data processing

---

## Why Backlogged?

1. **Market opportunity:** Social Campaign Creator addresses immediate pain point (2-4h/week wasted on social media)
2. **Technical foundation:** Browser MCP automation can be reused for tax portal automation later
3. **Lower complexity:** Content generation is lower risk than tax calculations
4. **Faster time-to-value:** 5 weeks vs 8+ weeks for tax workflows

---

## Task Summary

All issues are CLOSED in GitHub with label "Pratiko 1.9":

### Backend (7 tasks)

| Issue | Title | Effort |
|-------|-------|--------|
| DEV-260 | Workflow Data Layer | 2h |
| DEV-261 | Workflow Engine Core | 3h |
| DEV-262 | Projects & Workflows API | 2h |
| DEV-263 | Dichiarazione Redditi 730 Workflow | 3h |
| DEV-264 | Additional Workflows (F24, Apertura/Chiusura, Pensionamento) | 2.5h |
| DEV-265 | PDF Document Generator | 2h |
| DEV-266 | Integration Adapters + Notifications | 1.5h |

### Desktop KMP (4 tasks)

| Issue | Title | Effort |
|-------|-------|--------|
| DEV-267 | Projects API + Repository | 2h |
| DEV-268 | coPratiko Tab UI + State | 2.5h |
| DEV-269 | Folder Sync + Offline | 2h |
| DEV-270 | System Tray + Distribution | 1.5h |

### Frontend (3 tasks)

| Issue | Title | Effort |
|-------|-------|--------|
| DEV-271 | Projects Pages + API | 2h |
| DEV-272 | Workflow Status + Checkpoint UI | 2h |
| DEV-273 | Navigation + Session Integration | 1h |

**Total Effort:** ~29h

---

## Reactivation Criteria

Consider reactivating v1.9 when:
1. v1.8 Social Campaign Creator is complete and stable
2. Customer feedback indicates demand for tax workflow automation
3. Browser MCP automation is proven reliable
4. Team capacity is available

---

## Reference Documents

- Original functional requirements preserved in git history
- ADR-024: Workflow Automation Architecture (for future reference)
- PRATIKO_1.8_REFERENCE.md (original version in git history)

---

## Notes

The Browser MCP and sandbox infrastructure built for v1.8 can be reused for:
- Automating tax portal submissions (AdE, INPS)
- Document upload to government portals
- Form filling automation

This creates a technical foundation for v1.9 tax workflows.
