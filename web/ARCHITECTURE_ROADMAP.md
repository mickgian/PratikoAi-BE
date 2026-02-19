# PratikoAi Frontend - Development Roadmap

**Last Updated:** 2025-12-18
**Status:** Active Development
**Next Task ID:** DEV-13

---

## Overview

This roadmap tracks planned architectural improvements and enhancements for the PratikoAi frontend web application.
Each task follows the DEV-XX numbering scheme matching our development workflow.

**Current Architecture:** Next.js 14+ with App Router, TypeScript, Tailwind CSS v4, shadcn/ui components

**Development Approach:** All effort estimates account for AI-assisted development using Claude Code, which
significantly accelerates implementation, testing, and documentation tasks compared to traditional development timelines.

**Development Methodology:**

- **TDD (Test-Driven Development)**: Write tests BEFORE implementation for all features
- **Coverage Requirements**: All code must meet or exceed jest.config.js thresholds:
  - Branches: ≥58%
  - Functions: ≥70%
  - Lines: ≥69.5%
  - Statements: ≥70%
- **Testing Strategy**: Unit tests + Integration tests + E2E tests for critical flows
- **Language Requirement**: ALL UI text, labels, buttons, messages, errors, and user-facing
  content MUST be in Italian language
- **Code Quality (AUTOMATIC)**: Quality checks are enforced **automatically**, NO manual commands needed:
  - **WebStorm Setup (REQUIRED)**: Enable in Settings → Tools → Actions on Save:
    - ✅ Reformat code (Prettier)
    - ✅ Run eslint --fix
    - ✅ Optimize imports
    - TypeScript errors shown in real-time
  - **Pre-Commit Hooks**: Husky automatically runs quality checks on commit
    - Auto-fixes formatting and linting
    - Runs tests with coverage
    - Blocks commits if quality fails
  - **Verification Command**: `npm run check` (for final verification before PR, not regular use)
  - **Documentation**: See `docs/development/CODE_QUALITY.md` for details
- **Task Template**: Use `docs/development/TASK_TEMPLATE.md` for all new tasks

**Recent Completed Work:**

- DEV-006: Deploy QA Environment (via DEV-260) (2026-02-19)
- DEV-012: Fix Authentication Navigation Flow (2025-12-18)
- DEV-007: Implement File Attachment Feature (Claude.ai Style) (2025-12-18)
- DEV-004: Implement Super Users Feedback on Answers (Expert Feedback System) (2025-12-02)
- DEV-003: Fix Chat History Creation Behavior (Lazy Session Creation) (2025-12-02)
- DEV-002: Adjust UI for Source Citations (Figma Compliance) (2025-11-20)
- DEV-001: Initial test coverage implementation and streaming fixes (2025-11-14)

**Deployment Timeline Estimates:**

📅 **Time to QA Environment (DEV-006):**

- **Optimistic (parallel work):** ~2-3 weeks
- **Conservative (sequential):** ~3-4 weeks
- **Prerequisites:** DEV-002 ✅, DEV-003 ✅, DEV-004 ✅, DEV-005 ✅, DEV-006 ✅
- **Critical path:** All prerequisites completed

📅 **Time to Production Environment (DEV-011):**

- **Optimistic:** ~6-8 weeks from now
- **Conservative:** ~9-11 weeks from now
- **Prerequisites:** Path to QA + DEV-007, DEV-008, DEV-009, DEV-010, DEV-011
- **Note:** Production launch requires payment system (DEV-010) fully tested and validated

**Key Dependencies:**

- ⚠️ **DEV-010 (Payment System)** blocks Production deployment
- ✅ **DEV-004 (Expert Feedback)** COMPLETED (2025-12-02) - No longer blocking QA
- ⚠️ **Backend DEV-87** must be completed before frontend DEV-010 can start

---

## Q1 2025 (January - March)

<details>
<summary>
<h3>DEV-002: Adjust UI for Source Citations (Figma Compliance)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 3-5 days | <strong>Actual:</strong> 3 days | <strong>Status:</strong> ✅ COMPLETED (2025-11-20)<br>
Successfully adjusted UI for source citations to match Figma design specifications. Implemented consistent SourceCitation component with proper styling, responsive design, and comprehensive test coverage.
</summary>

### DEV-002: Adjust UI for Source Citations (Figma Compliance)

**Priority:** HIGH | **Effort:** 3-5 days | **Actual:** 3 days | **Dependencies:** None | **Status:** ✅ COMPLETED (2025-11-20)

**Problem:**
Source citations (e.g., "Circolare n.64 Agenzia delle Entrate") needed to match the Figma design specifications
for consistent branding and user experience.

**Development Methodology:** Follow TDD - Write tests FIRST, then implement features.
All code must meet coverage thresholds (jest.config.js).

**Implementation Tasks:**

**Phase 1: Design Analysis**

- [x] Review Figma design specifications for source citations
- [x] Identify all locations where citations are displayed in the app
- [x] Document current implementation vs. Figma design gaps
- [x] Create component specification document

**Phase 2: Component Implementation**

- [x] Create/update `SourceCitation` component according to Figma design
- [x] Implement styling with Tailwind CSS matching design tokens
- [x] Add proper typography, spacing, and colors per Figma
- [x] Add hover states and interactions as specified in Figma
- [x] Ensure responsive design for mobile/tablet/desktop

**Phase 3: Integration & Testing**

- [x] Replace existing citation displays with new component
- [x] Test citation rendering with various source formats
- [x] Verify visual consistency across different browsers
- [x] Add unit tests for `SourceCitation` component
- [x] Add E2E test for citation display in chat responses

**Acceptance Criteria:**

- ✅ Citations match Figma design pixel-perfect
- ✅ All citation instances use consistent component
- ✅ Responsive design works on all breakpoints
- ✅ **Italian Language:** All UI text in Italian (labels, tooltips, error messages)
- ✅ **TDD:** Tests written BEFORE implementation
- ✅ **Coverage:** Meets jest.config.js thresholds (branches ≥58%, functions ≥70%, lines ≥69.5%, statements ≥70%)
- ✅ **Code Quality:** All checks pass (TypeScript, ESLint, Prettier, Build)
- ✅ **No Unused Code:** Zero unused imports/variables (ESLint enforced)
- ✅ **Proper Formatting:** Code auto-formatted with Prettier
- ✅ Visual regression tests pass

**Completion Date:** 2025-11-20

</details>

---

<details>
<summary>
<h3>DEV-003: Fix Chat History Creation Behavior (Lazy Session Creation)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 3-4 days (with AI assistant) | <strong>Actual:</strong> ~1 week | <strong>Status:</strong> ✅ COMPLETED (2025-12-02)<br>
Implemented lazy session creation - sessions are now created only when user sends first message, not on "Nuova chat" click.
</summary>

