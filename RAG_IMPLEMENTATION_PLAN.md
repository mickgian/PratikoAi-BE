# RAG Implementation Strategy

## Overview
We'll implement the 135 RAG steps using a phased approach, starting with simple steps and progressing to more complex ones. Each step will follow TDD methodology as specified in the GitHub issues.

## Phase 1: Foundation Steps (Days 1-2)
**Quick wins - Simple message/prompt manipulation**

### Batch 1: Prompting Steps (46, 47, 44, 45) ✅ COMPLETED
- **Step 46**: Replace system message - Simple list manipulation ✅
- **Step 47**: Insert system message - Simple list insertion ✅
- **Step 44**: Use default SYSTEM_PROMPT - Return constant ✅
- **Step 45**: System message exists? - Check message type ✅

### Batch 2: Basic Platform Steps (10, 103, 110) ✅ COMPLETED
- **Step 10**: Log PII anonymization - GDPR compliance audit trail ✅
- **Step 103**: Log completion - RAG processing metrics and monitoring ✅
- **Step 110**: Send DONE frame - Multi-format streaming termination ✅

### Batch 3: Simple Decisions (3, 9, 13) ✅ COMPLETED
- **Step 3**: Request valid? - Multi-level validation (auth, content-type, method, body) ✅
- **Step 9**: PII detected? - Confidence-based PII detection with threshold filtering ✅
- **Step 13**: User message exists? - Message analysis with role-based detection ✅

## Phase 2: Classification & Metrics (Days 3-4)
**Medium complexity - Service integration**

### Batch 4: Classification Flow (31, 32, 33, 42) ✅ COMPLETED
- **Step 31**: Rule-based classification - Call DomainActionClassifier ✅
- **Step 32**: Calculate scores - Italian keyword matching ✅
- **Step 33**: Confidence check - Threshold comparison ✅
- **Step 42**: Classification confidence - Check existence & threshold ✅

### Batch 5: Metrics & Tracking (34, 74, 111) ✅ COMPLETED
- **Step 34**: Track classification metrics - Metrics service call ✅
- **Step 74**: Track API usage - Usage tracker call ✅
- **Step 111**: Collect usage metrics - Aggregate metrics ✅

## Phase 3: Caching System (Days 5-6)
**Complex - Redis integration**

### Batch 6: Cache Operations (59, 61, 62, 63, 65, 66, 68) ✅ COMPLETED
- **Step 59**: Check cache - Initialize cache check ✅
- **Step 61**: Generate hash - Create cache key ✅
- **Step 62**: Cache hit? - Check Redis ✅
- **Step 63**: Track cache hit - Metrics update ✅
- **Step 65**: Log cache hit - Logging ✅
- **Step 66**: Return cached - Return response ✅
- **Step 68**: Store in Redis - Cache write ✅

## Phase 4: Provider Routing (Days 7-9)
**Most complex - Factory pattern extraction**

### Batch 7: Provider Selection (48-58) ✅ COMPLETED
- **Step 48**: Select LLM provider - Entry point ✅
- **Step 49**: Apply routing strategy - Strategy pattern ✅
- **Step 50**: Routing strategy? - Decision node ✅
- **Step 51**: Select cheapest provider - Cost optimization ✅
- **Step 52**: Select best provider - Quality optimization ✅
- **Step 53**: Balance cost and quality - Hybrid strategy ✅
- **Step 54**: Use primary provider - Default strategy ✅
- **Step 55**: Estimate cost - Cost calculation ✅
- **Step 56**: Cost check - Budget validation ✅
- **Step 57**: Create provider - Instantiation ✅
- **Step 58**: Cheaper provider fallback - Error recovery ✅

## Phase 5: Platform & Request Handling (Days 10-12)
**Core platform operations**

### Batch 8: Request Processing (1-2, 4-8)
- **Step 1**: Validate request and authenticate - Entry point security ✅
- **Step 2**: User submits query via POST /api/v1/chat - Request handling ✅
- **Step 4**: Record processing log - GDPR compliance ✅
- **Step 5**: Return 400 bad request - Error handling ✅
- **Step 6**: Privacy anonymize requests enabled - Privacy check ✅
- **Step 7**: Anonymize PII - Text anonymization ✅
- **Step 8**: Get response initialize workflow - LangGraph setup ✅

