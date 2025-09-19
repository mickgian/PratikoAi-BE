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

### Batch 4: Classification Flow (31, 32, 33, 42)
- **Step 31**: Rule-based classification - Call DomainActionClassifier
- **Step 32**: Calculate scores - Keyword matching
- **Step 33**: Confidence check - Threshold comparison
- **Step 42**: Classification confidence - Check existence & threshold

### Batch 5: Metrics & Tracking (34, 74, 111)
- **Step 34**: Track classification metrics - Metrics service call
- **Step 74**: Track API usage - Usage tracker call
- **Step 111**: Collect usage metrics - Aggregate metrics

## Phase 3: Caching System (Days 5-6)
**Complex - Redis integration**

### Batch 6: Cache Operations (59, 61, 62, 63, 65, 66, 68)
- **Step 59**: Check cache - Initialize cache check
- **Step 61**: Generate hash - Create cache key
- **Step 62**: Cache hit? - Check Redis
- **Step 63**: Track cache hit - Metrics update
- **Step 65**: Log cache hit - Logging
- **Step 66**: Return cached - Return response
- **Step 68**: Store in Redis - Cache write

## Phase 4: Provider Routing (Days 7-9)
**Most complex - Factory pattern extraction**

### Batch 7: Provider Selection (48-58)
- **Step 48**: Select LLM provider - Entry point
- **Step 49**: Apply routing strategy - Strategy pattern
- **Step 50**: Routing strategy? - Decision node
- **Steps 51-54**: Provider strategies - Different selection logic
- **Step 55**: Estimate cost - Cost calculation
- **Step 56**: Cost check - Budget validation
- **Step 57**: Create provider - Instantiation
- **Step 58**: Cheaper provider fallback - Error recovery

## Phase 5: Document Processing (Days 10-12)
**Domain-specific parsers**

### Batch 8: Document Flow (87-97)
- **Step 87**: Sanitize documents - Security
- **Step 88**: Classify document - Type detection
- **Step 89**: Document type? - Router
- **Steps 90-94**: Specific parsers - Type handlers
- **Step 95**: Extract facts - Structured extraction
- **Step 96**: Store blob - Encrypted storage
- **Step 97**: Provenance logging - Audit trail

## Phase 6: Integration & Polish (Days 13-15)
**Wire everything together**

### Batch 9: End-to-end Flow
- Wire orchestrators into LangGraph
- Integration tests
- Performance optimization
- Error handling refinement

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

**Next Target:** Batch 4: Classification Flow (31, 32, 33, 42)
1. Pick GitHub issues for Steps 31, 32, 33, 42
2. Implement domain/action classification orchestrators
3. Integrate with DomainActionClassifier service
4. Build confidence scoring and threshold logic

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
- [⏳] Phase 2: Classification (Steps 31, 32, 33, 34, 42, 74, 111) - **NEXT**
  - ⏳ **Batch 4**: Steps 31, 32, 33, 42 (Classification Flow) - NEXT
  - [ ] **Batch 5**: Steps 34, 74, 111 (Metrics & Tracking)
- [ ] Phase 3: Caching (Steps 59, 61, 62, 63, 65, 66, 68)
- [ ] Phase 4: Providers (Steps 48-58)
- [ ] Phase 5: Documents (Steps 87-97)
- [ ] Phase 6: Integration

## Tools & Scripts

- **Scaffolder**: `scripts/rag_orchestrator_scaffold.py` (generates stubs)
- **Autowire**: `scripts/rag_autowire_orchestrators.py` (wires to LangGraph)
- **Audit**: `rag_audit_config.yml` (validates alignment)
- **Index**: `.rag_alignment_index.json` (investigation results)