### DEV-003: Fix Chat History Creation Behavior (Lazy Session Creation)

**Priority:** HIGH | **Effort:** 3-4 days (with AI assistant) | **Actual:** ~1 week | **Dependencies:** None | **Status:** ✅ COMPLETED (2025-12-02)

**Problem:**
Chat history items were created when user clicked "Nuova chat" button, creating empty chat entries.
Sessions should only be created when the user actually sends a message.

---

## Implementation Completed

### 1. Core Changes

**Files Modified:**

- `src/app/chat/components/ChatSidebar.tsx` - Updated `handleNewChat()` to not create session immediately
- `src/app/chat/hooks/useChatSessions.ts` - Deferred session creation until first message
- `src/app/chat/hooks/useChatSessionsV2.ts` - New V2 hook with lazy session creation
- `src/app/chat/hooks/useChatStorageV2.ts` - Storage hook supporting lazy sessions
- `src/app/chat/components/ChatMessagesArea.tsx` - Added empty state handling
- `src/lib/api/chat-history.ts` - Chat history API client

### 2. Key Features Implemented

- **Lazy Session Creation:** Session created only on first message send
- **Empty State UI:** Shows "Inizia una nuova conversazione" on sign-in
- **Chat History Selection:** Load existing sessions from sidebar
- **Session Token Management:** Proper token storage and Authorization header usage
- **No Empty Entries:** History sidebar never shows empty chat entries

### 3. Testing Implementation

**Tests Created:**

- `src/app/chat/components/__tests__/ChatSidebar.test.tsx`
- `src/app/chat/components/__tests__/ChatSidebar.integration.test.tsx`
- `src/app/chat/components/__tests__/ChatSidebar.newchat.test.tsx`
- `src/app/chat/hooks/__tests__/useChatSessions.test.tsx`
- `src/app/chat/hooks/__tests__/useChatSessionsV2.test.ts`
- `src/app/chat/hooks/__tests__/useChatStorageV2.simple.test.tsx`
- `src/lib/api/__tests__/chat-history.test.ts`

---

**Acceptance Criteria (All Met):**

- ✅ "Nuova chat" button does not create history entry immediately
- ✅ Session is created only when user sends first message
- ✅ History entry created only on first message send
- ✅ On sign-in, empty chat panel is shown
- ✅ Chat history selection loads correct messages
- ✅ Session token properly used in API calls
- ✅ No empty chat entries in history sidebar
- ✅ **Italian Language:** All UI text in Italian
- ✅ **TDD:** Tests written with comprehensive coverage
- ✅ **Coverage:** Exceeds jest.config.js thresholds
- ✅ **Code Quality:** All checks pass (TypeScript, ESLint, Prettier, Build)
- ✅ No regression in existing chat functionality

**Completion Date:** 2025-12-02

**PR:** #19 (DEV-FE-004-expert-feedback-ui branch - consolidated with DEV-004)

</details>

---

<details>
<summary>
<h3>DEV-004: Implement Super Users Feedback on Answers (Expert Feedback System)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1 week (with AI assistant) | <strong>Actual:</strong> 1.5 weeks | <strong>Status:</strong> ✅ COMPLETED (2025-12-02)<br>
Successfully implemented expert feedback UI allowing SUPER_USER role users to provide feedback on AI answers with Corretta/Incompleta/Errata options.
</summary>

### DEV-004: Implement Super Users Feedback on Answers (Expert Feedback System)

**Priority:** HIGH | **Effort:** 1 week (with AI assistant) | **Actual:** 1.5 weeks | **Dependencies:** None | **Status:** ✅ COMPLETED (2025-12-02)

**Problem:**
Super users (experts) need to provide feedback on AI-generated answers to improve quality and contribute
to FAQ generation. UI must match Figma design specifications.

**Backend Integration:**
This frontend task is linked to **DEV-BE-72** in backend roadmap:

- **Backend Task:** DEV-BE-72: Implement Expert Feedback System
- **Location:** `/Users/micky/PycharmProjects/PratikoAi-BE/ARCHITECTURE_ROADMAP.md`
- **Backend Status:** 🟢 COMPLETE (2024-11-25)
- **API Endpoints:** Frontend consumes `/api/v1/expert-feedback/*` endpoints

---

## Implementation Completed

### 1. Core Components Created

**File:** `src/app/chat/components/FeedbackButtons.tsx`

- Feedback UI with Italian labels (Corretta, Incompleta, Errata)
- Details input for incomplete/incorrect feedback
- Loading states and success/error messages
- Integration with expertFeedback API

**File:** `src/lib/api/expertFeedback.ts` - 222 lines

- `submitFeedback()` - Submit expert feedback to backend
- `getFeedbackHistory()` - Retrieve feedback history
- `getFeedbackById()` - Get specific feedback details
- `getExpertProfile()` - Get user role and profile
- `isUserSuperUser()` - Check if user can provide feedback
- Client-side validation for all required fields

**File:** `src/hooks/useExpertStatus.ts`

- React hook for checking super user status
- Loading, error, and success states
- Cleanup on unmount

**File:** `src/types/expertFeedback.ts` - 82 lines

- TypeScript types for FeedbackType, ExpertProfile, etc.
- Request/Response interfaces matching backend schema

### 2. Testing Implementation

**Tests Created:**

- `src/app/chat/components/__tests__/FeedbackButtons.test.tsx` - 12 tests
- `src/lib/api/__tests__/expertFeedback.test.ts` - 31 tests
- `src/hooks/__tests__/useExpertStatus.test.tsx` - 6 tests
- `src/components/__tests__/MigrationBanner.test.tsx` - 14 tests

**Total Tests:** 63 tests passing
**Coverage:** Exceeds all thresholds (statements 75.13%, branches 65.41%, functions 76.37%, lines 75.28%)

### 3. API Integration

**Endpoints Integrated:**

- `POST /api/v1/expert-feedback/submit` - Submit feedback
- `GET /api/v1/expert-feedback/history` - Feedback history
- `GET /api/v1/expert-feedback/experts/me/profile` - Check user role

**Request Validation:**

- query_id and feedback_type required
- query_text and original_answer required
- confidence_score must be 0-1
- time_spent_seconds must be > 0
- additional_details required for incomplete/incorrect feedback

---

**Acceptance Criteria (All Met):**