### Batch 9: Message Processing (11-12, 15) ✅ COMPLETED
- **Step 11**: Convert to message objects - Format standardization ✅
- **Step 12**: Extract user message - Message parsing ✅
- **Step 15**: Continue without classification - Workflow bypass ✅

## Phase 6: Classification & LLM Operations (Days 13-15)
**Advanced classification and LLM handling**

### Batch 10: Classification Logic (35-41, 43) ✅ COMPLETED
- **Step 35**: LLM fallback - Use LLM classification ✅
- **Step 36**: LLM better than rule-based - Quality check ✅
- **Step 37**: Use LLM classification - Apply LLM results ✅
- **Step 38**: Use rule-based classification - Apply rule results ✅
- **Step 39**: KB pre-fetch - Knowledge base retrieval ✅
- **Step 40**: Context builder merge - Merge facts and KB docs ✅
- **Step 41**: Select prompt - System prompt selection based on classification ✅
- **Step 43**: Domain-specific prompt - Generate Italian professional domain prompts ✅

### Batch 11: LLM Processing (67, 69-73, 75-78) ✅ COMPLETED
- **Step 67**: LLM call successful - Success validation ✅
- **Step 69**: Another attempt allowed - Retry check ✅
- **Step 70**: Prod environment and last retry - Final attempt ✅
- **Step 71**: Return 500 error - Critical error ✅
- **Step 72**: Get failover provider - Provider fallback ✅
- **Step 73**: Retry same provider - Retry logic ✅
- **Step 75**: Response has tool calls - Tool detection ✅
- **Step 76**: Convert to AI message with tool calls - Format conversion ✅
- **Step 77**: Convert to simple AI message - Simple format ✅
- **Step 78**: Execute tools - Tool execution ✅

## Phase 7: Document Processing (Days 16-18)
**Domain-specific parsers**

### Batch 12: Document Validation (17, 19, 21-22, 84-86) ✅ COMPLETED
- **Step 17**: Compute SHA-256 per attachment - File fingerprinting ✅
- **Step 19**: Attachments present - Document check ✅
- **Step 21**: Quick extract type sniff and key fields - Pre-processing ✅
- **Step 22**: Doc dependent or refers to doc - Document relationship ✅
- **Step 84**: Check files and limits - Validation ✅
- **Step 85**: Valid attachments - Validation result ✅
- **Step 86**: Return tool error invalid file - Error handling ✅

### Batch 13: Document Processing Pipeline (87-97) ✅ COMPLETED
- **Step 87**: Strip macros and JS - Security sanitization ✅
- **Step 88**: Detect document type - Type classification ✅
- **Step 89**: Document type decision - Routing ✅
- **Step 90**: XSD validation - Fattura processing ✅
- **Step 91**: Layout-aware OCR - F24 processing ✅
- **Step 92**: Contract parsing - Contract processing ✅
- **Step 93**: Payslip parsing - Payslip processing ✅
- **Step 94**: Parse with layout - Generic OCR ✅
- **Step 95**: Extract structured fields - Field extraction ✅
- **Step 96**: Encrypted TTL storage - Blob storage ✅
- **Step 97**: Ledger entry - Provenance logging ✅

## Phase 8: Facts & Knowledge Management (Days 19-21)
**Knowledge extraction and management**

### Batch 14: Facts Processing (14, 16, 18, 29, 98) ✅ COMPLETED
- **Step 14**: Extract atomic facts - AtomicFactsExtractor for Italian query fact extraction ✅
- **Step 16**: Normalize dates amounts rates - Validation orchestrator for fact canonicalization ✅
- **Step 17**: (Batch 12 routing fix) - Fixed routing from Step 19 to Step 18 per Mermaid diagram ✅
- **Step 18**: Hash from canonical facts - SHA256 query signature computation ✅
- **Step 29**: Merge facts and KB docs - ContextBuilderMerge for golden+KB context integration ✅
- **Step 98**: Convert to tool message facts and spans - ToolMessage conversion for LLM tool caller ✅

