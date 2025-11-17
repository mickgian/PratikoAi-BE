# PratikoAI Subagent Assignments

**Last Updated:** 2025-11-17 16:00
**Active Specialized Subagents:** 0/2
**Total Active Subagents:** 2/4 (Management only)
**Total Configured Subagents:** 9 (2 management + 7 specialized)

---

## Active Assignments

### Management Subagents (Always Active)

#### 🏛️ Architect Subagent (@Egidio)
**Status:** 🟢 ACTIVE
**Current Task:** Sprint 0 - System Setup Complete
**Last Activity:** 2025-11-17 14:00

**Recent Completions:**
- ✅ DEV-BE-93: Documented 10 architectural decisions in decisions.md
- ✅ Created comprehensive ADR template for future decisions
- ✅ Validated frontend tech stack (Next.js 15, React 19, Tailwind 4)

**Pending Reviews:**
- None (Sprint 0 setup phase)

**Monthly Responsibilities:**
- 📅 **Next AI Trends Review:** 2025-12-15
- 📧 **Next Report Email:** STAKEHOLDER_EMAIL (via environment variable)

---

#### 📋 Scrum Master Subagent (@Ottavio)
**Status:** 🟢 ACTIVE
**Current Task:** DEV-BE-94 - Creating sprint plan and subagent assignments
**Last Activity:** 2025-11-17 14:30

**Recent Completions:**
- ✅ DEV-BE-92: Created context files structure
- 🔄 DEV-BE-94: Sprint plan creation (IN PROGRESS)

**Active Responsibilities:**
- Creating sprint-plan.md and subagent-assignments.md
- Planning subagent configuration tasks (DEV-BE-95 to DEV-BE-102)
- Preparing for Sprint 1 planning

**Next Progress Update:** 2025-11-17 16:30 (Slack)

---

### Specialized Subagents (0/2 Active)

**Note:** No specialized subagents active during Sprint 0 setup phase. All will be activated in Sprint 1 after configuration is complete.

#### 💻 Backend Expert Subagent (@Ezio)
**Status:** ⚪ CONFIGURED - NOT ACTIVE
**Configuration:** Pending (DEV-BE-98)

**Planned Expertise:**
- Python 3.13, FastAPI, Pydantic V2
- LangGraph orchestration (134-step RAG)
- PostgreSQL + pgvector
- Redis semantic caching
- Hybrid search optimization

**Candidate Tasks (Sprint 1):**
- DEV-BE-67: Migrate FAQ Embeddings to pgvector
- DEV-BE-71: Disable Emoji in LLM Responses
- DEV-BE-76: Fix Cache Key + Add Semantic Layer

---

#### 🎨 Frontend Expert Subagent (@Livia)
**Status:** ⚪ CONFIGURED - NOT ACTIVE
**Configuration:** Pending (DEV-BE-97)

**Planned Expertise:**
- Next.js 15.5.0 (App Router, Turbopack)
- React 19.1.0 (Server Components)
- TypeScript 5.x (strict mode)
- Tailwind CSS 4.x
- Radix UI primitives
- Context API + useReducer

**Candidate Tasks (Future):**
- Frontend integration tasks from `/Users/micky/WebstormProjects/PratikoAiWebApp`
- Cross-repository coordination with backend

---

#### 🛡️ Security Audit Subagent (@Severino)
**Status:** ⚪ CONFIGURED - NOT ACTIVE
**Configuration:** Pending (DEV-BE-99)

**Planned Expertise:**
- GDPR compliance auditing
- Security vulnerability scanning
- Data protection assessments
- Stripe payment security
- Infrastructure hardening

**Scheduled Responsibilities:**
- 📅 **Weekly Compliance Reports:** Every Friday at 17:00
- 📧 **Report Recipient:** STAKEHOLDER_EMAIL (via environment variable)
- 🔒 **Focus Areas:** GDPR, PCI DSS, data encryption, API security

**Candidate Tasks (Future):**
- DEV-BE-74: GDPR Compliance Audit (QA Environment)
- DEV-BE-89: GDPR Compliance Audit (Preprod Environment)
- DEV-BE-91: GDPR Compliance Audit (Production Environment)