- ✅ Feedback UI implemented (FeedbackButtons component)
- ✅ Super users can provide feedback on answers
- ✅ Feedback types: Correct (Corretta), Incomplete (Incompleta), Incorrect (Errata)
- ✅ Required fields enforced for incomplete/incorrect feedback (additional_details)
- ✅ Feedback successfully submitted to backend with all required data
- ✅ Only super users/experts see feedback UI (role check via getExpertProfile)
- ✅ Regular users don't see feedback buttons
- ✅ **Italian Language:** All UI text in Italian (Corretta, Incompleta, Errata, etc.)
- ✅ **TDD:** Tests written with comprehensive coverage
- ✅ **Coverage:** Exceeds jest.config.js thresholds
- ✅ **Code Quality:** All checks pass (TypeScript, ESLint, Prettier, Build)
- ✅ **No Unused Code:** Zero unused imports/variables
- ✅ **Proper Formatting:** Code auto-formatted with Prettier

**Completion Date:** 2025-12-02

**PR:** #19 (DEV-FE-004-expert-feedback-ui branch)

</details>

---

<details>
<summary>
<h3>DEV-005: Investigate & Fix Source Citations for All RSS Feed Sources</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 3-5 days | <strong>Dependencies:</strong> DEV-002 (Completed) | <strong>Status:</strong> ✅ COMPLETED (2024-12-10)<br>
Fixed citation detection to support all 9 Italian institutional sources using centralized configuration-driven approach.
</summary>

### DEV-005: Investigate & Fix Source Citations for All RSS Feed Sources

**Priority:** HIGH | **Effort:** 3-5 days (with AI assistant) | **Dependencies:** DEV-002 ✅ | **Status:** ✅ COMPLETED (2024-12-10)

**Problem:**
The `SourceCitation` component styling (implemented in DEV-002) works correctly for Agenzia delle Entrate RSS feeds, but citations from other sources (e.g., INAIL) appear as plain links without the proper styling.

**Root Cause Identified:**
Frontend citation detection in `AIMessageV2.tsx:337-343` used hardcoded URL keyword matching that was INCOMPLETE:

- Missing keywords: 'inail', 'lavoro', 'finanze', 'governo'
- Backend was functioning correctly - INAIL URLs were properly stored and included in context

**Solution Implemented:**
Created centralized configuration-driven citation detection:

- New file: `src/config/citation-sources.ts` with `CITATION_DOMAINS` array (9 domains)
- New helper: `isCitationUrl(href)` using URL parsing instead of string matching
- Updated `AIMessageV2.tsx` to use the new helper
- UI polish: Increased font size (10px → 14px) and max-width (200px → 350px)

**Supported Sources (9 total):**

- Agenzia Entrate (agenziaentrate.gov.it)
- INPS (inps.it)
- INAIL (inail.it)
- Gazzetta Ufficiale (gazzettaufficiale.it)
- Normattiva (normattiva.it)
- MEF (mef.gov.it)
- Finanze (finanze.gov.it)
- Ministero Lavoro (lavoro.gov.it)
- Governo (governo.it)

**Files Changed:**

- `src/config/citation-sources.ts` - NEW: Centralized citation domain config
- `src/config/__tests__/citation-sources.test.ts` - NEW: 65 unit tests
- `src/app/chat/components/AIMessageV2.tsx` - Updated citation detection
- `src/app/chat/components/__tests__/AIMessageV2.citation.test.tsx` - NEW: 12 test suites
- `src/components/ui/source-citation.tsx` - UI polish (max-width)
- `e2e/source-citations.spec.ts` - NEW: E2E tests

**Test Coverage:**

- 86 citation-related tests passing
- citation-sources.ts: 100% coverage
- Overall coverage: 75.56% (above threshold)

---

**Acceptance Criteria:**

- [x] Root cause documented
- [x] All RSS feed sources render with `SourceCitation` component styling
- [x] No regression: Agenzia delle Entrate citations still work
- [x] Solution is extensible for future RSS sources
- [x] **Italian Language:** All UI text in Italian
- [x] **TDD:** Tests written BEFORE implementation
- [x] **Coverage:** Meets jest.config.js thresholds
- [x] **Code Quality:** All checks pass (TypeScript, ESLint, Prettier, Build)

</details>

---

<details>
<summary>
<h3>DEV-012: Fix Authentication Navigation Flow</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2-3 days | <strong>Actual:</strong> 1 day | <strong>Status:</strong> ✅ COMPLETED (2025-12-18)<br>
Implemented complete authentication navigation flow with auth event system, global context, route protection middleware, and logout UI.
</summary>

### DEV-012: Fix Authentication Navigation Flow

**Priority:** HIGH | **Effort:** 2-3 days (with AI assistant) | **Actual:** 1 day | **Dependencies:** None | **Status:** ✅ COMPLETED (2025-12-18)

**Problem:**
Authentication flow had critical gaps that affected user experience and security:

1. When access token expires and refresh fails, user is NOT redirected to login
2. Protected routes like `/chat` have no auth guard
3. No logout button exists in the UI
4. No global auth state management (context/provider)

---

## Implementation Completed

### 1. Auth Event System (Phase 1)

**File:** `src/lib/auth-events.ts` (NEW - 134 lines)

- Typed event emitter with events: `login`, `logout`, `session-expired`, `token-refreshed`
- Singleton pattern for coordinated auth state changes
- Listener subscription with unsubscribe functions

**File:** `src/lib/api.ts` (Modified)

- Added auth event emission on login, logout, register, OAuth
- Implemented refresh lock to prevent concurrent 401 race conditions
- Added auth status cookie for middleware route protection

### 2. Global Auth Context (Phase 2)

**File:** `src/contexts/AuthContext.tsx` (NEW - 164 lines)

- `AuthProvider` context wrapping the app
- Subscribes to auth events from ApiClient
- Exposes `isAuthenticated`, `isLoading`, `logout` via context
- Handles session expiry with callback

**File:** `src/hooks/useAuth.ts` (NEW - 30 lines)

- Thin wrapper hook for accessing auth context
- Re-exports types for convenience

**File:** `src/app/providers.tsx` (NEW - 54 lines)

- Root providers wrapper with session expiry handling
- Redirects to `/signin` with returnUrl on session expiry

**File:** `src/app/layout.tsx` (Modified)

- Wrapped app with `<Providers>` component

### 3. Route Protection Middleware (Phase 4)

**File:** `src/middleware.ts` (NEW - 138 lines)

- Edge-compatible middleware for route protection
- Protects `/chat` routes from unauthenticated access
- Uses cookie-based auth check (Edge Runtime compatible)
- Validates returnUrl to prevent open redirect attacks
- Redirects to `/signin` with returnUrl parameter

### 4. Logout UI (Phase 5)

**File:** `src/app/chat/components/ChatHeader.tsx` (Modified - 95→144 lines)

- Added user menu dropdown with "Esci" (logout) button
- Click-outside handling to close menu
- Loading state during logout
- Redirect to `/signin` after logout

### 5. Testing (Phase 6)

