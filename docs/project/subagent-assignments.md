# PratikoAI Subagent Assignments

**Last Updated:** 2025-11-19 10:05
**Architecture Status:** ✅ FULLY OPERATIONAL (Flat hierarchy with parallel invocation)
**Configured Subagent Files:** 10/10 (All configured with YAML frontmatter + proactive language)
**Location:** `.claude/agents/` directory

> **STATUS:** ✅ All 10 subagents FULLY OPERATIONAL with:
> - ✅ Proper YAML frontmatter
> - ✅ Italian names (ezio, livia, clelia, egidio, ottavio, severino, primo, valerio, silvano, tiziano)
> - ✅ Proactive language ("MUST BE USED", "Use PROACTIVELY") for automatic invocation
> - ✅ Successfully tested and recognized by Claude Code
>
> Ready for both manual invocation via `Task(subagent_type="tiziano")` and automatic triggering.

---

## Active Assignments

### Management Subagents (Always Active)

#### 🏛️ Architect Subagent (@Egidio)
**Status:** 🟢 ADVISORY ROLE
**Role Type:** Advisory/Review (does NOT directly invoke other subagents)
**Last Activity:** 2025-11-17 14:00

**Recent Completions:**
- ✅ DEV-BE-93: Documented 10 architectural decisions in decisions.md
- ✅ Created comprehensive ADR template for future decisions
- ✅ Validated frontend tech stack (Next.js 15, React 19, Tailwind 4)

**Advisory Responsibilities:**
- Reviews architectural decisions (veto power on tech choices)
- Provides architectural recommendations to main Claude thread
- Monthly AI trends analysis and reports
- **NOTE:** Does NOT coordinate specialized subagents (main Claude decides)

**Monthly Responsibilities:**
- 📅 **Next AI Trends Review:** 2025-12-15
- 📧 **Next Report Email:** STAKEHOLDER_EMAIL (via environment variable)

---

#### 📋 Scrum Master Subagent (@Ottavio)
**Status:** 🟢 ADVISORY ROLE
**Role Type:** Advisory/Planning (does NOT directly invoke other subagents)
**Last Activity:** 2025-11-17 14:30

**Recent Completions:**
- ✅ DEV-BE-92: Created context files structure
- ✅ DEV-BE-94: Sprint plan creation

**Advisory Responsibilities:**
- Maintains sprint-plan.md and subagent-assignments.md
- Provides task recommendations to main Claude thread
- Tracks velocity and estimates
- Suggests which specialized subagents should handle tasks
- **NOTE:** Does NOT directly assign tasks (main Claude decides invocations)

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
- Frontend integration tasks from `/Users/micky/PycharmProjects/PratikoAi-BE/web`
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

#### 🚀 DevOps Subagent (@Silvano)
**Status:** ⚪ CONFIGURED - NOT ACTIVE
**Configuration:** Complete (2025-11-17)
**Activation:** On-demand (PR creation, CI/CD monitoring, cost reviews)

**Planned Expertise:**
- GitHub integration (PR creation using `gh` CLI)
- CI/CD monitoring (GitHub Actions failure detection)
- PR failure notification to @Ottavio
- Cost optimization (Hetzner vs AWS, LLM API costs)
- Infrastructure as Code (Docker, docker-compose)
- Deployment troubleshooting (QA, Prod)

**Key Responsibilities:**
- Create PRs for completed subagent work
- Monitor CI/CD job status (pytest, Ruff, MyPy, coverage)
- Detect and analyze failures → Notify @Ottavio for coordination
- Quarterly cost optimization reports to @Egidio
- Docker image optimization
- **NO merge permissions** (human approval required)

**Activation Triggers (Main Claude Decides):**
1. Subagent completes task → Main Claude invokes @Silvano to create PR
2. PR CI/CD fails → @Silvano reports to main Claude thread for next steps
3. Quarterly cost review (every 3 months)
4. Infrastructure optimization tasks (Docker, deployment issues)

**Reporting Protocol:**
- **PR failures:** Reports to main Claude thread (which may consult @Ottavio for planning)
- **Cost reports:** Reports to main Claude thread (which may consult @Egidio for architecture)
- **CI/CD failures:** Returns details to main Claude for coordination
- **NOTE:** Does NOT directly coordinate with other subagents

**Cost Optimization Focus:**
- Current: Hetzner €56.70/month (vs AWS $300/month = €3,000/year savings)
- Monitor LLM API costs (OpenAI, Anthropic)
- Propose alternatives saving >€50/month
- Quarterly reports due: 15th of review month

