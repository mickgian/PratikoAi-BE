# PratikoAI v1.8 - Social Campaign Creator Tasks

**Version:** 1.8
**Date:** February 2026
**Status:** NOT STARTED
**Total Effort:** ~37h (5 weeks at 2h/day with Claude Code)
**Architecture:** ADR-025 (pending)

---

## Overview

PratikoAI 1.8 transforms coPratiko into an **AI-powered Social Campaign Creator** that:
- Creates professional social media campaigns for Italian professionals
- Uses Italian tax calendar (Scadenzario Fiscale) as default content source
- Automates Canva design creation via Browser MCP
- Provides iterative feedback loop (Week → Month → Year expansion)
- Runs in OS-level sandbox for security

**Reference Documents:**
- `docs/tasks/PRATIKO_1.8_REFERENCE.md` - Functional requirements
- `docs/architecture/decisions/ADR-025-social-campaign-creator.md` (pending)

---

## Key Innovation: coPratiko as "Social Media Manager"

**Value Proposition:**
- Italian commercialisti spend 2-4h/week on social media
- coPratiko generates a year of content in ~30 minutes
- Uses AI to create posts aligned with tax calendar deadlines
- Automates Canva design creation (no manual design work)
- Cost: $5-25/month per user (using Haiku for most tasks)

**Workflow:**
```
Select Folder → Analyze Docs → Get Scadenze → Generate 5 Posts (Week 1)
      ↓
User Approval → Expand to Month → Expand to Year → Create Canva Designs
```

---

## Project Locations

| Project | Path | Status |
|---------|------|--------|
| **Backend** | `/Users/micky/PycharmProjects/PratikoAi-BE` | Existing FastAPI |
| **Frontend** | `/Users/micky/PycharmProjects/PratikoAi-BE/web` | Existing Next.js 15 |
| **Desktop** | `/Users/micky/AndroidStudioProjects/PratikoAi-KMP` | Existing KMP project |

---

## Executive Summary

| Component | Tasks | Effort |
|-----------|-------|--------|
| Backend | 9 | ~23h |
| Desktop (KMP) | 5 | ~10h |
| Frontend | 3 | ~8h |
| **TOTAL** | **17** | **~37h** |

**Critical Path:** LLM Router → MCP → Canva Automation → Workflow Orchestrator → UI

---

## Task ID Mapping

| Task Range | Phase |
|------------|-------|
| DEV-280 to DEV-286, DEV-292-293 | Backend |
| DEV-287 to DEV-291 | Desktop (KMP) |
| DEV-294 to DEV-296 | Frontend (Next.js) |

---

## Phase 1: Backend (~23h)

---

### DEV-280: Cost-Optimized LLM Router

**Priority:** CRITICAL | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Need to route requests to appropriate model (Haiku/Sonnet/Opus) and implement caching to achieve $5-25/month target.

**Solution:**
Create LLMRouter with model selection logic and Anthropic prompt caching integration.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** DEV-284, DEV-286

**Change Classification:** ADDITIVE

**Files:**
- `app/services/llm/llm_router.py` - Model routing logic
- `app/services/llm/prompt_cache.py` - Anthropic prompt caching
- `app/services/llm/cost_tracker.py` - Token usage monitoring
- `tests/services/llm/test_llm_router.py`

**Key Components:**
- Route to Haiku ($1/$5) for document analysis, brand extraction, web research, Canva commands
- Route to Sonnet ($3/$15) for content generation
- Route to Opus ($5/$25) only for complex reasoning (fallback)
- Prompt caching for 90% savings on repeated context

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Model routing based on task type
- [ ] Prompt caching for static context (scadenzario, brand)
- [ ] Token usage tracking
- [ ] Cost dashboard endpoint

---

### DEV-281: MCP Integration Layer

**Priority:** CRITICAL | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
coPratiko needs to connect to MCP servers (Browser MCP) to enable browser automation for Canva.

**Solution:**
Create MCP client in Python that connects to MCP servers and exposes tools to LangGraph.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** DEV-285 (Canva Browser Automation)

**Change Classification:** ADDITIVE