**Tests Created:**

- `src/lib/__tests__/auth-events.test.ts` - 17 tests
- `src/contexts/__tests__/AuthContext.test.tsx` - 17 tests
- `src/hooks/__tests__/useAuth.test.tsx` - 5 tests
- `src/__tests__/middleware.test.ts` - 16 tests
- `src/app/chat/components/__tests__/ChatHeader.test.tsx` - 16 tests

**Total:** 71 new tests (707 total passing)
**Coverage:** Exceeds all thresholds

---

**Architectural Notes (per @egidio review):**

- Uses React Context API (ADR-008) - no Redux/Zustand
- Cookie-based middleware auth (Edge Runtime compatible)
- returnUrl validation prevents XSS/open redirect attacks
- Refresh lock prevents concurrent 401 race conditions

---

**Acceptance Criteria (All Met):**

- [x] User redirected to `/signin` when token refresh fails
- [x] Unauthenticated users cannot access `/chat` (redirected to `/signin`)
- [x] Logout button visible and functional in chat UI ("Esci")
- [x] Auth state accessible via `useAuth()` hook throughout app
- [x] 401 errors during streaming handled gracefully
- [x] **Italian Language:** All UI text in Italian (Esci, Disconnessione...)
- [x] **TDD:** Tests written with comprehensive coverage
- [x] **Coverage:** Exceeds jest.config.js thresholds
- [x] **Code Quality:** All checks pass (TypeScript, ESLint, Prettier, Build)

**Completion Date:** 2025-12-18

**PR:** #29

</details>

---

<details>
<summary>
<h3>DEV-006: Deploy QA Environment</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2-3 days | <strong>Dependencies:</strong> DEV-012 | <strong>Status:</strong> ✅ COMPLETED (via DEV-260)<br>
Deploy QA environment for integration testing with backend QA environment.
</summary>

### DEV-006: Deploy QA Environment

**Priority:** HIGH | **Effort:** 2-3 days (with AI assistant) | **Dependencies:** DEV-012 | **Status:** ✅ COMPLETED (via DEV-260)

**Problem:**
Currently only development environment is deployed on Vercel. Need QA environment for integration testing with backend QA environment before proceeding with feature development.

**Development Methodology:** Follow TDD - Write tests FIRST, then implement features. All code must meet coverage thresholds (jest.config.js).

**Backend QA Environment:**
Backend QA is deployed at `https://api-qa.pratikoai.com` (Hetzner VPS, APP_ENV=qa)

**Implementation Tasks:**

**Completed via DEV-260: Deploy to QA**

Deployed as part of the unified QA deployment (DEV-260), which set up CI/CD for both backend and frontend on Hetzner QA server.

**Phase 1: Platform Decision & Setup**

- [x] Decided deployment platform: Hetzner (same server as backend, via Docker Compose)
- [x] Domain configured

**Phase 2: Environment Configuration**

- [x] QA environment configuration created
- [x] CORS configured on backend QA
- [x] DNS record set up
- [x] SSL configured via Caddy reverse proxy

**Phase 3: CI/CD Pipeline**

- [x] Automatic deployment on merge to `develop` branch
- [x] Pre-deployment checks (build, tests)
- [x] Post-deployment health check

**Phase 4: Testing & Verification**

- [x] QA environment deployed
- [x] Frontend-backend connectivity verified
- [x] Authentication flow tested with QA backend
- [x] Chat functionality tested end-to-end

**Acceptance Criteria (All Met):**

- ✅ QA environment accessible
- ✅ Frontend connects successfully to backend QA API
- ✅ Environment variables loaded correctly (APP_ENV=qa)
- ✅ CI/CD pipeline deploys automatically on `develop` branch
- ✅ All core features functional (auth, chat, streaming)
- ✅ **Italian Language:** All UI text in Italian
- ✅ **Code Quality:** All checks pass

</details>

---

<details>
<summary>
<h3>DEV-007: Implement File Attachment Feature (Claude.ai Style)</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 9-11 days (FE + BE) | <strong>Actual:</strong> ~2 weeks | <strong>Status:</strong> ✅ COMPLETED (2025-12-18)<br>
Implemented file attachment functionality for chat with drag-and-drop and button upload, similar to Claude.ai. Spans both Frontend and Backend.
</summary>

### DEV-007: Implement File Attachment Feature (Claude.ai Style)

**Priority:** MEDIUM | **Effort:** 9-11 days (FE: 4-5 days, BE: 3-4 days, Testing: 2 days) | **Actual:** ~2 weeks | **Dependencies:** None | **Status:** ✅ COMPLETED (2025-12-18)

**Branch:** `DEV-007-File-Attachment-Feature` (used by both FE and BE repositories)

**Problem:**
Users need to attach documents (PDF, Excel, images, etc.) to their chat questions for the AI to analyze. Like Claude.ai, users should be able to attach files via button click or drag-and-drop, but must include a question text (cannot send just the attachment).

**Architecture Decision (ADR-017):**

- **Pattern:** Upload-first (like Claude.ai, ChatGPT)
- **Flow:** Upload file → get document ID → send chat with `attachment_ids`
- **Rationale:** 90% of backend infrastructure already exists, separation of concerns, retry resilience
- **Approved by:** @egidio (Architect)

**Development Methodology:** Follow TDD - Write tests FIRST, then implement features. All code must meet coverage thresholds.

---

## Requirements Specification

| Requirement               | Decision                                                           |
| ------------------------- | ------------------------------------------------------------------ |
| **File types**            | PDF, Excel (.xlsx/.xls), CSV, XML, Images (JPEG/PNG), Word (.docx) |
| **File preview**          | Simple: filename + size + remove button (chip style)               |
| **Upload methods**        | Button click (paperclip icon) + Drag-and-drop                      |
| **Mobile camera**         | No - file picker only                                              |
| **Error handling**        | Soft warning, graceful degradation, log internally                 |
| **Document library**      | No - new uploads only (MVP)                                        |
| **File limits**           | 10MB per file, max 5 files per message                             |
| **UI style**              | Paperclip icon (📎) like Claude.ai                                 |
| **Must include question** | Yes - cannot send attachment without text                          |

---

## Backend Implementation (Same Branch)

**Backend Repo:** `/Users/micky/PycharmProjects/PratikoAi-BE`

**Existing Infrastructure (90% ready):**

- `/api/v1/documents/upload` - Existing multipart upload endpoint
- `RAGState.attachments` - Already supports attachment list
- `DocumentIngestTool` - Document processing pipeline (steps S082-S098)
- `SecureDocumentStorage` - Encrypted 48h TTL storage
- `AttachmentValidator` - File validation (type, size)

**Files to Modify:**

