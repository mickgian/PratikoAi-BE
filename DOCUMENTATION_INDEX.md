# Master Documentation Index

**Auto-generated:** 2025-11-15 13:45:46
**Total Documents:** 216 markdown files

> 💡 This index is automatically generated. To update, run: `python scripts/generate_docs_index.py`

---

## 🚀 Quick Start (New Users)

**Start here if you're new to the project:**

1. **[Hybrid RAG Implementation](docs/getting-started/HYBRID_RAG_IMPLEMENTATION.md)** - Core RAG system architecture
2. **[RAG Architecture Overview](docs/architecture/INDEX.md)** - Complete system design
3. **[SSE Streaming Guide](docs/getting-started/SSE_STREAMING_COMPLETE_GUIDE.md)** - Real-time streaming implementation
4. **[Testing Status](docs/getting-started/TESTING_IMPLEMENTATION_STATUS.md)** - Test coverage and guidelines

---

## 📚 By Audience

### 👨‍💻 Developers
- **Getting Started:** [Hybrid RAG Implementation](docs/getting-started/HYBRID_RAG_IMPLEMENTATION.md)
- **Architecture:** [docs/architecture/](docs/architecture/INDEX.md)
- **Streaming:** [SSE Streaming Guide](docs/getting-started/SSE_STREAMING_COMPLETE_GUIDE.md)
- **Testing:** [Testing Implementation Status](docs/getting-started/TESTING_IMPLEMENTATION_STATUS.md)
- **Feature Flags:** [feature-flags/](feature-flags/INDEX.md)

### 🏗️ DevOps / SRE
- **Deployment:** [deployment-orchestration/](deployment-orchestration/INDEX.md)
- **Monitoring:** [monitoring/](monitoring/INDEX.md)
- **Alerts:** [monitoring/ALERTS.md](monitoring/ALERTS.md)
- **Runbooks:** [monitoring/RUNBOOKS.md](monitoring/RUNBOOKS.md)
- **Rollback:** [rollback-system/](rollback-system/INDEX.md)

### 🏛️ Architects
- **System Design:** [docs/architecture/](docs/architecture/INDEX.md)
- **RAG Pipeline:** [docs/architecture/steps/](docs/architecture/steps/INDEX.md) (134 steps)
- **Policy Gated Autonomy:** [docs/architecture/POLICY_GATED_AUTONOMY_INTEGRATION.md](docs/architecture/POLICY_GATED_AUTONOMY_INTEGRATION.md)

### 🧪 QA / Testing
- **Test Coverage:** [Testing Implementation Status](docs/getting-started/TESTING_IMPLEMENTATION_STATUS.md)
- **Test Documents:** [tests/test_documents/](tests/test_documents/INDEX.md)

---

## 🗂️ Documentation by Subsystem

| Subsystem | Documents | Primary Index |
|-----------|-----------|---------------|
| **RAG Architecture** | 134 steps | [docs/architecture/](docs/architecture/INDEX.md) |
| **Core Docs** | 19 docs | [docs/](docs/INDEX.md) |
| **Monitoring** | 11 docs | [monitoring/](monitoring/INDEX.md) |
| **Deployment** | 3 docs | [deployment-orchestration/](deployment-orchestration/INDEX.md) |
| **MCP Servers** | 5 docs | [mcp-servers/](mcp-servers/INDEX.md) |
| **Feature Flags** | 3 docs | [feature-flags/](feature-flags/INDEX.md) |
| **Version Management** | 5 docs | [version-management/](version-management/INDEX.md) |
| **Rollback System** | 3 docs | [rollback-system/](rollback-system/INDEX.md) |
| **Failure Recovery** | 1 doc | [failure-recovery-system/](failure-recovery-system/INDEX.md) |

---

## 📖 Documentation by Category

### Getting Started (6 docs)
- **[Hybrid RAG Implementation Summary](docs/getting-started/HYBRID_RAG_IMPLEMENTATION.md)** ✅ Current
  - Implemented a complete hybrid RAG (Retrieval-Augmented Generation) system combining: - **FTS (Full-Text Search)** using PostgreSQL tsvector with It...
- **[SSE Streaming - Complete Implementation Guide](docs/getting-started/SSE_STREAMING_COMPLETE_GUIDE.md)** ✅ Current
  - **Date:** November 12, 2025 **Status:** ✅ FULLY FIXED AND TESTED
- **[SSE Streaming Fix - Content Starting with Colon](docs/getting-started/SSE_STREAMING_FIX_COLON_CONTENT.md)** ✅ Current
  - **Date:** November 12, 2025 **Issue:** Frontend stuck on "Sto pensando..." animation - streaming broken
- **[SSE Streaming Fix - TDD Approach (Historical)](docs/getting-started/SSE_STREAMING_TDD_FIX_FINAL.md)** ✅ Current
  - **Date:** November 11, 2025 **Approach:** Test-Driven Development (TDD)
- **[Testing Implementation Status](docs/getting-started/TESTING_IMPLEMENTATION_STATUS.md)** ✅ Current
  - **Created:** November 12, 2025 **Status:** Phase 1-2 Complete, Phase 3-5 Templates Provided
- **[pgvector Setup Guide](docs/getting-started/PGVECTOR_SETUP_GUIDE.md)** ✅ Current
  - ✅ **Completed**: - Created Alembic migrations for pgvector enablement

### Operations (1 docs)
- **[PratikoAI Deployment Checklist](docs/operations/DEPLOYMENT_CHECKLIST.md)** ✅ Current
  - **Pinecone Configuration** - [ ] `PINECONE_API_KEY` - Staging Pinecone API key

### Meta Documentation (2 docs)
- **[Documentation Cleanup Summary](docs/meta/DOCUMENTATION_CLEANUP_SUMMARY.md)** ✅ Current
  - **Date:** November 12, 2025 **Action:** Reviewed and cleaned up all documentation in active changelist
- **[RSS Feed Collection Activation - Complete ✅](docs/meta/RSS_ACTIVATION_SUMMARY.md)** ✅ Current
  - Successfully activated the RSS feed collection system for PratikoAI's Italian regulatory knowledge base using Test-Driven Development methodology. ...

---

## 🔍 Quick Find

**Common Documentation Needs:**

- **How does streaming work?** → [SSE Streaming Complete Guide](docs/getting-started/SSE_STREAMING_COMPLETE_GUIDE.md)
- **How to set up pgvector?** → [pgVector Setup Guide](docs/getting-started/PGVECTOR_SETUP_GUIDE.md)
- **What are the RAG steps?** → [docs/architecture/steps/](docs/architecture/steps/INDEX.md)
- **How to add tests?** → [Testing Implementation Status](docs/getting-started/TESTING_IMPLEMENTATION_STATUS.md)
- **How to deploy?** → [deployment-orchestration/](deployment-orchestration/INDEX.md)
- **How to monitor?** → [monitoring/](monitoring/INDEX.md)
- **Troubleshooting?** → Check subsystem's TROUBLESHOOTING.md

---

## 🛠️ Maintenance

This index is **automatically generated** from all markdown files in the repository.

**To regenerate:**
```bash
python scripts/generate_docs_index.py
```

**Pre-commit hook:**
The index is automatically regenerated on commit if markdown files change.

---

## 📊 Documentation Statistics

- **Total Documents:** {len(self.all_docs)}
- **Root Level:** {len(root_docs)}
- **Architecture Steps:** {subsystems['docs/architecture/steps']}
- **Subsystems with Docs:** {len([k for k, v in subsystems.items() if v > 0])}

---

**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Generator:** `scripts/generate_docs_index.py`