**Files:**
- `app/services/mcp/mcp_client.py` - MCP client connection
- `app/services/mcp/browser_mcp_adapter.py` - Browser MCP specific adapter
- `app/services/mcp/tool_registry.py` - Tool discovery and registration
- `config/mcp_servers.yaml` - MCP server configurations
- `tests/services/mcp/test_mcp_client.py`

**Fields/Methods/Components:**

```python
class MCPClient:
    async def connect(self, server_url: str) -> bool
    async def list_tools(self) -> list[MCPTool]
    async def call_tool(self, tool_name: str, args: dict) -> ToolResult
    async def disconnect() -> None

class BrowserMCPAdapter:
    async def navigate(self, url: str) -> None
    async def click(self, selector: str) -> None
    async def type_text(self, selector: str, text: str) -> None
    async def screenshot() -> bytes
```

**Resources:**
- Browser MCP: https://github.com/browser-use/browser-use
- MCP Specification: https://modelcontextprotocol.io/

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] MCP client connects to Browser MCP extension
- [ ] Tools are discovered and registered
- [ ] Tool calls execute in browser
- [ ] Error handling for connection failures

---

### DEV-282: Scadenzario Fiscale Service

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Need Italian tax calendar data to generate social campaign content.

**Solution:**
Create ScadenzarioService that provides upcoming tax deadlines with Italian descriptions and hashtags.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** DEV-284 (Social Campaign Generator)

**Change Classification:** ADDITIVE

**Files:**
- `app/services/scadenzario/scadenzario_service.py` - Main service
- `app/services/scadenzario/deadline_types.py` - Deadline definitions
- `config/scadenzario_fiscale_2026.yaml` - Italian tax deadlines
- `tests/services/scadenzario/test_scadenzario_service.py`

**Italian Tax Deadlines (2026):**
- 16 gennaio: Versamento IVA mese precedente (F24)
- 28 febbraio: Consegna Certificazione Unica (CU)
- 30 aprile: Dichiarazione IVA annuale
- 16 giugno: Acconto IMU 2026
- 30 giugno: Versamento saldo IRPEF
- 30 settembre: Modello 730 (integrativo)
- 30 novembre: Acconto IRPEF secondo o unico
- 16 dicembre: Saldo IMU 2026

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Service returns upcoming deadlines
- [ ] Deadlines include Italian descriptions and hashtags
- [ ] Filtering by date range
- [ ] Filtering by deadline type

---

### DEV-283: Brave Web Search Integration

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
For custom topics (not scadenze fiscali), coPratiko needs to research the topic before generating posts.

**Solution:**
Integrate Brave Search API for web research on custom topics. Extract relevant information to feed to LLM.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** DEV-284 (Social Campaign Generator)

**Change Classification:** ADDITIVE

**Files:**
- `app/services/search/brave_search_client.py` - Brave API client
- `app/services/search/content_extractor.py` - Extract key info from search results
- `app/services/search/topic_researcher.py` - Orchestrate research
- `tests/services/search/test_brave_search.py`

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Brave API integration working
- [ ] Content extraction from search results
- [ ] Caching to reduce API costs
- [ ] Rate limiting

---

### DEV-284: Social Campaign Generator

**Priority:** CRITICAL | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Need to generate social media posts that match brand voice, deadline timing, and platform requirements.

**Solution:**
Create SocialCampaignGenerator that uses LLM with cached prompts to generate platform-specific posts.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-280 (LLM Router), DEV-282 (Scadenzario)
- **Unlocks:** DEV-286 (Workflow Orchestrator)

**Change Classification:** ADDITIVE

**Files:**
- `app/services/campaign/campaign_generator.py` - Main generator
- `app/services/campaign/brand_analyzer.py` - Extract brand voice from assets
- `app/services/campaign/post_formatter.py` - Platform-specific formatting
- `config/prompts/campaign/` - Campaign generation prompts
- `tests/services/campaign/test_campaign_generator.py`

**Platform Requirements:**

| Platform | Character Limit | Hashtags | Media |
|----------|-----------------|----------|-------|
| Instagram | 2,200 | 3-5 | Required |
| LinkedIn | 3,000 | 3-5 | Optional |
| Facebook | 63,206 | 1-2 | Optional |
| Twitter/X | 280 | 1-2 | Optional |

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Platform-specific post generation
- [ ] Brand voice extraction from uploaded assets
- [ ] Deadline-aligned content for scadenze
- [ ] Iterative refinement with user feedback