1. **`app/schemas/chat.py`** - Add attachment support to ChatRequest

   ```python
   attachment_ids: list[UUID] | None = Field(
       default=None,
       description="IDs of uploaded documents to include",
       max_length=5
   )
   ```

2. **`app/api/v1/chatbot.py`** - Resolve attachments in chat endpoints
   - Add attachment resolution in `chat()` and `chat_stream()`
   - Validate user owns referenced documents
   - Inject attachments into RAGState

3. **`app/services/document_config.py`** - Add Word MIME type
   ```python
   "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.WORD_DOCX
   ```

**Files to Create:**

1. **`app/services/attachment_resolver.py`** - Attachment resolution service
   - `resolve_attachments(db, attachment_ids, user_id)` → list[Attachment]
   - Validates ownership (document.user_id == user_id)
   - Returns parsed document content for RAG pipeline

**Backend Tasks:**

- [x] Add `attachment_ids` field to `ChatRequest` schema
- [x] Create `AttachmentResolver` service with ownership validation
- [x] Wire attachments into `chat()` endpoint
- [x] Wire attachments into `chat_stream()` endpoint
- [x] Add Word (.docx) MIME type to document config
- [x] Add SSE progress event: "Analyzing document..."
- [x] Inject attachments into RAGState for processing
- [x] Unit tests for AttachmentResolver
- [x] Integration tests for chat + attachments flow

---

## Frontend Implementation

**Frontend Repo:** `/Users/micky/PycharmProjects/PratikoAi-BE/web`

**Files to Modify:**

1. **`src/app/chat/components/ChatInputArea.tsx`** (or equivalent)
   - Add paperclip button for file attachment
   - Add drag-and-drop zone overlay
   - Show attached files as preview chips
   - Disable send button if attachment without text

2. **`src/app/chat/handlers/StreamingHandler.ts`**
   - Include `attachment_ids` in chat request body

3. **`src/lib/api/chat.ts`** (or equivalent)
   - Update `ChatRequest` type with `attachment_ids`

**Files to Create:**

1. **`src/app/chat/components/FileAttachment.tsx`**
   - Paperclip button component
   - Hidden file input with supported types
   - Click handler to open file picker

2. **`src/app/chat/components/AttachmentPreview.tsx`**
   - File chip component (filename + size + X button)
   - Progress indicator during upload
   - Error state styling

3. **`src/app/chat/components/DragDropZone.tsx`**
   - Drag-and-drop overlay for chat area
   - Visual feedback when dragging files

4. **`src/app/chat/hooks/useFileUpload.ts`**
   - Upload state management (files, uploading, errors)
   - `uploadFile(file)` → document ID
   - `removeFile(index)` → remove from list
   - `clearFiles()` → reset state

5. **`src/lib/api/documents.ts`**
   - `uploadDocument(file: File)` → `{ id: string }`
   - Uses existing `/api/v1/documents/upload` endpoint

**Frontend Tasks:**

- [x] Create `FileAttachment` component (paperclip button)
- [x] Create `AttachmentPreview` component (file chips)
- [x] Create `DragDropZone` component (drag overlay)
- [x] Create `useFileUpload` hook (upload state management)
- [x] Create document upload API client
- [x] Integrate attachment button into chat input area
- [x] Implement drag-and-drop functionality
- [x] Update StreamingHandler with attachment_ids
- [x] Disable send if attachment without question text
- [x] Add upload progress indicator
- [x] Add error handling with Italian messages
- [x] Unit tests for all new components
- [x] Unit tests for useFileUpload hook
- [x] E2E test: Upload via button and send
- [x] E2E test: Upload via drag-and-drop
- [x] E2E test: File validation errors
- [x] E2E test: Cannot send without question

---

## UI/UX Specification

**Chat Input Area Layout:**

```
┌─────────────────────────────────────────────────────┐
│  [Attached files appear here as chips]              │
│  ┌──────────────┐ ┌──────────────┐                 │
│  │ 📄 doc.pdf   │ │ 📊 data.xlsx │                 │
│  │ 2.3 MB    ✕  │ │ 1.1 MB    ✕  │                 │
│  └──────────────┘ └──────────────┘                 │
├─────────────────────────────────────────────────────┤
│ 📎 │ Scrivi la tua domanda...              │ ➤     │
└─────────────────────────────────────────────────────┘
```

**Italian UI Text:**

- Button tooltip: "Allega file"
- Drag zone: "Trascina qui i file"
- File preview: "{filename} • {size} MB"
- Error: "Tipo di file non supportato"
- Error: "File troppo grande (max 10 MB)"
- Error: "Massimo 5 file per messaggio"
- Warning: "Aggiungi una domanda per inviare"
- Progress: "Caricamento in corso..."
- Parsing: "Analisi documento in corso..."

**Supported File Types:**

- PDF: `.pdf`
- Excel: `.xlsx`, `.xls`
- CSV: `.csv`
- XML: `.xml`
- Word: `.docx`
- Images: `.jpg`, `.jpeg`, `.png`

---

## Acceptance Criteria

**Functional:**

- [x] Paperclip button opens file picker
- [x] Drag-and-drop uploads files
- [x] File preview shows filename, size, remove button
- [x] Upload progress indicator displayed
- [x] Cannot send message with only attachment (question required)
- [x] Send button disabled until question text added
- [x] Multiple files can be attached (up to 5)
- [x] Files sent to backend and processed by RAG
- [x] AI response incorporates document content

**File Handling:**

- [x] All file types supported (PDF, Excel, CSV, XML, Word, Images)
- [x] 10MB per file limit enforced
- [x] Max 5 files per message enforced
- [x] Invalid files show error message
- [x] Oversized files rejected with message

**Error Handling:**

- [x] Soft warning for parsing issues (graceful degradation)
- [x] Clear error messages for invalid files
- [x] Retry option for failed uploads
- [x] Backend logs parsing errors for debugging

**Quality Standards:**

- [x] **Italian Language:** All UI text in Italian
- [x] **TDD:** Tests written BEFORE implementation
- [x] **Coverage FE:** Meets jest.config.js thresholds (branches ≥58%, functions ≥70%, lines ≥69.5%, statements ≥70%)
- [x] **Coverage BE:** Meets pytest coverage threshold (≥49%)
- [x] **Code Quality:** All checks pass (TypeScript, ESLint, Prettier, Build)
- [x] **No Unused Code:** Zero unused imports/variables
- [x] **Proper Formatting:** Code auto-formatted

**Completion Date:** 2025-12-18

**PRs:**

- Frontend: Branch `DEV-007-Implement-File-Attachment-Feature`
- Backend: Branch `DEV-007-Implement-File-Attachment-Feature`

---

## Testing Strategy

**Backend Tests:**