### Batch 15: Knowledge Operations (80-83)
- **Step 80**: Search KB on demand - Knowledge search
- **Step 81**: Query labor agreements - CCNL queries
- **Step 82**: Query golden set - FAQ search
- **Step 83**: Query FAQ - FAQ retrieval

## Phase 9: Golden Set & FAQ Management (Days 22-24)
**FAQ and golden answer management**

### Batch 16: Golden Set Matching (23-28, 60)
- **Step 23**: Require doc ingest first - Planning hint
- **Step 24**: Match by signature or semantic - Golden matching
- **Step 25**: Score at least 0.90 - High confidence match
- **Step 26**: Serve golden answer with citations - Golden response
- **Step 27**: Return chat response - Response delivery
- **Step 28**: Return to chat node for final response - Workflow return
- **Step 60**: Resolve epochs - Timestamp resolution

### Batch 17: Golden Set Updates (117, 127-131, 135)
- **Step 117**: Post API v1 FAQ feedback - Feedback endpoint
- **Step 127**: Propose candidate from expert feedback - Golden candidate
- **Step 128**: Auto threshold met or manual approval - Approval logic
- **Step 129**: Publish or update versioned entry - Golden publishing
- **Step 130**: Invalidate FAQ by ID or signature - Cache invalidation
- **Step 131**: Update embeddings - Vector index update
- **Step 135**: Auto rule eval new or obsolete candidates - Rule evaluation

## Phase 10: Streaming & Response Handling (Days 25-26)
**Real-time response delivery**

### Batch 18: Streaming Operations (101-102, 104-109, 112)
- **Step 101**: Return to chat node for final response - Response routing
- **Step 102**: Convert to dict - Format conversion
- **Step 104**: Streaming requested - Stream detection
- **Step 105**: Setup SSE - Server-sent events
- **Step 106**: Create async generator - Stream generator
- **Step 107**: Prevent double iteration - Stream protection
- **Step 108**: Write SSE format chunks - Chunk formatting
- **Step 109**: Send chunks - Stream delivery
- **Step 112**: Return response to user - Final response

### Batch 19: Cache Management (64, 125)
- **Step 64**: Cache miss - Cache miss handling
- **Step 125**: Cache feedback 1h TTL - Feedback caching

## Phase 11: Feedback & Learning System (Days 27-28)
**Expert feedback and continuous learning**

### Batch 20: Feedback Collection (113-116, 118-124)
- **Step 113**: Show options correct incomplete wrong - Feedback UI
- **Step 114**: User provides feedback - Feedback input
- **Step 115**: No feedback - Feedback timeout
- **Step 116**: Feedback type selected - Feedback classification
- **Step 118**: Post API v1 knowledge feedback - Knowledge feedback
- **Step 119**: Collect feedback - Feedback aggregation
- **Step 120**: Validate expert credentials - Expert validation
- **Step 121**: Trust score at least 0.7 - Quality threshold
- **Step 122**: Feedback rejected - Rejection handling
- **Step 123**: Create expert feedback record - Record creation
- **Step 124**: Update expert metrics - Metrics update

## Phase 12: Platform Integration & Advanced Features (Days 29-30)
**Final integration and advanced capabilities**

### Batch 21: Advanced Processing (20, 30, 79, 99-100, 126, 132-134)
- **Step 20**: Continue processing - Workflow continuation
- **Step 30**: Return ChatResponse - Response formatting
- **Step 79**: Return to tool caller - Tool response
- **Step 99**: Return to tool caller - Tool completion
- **Step 100**: Perform calculations - CCNL calculations
- **Step 126**: Determine action - Action routing
- **Step 132**: RSS monitor - Content monitoring
- **Step 133**: Fetch and parse sources - Source processing
- **Step 134**: Extract text and metadata - Content extraction

## Implementation Process per Step

