# PratikoAI Sprint Plan

**Last Updated:** 2025-11-17
**Current Sprint:** Sprint 0 - Subagent System Setup
**Sprint Duration:** 2025-11-15 to 2025-11-21 (1 week)
**Scrum Master:** PratikoAI Scrum Master Subagent
**Architect:** PratikoAI Architect Subagent

---

## Sprint 0: Subagent System Setup (Current)

**Sprint Goal:**
Establish the multi-agent system foundation with context files, subagent configurations, and notification integrations to enable efficient task delegation and progress tracking.

**Sprint Status:** IN PROGRESS (Day 3 of 7)

### Committed Tasks

| Task ID | Description | Assigned To | Status | Blockers |
|---------|-------------|-------------|--------|----------|
| DEV-BE-92 | Create context files structure | Architect | ✅ COMPLETED | None |
| DEV-BE-93 | Document architectural decisions (decisions.md) | Architect | ✅ COMPLETED | None |
| DEV-BE-94 | Create sprint-plan.md and subagent-assignments.md | Scrum Master | 🔄 IN PROGRESS | None |
| DEV-BE-95 | Create Architect subagent configuration | Scrum Master | ⏳ PENDING | DEV-BE-94 |
| DEV-BE-96 | Create Scrum Master subagent configuration | Scrum Master | ⏳ PENDING | DEV-BE-94 |
| DEV-BE-97 | Create Frontend Expert subagent configuration | Scrum Master | ⏳ PENDING | DEV-BE-94 |
| DEV-BE-98 | Create Backend Expert subagent configuration | Scrum Master | ⏳ PENDING | DEV-BE-94 |
| DEV-BE-99 | Create Security Audit subagent configuration | Scrum Master | ⏳ PENDING | DEV-BE-94 |
| DEV-BE-100 | Create Test Generation subagent configuration | Scrum Master | ⏳ PENDING | DEV-BE-94 |
| DEV-BE-101 | Create Performance Optimizer configuration (PREPARED, NOT ACTIVE) | Scrum Master | ⏳ PENDING | DEV-BE-94 |
| DEV-BE-102 | Create Database Designer subagent configuration | Scrum Master | ⏳ PENDING | DEV-BE-94 |

### Current Subagent Assignments

**Active Subagents:** 2/4 (Management only during setup)

| Subagent | Type | Status | Current Task | Last Progress Update |
|----------|------|--------|--------------|----------------------|
| Architect | Management | 🟢 ACTIVE | Completed architectural decisions documentation | 2025-11-17 14:00 |
| Scrum Master | Management | 🟢 ACTIVE | Creating sprint plan and subagent assignments | 2025-11-17 14:30 |

**Specialized Subagents:** 0/2 (None active during setup phase)

All specialized subagents will be activated in Sprint 1 after configuration is complete.

### Dependencies & Blockers

**No Active Blockers**

**Dependency Chain:**
1. ✅ Context structure created (DEV-BE-92)
2. ✅ Architectural decisions documented (DEV-BE-93)
3. 🔄 Sprint plan creation (DEV-BE-94) - IN PROGRESS
4. ⏳ All subagent configurations (DEV-BE-95 to DEV-BE-102) - Waiting for DEV-BE-94

### Sprint Progress Tracking

**Completion:** 2/12 tasks (17%)

**Velocity Metrics:**
- Planned Story Points: 12
- Completed Story Points: 2
- Current Velocity: 2 points/3 days (0.67 points/day)
- Projected Completion: 2025-11-22 (1 day over sprint)

**Risk Assessment:**
- 🟡 MEDIUM RISK: Sprint may extend 1 day beyond deadline
- Mitigation: Prioritize core subagent configurations (Architect, Scrum Master, Backend Expert) first

### Daily Progress Updates

**2025-11-17 14:30:**
- ✅ Created `/docs/architecture/` and `/docs/project/` directories
- ✅ Completed `decisions.md` with 10 comprehensive ADRs
- 🔄 Started `sprint-plan.md` creation
- Next: Complete `subagent-assignments.md` and begin subagent configurations

**2025-11-16:**
- Context structure planning
- ADR template preparation

**2025-11-15:**
- Sprint 0 initiated
- Subagent system requirements gathered

---

## Sprint 1: Backend Foundation (Next Sprint)

**Planned Start:** 2025-11-22
**Planned End:** 2025-11-29
**Sprint Goal:** Complete critical backend infrastructure and testing improvements

### Candidate Tasks for Sprint 1

| Task ID | Description | Priority | Effort (days) | Dependencies | Proposed Assignment |
|---------|-------------|----------|---------------|--------------|---------------------|
| DEV-BE-67 | Migrate FAQ Embeddings to pgvector | HIGH | 3-5 | None | Backend Expert |
| DEV-BE-76 | Fix Cache Key + Add Semantic Layer | HIGH | 5-7 | None | Backend Expert + Performance Optimizer |
| DEV-BE-71 | Disable Emoji in LLM Responses | MEDIUM | 1-2 | None | Backend Expert |
| TBD | Increase test coverage to 69.5% | CRITICAL | 7-10 | None | Test Generation |