- Unit: AttachmentResolver ownership validation
- Unit: ChatRequest schema with attachment_ids
- Integration: Upload → Chat with attachment flow
- Integration: Streaming with attachment parsing

**Frontend Tests:**

- Unit: FileAttachment component renders
- Unit: AttachmentPreview shows file info
- Unit: useFileUpload hook state management
- Unit: File validation logic
- E2E: Complete upload and chat flow
- E2E: Drag-and-drop functionality
- E2E: Error handling scenarios

---

## Related Backend Documentation

**RAG Pipeline Steps (from pratikoai_rag_hybrid.mmd):**

- S017-S018: AttachmentFingerprint.compute, QuerySignature.compute
- S019-S023: Attachment-aware gating and doc pre-ingest
- S082-S098: DocumentIngestTool processing pipeline
  - S084-S085: AttachmentValidator.validate
  - S087: DocSanitizer.sanitize
  - S088-S094: Parsers (Fattura, F24, Contract, Payslip, GenericOCR)
  - S095-S097: Extractor.extract → BlobStore.put → Provenance.log
  - S098: Convert to ToolMessage with facts

**Existing Endpoints:**

- `POST /api/v1/documents/upload` - Multipart file upload
- `POST /api/v1/chatbot/chat` - Chat endpoint (needs attachment_ids)
- `POST /api/v1/chatbot/chat/stream` - Streaming (needs attachment_ids)

</details>

---

<details>
<summary>
<h3>DEV-008: Review and Update Landing Page & Sign-in Page UI</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 1 week | <strong>Dependencies:</strong> None | <strong>Status:</strong> ❌ NOT STARTED<br>
Review and update landing page and sign-in page UI for Figma design compliance.
</summary>

### DEV-008: Review and Update Landing Page & Sign-in Page UI

**Priority:** MEDIUM | **Effort:** 1 week (with AI assistant) | **Dependencies:** None | **Status:** ❌ NOT STARTED

**Problem:**
Landing page and sign-in page UI need review for Figma design compliance and modern best practices.

**Development Methodology:** Follow TDD - Write tests FIRST, then implement features. All code must meet coverage thresholds (jest.config.js).

**Implementation Tasks:**

**Phase 1: Design Audit**

- [ ] Compare current landing page with Figma design
- [ ] Compare current sign-in page with Figma design
- [ ] List all visual/UX discrepancies
- [ ] Review accessibility compliance (WCAG 2.1)
- [ ] Review mobile responsiveness
- [ ] Create update specification document

**Phase 2: Landing Page Updates**

- [ ] Update hero section (copy, images, CTAs)
- [ ] Implement proper spacing and typography per Figma
- [ ] Add/update feature showcase section
- [ ] Optimize images and assets for performance
- [ ] Ensure responsive design for all breakpoints
- [ ] Add loading states and transitions

**Phase 3: Sign-in Page Updates**

- [ ] Update sign-in form layout per Figma
- [ ] Style form inputs with proper focus states
- [ ] Update button styles and hover states
- [ ] Add proper error message displays
- [ ] Implement loading states for authentication
- [ ] Add password visibility toggle

**Phase 4: Testing & Optimization**

- [ ] Visual regression testing with Playwright
- [ ] Test responsiveness on various devices
- [ ] Lighthouse performance audit (target: >90 score)
- [ ] Accessibility audit with axe-core
- [ ] Cross-browser testing (Chrome, Firefox, Safari)
- [ ] E2E tests for landing page navigation
- [ ] E2E tests for sign-in flow

**Acceptance Criteria:**

- ✅ Landing page matches Figma design
- ✅ Sign-in page matches Figma design
- ✅ Lighthouse performance score >90
- ✅ WCAG 2.1 AA compliance
- ✅ Mobile-responsive on all breakpoints
- ✅ Cross-browser compatibility verified
- ✅ **Italian Language:** All UI text in Italian (headings, CTAs, form labels, error messages, links)
- ✅ **TDD:** Tests written BEFORE implementation
- ✅ **Coverage:** Meets jest.config.js thresholds (branches ≥58%, functions ≥70%, lines ≥69.5%, statements ≥70%)
- ✅ **Code Quality:** All checks pass (TypeScript, ESLint, Prettier, Build)
- ✅ **No Unused Code:** Zero unused imports/variables (ESLint enforced)
- ✅ **Proper Formatting:** Code auto-formatted with Prettier
- ✅ All E2E tests pass

</details>

---

<details>
<summary>
<h3>DEV-009: Implement Social Login (Google, LinkedIn, etc.)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1-2 weeks | <strong>Dependencies:</strong> DEV-008 | <strong>Status:</strong> ❌ NOT STARTED<br>
Implement OAuth authentication with Google, LinkedIn, and other social providers.
</summary>

### DEV-009: Implement Social Login (Google, LinkedIn, etc.)

**Priority:** HIGH | **Effort:** 1-2 weeks (with AI assistant) | **Dependencies:** DEV-008 (sign-in page updates) | **Status:** ❌ NOT STARTED

**Problem:**
Social login options (Google, LinkedIn, etc.) are not implemented. Users expect OAuth authentication for faster onboarding.

**Development Methodology:** Follow TDD - Write tests FIRST, then implement features. All code must meet coverage thresholds (jest.config.js).

**Implementation Tasks:**

**Phase 1: Backend Coordination**

- [ ] Verify backend OAuth endpoints (`/api/v1/auth/google`, `/api/v1/auth/linkedin`)
- [ ] Document OAuth callback flow and token handling
- [ ] Get OAuth client IDs and secrets from backend team
- [ ] Review session management strategy
- [ ] Create OAuth integration specification

**Phase 2: Google OAuth Integration**

- [ ] Add `@react-oauth/google` package
- [ ] Create `GoogleLoginButton` component per Figma
- [ ] Implement Google OAuth flow
- [ ] Handle OAuth callback and token exchange
- [ ] Store authentication tokens in secure storage
- [ ] Add error handling for failed OAuth

**Phase 3: LinkedIn OAuth Integration**

- [ ] Add LinkedIn OAuth SDK or custom implementation
- [ ] Create `LinkedInLoginButton` component per Figma
- [ ] Implement LinkedIn OAuth flow
- [ ] Handle OAuth callback and token exchange
- [ ] Ensure consistent auth state management with Google

**Phase 4: Additional Providers** (if required)

- [ ] Identify other OAuth providers needed
- [ ] Implement additional provider buttons
- [ ] Ensure consistent UI/UX across all providers

**Phase 5: Security & Testing**

- [ ] Implement CSRF protection for OAuth flows
- [ ] Add OAuth state parameter validation
- [ ] Implement PKCE for enhanced security
- [ ] Add unit tests for OAuth components
- [ ] E2E test: Google login flow
- [ ] E2E test: LinkedIn login flow
- [ ] Test error scenarios (denied permissions, network errors)
- [ ] Security audit for token storage and transmission