---

### DEV-285: Canva Browser Automation

**Priority:** CRITICAL | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Need to create designs in Canva automatically using Browser MCP.

**Solution:**
Create CanvaAutomator that uses Browser MCP to navigate Canva, create designs, and export them.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-281 (MCP Integration Layer)
- **Unlocks:** DEV-286 (Workflow Orchestrator)

**Change Classification:** ADDITIVE

**Files:**
- `app/services/canva/canva_automator.py` - Main automation
- `app/services/canva/template_selector.py` - Choose templates
- `app/services/canva/design_commands.py` - Canva operations
- `tests/services/canva/test_canva_automator.py`

**Fields/Methods/Components:**

```python
class CanvaAutomator:
    async def login_to_canva(self) -> bool
    async def create_design(self, template: str, dimensions: tuple) -> str
    async def add_text(self, text: str, position: str) -> None
    async def change_colors(self, color_scheme: str) -> None
    async def add_elements(self, elements: list[str]) -> None
    async def export_design(self, format: str) -> bytes
    async def save_to_folder(self, path: Path) -> str
```

**Browser MCP Actions Used:**
- `navigate` - Go to canva.com
- `click` - Select templates, tools
- `type` - Enter text content
- `screenshot` - Capture design previews
- `download` - Export final designs

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Automated Canva login (user provides credentials)
- [ ] Create design from template
- [ ] Add text and customize colors
- [ ] Export to PNG/PDF
- [ ] Save to project folder

---

### DEV-286: Workflow Orchestrator (LangGraph)

**Priority:** CRITICAL | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Need to orchestrate the full workflow: folder → content → Canva → export.

**Solution:**
Create LangGraph workflow that coordinates all services with checkpoints for user approval.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-284 (Social Campaign Generator), DEV-285 (Canva Automation)
- **Unlocks:** DEV-288 (Campaign Progress UI)

**Change Classification:** ADDITIVE

**Files:**
- `app/services/workflow/social_campaign_workflow.py` - Main workflow
- `app/core/langgraph/nodes/folder_analyzer_node.py` - Analyze folder
- `app/core/langgraph/nodes/campaign_generator_node.py` - Generate content
- `app/core/langgraph/nodes/canva_automation_node.py` - Create designs
- `tests/services/workflow/test_social_campaign_workflow.py`

**Workflow Steps:**
```
Select Folder → Analyze Docs → Get Deadlines → Generate Posts
      ↓
User Approval (CHECKPOINT) → Connect Canva → Create Designs → Export & Save
```

**Iterative Generation:**
1. Week 1: Generate 5 posts, get user feedback
2. If approved: Offer to expand to full month
3. If approved: Offer to expand to full year
4. Cached context = 90% cost savings after Week 1

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Full workflow executes end-to-end
- [ ] Checkpoint for user approval between generation and design
- [ ] Error recovery at each step
- [ ] Progress updates via SSE
- [ ] Support iterative week → month → year expansion

---

### DEV-292: Error Handling & Recovery

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Browser automation can fail; need graceful recovery.

**Solution:**
Implement retry logic and user intervention points.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-285, DEV-286
- **Unlocks:** None

**Change Classification:** ADDITIVE

**Files:**
- `app/services/workflow/error_recovery.py`
- `app/services/canva/canva_error_handler.py`
- `tests/services/workflow/test_error_recovery.py`

**Error Scenarios:**

| Scenario | Recovery |
|----------|----------|
| Browser MCP disconnection | Prompt reconnect |
| Canva session expired | Prompt re-login |
| Design creation failed | Retry or skip |
| Network error | Queue for retry |

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Automatic retry (3 attempts)
- [ ] User intervention dialogs
- [ ] Skip and continue option
- [ ] Error log for support

---

### DEV-293: Prompt Engineering System

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Need structured prompt management with versioning, caching, and A/B testing.

**Solution:**
Create PromptRegistry with YAML-based prompts, versioning, and performance tracking.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** DEV-284

**Change Classification:** ADDITIVE

