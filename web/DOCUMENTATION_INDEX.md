# Master Documentation Index

**Auto-generated:** 2025-12-31 12:29
**Total Documents:** 26 markdown files

> 💡 This index is automatically generated. To update, run: `npm run docs:generate`

---

## 🚀 Quick Start (New Users)

**Start here if you're new to the project:**

1. **[README](README.md)** - Project overview and setup
2. **[Backend Integration Guide](docs/getting-started/BACKEND_INTEGRATION_GUIDE.md)** - Connect to PratikoAI backend
3. **[Testing Guide](docs/getting-started/TESTING.md)** - Run tests and understand test structure
4. **[Chat Requirements](docs/development/CHAT_REQUIREMENTS.md)** - Complete chat system specification

---

## 📚 By Audience

### 👨‍💻 Frontend Developers
- **Getting Started:** [docs/getting-started/](docs/getting-started/)
- **Development Guides:** [docs/development/](docs/development/)
- **Chat System:** [Chat Requirements](docs/development/CHAT_REQUIREMENTS.md)
- **Testing:** [Testing Guide](docs/getting-started/TESTING.md)

### 🎨 UI/UX Designers
- **Design System:** [Design System Guide](docs/development/DESIGN_SYSTEM.md)
- **Figma Setup:** [Figma Integration](docs/development/FIGMA_SETUP.md)
- **Component Matching:** [Figma Matching Guide](docs/development/FIGMA_MATCHING_GUIDE.md)

### 🏗️ DevOps / SRE
- **Deployment:** [Deployment Guide](docs/getting-started/DEPLOYMENT.md)
- **Backend Integration:** [Integration Guide](docs/getting-started/BACKEND_INTEGRATION_GUIDE.md)

### 🧪 QA / Testing
- **Testing:** [Testing Guide](docs/getting-started/TESTING.md)
- **Troubleshooting:** [docs/troubleshooting/](docs/troubleshooting/)

---

## 🗂️ Documentation by Category

### Getting Started (3 docs)
- **[Backend API Integration Guide](docs/getting-started/BACKEND_INTEGRATION_GUIDE.md)** ✅ Current
    - The chat interface has been successfully integrated with the real PratikoAI backend API using Test-Driven Development (TDD) methodology. This guide...
- **[🚀 PratikoAI Vercel Deployment Guide](docs/getting-started/DEPLOYMENT.md)** ✅ Current
    - 1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com) 2. **API Token**: Get your token from [vercel.com/account/tokens](https://vercel...
- **[Testing Guide for PratikoAi WebApp](docs/getting-started/TESTING.md)** ✅ Current
    - This document provides comprehensive information about the testing infrastructure for the PratikoAi web application.

### Development Guides (4 docs)
- **[PratikoAI Chat Interface Requirements](docs/development/CHAT_REQUIREMENTS.md)** ✅ Current
    - This document outlines the requirements for the PratikoAI chat interface based on the Figma export analysis and implementation discussions. The cha...
- **[PratikoAI Design System Documentation](docs/development/DESIGN_SYSTEM.md)** ✅ Current
    - - **Primary Blue**: `#256cdb` - Professional primary color for CTAs, links, and interactive elements - **Success Green**: `#06ac2e` - Trust & succe...
- **[Figma Design Matching Guide](docs/development/FIGMA_MATCHING_GUIDE.md)** ✅ Current
    - This guide ensures pixel-perfect implementation of Figma designs in the PratikoAI project.
- **[Figma Code Connect Setup Guide](docs/development/FIGMA_SETUP.md)** ✅ Current
    - - Node.js 18+ installed - Figma account with access to your PratikoAI project - Admin access to your Figma team/organization

### Troubleshooting (1 docs)
- **[Debugging Current Chat Issues](docs/troubleshooting/DEBUGGING_CURRENT_ISSUES.md)** ✅ Current
    - **Root Cause**: LOAD_SESSION was only preserving messages within 10 seconds during streaming **Fix Applied**: Extended preservation to 60 seconds f...

### Meta Documentation (7 docs)
- **[Manual Verification Checklist - Complete Streaming Flow](docs/meta/MANUAL_VERIFICATION_CHECKLIST.md)** ✅ Current
    - Verify the complete streaming system works end-to-end as specified in CHAT_REQUIREMENTS.md Section 19.
- **[Manual Verification: Complete First Message Flow](docs/meta/MANUAL_VERIFICATION_COMPLETE_FLOW.md)** ✅ Current
    - **Root Cause**: LOAD_SESSION was only preserving streaming messages within 10 seconds **Fix Applied**: Extended preservation window and added speci...
- **[Manual Verification: Session-Streaming Race Condition Fix](docs/meta/MANUAL_VERIFICATION_SESSION_RACE_FIX.md)** ✅ Current
    - Session history loading was clearing active streaming messages, causing the first message to fail completely.
- **[Production Optimization Summary - Phase 14 Complete](docs/meta/PRODUCTION_OPTIMIZATION_SUMMARY.md)** ✅ Current
    - Successfully completed Phase 14: Production cleanup and optimization for the PratikoAI chat application. The application is now production-ready wi...
- **[PratikoAI Chat System - Production Ready Verification](docs/meta/PRODUCTION_READY_VERIFICATION.md)** ✅ Current
    - ✅ **HTML-Aware Typing Effect**
- **[TDD Complete Streaming Flow Integration: Final Summary](docs/meta/TDD_COMPLETE_STREAMING_INTEGRATION_SUMMARY.md)** ✅ Current
    - Successfully implemented and verified the complete streaming system works end-to-end as specified in CHAT_REQUIREMENTS.md Section 19.
- **[TDD Frontend Double Response Prevention Implementation Summary](docs/meta/TDD_FRONTEND_DOUBLE_RESPONSE_PREVENTION_SUMMARY.md)** ✅ Current
    - Successfully verified and documented that the frontend properly accumulates HTML chunks AND prevents double responses when streaming completes, as ...

---

## 🔍 Quick Find

**Common Documentation Needs:**

- **How do I set up the project?** → [README](README.md)
- **How do I connect to the backend?** → [Backend Integration Guide](docs/getting-started/BACKEND_INTEGRATION_GUIDE.md)
- **How does the chat system work?** → [Chat Requirements](docs/development/CHAT_REQUIREMENTS.md)
- **How do I run tests?** → [Testing Guide](docs/getting-started/TESTING.md)
- **How do I deploy?** → [Deployment Guide](docs/getting-started/DEPLOYMENT.md)
- **What's the design system?** → [Design System Guide](docs/development/DESIGN_SYSTEM.md)
- **How do I use Figma?** → [Figma Setup](docs/development/FIGMA_SETUP.md)

---

## 🛠️ Maintenance

This index is **automatically generated** from all markdown files in the repository.

**To regenerate:**
```bash
npm run docs:generate
```

**Pre-commit hook:**
The index is automatically regenerated on commit if markdown files change.

---

## 📊 Documentation Statistics

- **Total Documents:** 26
- **Getting Started:** 3
- **Development Guides:** 4
- **Troubleshooting:** 1
- **Meta/Historical:** 7

---

**Last Updated:** 2025-12-31 12:29
**Generator:** `scripts/generate-docs-index.js`