---

#### 🔍 Debug Specialist Subagent (@Tiziano)
**Status:** ✅ OPERATIONAL
**Configuration:** Complete (2025-11-19)
**Activation:** Automatic (error detection, test failures, unexpected behavior)
**Italian Name:** Tiziano (meaning "of the Titans")

**Core Expertise:**
- Systematic problem investigation and root cause analysis
- Error diagnosis (runtime, logic, configuration, integration)
- Test failure analysis (flaky tests, timing issues, isolation problems)
- Performance debugging and profiling
- CI/CD failure investigation
- Cross-platform debugging (local vs. CI environments)

**Key Responsibilities:**
- Investigate errors, exceptions, and unexpected behavior proactively
- Analyze test failures and determine if tests are failing correctly
- Diagnose intermittent issues and race conditions
- Provide actionable fixes with code examples
- Distinguish between symptoms and root causes
- Suggest preventive measures to avoid similar issues

**Activation Triggers (Automatic via Proactive Language):**
1. Code throws an error or exception
2. Tests fail or produce unexpected results
3. Application behaves differently than intended
4. Debugging output shows anomalies
5. Performance degrades unexpectedly
6. Integration issues arise between components
7. CI/CD pipeline failures occur

**Debugging Methodologies:**
- Binary Search: Systematically narrow down problem location
- Rubber Duck: Step-by-step code flow explanation
- Divide and Conquer: Break complex issues into testable components
- Comparative Analysis: Compare working vs. broken states
- Minimal Reproduction: Create simplest case demonstrating issue
- Time Travel: Use git history to identify when issue was introduced

**Common Red Flags:**
- Off-by-one errors in loops or array access
- Null/undefined reference issues
- Type mismatches or coercion problems
- Asynchronous timing issues and race conditions
- Memory leaks or resource exhaustion
- State mutation in unexpected places
- Environment-specific configuration differences
- Dependency version conflicts

**Quality Standards:**
- Confirm diagnosis with evidence, not theory
- Test proposed solutions before recommending
- Consider side effects and unintended consequences
- Verify fix doesn't break other functionality
- Ensure solution addresses root cause, not symptoms

---

## Assignment History

### Sprint 0: Subagent System Setup (2025-11-15 to 2025-11-21)

| Date | Subagent | Task | Status | Duration |
|------|----------|------|--------|----------|
| 2025-11-17 | Architect | DEV-BE-93: Document architectural decisions | ✅ COMPLETED | 2 hours |
| 2025-11-17 | Architect | DEV-BE-92: Create context structure | ✅ COMPLETED | 1 hour |
| 2025-11-17 | Scrum Master | DEV-BE-94: Create sprint plan | 🔄 IN PROGRESS | - |

---

## Parallel Invocation Architecture

### How Subagents Work in Claude Code

**Official Architecture (Verified):**
- ✅ **Flat structure**: Main Claude Code → Subagents (single level only)
- ❌ **No hierarchical coordination**: Subagents CANNOT spawn other subagents
- ✅ **Parallel invocation**: Main Claude can invoke multiple subagents in parallel
- 📋 **Source**: https://code.claude.com/docs/en/sub-agents

**Key Limitation:**
> "prevents infinite nesting of agents (subagents cannot spawn other subagents)"

This means @Ottavio (Scrum Master) and @Egidio (Architect) **cannot directly assign tasks to** @Ezio, @Livia, or @Clelia. Instead, the main Claude Code conversation decides which subagents to invoke.

### Parallel Invocation Pattern

**To run backend + frontend work in parallel:**
```
Main Claude Code invokes:
├─ Task(subagent: backend-expert, prompt: "Implement API endpoint...")
└─ Task(subagent: frontend-expert, prompt: "Build UI component...")
```

Both execute concurrently and report back to main thread when done.

**Best Practices:**
1. Main conversation analyzes task requirements
2. Identifies independent work streams (backend, frontend, tests)
3. Invokes multiple Task tools in single message for parallel execution
4. Waits for all to complete before proceeding
5. Integrates results

### Concrete Invocation Examples

**Example 1: Parallel Backend + Frontend Development**

User requests: "Add user profile editing feature"

Main Claude analysis:
- Backend API needed (handled by backend-expert subagent)
- Frontend UI needed (handled by frontend-expert subagent)
- These can run in PARALLEL since they're independent

Main Claude sends ONE message with TWO Task tool invocations to execute concurrently.

