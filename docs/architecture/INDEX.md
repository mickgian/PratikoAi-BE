# RAG Architecture Documentation

**Auto-generated:** 2025-12-24 19:08:29

> 💡 Complete documentation of the RAG (Retrieval-Augmented Generation) system architecture.

---

## 📚 Overview

This directory contains comprehensive documentation of the RAG system, including:
- High-level architecture documents
- Detailed implementation guides
- 134 step-by-step pipeline documents
- Policy and conformance guidelines

---

## 🏗️ RAG Flow Implementation Series

- **[RAG Implementation Strategy](RAG_FLOW_IMPLEMENTATION_00_orchestrators.md)** ✅ Current
  - We'll implement the 135 RAG steps using a phased approach, starting with simple steps and progressing to more complex ones. Each step will follow T...
- **[RAG Architecture Migration Plan](RAG_FLOW_IMPLEMENTATION_01_hybrid_architecture.md)** ✅ Current
  - **← Context**: [RAG_FLOW_IMPLEMENTATION_00_orchestrators.md](./RAG_FLOW_IMPLEMENTATION_00_orchestrators.md) (135 orchestrators implemented)
- **[RAG Flow Analysis & Fix Plan](RAG_FLOW_IMPLEMENTATION_02_unified_graph.md)** ✅ Current
  - **← Prerequisites**: [RAG_FLOW_IMPLEMENTATION_01_hybrid_architecture.md](./RAG_FLOW_IMPLEMENTATION_01_hybrid_architecture.md) (Phases 0-8 complete)
- **[RAG Flow Verification & Testing Implementation](RAG_FLOW_IMPLEMENTATION_03_verification_testing.md)** ✅ Current
  - **← Prerequisites**: [RAG_FLOW_IMPLEMENTATION_02_unified_graph.md](./RAG_FLOW_IMPLEMENTATION_02_unified_graph.md) (Phases 2-6 complete, unified gra...

## 🛡️ Policy & Governance

- **[Policy-Gated Autonomy Implementation Summary](POLICY_GATED_AUTONOMY_SUMMARY.md)** ✅ Current
  - This document summarizes the policy-gated autonomy changes implemented for the PratikoAI RAG stack. These changes enable intelligent, policy-driven...
- **[Policy-Gated Autonomy Integration Guide](POLICY_GATED_AUTONOMY_INTEGRATION.md)** ✅ Current
  - This document explains how to integrate the policy-gated autonomy components into your RAG pipeline.

## 📋 Other Architecture Docs

- **[AI Application Architect Knowledge Base](AI_ARCHITECT_KNOWLEDGE_BASE.md)** ✅ Current
  - **Purpose:** Domain expertise for reviewing and designing AI/LLM applications **Audience:** Egidio (Architect Agent) and human architects
- **[Architectural Decision Records (ADRs)](decisions.md)** ✅ Current
  - | ADR | Date | Status | Title | |-----|------|--------|-------|
- **[PratikoAI Conversation Context Architecture](PRATIKOAI_CONTEXT_ARCHITECTURE.md)** ✅ Current
  - **Purpose:** Document how conversation context flows through PratikoAI's RAG pipeline **Audience:** Developers and architects working on PratikoAI
- **[PratikoAI RAG — Multi-Sprint Plan](rag_sprints.md)** ✅ Current
  - This plan sequences the 135 RAG steps into pragmatic sprints with clear scope and commands to open/issues per sprint.
- **[Prompt Engineering Knowledge Base](PROMPT_ENGINEERING_KNOWLEDGE_BASE.md)** ✅ Current
  - **Purpose:** Senior-level prompt engineering patterns for PratikoAI **Audience:** Developers, architects, and agents working on prompts
- **[RAG Architecture Documentation](INDEX.md)** 📚 Historical
  - **Auto-generated:** 2025-12-24 19:08:01
- **[RAG Conformance Dashboard](rag_conformance.md)** ✅ Current
  - This dashboard tracks the implementation status of each step in the PratikoAI RAG blueprint. It is automatically generated from the Mermaid diagram...
- **[RAG Implementation Sprint Plan](rag_sprint_plan.md)** ✅ Current
  - This prioritized sprint plan focuses on the most critical RAG pipeline components based on the audit results. Each section represents a weekly spri...
- **[RAG Pipeline Documentation](README_rag_pipeline.md)** ✅ Current
  - The RAG (Retrieval-Augmented Generation) pipeline provides automated tools for auditing RAG implementation conformance and generating actionable ba...
- **[SQLModel Code Review Checklist](SQLMODEL_REVIEW_CHECKLIST.md)** ✅ Current
  - **Mandatory checklist for ALL pull requests modifying database models**
- **[SQLModel Standards and Patterns](SQLMODEL_STANDARDS.md)** ✅ Current
  - **Mandatory Reference for All Database Models**
- **[Vector Search Architecture & Guardrails](vector-search.md)** ✅ Current
  - This document describes the vector search architecture with environment-aware guardrails, provider selection logic, and safety mechanisms to preven...

---

## 🔢 Detailed Pipeline Steps

**Complete step-by-step documentation of the RAG pipeline:**

→ **[View all 134 steps](steps/INDEX.md)**

The steps directory contains detailed documentation for every step in the RAG pipeline, from request validation to feedback collection.

---

## 📊 Statistics

- **Overview Docs:** 18
- **Detailed Steps:** 134
- **Total Architecture Docs:** 152

---

**Last Updated:** 2025-12-24 19:08:29