**Note:** Final task selection and priorities will be confirmed by human stakeholder at Sprint 1 planning meeting.

**Estimated Capacity:** 2 specialized subagents × 7 days = 14 agent-days

---

## Sprint Backlog (Prioritized)

### Q1 2025 Priorities (From ARCHITECTURE_ROADMAP.md)

**Critical Path to QA Environment (DEV-BE-75):**
1. DEV-BE-67: Migrate FAQ Embeddings to pgvector (3-5 days)
2. DEV-BE-68: Remove Pinecone Integration Code (1-2 days)
3. DEV-BE-70: Daily RSS Collection Email Report (2-3 days)
4. DEV-BE-74: GDPR Compliance Audit (QA Environment) (3-4 days)
5. DEV-BE-75: Deploy QA Environment (Hetzner VPS) (7 days)

**Critical Path to Production (DEV-BE-90):**
- Above + DEV-BE-72 (Expert Feedback System - 10 days)
- DEV-BE-87 (Payment System - 10-15 days)
- DEV-BE-90 (Production Deployment - 7 days)
- DEV-BE-91 (Production GDPR Audit - 4-5 days)

**High-Impact Quick Wins:**
1. DEV-BE-71: Disable Emoji in LLM Responses (1-2 days) - Immediate UX improvement
2. DEV-BE-76: Fix Cache Key (5-7 days) - $1,500-1,800/month savings
3. DEV-BE-69: Expand RSS Feed Sources (7 days) - 5-10x content coverage

---

## Subagent Governance Rules

### Parallel Execution Limits
- **Management Subagents:** 2 always active (Architect + Scrum Master)
- **Specialized Subagents:** Max 2 active in parallel
- **Total Active:** Max 4 subagents (2 management + 2 specialized)

### Task Assignment Protocol
1. Scrum Master proposes task assignments based on sprint backlog
2. Human stakeholder approves priorities and deadlines
3. Scrum Master assigns tasks to specialized subagents (max 2 parallel)
4. Architect reviews technical decisions (veto power on architecture)
5. Progress updates sent every 2 hours via Slack

### Decision Authority Matrix

| Decision Type | Architect | Scrum Master | Human | Notes |
|--------------|-----------|--------------|-------|-------|
| Task Priorities | Propose | Propose | **APPROVE** | Human always decides |
| Task Deadlines | - | Propose | **APPROVE** | Human always decides |
| Architecture Changes | **VETO** (notify Slack) | - | Final say | Architect can veto autonomously |
| Technology Selection | **VETO** (notify Slack) | - | Final say | Architect has veto power |
| Sprint Scope | Advise | Propose | **APPROVE** | Human controls scope |
| Roadmap Updates | Propose | Update | **APPROVE** | Changes require approval |
| Feature Prioritization | Propose | - | **APPROVE** | Only Architect can propose changes |

### Notification Protocols

**Slack Notifications (Immediate):**
- Architect veto events (with rationale)
- Task blockers detected
- Critical errors in deployment
- Sprint scope changes proposed
- Progress updates every 2 hours

**Email Notifications (Weekly/Monthly):**
- Security Audit: Weekly compliance reports to STAKEHOLDER_EMAIL (via environment variable)
- Architect: Monthly AI trends review to STAKEHOLDER_EMAIL (via environment variable)
- Scrum Master: Weekly sprint summary

---

## Sprint Metrics & KPIs

### Sprint 0 Metrics
- **Planned Capacity:** 7 days
- **Committed Tasks:** 12
- **Completed Tasks:** 2 (17%)
- **Blocked Tasks:** 0
- **Velocity:** 0.67 points/day

### Historical Velocity
(Will be populated after Sprint 1)

### Quality Metrics
- **Test Coverage:** 4% (Target: 69.5%)
- **Linter Violations:** 0 (Ruff auto-fix enabled)
- **Type Coverage:** TBD (MyPy validation pending)

---

## Notes & Decisions

### Sprint 0 Decisions
- **2025-11-17:** Created comprehensive ADR file with 10 initial decisions
- **2025-11-17:** Confirmed frontend tech stack: Next.js 15, React 19, Tailwind 4, Radix UI, Context API
- **2025-11-15:** Subagent system approved with 2+2 parallel execution model

### Sprint Retrospective (Pending)
(Will be completed at end of Sprint 0)

---

## Stakeholder Contact

**Primary Stakeholder:** Michele Giannone (STAKEHOLDER_EMAIL (via environment variable))
**Slack:** [Configured for notifications]
**Preferred Communication:** Slack for immediate, Email for weekly/monthly reports

---

**Document Status:** 🔄 ACTIVE
**Next Update:** 2025-11-17 16:30 (2-hour progress update)
**Maintained By:** Scrum Master Subagent
