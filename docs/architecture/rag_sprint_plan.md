# RAG Implementation Sprint Plan

This prioritized sprint plan focuses on the most critical RAG pipeline components based on the audit results. Each section represents a weekly sprint with specific focus areas.

## Section A: High Impact (Week 1) — Core Pipeline

### Step 20: Golden fast-path eligible? (RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe)
**Status**: 🔌 Not wired  
**Priority**: Critical - Pre-LLM fast-path for known answers

**TDD Checklist**:
- [ ] Connect existing implementation to RAG workflow
- [ ] Add integration tests for end-to-end flow  
- [ ] Verify error handling and edge cases
- [ ] Test FAQ matching and confidence scoring
- [ ] Implement semantic matching fallbacks

**Links**: [Step 20 Doc](steps/STEP-20-RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe.md)

---

### Step 39: KBPreFetch (RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost)  
**Status**: ❌ Missing  
**Priority**: Critical - Knowledge retrieval foundation

**TDD Checklist**:
- [ ] Create process implementation for KBPreFetch
- [ ] Add unit tests covering happy path and edge cases
- [ ] Wire into the RAG pipeline flow
- [ ] Implement BM25 + vector hybrid search
- [ ] Add recency boost algorithms
- [ ] Test knowledge base integration

**Links**: [Step 39 Doc](steps/STEP-39-RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost.md)

---

### Step 59: CheckCache (RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response)
**Status**: 🔌 Not wired  
**Priority**: High - Performance optimization

**TDD Checklist**:
- [ ] Connect existing implementation to RAG workflow
- [ ] Add integration tests for end-to-end flow
- [ ] Verify error handling and edge cases  
- [ ] Add cache invalidation and TTL tests
- [ ] Test epoch-based cache versioning

**Links**: [Step 59 Doc](steps/STEP-59-RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response.md)

---

### Step 79: Tool type? (RAG.routing.tool.type)
**Status**: ❌ Missing  
**Priority**: Critical - Tool routing decision point

**TDD Checklist**:
- [ ] Create decision implementation for ToolType
- [ ] Add unit tests covering happy path and edge cases
- [ ] Wire into the RAG pipeline flow
- [ ] Implement tool classification logic
- [ ] Test routing to KB/CCNL/DocIngest/FAQ tools

**Links**: [Step 79 Doc](steps/STEP-79-RAG.routing.tool.type.md)

---

### Step 82: DocIngest pipeline (RAG.preflight.documentingesttool.process.process.attachments)
**Status**: ❌ Missing  
**Priority**: High - Document processing capability

**TDD Checklist**:
- [ ] Create process implementation for DocIngest  
- [ ] Add unit tests covering happy path and edge cases
- [ ] Wire into the RAG pipeline flow
- [ ] Test document parsing and validation
- [ ] Implement security sanitization
- [ ] Test OCR and structured extraction

**Links**: [Step 82 Doc](steps/STEP-82-RAG.preflight.documentingesttool.process.process.attachments.md)

---

### Step 64: LLMCall (RAG.providers.llmprovider.chat.completion.make.api.call)
**Status**: 🔌 Not wired  
**Priority**: Critical - Core LLM integration

**TDD Checklist**:
- [ ] Connect existing implementation to RAG workflow
- [ ] Add integration tests for end-to-end flow
- [ ] Verify error handling and edge cases
- [ ] Test failover and retry mechanisms
- [ ] Implement cost tracking and limits

**Links**: [Step 64 Doc](steps/STEP-64-RAG.providers.llmprovider.chat.completion.make.api.call.md)

## Section B: Core Retrieval (Week 2)

### Knowledge Base Integration
- **Step 27**: KBDelta - Knowledge freshness detection
- **Step 26**: KBContextCheck - KB context validation  
- **Step 40**: BuildContext - Context merging and preparation
- **Step 41**: SelectPrompt - Dynamic prompt selection

**Focus**: Complete the knowledge retrieval pipeline, ensuring fresh context delivery and optimal prompting.

## Section C: Hardening (Week 3)  

### Reliability & Observability
- **Step 72**: FailoverProvider - Provider failover logic
- **Step 73**: RetrySame - Retry mechanisms
- **Step 108**: WriteSSE - Streaming implementation
- **Step 111**: CollectMetrics - Usage tracking
- **Step 113**: FeedbackUI - Expert feedback collection

**Focus**: Production-ready reliability, monitoring, and continuous improvement mechanisms.

## Implementation Notes

**Week 1 Success Criteria**:
- [ ] Golden fast-path reduces LLM calls by >30%
- [ ] KB retrieval returns relevant context in <200ms
- [ ] Cache hit rate >60% for common queries
- [ ] Tool routing accuracy >95%
- [ ] Document ingestion processes 3+ file types
- [ ] LLM integration handles all provider types

**Risk Mitigation**:
- Implement feature flags for each major component
- Gradual rollout with A/B testing
- Comprehensive integration test coverage
- Performance benchmarks for each step

**Dependencies**:
- Redis cache infrastructure
- Vector database (Pinecone) connectivity  
- Document parsing libraries
- LLM provider APIs (Anthropic, OpenAI)

## Next Steps After Sprint Plan

1. Run `python scripts/rag_issue_prompter.py --create --dry-run` to preview issues
2. Assign engineering resources to each week
3. Set up monitoring dashboards for each step
4. Schedule weekly reviews against conformance dashboard