**Acceptance Criteria:**

- ✅ Google OAuth login fully functional
- ✅ LinkedIn OAuth login fully functional
- ✅ OAuth buttons match Figma design
- ✅ Secure token storage implementation
- ✅ CSRF and PKCE protection enabled
- ✅ Error handling for all failure scenarios
- ✅ Session persistence after OAuth login
- ✅ **Italian Language:** All UI text in Italian (button labels, error messages, success messages, loading states)
- ✅ **TDD:** Tests written BEFORE implementation
- ✅ **Coverage:** Meets jest.config.js thresholds (branches ≥58%, functions ≥70%, lines ≥69.5%, statements ≥70%)
- ✅ **Code Quality:** All checks pass (TypeScript, ESLint, Prettier, Build)
- ✅ **No Unused Code:** Zero unused imports/variables (ESLint enforced)
- ✅ **Proper Formatting:** Code auto-formatted with Prettier
- ✅ All E2E tests pass
- ✅ Security audit passed

</details>

---

<details>
<summary>
<h3>DEV-010: Integrate User Subscription Payment (Stripe)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1-2 weeks | <strong>Dependencies:</strong> DEV-009 | <strong>Status:</strong> ❌ NOT STARTED<br>
Integrate Stripe payment for €69/month subscription with 7-day trial.
</summary>

### DEV-010: Integrate User Subscription Payment (Stripe)

**Priority:** HIGH | **Effort:** 1-2 weeks (with AI assistant) | **Dependencies:** DEV-009 (Social Login complete) | **Status:** ❌ NOT STARTED

**Problem:**
Users need to subscribe and pay for the service (€69/month with 7-day trial). Payment system must be fully functional before production launch.

**Development Methodology:** Follow TDD - Write tests FIRST, then implement features. All code must meet coverage thresholds (jest.config.js).

**Backend Integration:**
This frontend task is linked to **DEV-87** in backend roadmap:

- **Backend Task:** DEV-87: User Subscription & Payment Management
- **Location:** `/Users/micky/PycharmProjects/PratikoAi-BE/ARCHITECTURE_ROADMAP.md`
- **Coordination Required:** Backend APIs must be completed BEFORE frontend implementation
- **Backend Configuration:**
  - Stripe SDK integration: `app/services/stripe_service.py`
  - Monthly subscription: €69/month with 7-day trial
  - Webhook support for subscription events
  - API Endpoints: `/api/v1/subscriptions/*` and `/api/v1/webhooks/stripe`
  - Stripe keys must match between frontend (publishable) and backend (secret)
- **IMPORTANT:** Backend implementation (DEV-87) should be completed first. Verify all endpoints are functional before implementing frontend.

**Implementation Tasks:**

**Phase 1: Stripe Setup & SDK Integration**

- [ ] Install Stripe SDK: `@stripe/stripe-js`, `@stripe/react-stripe-js`
- [ ] Get Stripe publishable key from backend team
- [ ] Create Stripe provider wrapper component
- [ ] Set up environment variables:
  ```env
  NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_...
  ```
- [ ] Configure Stripe Elements for payment forms

**Phase 2: Subscription Checkout Flow**

- [ ] Create subscription pricing page showing €69/month plan
- [ ] Implement "Subscribe" button on pricing page
- [ ] Create checkout page with Stripe Payment Element
- [ ] Implement subscription creation flow:
  - Call backend: `POST /api/v1/payments/create-subscription`
  - Redirect to Stripe Checkout or use embedded form
  - Handle 7-day trial period display
- [ ] Add payment method selection (card, SEPA, etc.)
- [ ] Display subscription summary before confirmation

**Phase 3: Payment Success/Failure Handling**

- [ ] Create payment success page (`/payment/success`)
  - Display confirmation message
  - Show subscription details (next billing date, amount)
  - Redirect to dashboard
- [ ] Create payment failure/cancel page (`/payment/cancel`)
  - Display error message
  - Allow user to retry payment
  - Show support contact information
- [ ] Handle payment redirects from Stripe
- [ ] Update user subscription status in UI after successful payment

**Phase 4: Subscription Management UI**

- [ ] Create subscription status component for user dashboard
  - Show current plan (Active/Trial/Expired)
  - Display next billing date
  - Show payment method (last 4 digits)
  - Trial days remaining indicator
- [ ] Create "Manage Subscription" page:
  - Update payment method
  - Cancel subscription (with confirmation)
  - Reactivate canceled subscription
  - View billing history
- [ ] Add subscription status badge to user profile
- [ ] Implement access control based on subscription status

**Phase 5: Webhook Integration**