1. **Pick GitHub Issue** (e.g., #46)
2. **Copy Claude Code Instructions** from issue
3. **TDD Workflow**:
   - Write unit tests first
   - Write integration tests
   - Implement orchestrator function
   - Wire into workflow
4. **Validate**:
   - Run audit tool
   - Check alignment
   - Run test suite

## Priority Rationale

1. **Start Simple**: Steps 46/47 are pure data manipulation
2. **Build Foundation**: Logging and basic checks establish patterns
3. **Add Complexity Gradually**: Classification → Caching → Providers
4. **High-Impact First**: Provider routing affects entire system
5. **Domain-Specific Last**: Document parsers are isolated

## Success Metrics

- All 135 orchestrator functions implemented
- 100% test coverage per step
- Audit tool shows full alignment
- Integration tests pass
- Performance benchmarks met

## Current Status

**✅ COMPLETED:**
- Batch 1: Prompting Steps (46, 47, 44, 45) - Full TDD implementation with comprehensive tests
- Batch 2: Basic Platform Steps (10, 103, 110) - Real orchestrator logic with audit trails
- Batch 3: Simple Decisions (3, 9, 13) - Advanced decision logic with validation, PII detection, and message analysis
- Batch 4: Classification Flow (31, 32, 33, 42) - Complete classification pipeline with Italian domain/action detection
  - ✅ **Step 31**: Async rule-based classification with DomainActionClassifier integration (10 tests)
  - ✅ **Step 32**: Italian keyword scoring with confidence detection (10 tests)
  - ✅ **Step 33**: Configurable confidence threshold validation (11 tests)
  - ✅ **Step 42**: Classification existence + 0.6 confidence check (11 tests)
  - ✅ **Total**: 42 comprehensive tests, 100% pass rate, full async orchestration
- Batch 5: Metrics & Tracking (34, 74, 111) - Complete metrics collection and usage tracking
  - ✅ **Step 34**: Async classification metrics tracking with monitoring infrastructure (10 tests)
  - ✅ **Step 74**: API usage tracking with LLM token/cost monitoring and format compatibility (10 tests)
  - ✅ **Step 111**: Usage metrics collection with user/system aggregation and environment-aware reporting (10 tests)
  - ✅ **Total**: 30 comprehensive tests, 100% pass rate, full metrics infrastructure integration
- Batch 6: Cache Operations (59, 61, 62, 63, 65, 66, 68) - Complete Redis-based cache workflow
  - ✅ **Step 59**: Cache check initialization with message processing and hash generation setup (10 tests)
  - ✅ **Step 61**: Composite cache key generation using query signatures, document hashes, epochs, and versions (10 tests)
  - ✅ **Step 62**: Redis cache hit/miss detection with LLMResponse compatibility (10 tests)
  - ✅ **Step 63**: Zero-cost usage tracking for cache hits with UsageTracker integration (10 tests)
  - ✅ **Step 65**: Structured cache event logging with performance metrics and context (10 tests)
  - ✅ **Step 66**: Cached response formatting and return with metadata preservation (10 tests)
  - ✅ **Step 68**: LLM response storage in Redis with TTL, compression, and encryption support (10 tests)
  - ✅ **Total**: 70 comprehensive tests, 100% pass rate, full Redis cache infrastructure with cost optimization
- Batch 7: Provider Selection (48-58) - Complete LLM provider routing and cost optimization workflow
  - ✅ **Step 48**: Provider selection initiation with routing context preparation (7 tests)
  - ✅ **Step 49**: Routing strategy application using LLMFactory integration (10 tests)
  - ✅ **Step 50**: Strategy-based decision routing to provider selection steps (10 tests)
  - ✅ **Step 51**: Cost-optimized provider selection with budget constraints (7 tests)
  - ✅ **Step 52**: Quality-first provider selection for complex queries (3 tests)
  - ✅ **Step 53**: Balanced provider selection optimizing cost and quality (3 tests)
  - ✅ **Step 54**: Primary provider selection with failover capability (3 tests)
  - ✅ **Step 55**: Token-based cost estimation with provider pricing (8 tests)
  - ✅ **Step 56**: Budget validation and routing decision logic (8 tests)
  - ✅ **Step 57**: Final provider instance creation for processing (8 tests)
  - ✅ **Step 58**: Cheaper provider fallback with cost re-evaluation (8 tests)
  - ✅ **Total**: 85 comprehensive tests, 100% pass rate, full provider routing infrastructure
- Batch 8: Request Processing (1-2, 4-8) - Complete request processing pipeline with authentication, GDPR logging, privacy routing, and LangGraph initialization
  - ✅ **Step 1**: Async request validation with FastAPI auth integration (12 tests)
  - ✅ **Step 2**: Workflow initialization with context building (10 tests)
  - ✅ **Step 4**: GDPR compliance logging with data processing records (10 tests)
  - ✅ **Step 5**: HTTP error handling with status code mapping (12 tests)
  - ✅ **Step 6**: Privacy decision routing with anonymization workflow (3 tests)
  - ✅ **Step 7**: PII anonymization with text processing (10 tests)
  - ✅ **Step 8**: LangGraph workflow initialization with agent setup (8 tests)
  - ✅ **Total**: 65 comprehensive tests, 100% pass rate, full request processing infrastructure
- Batch 9: Message Processing (11-12, 15) - Complete message format standardization, user query extraction, and classification bypass workflow
  - ✅ **Step 11**: Message format standardization with dict/LangChain/Message object conversion (11 tests)
  - ✅ **Step 12**: User query extraction from conversation history with preprocessing (12 tests)
  - ✅ **Step 15**: Classification bypass with default prompting and query analysis (12 tests)
  - ✅ **Total**: 35 comprehensive tests, 100% pass rate, full message processing infrastructure
- Batch 10: Classification Logic (35-41, 43) - Complete advanced classification with LLM fallback and domain-specific prompts
  - ✅ **Step 35**: Async LLM fallback classification with DomainActionClassifier integration (10 tests)
  - ✅ **Step 36**: LLM vs rule-based quality comparison with confidence scoring (10 tests)
  - ✅ **Step 37**: LLM classification application with format standardization (10 tests)
  - ✅ **Step 38**: Rule-based classification application with direct routing (10 tests)
  - ✅ **Step 39**: Knowledge base pre-fetch with BM25/vector/recency retrieval (12 tests)
  - ✅ **Step 40**: Context building with facts, KB docs, and document integration (10 tests)
  - ✅ **Step 41**: System prompt selection based on classification confidence (11 tests)
  - ✅ **Step 43**: Domain-specific Italian professional prompt generation (13 tests)
  - ✅ **Total**: 86 comprehensive tests, 100% pass rate, full classification infrastructure
- Batch 11: LLM Processing (67, 69-73, 75-78) - Complete LLM call handling with retry, failover, and tool execution
  - ✅ **Step 67**: LLM call success validation with response processing (8 tests)
  - ✅ **Step 69**: Retry attempt validation with max_retries checking (10 tests)
  - ✅ **Step 70**: Production environment and last retry decision routing (13 tests)
  - ✅ **Step 71**: HTTP 500 error handling with exhausted retries (10 tests)
  - ✅ **Step 72**: Failover provider selection with 2x cost limit (10 tests)
  - ✅ **Step 73**: Same provider retry with attempt increment (10 tests)
  - ✅ **Step 75**: Tool calls detection in LLM response (10 tests)
  - ✅ **Step 76**: AIMessage creation with tool_calls attachment (9 tests)
  - ✅ **Step 77**: Simple AIMessage creation without tools (9 tests)
  - ✅ **Step 78**: Tool execution with ToolMessage generation (9 tests)
  - ✅ **Total**: 98 comprehensive tests, 94/98 pass when run together, full LLM processing infrastructure
- Batch 12: Document Validation (17, 19, 21-22, 84-86) - Complete attachment validation and document pre-processing pipeline
  - ✅ **Step 17**: SHA-256 attachment fingerprinting with hash computation and deduplication detection (11 tests)
  - ✅ **Step 19**: Attachment presence check with validation routing decision (10 tests)
  - ✅ **Step 21**: Document pre-ingest with MIME type detection and Italian category hints (9 tests)
  - ✅ **Step 22**: Document dependency detection with keyword-based query analysis (9 tests)
  - ✅ **Step 84**: Attachment validation with size/count/MIME type checks against DOCUMENT_CONFIG (14 tests)
  - ✅ **Step 85**: Validation result decision routing to processing or error (10 tests)
  - ✅ **Step 86**: Tool error creation with ToolMessage format for invalid attachments (11 tests)
  - ✅ **Total**: 74 comprehensive tests, 100% pass rate, full document validation infrastructure
- Batch 13: Document Processing Pipeline (87-97) - Complete Italian document parsing with security, classification, and provenance
  - ✅ **Step 87**: Document security sanitization with macro/JS stripping and malware detection (7 tests)
  - ✅ **Step 88**: Document type classification detecting fattura/F24/contract/payslip/generic (7 tests)
  - ✅ **Step 89**: Document type routing decision for parser selection (7 tests)
  - ✅ **Step 90**: Fattura Elettronica XML parser with XSD namespace validation (7 tests)
  - ✅ **Step 91**: F24 tax form parser with layout-aware OCR and regex extraction (7 tests)
  - ✅ **Step 92**: Contract parser with type detection (compravendita/locazione/appalto/servizi/lavoro) (7 tests)
  - ✅ **Step 93**: Payslip parser extracting employee and salary data (7 tests)
  - ✅ **Step 94**: Generic OCR parser with layout-aware text extraction fallback (7 tests)
  - ✅ **Step 95**: Document facts extractor converting parsed fields to atomic facts (8 tests)
  - ✅ **Step 96**: Encrypted blob storage with SHA-256 hashing and 24h TTL (7 tests)
  - ✅ **Step 97**: Provenance ledger logging for immutable audit trail (7 tests)
  - ✅ **Total**: 78 comprehensive tests, 100% pass rate, full document processing pipeline
  - ✅ **Critical Fix**: Updated rag_code_graph.py to index AsyncFunctionDef (added 500+ async functions to code index)
- Batch 14: Facts Processing (14, 16, 17-fix, 18, 29, 98) - Complete atomic facts extraction, canonicalization, query signature, and context merging
  - ✅ **Step 14**: Atomic facts extraction for Italian queries with monetary amounts, dates, legal entities, professional categories, geographic info (11 tests)
  - ✅ **Step 16**: Fact canonicalization validation ensuring proper normalization from Step 14 (10 tests)
  - ✅ **Step 17**: (Routing fix from Batch 12) - Fixed routing from Step 19 to Step 18 per Mermaid diagram (11 tests)
  - ✅ **Step 18**: Query signature generation with deterministic SHA256 hash from canonical facts for caching/deduplication (9 tests)
  - ✅ **Step 29**: Pre-context merge orchestrator combining golden answers with KB deltas using ContextBuilderMerge (9 tests)
  - ✅ **Step 98**: ToolMessage conversion for document facts and provenance, formatted for LLM tool caller (9 tests)
  - ✅ **Total**: 59 comprehensive tests, 100% pass rate, full facts processing infrastructure
  - ✅ **Critical Fix**: Step 17 routing bug fixed (was routing to Step 19 instead of Step 18, now complies with Mermaid)

**Next Target:** Batch 15: Knowledge Operations (80-83)
1. Pick GitHub issues for knowledge search steps
2. Implement on-demand KB search tool
3. Build CCNL labor agreement queries
4. Create golden set FAQ query tool
5. Implement FAQ retrieval functionality

## GitHub Issues Reference

All 135 GitHub issues are available at: https://github.com/mickgian/PratikoAi-BE/issues

Each issue contains:
- Claude Code copy-pasteable instructions
- TDD requirements (unit + integration tests)
- Orchestrator implementation guidance
- Wiring instructions for LangGraph

## Daily Workflow

1. **Morning**: Review batch for the day
2. **Implementation**:
   - Pick issue from current batch
   - Follow TDD process
   - Commit with descriptive message
3. **Testing**: Run full test suite
4. **Integration**: Wire completed steps
5. **Evening**: Update progress tracker

## Progress Tracking

- [✅] Phase 1: Foundation (Steps 3, 9, 10, 13, 44, 45, 46, 47, 103, 110) - **COMPLETED**
  - ✅ **Batch 1**: Steps 44, 45, 46, 47 (Prompting)
  - ✅ **Batch 2**: Steps 10, 103, 110 (Platform)
  - ✅ **Batch 3**: Steps 3, 9, 13 (Simple Decisions)
- [✅] Phase 2: Classification (Steps 31, 32, 33, 34, 42, 74, 111) - **COMPLETED**
  - ✅ **Batch 4**: Steps 31, 32, 33, 42 (Classification Flow) - **COMPLETED**
  - ✅ **Batch 5**: Steps 34, 74, 111 (Metrics & Tracking) - **COMPLETED**
- [✅] Phase 3: Caching (Steps 59, 61, 62, 63, 65, 66, 68) - **COMPLETED**
  - ✅ **Batch 6**: Steps 59, 61, 62, 63, 65, 66, 68 (Cache Operations) - **COMPLETED**
- [✅] Phase 4: Provider Routing (Steps 48-58) - **COMPLETED**
  - ✅ **Batch 7**: Steps 48-58 (Provider Selection) - **COMPLETED**
- [✅] Phase 5: Platform & Request Handling (Steps 1-2, 4-8, 11-12, 15) - **COMPLETED**
  - [✅] **Batch 8**: Steps 1-2, 4-8 (Request Processing) - **COMPLETED**
  - [✅] **Batch 9**: Steps 11-12, 15 (Message Processing) - **COMPLETED**
- [✅] Phase 6: Classification & LLM Operations (Steps 35-41, 43, 67, 69-73, 75-78) - **COMPLETED**
  - [✅] **Batch 10**: Steps 35-41, 43 (Classification Logic) - **COMPLETED**
  - [✅] **Batch 11**: Steps 67, 69-73, 75-78 (LLM Processing) - **COMPLETED**
- [✅] Phase 7: Document Processing (Steps 17, 19, 21-22, 84-97) - **COMPLETED**
  - [✅] **Batch 12**: Steps 17, 19, 21-22, 84-86 (Document Validation) - **COMPLETED**
  - [✅] **Batch 13**: Steps 87-97 (Document Processing Pipeline) - **COMPLETED**
- [🔄] Phase 8: Facts & Knowledge Management (Steps 14, 16, 18, 29, 80-83, 98) - **IN PROGRESS**
  - [✅] **Batch 14**: Steps 14, 16, 17-fix, 18, 29, 98 (Facts Processing) - **COMPLETED**
  - [ ] **Batch 15**: Steps 80-83 (Knowledge Operations)
- [ ] Phase 9: Golden Set & FAQ Management (Steps 23-28, 60, 117, 127-131, 135)
  - [ ] **Batch 16**: Steps 23-28, 60 (Golden Set Matching)
  - [ ] **Batch 17**: Steps 117, 127-131, 135 (Golden Set Updates)
- [ ] Phase 10: Streaming & Response Handling (Steps 64, 101-102, 104-109, 112, 125)
  - [ ] **Batch 18**: Steps 101-102, 104-109, 112 (Streaming Operations)
  - [ ] **Batch 19**: Steps 64, 125 (Cache Management)
- [ ] Phase 11: Feedback & Learning System (Steps 113-116, 118-124)
  - [ ] **Batch 20**: Steps 113-116, 118-124 (Feedback Collection)
- [ ] Phase 12: Platform Integration & Advanced Features (Steps 20, 30, 79, 99-100, 126, 132-134)
  - [ ] **Batch 21**: Steps 20, 30, 79, 99-100, 126, 132-134 (Advanced Processing)

## Tools & Scripts

- **Scaffolder**: `scripts/rag_orchestrator_scaffold.py` (generates stubs)
- **Autowire**: `scripts/rag_autowire_orchestrators.py` (wires to LangGraph)
- **Audit**: `rag_audit_config.yml` (validates alignment)
- **Index**: `.rag_alignment_index.json` (investigation results)