**Example 2: Sequential with Dependency**

User requests: "Migrate database schema and update API"

Main Claude analysis:
- Database migration must complete FIRST (database-designer subagent)
- API updates depend on new schema (backend-expert subagent)
- These must run SEQUENTIALLY

Main Claude invokes database-designer first, waits for completion, then invokes backend-expert.

**Example 3: Test Generation After Implementation**

After backend implementation completes:
- Main Claude invokes test-generation subagent to add comprehensive tests
- Single invocation since previous work is done

### Task Assignment Protocol

**Before Invoking Subagent:**
1. ✅ Main Claude verifies task is well-defined
2. ✅ Checks dependencies are resolved
3. ✅ Confirms no blockers
4. ✅ Gets human approval if needed
5. ✅ Invokes appropriate subagent(s) via Task tool

**During Task Execution:**
- Subagent works independently with isolated context
- Reports progress in final message back to main thread
- Main Claude monitors and can resume via agentId if needed

**After Task Completion:**
- Subagent returns final report to main thread
- Main Claude marks task completed
- Main Claude decides next actions

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
- **Frontend:** `/Users/micky/PycharmProjects/PratikoAi-BE/web`

**Linked Tasks Requiring Coordination:**
1. DEV-BE-72 (Backend) → DEV-FE-004 (Frontend): Expert Feedback System
2. DEV-BE-87 (Backend) → DEV-FE-009 (Frontend): Payment Integration (Stripe)

**Coordination Protocol (Main Claude Thread Orchestrates):**
- Main Claude invokes Backend Expert subagent FIRST for API development
- After backend completion, main Claude invokes Frontend Expert for UI integration
- Main Claude coordinates integration testing on QA environment
- **NOTE:** Subagents do NOT coordinate with each other - main thread sequences work

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

## Completed Work

**Sprint 0 Subagent Configuration (2025-11-18):**
1. ✅ Complete sprint-plan.md and subagent-assignments.md (DEV-BE-94)
2. ✅ Create subagent configuration files (DEV-BE-95 to DEV-BE-102) - **COMPLETE**

**Successfully Configured File Structure:**
```
.claude/agents/
├── architect.md                    # @Egidio ✅ OPERATIONAL
├── scrum-master.md                 # @Ottavio ✅ OPERATIONAL
├── frontend-expert.md              # @Livia ✅ OPERATIONAL
├── backend-expert.md               # @Ezio ✅ OPERATIONAL
├── security-audit.md               # @Severino ✅ OPERATIONAL
├── test-generation.md              # @Clelia ✅ OPERATIONAL
├── performance-optimizer.md        # @Valerio ✅ OPERATIONAL
├── database-designer.md            # @Primo ✅ OPERATIONAL
├── devops.md                       # @Silvano ✅ OPERATIONAL
└── debug-specialist.md             # @Tiziano ✅ OPERATIONAL
```

**Configuration Details:**
- ✅ All files contain proper YAML frontmatter
- ✅ Italian names configured (ezio, livia, clelia, egidio, ottavio, severino, primo, valerio, silvano, tiziano)
- ✅ Proactive language added ("MUST BE USED", "Use PROACTIVELY")
- ✅ Color coding implemented for visual identification
- ✅ Tools restricted appropriately per subagent role
- ✅ Successfully tested and recognized by Claude Code

**Next Steps (Sprint 1):**
- ✅ Subagent system ready for production use
- Ready to test parallel invocation with real development tasks
- Can now automatically trigger appropriate subagents based on task context
- Backend + Frontend parallel work now supported

---

**Document Status:** ✅ COMPLETE
**Last Updated:** 2025-11-19 10:05
**Maintained By:** Scrum Master Subagent

**Subagent Roster:**
1. @Egidio (architect) - Advisory role for architectural decisions
2. @Ottavio (scrum-master) - Advisory role for sprint planning
3. @Ezio (backend-expert) - Python, FastAPI, LangGraph, PostgreSQL
4. @Livia (frontend-expert) - Next.js, React, TypeScript, Tailwind
5. @Clelia (test-generation) - pytest, TDD, coverage optimization
6. @Severino (security-audit) - GDPR, security scanning, compliance
7. @Primo (database-designer) - PostgreSQL, pgvector, query optimization
8. @Valerio (performance-optimizer) - Cache tuning, load testing, profiling
9. @Silvano (devops) - PR creation, CI/CD monitoring, deployment
10. @Tiziano (debug-specialist) - Error diagnosis, root cause analysis, debugging