- [ ] Verify backend webhook endpoint is configured
- [ ] Test webhook events from Stripe dashboard:
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`
- [ ] Handle subscription status updates in real-time
- [ ] Show notifications for payment events (success, failure, renewal)

**Phase 6: Trial Period Handling**

- [ ] Display trial period information during signup
- [ ] Show trial countdown in user dashboard
- [ ] Send trial expiration reminders (coordinate with backend)
- [ ] Handle trial-to-paid conversion flow
- [ ] Implement trial extension logic (if applicable)

**Phase 7: Access Control & Paywalls**

- [ ] Implement subscription status check on protected routes
- [ ] Create paywall component for non-subscribed users
- [ ] Redirect to pricing page when subscription required
- [ ] Handle expired subscription grace period
- [ ] Display upgrade prompts for free/trial users

**Phase 8: Testing & Security**

- [ ] Use Stripe test mode for all development/QA testing
- [ ] Test with Stripe test cards:
  - Success: `4242 4242 4242 4242`
  - Decline: `4000 0000 0000 0002`
  - 3D Secure: `4000 0027 6000 3184`
- [ ] Test subscription lifecycle:
  - Create subscription with trial
  - Update payment method
  - Cancel subscription
  - Reactivate subscription
- [ ] Test webhook event handling
- [ ] Security audit: Ensure no sensitive Stripe data stored in frontend
- [ ] Verify PCI compliance (Stripe Elements handles this)
- [ ] Test error handling for all payment failures
- [ ] E2E test: Complete subscription flow from signup to first payment

**Phase 9: Documentation & Compliance**

- [ ] Document subscription flow: `docs/features/SUBSCRIPTION_FLOW.md`
- [ ] Create user documentation for payment/billing
- [ ] Verify GDPR compliance for payment data
- [ ] Add terms of service and refund policy links
- [ ] Document Stripe webhook configuration

**Acceptance Criteria:**

- ✅ Users can subscribe to €69/month plan with 7-day trial
- ✅ Stripe checkout flow works end-to-end
- ✅ Payment success/failure pages functional
- ✅ Subscription status displayed in user dashboard
- ✅ Users can manage subscription (update payment, cancel)
- ✅ Webhooks handle subscription events correctly
- ✅ Access control enforced based on subscription status
- ✅ Trial period countdown displayed correctly
- ✅ All payment tests pass (including test cards)
- ✅ **Italian Language:** All UI text in Italian (pricing labels, payment form text, success/error messages, subscription status, billing history)
- ✅ **TDD:** Tests written BEFORE implementation
- ✅ **Coverage:** Meets jest.config.js thresholds (branches ≥58%, functions ≥70%, lines ≥69.5%, statements ≥70%)
- ✅ **Code Quality:** All checks pass (TypeScript, ESLint, Prettier, Build)
- ✅ **No Unused Code:** Zero unused imports/variables (ESLint enforced)
- ✅ **Proper Formatting:** Code auto-formatted with Prettier
- ✅ Security audit passed (no PCI violations)
- ✅ Documentation complete

**Stripe Test Mode Configuration:**

- Use Stripe test keys for development/QA
- Switch to live keys only for production deployment
- Test all payment scenarios before going live

**Cost:**

- Stripe fees: 2.9% + €0.25 per transaction
- No monthly Stripe subscription fee (pay-as-you-go)

</details>

---

<details>
<summary>
<h3>DEV-011: Deploy Production Environments</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 3-5 days | <strong>Dependencies:</strong> DEV-010 | <strong>Status:</strong> ❌ NOT STARTED<br>
Deploy Production environments for final testing and live launch.
</summary>

### DEV-011: Deploy Production Environments

**Priority:** HIGH | **Effort:** 3-5 days (with AI assistant) | **Dependencies:** DEV-010 (Payment integration complete) | **Status:** ❌ NOT STARTED

**Problem:**
After payment system is fully integrated and tested, need to deploy Production environment for final testing and live launch with real users.

**Development Methodology:** Follow TDD - Write tests FIRST, then implement features. All code must meet coverage thresholds (jest.config.js).

**Backend Environments:**

- Production: `https://api.pratikoai.com` (Hetzner VPS, APP_ENV=production)

**Implementation Tasks:**

**Phase 1: Production Deployment**

- [ ] Create `.env.production` configuration file:
  ```env
  NEXT_PUBLIC_APP_ENV=production
  NEXT_PUBLIC_API_URL=https://api.pratikoai.com
  NEXT_PUBLIC_DEBUG=false
  NEXT_PUBLIC_ENABLE_ANALYTICS=true
  NEXT_PUBLIC_ENABLE_ERROR_TRACKING=true
  ```
- [ ] Deploy Production environment with highest security settings
- [ ] Configure custom domain: `https://pratikoai.com` and `https://www.pratikoai.com`
- [ ] Configure SSL certificate with auto-renewal
- [ ] Set up CI/CD for `main` branch deployment
- [ ] Configure CORS on backend Production
- [ ] Enable CDN caching and edge optimization
- [ ] Configure monitoring and error tracking (Sentry or similar)
- [ ] Set up alerting for deployment failures and errors
- [ ] Enable rate limiting and DDoS protection
- [ ] Configure production analytics

**Phase 2: Security & Compliance**

- [ ] Security audit on Production environment
- [ ] SSL/TLS configuration (A+ rating on SSL Labs)
- [ ] GDPR compliance verification (cookie consent, privacy policy)
- [ ] Test OAuth security on Production
- [ ] Verify no sensitive data in logs or error messages
- [ ] Test API authentication and authorization

**Phase 3: Testing & Documentation**

- [ ] Smoke tests on Prod
- [ ] Full regression testing on Prod
- [ ] Validate all OAuth providers on Production
- [ ] Performance testing (Lighthouse score >90)
- [ ] Document deployment procedures: `docs/deployment/DEPLOYMENT_PROCEDURES.md`
- [ ] Create production deployment runbook
- [ ] Train team on deployment and rollback procedures

**Acceptance Criteria:**

- ✅ Production environment deployed and accessible
- ✅ Custom domains configured with SSL for both environments
- ✅ CI/CD pipelines operational (`main` branche)
- ✅ Frontend-backend connectivity verified for both environments
- ✅ All features functional including social login
- ✅ Security audit passed for Production
- ✅ Monitoring and alerting configured
- ✅ Rollback procedures tested and documented
- ✅ **Italian Language:** All UI text in Italian (deployment status messages, error notifications, monitoring alerts)
- ✅ **TDD:** Tests written BEFORE implementation
- ✅ **Coverage:** Meets jest.config.js thresholds (branches ≥58%, functions ≥70%, lines ≥69.5%, statements ≥70%)
- ✅ **Code Quality:** All checks pass (TypeScript, ESLint, Prettier, Build)
- ✅ **No Unused Code:** Zero unused imports/variables (ESLint enforced)
- ✅ **Proper Formatting:** Code auto-formatted with Prettier
- ✅ GDPR compliance verified

**Cost Estimation:**

- If Vercel: $0-20/month (may fit in existing plan)
- If AWS/Hetzner: ~$10-20/month (Production)

</details>

---

## Future Roadmap (Q2 2025+)

### Planned Features

- Real-time collaboration features
- Advanced analytics dashboard
- Offline mode support
- Progressive Web App (PWA) capabilities
- Internationalization (i18n) support
- Dark mode implementation
- Accessibility enhancements
- Performance optimizations

---

## Notes

**Testing & Quality Requirements:**

- **TDD Mandatory**: Write tests BEFORE implementation for ALL features (Red → Green → Refactor cycle)
- **Coverage Thresholds** (jest.config.js): All code must meet minimum thresholds:
  - Branches: ≥58%
  - Functions: ≥70%
  - Lines: ≥69.5%
  - Statements: ≥70%
- **Test Types Required**:
  - Unit tests: Individual functions and components
  - Integration tests: Feature workflows
  - E2E tests: Critical user flows (Playwright)
- **Coverage Verification**: Run `npm test -- --coverage` before committing

**Development Standards:**

- **Code Quality Enforcement**: See `docs/development/CODE_QUALITY.md` for complete standards
  - Run `npm run check` before every commit to catch all issues early
  - Pre-commit hooks automatically fix formatting and run tests
  - No unused imports/variables allowed (ESLint errors)
  - Correct React hook dependencies required (ESLint errors)
  - TypeScript compilation must succeed (zero errors)
- All UI changes must match Figma design specifications pixel-perfect
- Security reviews required for authentication-related tasks
- Deployment requires staging environment verification first
- Code reviews mandatory for all PRs
- TypeScript strict mode enabled (no `any` types without justification)