**Files:**
- `app/services/prompts/prompt_registry.py` - Prompt management
- `app/services/prompts/prompt_loader.py` - Load from YAML
- `config/prompts/system/scadenzario_fiscale.txt` - Cached context
- `config/prompts/system/brand_template.txt` - Brand context template
- `config/prompts/tasks/generate_weekly_posts.txt`
- `config/prompts/tasks/incorporate_feedback.txt`
- `config/prompts/tasks/canva_design_instructions.txt`
- `tests/services/prompts/test_prompt_registry.py`

**Key Prompts:**
- `SYSTEM_PROMPT_SCADENZARIO` - Italian tax calendar context (cached)
- `SYSTEM_PROMPT_BRAND` - Brand identity template (cached per client)
- `PROMPT_GENERATE_WEEKLY_POSTS` - Generate 5 posts for a week
- `PROMPT_INCORPORATE_FEEDBACK` - Regenerate with user feedback
- `PROMPT_CANVA_DESIGN_INSTRUCTIONS` - Convert brief to Canva actions

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All prompts stored in config/prompts/
- [ ] Version tracking for each prompt
- [ ] A/B testing support
- [ ] Integration with cost-optimized router (cached prompts)
- [ ] Italian language prompts

---

## Phase 2: Desktop KMP (~10h)

**Location:** `/Users/micky/AndroidStudioProjects/PratikoAi-KMP`

---

### DEV-287: KMP Project Selector UI

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Desktop app needs UI for folder selection and project management.

**Solution:**
Create Compose Desktop screens for project/folder management.