---

#### ✅ Test Generation Subagent (@Clelia)
**Status:** ⚪ CONFIGURED - NOT ACTIVE
**Configuration:** Pending (DEV-BE-100)

**Planned Expertise:**
- pytest test generation
- Test coverage optimization (target: 69.5%)
- TDD methodology (Red-Green-Refactor)
- Integration test scenarios
- Mock/fixture creation

**Critical Responsibility:**
- **PRIORITY:** Increase test coverage from 4% to 69.5%
- Current blocker for all commits (pre-commit hook threshold)

**Candidate Tasks (Sprint 1 - HIGH PRIORITY):**
- TBD: Comprehensive test coverage improvement
  - app/services/* - Service layer tests
  - app/orchestrators/* - LangGraph orchestration tests
  - app/api/v1/* - API endpoint tests
  - app/core/* - Core utilities tests
  - app/models/* - Database model tests

---

#### 🗄️ Database Designer Subagent (@Primo)
**Status:** ⚪ CONFIGURED - NOT ACTIVE
**Configuration:** Pending (DEV-BE-102)

**Planned Expertise:**
- PostgreSQL 15+ optimization
- pgvector index tuning (IVFFlat → HNSW)
- Full-text search (GIN indexes)
- Alembic migrations
- Query performance optimization

**Candidate Tasks (Future):**
- DEV-BE-67: FAQ embeddings table design
- DEV-BE-79: Upgrade to HNSW index
- DEV-BE-85: Configure PostgreSQL High Availability
- DEV-BE-86: Automated Index Health Monitoring

---

#### ⚡ Performance Optimizer Subagent (@Valerio)
**Status:** ⚪ PREPARED - NOT ACTIVE (BY DESIGN)
**Configuration:** Pending (DEV-BE-101)
**Activation:** Manual activation only, not for current sprints

**Planned Expertise:**
- Cache optimization strategies
- Query performance profiling
- Load testing and benchmarking
- Latency reduction techniques
- Resource utilization analysis

**Future Activation Criteria:**
- Production performance issues detected
- User-reported slowness
- Scaling requirements for 500+ users
- Manual activation by stakeholder request

**Candidate Tasks (When Active):**
- DEV-BE-76: Semantic caching optimization
- DEV-BE-78: Cross-Encoder Reranking performance tuning
- DEV-BE-77: Prometheus metrics optimization

---

#### 🚀 DevOps Subagent (@Dario)
**Status:** ⚪ CONFIGURED - NOT ACTIVE
**Configuration:** Complete (2025-11-17)
**Activation:** On-demand (PR creation, CI/CD monitoring, cost reviews)

**Planned Expertise:**
- GitHub integration (PR creation using `gh` CLI)
- CI/CD monitoring (GitHub Actions failure detection)
- PR failure notification to @Ottavio
- Cost optimization (Hetzner vs AWS, LLM API costs)
- Infrastructure as Code (Docker, docker-compose)
- Deployment troubleshooting (QA, Preprod, Prod)

**Key Responsibilities:**
- Create PRs for completed subagent work
- Monitor CI/CD job status (pytest, Ruff, MyPy, coverage)
- Detect and analyze failures → Notify @Ottavio for coordination
- Quarterly cost optimization reports to @Egidio
- Docker image optimization
- **NO merge permissions** (human approval required)

**Activation Triggers:**
1. Subagent completes task → @Ottavio assigns @Dario to create PR
2. PR CI/CD fails → @Dario monitors and reports to @Ottavio
3. Quarterly cost review (every 3 months)
4. Infrastructure optimization tasks (Docker, deployment issues)

**Coordination Protocol:**
- **With @Ottavio:** Report ALL PR failures for task reassignment
- **With @Egidio:** Submit quarterly cost reports, propose infrastructure changes
- **With specialized subagents:** Provide CI/CD failure details for fixes

**Cost Optimization Focus:**
- Current: Hetzner €56.70/month (vs AWS $300/month = €3,000/year savings)
- Monitor LLM API costs (OpenAI, Anthropic)
- Propose alternatives saving >€50/month
- Quarterly reports due: 15th of review month

---

## Assignment History

### Sprint 0: Subagent System Setup (2025-11-15 to 2025-11-21)

| Date | Subagent | Task | Status | Duration |
|------|----------|------|--------|----------|
| 2025-11-17 | Architect | DEV-BE-93: Document architectural decisions | ✅ COMPLETED | 2 hours |
| 2025-11-17 | Architect | DEV-BE-92: Create context structure | ✅ COMPLETED | 1 hour |
| 2025-11-17 | Scrum Master | DEV-BE-94: Create sprint plan | 🔄 IN PROGRESS | - |

---

## Parallel Execution Rules

### Current Limits
- **Management Subagents:** 2/2 ACTIVE (Architect + Scrum Master)
- **Specialized Subagents:** 0/2 ACTIVE
- **Total:** 2/4 ACTIVE

### Assignment Protocol

**Before Assigning Task:**
1. ✅ Check available specialized slots (max 2)
2. ✅ Verify task dependencies resolved
3. ✅ Confirm no blockers
4. ✅ Get human approval for priorities/deadlines
5. ✅ Assign to appropriate specialized subagent

**During Task Execution:**
- Send progress updates every 2 hours (Slack)
- Monitor for blockers
- Architect reviews architecture decisions (can veto)
- Escalate issues to human stakeholder

**After Task Completion:**
- Mark task as completed in sprint plan
- Release specialized subagent slot
- Update velocity metrics
- Assign next priority task (if slots available)

---

## Escalation Matrix

### Who to Escalate To

| Issue Type | First Escalation | Final Decision |
|------------|------------------|----------------|
| Technical blocker | Architect | Human Stakeholder |
| Architecture change | Architect (can veto) | Human Stakeholder |
| Priority conflict | Scrum Master | Human Stakeholder |
| Deadline concern | Scrum Master | Human Stakeholder |
| Security risk | Security Audit | Human Stakeholder |
| GDPR compliance | Security Audit | Human Stakeholder |
| Resource constraint | Scrum Master | Human Stakeholder |
| Sprint scope change | Scrum Master | Human Stakeholder |

### Architect Veto Power
- Architect can autonomously veto architectural/technology decisions
- Veto triggers immediate Slack notification to stakeholder
- Veto includes detailed technical rationale
- Human stakeholder has final override authority

---

## Coordination Notes

### Cross-Repository Work
- **Backend:** `/Users/micky/PycharmProjects/PratikoAi-BE`
- **Frontend:** `/Users/micky/WebstormProjects/PratikoAiWebApp`

**Linked Tasks Requiring Coordination:**
1. DEV-BE-72 (Backend) → DEV-FE-004 (Frontend): Expert Feedback System
2. DEV-BE-87 (Backend) → DEV-FE-009 (Frontend): Payment Integration (Stripe)

**Coordination Protocol:**
- Backend APIs must be completed FIRST
- Frontend Expert waits for Backend Expert completion
- Integration testing on QA environment before production

---

## Performance Metrics

### Subagent Efficiency (Will be tracked from Sprint 1)
- Average task completion time by subagent type
- Rework rate (tasks requiring fixes)
- Blocker frequency
- Stakeholder escalation rate

### Quality Metrics
- Test coverage contribution per subagent
- Code quality scores (Ruff, MyPy)
- Architecture decision adherence

---

## Next Actions

**Sprint 0 Remaining Work:**
1. ✅ Complete sprint-plan.md and subagent-assignments.md (DEV-BE-94)
2. ⏳ Create Architect configuration file (DEV-BE-95)
3. ⏳ Create Scrum Master configuration file (DEV-BE-96)
4. ⏳ Create all specialized subagent configurations (DEV-BE-97 to DEV-BE-102)

**Sprint 1 Preparation:**
- Human stakeholder meeting: Confirm Sprint 1 priorities
- Activate first 2 specialized subagents based on approved priorities
- Begin high-priority backend tasks (likely Backend Expert + Test Generation)

---

**Document Status:** 🔄 ACTIVE
**Next Update:** 2025-11-17 16:30 (With progress on subagent configurations)
**Maintained By:** Scrum Master Subagent