**Agent Assignment:** @livia (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-291 (Folder Permission System)
- **Unlocks:** DEV-288 (Campaign Progress UI)

**Change Classification:** ADDITIVE

**Files:**
- `desktopApp/src/desktopMain/kotlin/ui/campaign/ProjectSelectorScreen.kt`
- `desktopApp/src/desktopMain/kotlin/ui/campaign/FolderPickerDialog.kt`
- `shared/src/commonMain/kotlin/viewmodel/CampaignProjectViewModel.kt`
- `shared/src/commonMain/kotlin/models/CampaignProject.kt`

**UI Components:**

```kotlin
@Composable
fun ProjectSelectorScreen(
    onFolderSelected: (Path) -> Unit,
    onStartCampaign: () -> Unit
) {
    Column {
        FolderDropZone(onDrop = onFolderSelected)
        FolderPickerButton(onPick = onFolderSelected)
        SelectedFolderInfo(folder)
        DocumentPreview(documents)
        StartCampaignButton(onClick = onStartCampaign)
    }
}
```

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Folder selection via picker or drag-drop
- [ ] Document preview
- [ ] Start campaign button
- [ ] Project list view

---

### DEV-288: Campaign Progress UI

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
User needs to see campaign creation progress and approve content.

**Solution:**
Create progress screens with real-time updates and approval dialogs.

**Agent Assignment:** @livia (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-287 (Project Selector UI), DEV-286 (Workflow Orchestrator)
- **Unlocks:** None (end of chain)

**Change Classification:** ADDITIVE

**Files:**
- `desktopApp/src/desktopMain/kotlin/ui/campaign/CampaignProgressScreen.kt`
- `desktopApp/src/desktopMain/kotlin/ui/campaign/ContentApprovalDialog.kt`
- `desktopApp/src/desktopMain/kotlin/ui/campaign/DesignPreviewCard.kt`
- `shared/src/commonMain/kotlin/viewmodel/CampaignProgressViewModel.kt`

**UI Components:**

```kotlin
@Composable
fun CampaignProgressScreen(
    progress: CampaignProgress,
    onApprove: (PostContent) -> Unit,
    onReject: (PostContent, String) -> Unit
) {
    Column {
        StepProgressIndicator(currentStep, totalSteps)
        CurrentStepDetails(step)

        when (progress.state) {
            APPROVAL_NEEDED -> ContentApprovalDialog(...)
            CREATING_DESIGNS -> CanvaProgressView(...)
            COMPLETED -> DownloadResultsView(...)
        }
    }
}
```

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Real-time progress via SSE
- [ ] Content approval dialog with "Mi piace" / "Modifica" / "Rigenera"
- [ ] Design preview
- [ ] Download results
- [ ] Week → Month → Year expansion prompts

---

### DEV-289: Browser MCP Connection UI

**Priority:** MEDIUM | **Effort:** 1.5h | **Status:** NOT STARTED

**Problem:**
User needs to connect Browser MCP extension and grant permissions.

**Solution:**
Create setup wizard for Browser MCP connection.

**Agent Assignment:** @livia (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** DEV-285 (Canva Browser Automation)

**Change Classification:** ADDITIVE

**Files:**
- `desktopApp/src/desktopMain/kotlin/ui/setup/BrowserMCPSetupScreen.kt`
- `desktopApp/src/desktopMain/kotlin/ui/setup/CanvaLoginDialog.kt`
- `shared/src/commonMain/kotlin/viewmodel/MCPSetupViewModel.kt`

**Setup Flow:**
1. Check if Browser MCP extension installed
2. Guide user to Chrome Web Store if not
3. Request connection permission
4. Test connection with ping
5. Store connection config

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Extension detection
- [ ] Setup wizard with clear instructions
- [ ] Connection test
- [ ] Credential storage (secure, in OS keychain)

---

### DEV-290: WSL2/VM Sandbox Integration

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Need OS-level isolation for security when running automated browser.

**Solution:**
Create platform-specific sandbox implementations.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** DEV-285 (Canva Browser Automation)

**Change Classification:** ADDITIVE

**Files:**
- `desktopApp/src/jvmMain/kotlin/sandbox/SandboxManager.kt`
- `desktopApp/src/jvmMain/kotlin/sandbox/MacOSVMSandbox.kt` - VZVirtualMachine
- `desktopApp/src/jvmMain/kotlin/sandbox/WindowsWSL2Sandbox.kt` - WSL2
- `desktopApp/src/jvmMain/kotlin/sandbox/LinuxDockerSandbox.kt` - Docker

**Platform Detection:**

```kotlin
object SandboxManager {
    fun createSandbox(): Sandbox = when {
        isMacOS() -> MacOSVMSandbox()      // Apple Virtualization Framework
        isWindows() -> WindowsWSL2Sandbox() // Works on Home edition!
        isLinux() -> LinuxDockerSandbox()   // Docker + seccomp
        else -> NoOpSandbox()               // Fallback
    }
}
```

**Key Insight:**
> WSL2 works on Windows Home too! Microsoft added WSL2 support to Home edition.
> No need for Hyper-V or Pro/Enterprise for OS-level isolation.

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] macOS VM sandbox works (VZVirtualMachine)
- [ ] Windows WSL2 sandbox works (including Home edition)
- [ ] Linux Docker sandbox works
- [ ] Fallback for unsupported platforms

---

### DEV-291: Folder Permission System

**Priority:** HIGH | **Effort:** 1.5h | **Status:** NOT STARTED

**Problem:**
Need explicit user permission for folder access (like Claude Cowork).

**Solution:**
Create permission dialog and persistence system.

**Agent Assignment:** @livia (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** DEV-287 (Project Selector UI)

**Change Classification:** ADDITIVE

**Files:**
- `desktopApp/src/desktopMain/kotlin/permissions/FolderPermissionManager.kt`
- `desktopApp/src/desktopMain/kotlin/ui/permissions/FolderPermissionDialog.kt`
- `shared/src/commonMain/kotlin/models/FolderPermission.kt`

**Permission Model:**

```kotlin
data class FolderPermission(
    val path: Path,
    val canRead: Boolean,
    val canWrite: Boolean,
    val isPersistent: Boolean,  // "Always Allow" vs one-time
    val grantedAt: Instant
)
```

**UI Flow:**
1. User selects folder
2. Permission dialog appears: "coPratiko vuole accedere a [folder]. Consentire?"
3. Options: "Consenti una volta" / "Consenti sempre" / "Nega"
4. Permission stored securely

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Permission dialog before folder access
- [ ] "Always Allow" option (Consenti sempre)
- [ ] Permission revocation UI
- [ ] Secure permission storage
- [ ] Italian language UI

---

## Phase 3: Frontend Next.js (~8h)

**Location:** `/Users/micky/PycharmProjects/PratikoAi-BE/web`

---

### DEV-294: Social Campaign Wizard UI

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Web app needs UI for the guided social campaign creation workflow.

**Solution:**
Create multi-step wizard for social campaign generation in the coPratiko web interface.

**Agent Assignment:** @livia (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** DEV-295 (Campaign Preview UI)

**Change Classification:** ADDITIVE

**Files:**
- `src/components/features/campaign/CampaignWizard.tsx`
- `src/components/features/campaign/SocialNetworkSelector.tsx`
- `src/components/features/campaign/BrandAssetsUploader.tsx`
- `src/components/features/campaign/TopicSelector.tsx`
- `src/lib/hooks/useCampaignWizard.ts`

**UX Flow:**
```
Step 1: Select Social Networks (Instagram, Facebook, LinkedIn, Twitter)
Step 2: Upload Brand Assets (logo, colors, guidelines, fonts)
Step 3: Select Topics (Scadenze fiscali default + custom topics via Brave Search)
```

**UI Components:**

```tsx
// Step 1: Network Selection
<SocialNetworkSelector
  options={['instagram', 'facebook', 'linkedin', 'twitter']}
  selected={selectedNetworks}
  onSelect={setSelectedNetworks}
/>

// Step 2: Brand Assets
<BrandAssetsUploader
  onUpload={handleBrandAssets}
  acceptedTypes={['png', 'jpg', 'pdf', 'json']}
/>

// Step 3: Topic Selection
<TopicSelector
  defaultTopics={['Scadenze fiscali']}
  customTopics={customTopics}
  onAddCustom={handleAddCustomTopic}  // Triggers Brave Search
/>
```

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Multi-step wizard with progress indicator
- [ ] Social network selection (multi-select)
- [ ] Brand assets drag-drop upload
- [ ] Topic selection with custom topic support
- [ ] Italian language UI
- [ ] Responsive design

---

### DEV-295: Campaign Preview & Approval UI

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Users need to preview generated posts and approve/reject/modify them before Canva design creation.

**Solution:**
Create preview UI with approval workflow and feedback incorporation.

**Agent Assignment:** @livia (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-294 (Campaign Wizard UI), DEV-284 (Social Campaign Generator)
- **Unlocks:** DEV-296 (Campaign Progress UI)

**Change Classification:** ADDITIVE

**Files:**
- `src/components/features/campaign/WeekPreview.tsx`
- `src/components/features/campaign/PostCard.tsx`
- `src/components/features/campaign/PostApprovalDialog.tsx`
- `src/components/features/campaign/FeedbackInput.tsx`
- `src/lib/hooks/usePostApproval.ts`

**UX Flow:**
```
Step 4: Generate Week 1 Preview (5 posts, Mon-Fri)
Step 5: Iterate Until Satisfied ("Mi piace" / "Modifica" / "Rigenera")
Step 6: Propose Month Expansion
```

**UI Components:**

```tsx
// Week Preview Grid
<WeekPreview week={1} posts={generatedPosts}>
  {posts.map(post => (
    <PostCard
      key={post.id}
      post={post}
      onApprove={() => handleApprove(post)}
      onModify={() => openFeedbackDialog(post)}
      onRegenerate={() => handleRegenerate(post)}
    />
  ))}
</WeekPreview>

// Approval Actions
<PostApprovalDialog>
  <Button onClick={onApprove}>👍 Mi piace</Button>
  <Button onClick={onModify}>✏️ Modifica</Button>
  <Button onClick={onRegenerate}>🔄 Rigenera</Button>
</PostApprovalDialog>

// Month Expansion Prompt
<ExpansionPrompt
  message="Ti è piaciuta la settimana 1! Vuoi generare il resto del mese?"
  onAccept={generateMonth}
  onDecline={finishCampaign}
/>
```

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Week preview with 5 post cards (Mon-Fri)
- [ ] Approval actions: Mi piace / Modifica / Rigenera
- [ ] Feedback input for modifications
- [ ] Month/Year expansion prompts
- [ ] Italian language UI

---

### DEV-296: Campaign Progress & Results UI

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Users need to see real-time progress during Canva design creation and download results.

**Solution:**
Create progress tracking UI with SSE updates and download functionality.

**Agent Assignment:** @livia (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-295 (Campaign Preview UI), DEV-286 (Workflow Orchestrator)
- **Unlocks:** None (end of chain)

**Change Classification:** ADDITIVE

**Files:**
- `src/components/features/campaign/CampaignProgress.tsx`
- `src/components/features/campaign/DesignPreview.tsx`
- `src/components/features/campaign/DownloadResults.tsx`
- `src/lib/hooks/useCampaignProgress.ts`
- `src/lib/api/campaignApi.ts`

**UI Components:**

```tsx
// Progress Tracking
<CampaignProgress>
  <StepIndicator current={currentStep} total={totalSteps} />
  <ProgressBar value={progress} />
  <CurrentAction>{currentAction}</CurrentAction>
</CampaignProgress>

// Design Preview (from Canva)
<DesignPreview
  designs={completedDesigns}
  onPreview={openPreview}
/>

// Download Results
<DownloadResults
  designs={allDesigns}
  onDownloadAll={downloadZip}
  onDownloadSingle={downloadDesign}
/>
```

**Real-time Updates:**
- SSE connection for progress updates
- Step-by-step status (Connecting to Canva → Creating design 1/5 → ...)
- Error handling with retry options

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Real-time progress via SSE
- [ ] Step indicator and progress bar
- [ ] Design previews as they complete
- [ ] Download all as ZIP
- [ ] Download individual designs
- [ ] Error recovery UI
- [ ] Italian language UI

---

## Task Dependency Map

```
DEV-280 (LLM Router)
    │
    └──┬─ DEV-284 (Campaign Generator) ─────────────────┐
       │                                                 │
DEV-281 (MCP Integration)                                │
    │                                                    │
    └── DEV-285 (Canva Automation) ─────────────────────┤
                                                         │
DEV-282 (Scadenzario) ──── DEV-284                      │
                                                         │
DEV-283 (Brave Search) ─── DEV-284                      │
                                                         ▼
DEV-293 (Prompts) ─────────── DEV-284 ─────────▶ DEV-286 (Workflow Orchestrator)
                                                         │
                                                         ▼
DEV-291 (Folder Permissions) ── DEV-287 (Project UI) ── DEV-288 (Progress UI)
                                                         │
DEV-289 (MCP Setup UI) ─────────────────────────────────┘
                                                         │
DEV-290 (Sandbox) ──────────────────────────────────────┘

DEV-294 (Wizard UI) ── DEV-295 (Preview UI) ── DEV-296 (Results UI)
                              │
                              └── DEV-284 (needs content)

DEV-292 (Error Handling) ─── DEV-285, DEV-286
```

---

## Implementation Order

```
Week 1 (Foundation):
  DEV-280 (LLM Router) → DEV-293 (Prompts) → DEV-281 (MCP)
  DEV-282 (Scadenzario) parallel

Week 2 (Core Services):
  DEV-283 (Brave Search) → DEV-284 (Campaign Generator)
  DEV-291 (Folder Permissions) parallel

Week 3 (Automation):
  DEV-285 (Canva Automation) → DEV-286 (Workflow)
  DEV-290 (Sandbox) parallel

Week 4 (Desktop UI):
  DEV-287 (Project UI) → DEV-288 (Progress UI)
  DEV-289 (MCP Setup UI)

Week 5 (Frontend + Polish):
  DEV-294 (Wizard UI) → DEV-295 (Preview UI) → DEV-296 (Results UI)
  DEV-292 (Error Handling)
```

---

## Cost Model

**Target: $5-25/month per user**

| Task | Model | Cost/1M tokens | Usage |
|------|-------|----------------|-------|
| Document analysis | Haiku | $1/$5 | ~100k tokens/campaign |
| Brand extraction | Haiku | $1/$5 | ~50k tokens (cached) |
| Web research | Haiku | $1/$5 | ~200k tokens |
| Canva commands | Haiku | $1/$5 | ~50k tokens |
| Content generation | Sonnet | $3/$15 | ~500k tokens |
| Complex reasoning | Opus | $5/$25 | ~50k tokens (fallback) |

**With prompt caching:** 90% savings on scadenzario + brand context

---

## Verification

After each task:
1. `uv run pytest` - all tests pass
2. `./scripts/check_code.sh` - pre-commit hooks pass
3. APIs: Test with curl/httpie against local server
4. Desktop: Build and run locally
5. Frontend: `npm run dev` and manual test

---

## Related Documents

- **Old Tax Workflow Plan:** Moved to `docs/tasks/PRATIKO_1.9_BACKLOG.md`
- **v2.0 Roadmap:** `docs/tasks/PRATIKO_2.0.md` (Client Database, Matching Engine)
