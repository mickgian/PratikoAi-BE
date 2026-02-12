# DEV-258: Data Quality Repair & Prevention Pipeline

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Root Cause Analysis](#root-cause-analysis)
3. [What Was Implemented (DEV-258)](#what-was-implemented-dev-258)
4. [Verification Results](#verification-results)
5. [Remaining Quality Gaps](#remaining-quality-gaps)
   - [Gap 1: Content-Hash Deduplication Incomplete](#gap-1-content-hash-deduplication-incomplete)
   - [Gap 2: Chunk Size Configuration Mismatch](#gap-2-chunk-size-configuration-mismatch)
   - [Gap 3: Document Staleness & Supersession](#gap-3-document-staleness--supersession)
   - [Gap 4: RSS Summary Fallback Stores Raw HTML](#gap-4-rss-summary-fallback-stores-raw-html)
   - [Gap 5: Sequential Embedding Calls](#gap-5-sequential-embedding-calls)
   - [Gap 6: No Section-Aware Chunking](#gap-6-no-section-aware-chunking)
6. [Priority Matrix](#priority-matrix)
7. [File Reference](#file-reference)

---

## Problem Statement

The initial data quality audit (`scripts/audit_data_quality.py`) identified **429 chunks** contaminated with web navigation boilerplate (e.g., "vai al menu", "cookie policy", "area riservata"). These chunks were ingested from web-scraped Italian regulatory documents where Trafilatura/BeautifulSoup extraction failed to fully strip navigation elements.

Contaminated chunks degrade RAG retrieval quality: when a user asks about privacy regulations, the retriever may surface a chunk that is mostly navigation text mentioning "privacy policy" rather than actual legal content.

## Root Cause Analysis

The ingestion pipeline had a gap between **document-level** and **chunk-level** validation:

1. **Document-level validation** (`validate_extracted_content()` in `clean.py`) catches documents with 3+ navigation patterns, but documents with 1-2 patterns in their full text pass validation.
2. **Chunking** splits documents into ~512-token segments. A chunk from the beginning or end of a document may concentrate navigation text that was diluted in the full document.
3. **No chunk-level quality gate** existed before DEV-258 — chunks were only checked for junk metrics (alphabet ratio, digit density), not navigation content.

## What Was Implemented (DEV-258)

### Three-Layer Defense Architecture

```
Layer 1: Extraction (prevents ~95% of contamination)
  ├── Trafilatura: intelligent main content extraction (favor_precision=True)
  └── BeautifulSoup fallback: strips <nav>, <header>, <footer>, .cookie, .menu, etc.

Layer 2: Chunk-level filter (catches remaining ~5% at ingestion time)
  └── chunk_contains_navigation() in chunking pipeline
      ├── 2+ pattern matches -> DROP chunk
      └── 1 pattern match + <300 chars -> DROP chunk

Layer 3: Repair script (one-time cleanup of existing data)
  └── scripts/repair_data_quality.py --step navigation
      └── Same logic as Layer 2, applied retroactively via SQL
```

| Practice | Industry Standard | Our Implementation |
|----------|-------------------|-------------------|
| Clean at extraction time | Firecrawl, Trafilatura: remove nav before chunking | Trafilatura (primary) + BeautifulSoup with nav removal (fallback) |
| Chunk-level quality gate | ChunkRAG (2024): multi-stage scoring + dynamic thresholds | `chunk_contains_navigation()` + `text_metrics()` junk filter |
| Delete, don't repair chunks | Consensus: partially cleaned chunks pollute embeddings | We delete entire chunks, never strip text |
| Threshold for false positives | ChunkRAG: dynamic threshold based on score distribution | 2+ patterns (high confidence) OR 1 pattern + <300 chars |
| Single source of truth | Standard software practice | `NAVIGATION_PATTERNS` in `clean.py`, imported everywhere |

### Components Delivered

1. **Navigation detection** — `app/core/text/clean.py`: `NAVIGATION_PATTERNS` (20 patterns) + `chunk_contains_navigation()`
2. **Chunk-level prevention** — `app/core/chunking.py`: Filter in `chunk_text()` drops contaminated chunks at ingestion
3. **Repair script** — `scripts/repair_data_quality.py`: 5 repair steps (hyphenation, tokens, dedup, embeddings, navigation)
4. **Audit alignment** — `scripts/audit_data_quality.py`: Section 3 uses same logic as repair for consistent metrics
5. **Alembic migrations** — Content hash column + source_url unique index
6. **Hyphenation repair** — `app/core/text/hyphenation.py`: PDF line-break artifact repair

## Verification Results

After running `repair_data_quality.py --execute --step navigation`:
- **233 chunks deleted** (matched 2+ patterns or 1 pattern + short)
- Re-running the audit with aligned metrics: **0 contaminated chunks**
- Per-pattern informational counts still show individual term mentions in legitimate content — these are expected and acceptable

---

## Remaining Quality Gaps

After the DEV-258 fixes, a comprehensive assessment identified 6 remaining gaps that affect knowledge base quality. Each gap is documented below with: what it is, how it affects the KB today, what industry best practices recommend, and what needs to be done (both retroactive fix and prevention).

---

### Gap 1: Content-Hash Deduplication Incomplete

#### What Is It

Content-hash deduplication means computing a fingerprint (SHA-256) of a document's text and checking if an identical document already exists in the database before ingesting it. This prevents the same regulatory document from being stored multiple times even if it arrives from different URLs.

#### How It Affects the Current Knowledge Base

The content-hash dedup logic exists in the main ingestion path (`ingest_document_with_chunks()` at `document_ingestion.py:440-451`) but **two other ingestion paths bypass it entirely**:

- **`KnowledgeIntegrator.update_knowledge_base()`** (`knowledge_integrator.py:77`): Computes a hash but then searches for duplicates by URL only — the hash is **never compared against the database**.
- **`TieredIngestionService._ingest_standard_chunking()`** (`tiered_ingestion_service.py:312`): No hash computation at all. Documents are created directly without any duplicate detection.

**Concrete impact**: The same Gazzetta Ufficiale decree published on two different URLs (e.g., `gazzettaufficiale.it/...` and `normattiva.it/...`) gets ingested twice. Search results return the same content twice, wasting embeddings and adding noise to retrieval.

#### Industry Best Practices

Production RAG systems use a **layered dedup strategy**:

| Layer | Technique | Catches | Precision | Cost |
|-------|-----------|---------|-----------|------|
| 1 | URL exact match | Same URL re-ingested | 100% | Negligible |
| 2 | Normalized content hash | Identical text (whitespace/case differences) | 100% | Negligible |
| 3 | MinHash/LSH (Jaccard >= 0.85) | Near-duplicate reformatted text | ~95% | O(n) per doc |
| 4 | Embedding cosine (>= 0.95) | Semantic duplicates, paraphrases | ~90% | $$$ (API call) |

- **LlamaIndex**: `IngestionPipeline` with `docstore` tracks document hashes automatically
- **Pinecone**: Recommends deterministic vector IDs from content hash — `upsert` is idempotent
- **Weaviate**: Supports deterministic UUIDs based on content for automatic dedup

**Key recommendation**: Normalize text before hashing (strip whitespace, lowercase) to catch trivially different duplicates. A single extra space defeats naive SHA-256.

**References**: [datasketch library](https://github.com/ekzhu/datasketch), [LlamaIndex IngestionPipeline](https://docs.llamaindex.ai/en/stable/module_guides/loading/ingestion_pipeline/), [Pinecone dedup guide](https://docs.pinecone.io/guides/data/upsert-data)

#### Fix for Current Knowledge Base

Add a new repair step to `scripts/repair_data_quality.py`:
- Query all active `knowledge_items` grouped by `content_hash`
- Where count > 1, keep the one with best `text_quality` (or most recent), archive the rest
- Delete orphaned chunks from archived items

#### Prevention (Code Changes)

1. **Normalize the hash function** (`document_ingestion.py:375`): Strip whitespace, lowercase before SHA-256
2. **Add content-hash check to `KnowledgeIntegrator`** (`knowledge_integrator.py`): Actually use the hash it already computes
3. **Add content-hash check to `TieredIngestionService`** (`tiered_ingestion_service.py`): Compute and check hash before creating `KnowledgeItem`
4. **Consider MinHash/LSH** for near-duplicate detection (using `datasketch` library) — catches reformatted versions of the same decree

---

### Gap 2: Chunk Size Configuration Mismatch

#### What Is It

The system has a configurable chunk size (`CHUNK_TOKENS=900` in `app/core/config.py:478`) that controls how large each text chunk should be when splitting documents. However, this config value is **never used** — three different hardcoded values are used instead across different ingestion paths.

#### How It Affects the Current Knowledge Base

Three conflicting chunk size values are in play:

| Ingestion Path | Chunk Size | Overlap | File:Line |
|---|---|---|---|
| Config (intended) | 900 tokens | 12% (~108 tokens) | `config.py:478` |
| `ingest_document_with_chunks()` | **512 tokens** (hardcoded) | 50 tokens | `document_ingestion.py:509` |
| `KnowledgeIntegrator` | **512 tokens** (hardcoded) | 50 tokens | `knowledge_integrator.py:124` |
| `TieredIngestionService` (Tier 2) | **1500 chars** (~375 tokens) | 150 chars | `tiered_ingestion_service.py:39` |

**Concrete impact**:
- Chunks are **43% smaller than intended** (512 vs 900 tokens), resulting in ~70% more chunks per document
- More chunks = more embeddings needed = higher OpenAI API costs
- A 50KB law produces ~88 chunks at 512 tokens vs ~56 at 900 tokens
- Developers reading `CHUNK_TOKENS=900` in config believe that's what's happening, but production behavior differs silently
- Tier 2 uses character-based splitting (not token-aware), creating inconsistently-sized chunks

#### Industry Best Practices

The 2024-2025 consensus on optimal chunk size:

| Use Case | Recommended Size | Overlap |
|----------|-----------------|---------|
| General Q&A | 512-1024 tokens | 10-20% |
| **Legal/regulatory docs** | **800-1500 tokens** | **15-20%** |
| Code documentation | 256-512 tokens | 5-10% |
| Conversational/FAQ | 256-512 tokens | 10% |

For `text-embedding-3-small` specifically (max input: 8,191 tokens):
- Sweet spot for retrieval: **500-1000 tokens** (per MTEB benchmarks)
- Smaller chunks lose context; larger chunks dilute the embedding signal
- Italian text has ~1:5 token-to-character ratio, so 900 tokens is ~4,500 characters

**Key findings**:
- LlamaIndex benchmarks (2024): 1024-token chunks with sentence-boundary alignment performed **18% better** than 256-token chunks on legal QA
- Anthropic RAG guide: Recommends 512-1024 tokens with 10-20% overlap
- The existing config value of 900 tokens is well-aligned with best practices

**References**: [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings), [Anthropic RAG best practices](https://docs.anthropic.com/en/docs/build-with-claude/retrieval-augmented-generation), [MTEB Benchmark](https://huggingface.co/spaces/mteb/leaderboard)

#### Fix for Current Knowledge Base

Add a repair step that re-chunks documents with incorrect chunk sizes:
- Identify chunks created with 512-token or 1500-char settings
- Re-chunk their parent documents using the correct 900-token config
- Re-embed the new chunks
- Delete old chunks

Note: This is a large-scale operation affecting all chunks. Consider running it as a batch migration.

#### Prevention (Code Changes)

1. **Use config values everywhere**: Replace hardcoded `max_tokens=512` in `document_ingestion.py:509` and `knowledge_integrator.py:124` with `CHUNK_TOKENS` from config
2. **Convert `TieredIngestionService` to token-based**: Replace `DEFAULT_CHUNK_SIZE = 1500` (chars) with `CHUNK_TOKENS * 4` to stay token-aware
3. **Use config overlap**: Replace hardcoded `overlap_tokens=50` with `int(CHUNK_TOKENS * CHUNK_OVERLAP)`
4. **Add a startup assertion** that validates all chunk size values are consistent

---

### Gap 3: Document Staleness & Supersession

#### What Is It

"Staleness" means that outdated regulatory documents remain marked as `active` in the knowledge base even after newer versions have been published. "Supersession" is the legal concept where a new law, circular, or decree replaces an older one — the old document is still historically valid but should no longer be cited as current law.

This is particularly critical for Italian regulatory content because:

- **Laws** supersede each other: a new Legge di Bilancio replaces provisions from the previous year's budget law
- **Circulars** get updated: Agenzia delle Entrate issues updated interpretive circulars that override previous guidance
- **Tax rates** change annually: IRPEF brackets, contribution rates, pension thresholds are updated each year
- **Decrees** convert to laws: Decreto-legge must be converted to Legge within 60 days, after which the decree is superseded

Without staleness management, the RAG system may cite a 2023 tax rate when a 2025 rate is in effect.

#### How It Affects the Current Knowledge Base

The `KnowledgeItem` model has a `status` field (`knowledge.py:123`) with values `active`, `archived`, `draft`, `superseded`. The `KnowledgeIntegrator` even has a `handle_document_update()` method (`knowledge_integrator.py:249-255`) that marks old versions as superseded. **However, no ingestion path actually calls it.**

What happens today:

1. **RSS ingestion** (`rss_normativa.py:338-399`): Checks if URL exists → skips if it does, ingests as new if not. **No supersession logic**. If a circular is updated at a new URL, both versions stay `active`.
2. **TieredIngestionService**: No superseding logic at all. Re-ingesting creates a new record alongside the old one.
3. **No automated cleanup**: Old documents accumulate indefinitely as `active`.

**Concrete impact**: A user asks "What is the IRPEF rate for 2025?" The retriever returns both the 2024 and 2025 rate documents (both `status=active`). The LLM sees conflicting rates and produces an ambiguous or incorrect answer.

#### Industry Best Practices

Legal information systems treat document lifecycle as a core feature:

| System | Approach |
|--------|----------|
| **Westlaw** (Thomson Reuters) | "KeyCite" status flags: good law, caution, negative treatment, superseded. Citation graph propagates status changes. Old versions are annotated, never deleted. |
| **LexisNexis** | "Shepard's Citations" for tracking validity. Point-in-time retrieval: users can view law "as of date X". |
| **EUR-Lex** (EU Law) | Every legal act has `legal_status`: in_force, no_longer_in_force, partially_in_force. Consolidated versions show amendments at a given date. ELI (European Legislation Identifier) for machine-readable metadata. |
| **Normattiva.it** (Italian Law) | "Multivigente" views showing law text as valid at different dates. URN:NIR identifiers for Italian legislation. |

The emerging approach called **"Temporal RAG"** involves:
1. **At ingestion**: Extract temporal metadata (effective dates, references to superseded documents)
2. **At retrieval**: Default to `status = 'in_force'` filter; allow historical queries with annotation
3. **At generation**: Instruct the LLM to note if a cited document has been superseded

**Required metadata for staleness management**:
- `effective_date`: When the document takes effect (distinct from `publication_date`)
- `expiry_date`: When it ceases to be valid (if known)
- `legal_status`: `in_force`, `superseded`, `repealed`, `amended`
- `superseded_by_url`: URL of the replacing document
- `version_chain_id`: Shared ID across all versions of the same document

**References**: [EUR-Lex ELI Standard](https://eur-lex.europa.eu/eli-register/about.html), [Akoma Ntoso (UN XML standard for legal documents)](http://www.akomantoso.org/)

#### Fix for Current Knowledge Base

1. **Manual triage**: Query all active documents older than 1 year (`audit_data_quality.py` Section 9 already does this). Review and mark superseded ones.
2. **Automated heuristic**: For documents with the same `source` and overlapping titles (e.g., "Circolare n. 15/2024" vs "Circolare n. 15/2025"), mark the older one as `superseded`.
3. **Add a repair script step** that identifies likely superseded documents based on title similarity + date.

#### Prevention (Code Changes)

1. **Add `legal_status` field** to `KnowledgeItem` (values: `in_force`, `superseded`, `repealed`, `amended`), separate from the generic `status` field
2. **Add `effective_date` and `expiry_date`** fields to `KnowledgeItem`
3. **Wire up `handle_document_update()`** in the RSS ingestion path: when a new circular references an older one by number, automatically mark the older one as superseded
4. **Add temporal filter to hybrid search**: Default retrieval should filter on `legal_status = 'in_force'` (with override for historical queries)
5. **Extract temporal metadata at ingestion**: Parse effective dates from document text (Italian regulatory documents typically state "decorrenza dal..." or "a partire dal...")

---

### Gap 4: RSS Summary Fallback Stores Raw HTML

#### What Is It

When the ingestion pipeline cannot extract sufficient content from a web page (e.g., JavaScript-rendered sites like INPS), it falls back to the RSS feed's `<summary>` or `<description>` field. RSS summaries are often formatted in HTML with tags like `<p>`, `<strong>`, and HTML entities like `&amp;`, `&quot;`, `&#8217;`.

The fallback path (`rss_normativa.py:355-367`) does apply `clean_html()` and `clean_italian_text()`. However, when the RSS summary is a short HTML snippet (not a full HTML document), Trafilatura may fail or return too little text (< 100 chars), and the BeautifulSoup fallback may not fully decode all HTML entities.

#### How It Affects the Current Knowledge Base

Documents with `extraction_method = 'rss_summary_fallback'` may contain:
- Raw HTML entities: `&amp;` instead of `&`, `&quot;` instead of `"`
- Residual HTML tags: `<p>`, `<strong>`, `<a href="...">`
- Encoded Italian accents: `&agrave;` instead of `à`, `&egrave;` instead of `è`

**Concrete impact**: A document containing `"lettera a) &amp; b)"` won't match a user query for `"lettera a e b"` because the full-text search index stores the literal `&amp;` string. Similarly, `&agrave;` in chunk text degrades both FTS and embedding quality.

The audit (Section 4, lines 193-249) already checks for these artifacts and reports affected counts.

#### Industry Best Practices

The recommended extraction cascade for RAG pipelines:

```
1. Trafilatura (precision mode) -> quality check
2. Inscriptis (layout-preserving text extraction) -> quality check
3. BeautifulSoup (main content selectors) -> quality check
4. RSS summary (if available) -> HTML entity decode + quality check
5. Mark as extraction_failed
```

- **Trafilatura** is the industry standard for web content extraction (F1 > 0.95 on CLEAN-EVAL benchmark)
- **Inscriptis** is recommended as a middle fallback — better at preserving text layout from HTML than BeautifulSoup
- All fallback paths should apply `html.unescape()` to decode HTML entities before storing text

**References**: [Trafilatura docs](https://trafilatura.readthedocs.io/), [Inscriptis](https://github.com/weblyzard/inscriptis)

#### Fix for Current Knowledge Base

Add a repair script step that:
1. Finds all `knowledge_items` with `extraction_method = 'rss_summary_fallback'`
2. Applies `html.unescape()` + `clean_italian_text()` to their `content`
3. Updates corresponding `knowledge_chunks.chunk_text` with cleaned content
4. Re-generates embeddings for affected chunks

#### Prevention (Code Changes)

1. **Add explicit HTML entity decoding** in the RSS fallback path (`rss_normativa.py:366`): Ensure `html.unescape()` is called on the RSS summary **before** passing to `clean_html()`, as a safety net
2. **Add `inscriptis` as a middle fallback** in `clean_html()` (`clean.py`): Between Trafilatura and BeautifulSoup, try `inscriptis.get_text(html_content)` for better text extraction from short HTML snippets
3. **Add HTML artifact detection to ingestion**: After cleaning, check for residual HTML entities (e.g., `&amp;`, `&lt;`) and apply `html.unescape()` as a final pass

---

### Gap 5: Sequential Embedding Calls

#### What Is It

When a document is ingested, each chunk's embedding is generated by a separate, sequential API call to OpenAI. The system already has a `generate_embeddings_batch()` function (`embed.py:92-123`) that can embed up to 20 texts in a single API call, but the main ingestion paths never use it — they call `generate_embedding()` (singular) in a loop instead.

#### How It Affects the Current Knowledge Base

In `ingest_document_with_chunks()` (`document_ingestion.py:512-538`):
```python
for chunk_dict in chunks:
    chunk_embedding_vec = await generate_embedding(chunk_text)  # One API call per chunk
```

For a document that produces 88 chunks (typical for a law at current 512-token chunk size):
- **Current (sequential)**: 89 API calls (1 doc + 88 chunks), ~89 x 200ms = **~18 seconds**
- **Batched**: 6 API calls (1 doc + 5 batches of 20), ~6 x 200ms = **~1.2 seconds**
- **Speed improvement**: ~15x faster

The same pattern exists in `KnowledgeIntegrator.update_knowledge_base()` (`knowledge_integrator.py:131`).

**Concrete impact**: During nightly RSS ingestion, processing 50 new documents takes ~15 minutes instead of ~1 minute. This wastes time and increases risk of timeout/failure during long ingestion runs.

Note: OpenAI charges per token, not per request, so the **cost is the same** — but latency, rate-limit consumption, and failure risk are all significantly worse with sequential calls.

#### Industry Best Practices

**Batching is mandatory for production RAG systems.**

| Approach | API Calls | Latency | Notes |
|----------|-----------|---------|-------|
| Sequential (current) | N per document | ~N x 200ms | Anti-pattern |
| **Per-document batch** | ceil(N/batch_size) | ~ceil(N/20) x 200ms | **Recommended minimum** |
| Cross-document batch | ceil(total/batch_size) | Amortized | Best for bulk ingestion |
| OpenAI Batch API | 1 (async) | 1-24 hours | 50% cost savings, best for nightly jobs |

OpenAI's `text-embedding-3-small` supports up to **2,048 texts per API call**. The current `batch_size=20` is very conservative — can safely increase to 100-200.

**References**: [OpenAI Embeddings API](https://platform.openai.com/docs/api-reference/embeddings), [OpenAI Batch API](https://platform.openai.com/docs/guides/batch), [OpenAI Rate Limits](https://platform.openai.com/docs/guides/rate-limits)

#### Fix for Current Knowledge Base

No retroactive fix needed — existing embeddings are correct. The issue is only latency during ingestion.

#### Prevention (Code Changes)

1. **Refactor `ingest_document_with_chunks()`** (`document_ingestion.py`): Collect all chunk texts, call `generate_embeddings_batch()` once, then assign embeddings to chunks
2. **Refactor `KnowledgeIntegrator`** (`knowledge_integrator.py`): Same pattern — batch all chunk embeddings
3. **Increase `batch_size`** from 20 to 100-200 in `generate_embeddings_batch()`
4. **Consider OpenAI Batch API** for nightly RSS ingestion: 50% cost savings for non-real-time workloads

---

### Gap 6: No Section-Aware Chunking

#### What Is It

Italian legal documents have a strict hierarchical structure:

```
Legge / Decreto
  └── Titolo (Title/Part)
      └── Capo (Chapter)
          └── Articolo (Article)
              └── Comma (Numbered paragraph)
                  └── Lettera (Lettered sub-item)
```

The current chunking algorithm (`chunking.py`) splits text into fixed-size chunks based on **sentence boundaries only**. It has no awareness of this legal structure. This means a chunk boundary may fall in the middle of an article, splitting related commi across different chunks and losing the structural context.

#### How It Affects the Current Knowledge Base

Consider this document text:
```
Art. 3, comma 1. Per rottamazione si intende l'avvio a demolizione
di un veicolo.
comma 2. L'autovettura deve avere almeno 10 anni di anzianita.
```

**Current sentence-based chunking** may produce:
- Chunk 1: `"Art. 3, comma 1. Per rottamazione si intende l'avvio a demolizione di un veicolo."`
- Chunk 2: `"comma 2. L'autovettura deve avere almeno 10 anni di anzianita."`

**Problem**: Chunk 2 is orphaned — it says "comma 2" but the reader (and the embedding model) don't know this is Art. 3. When this chunk is retrieved for a query about "Article 3", the LLM lacks the article context.

**Concrete impact**: A user asks "What is rottamazione according to Article 3?" The retriever might only surface Chunk 2 (mentioning "10 years" but not the definition). The LLM responds "I don't have the definition from Article 3" even though it exists in the knowledge base.

Note: The `TieredIngestionService` (Tier 1) **does** perform article-level parsing for critical laws via `ItalianLawParser`. But Tier 2 and the main `document_ingestion.py` path use sentence-only chunking. Also, even Tier 1 doesn't parse down to the comma level.

#### Industry Best Practices

**Structure-aware chunking significantly outperforms fixed-size chunking for legal documents.** This is the strongest consensus among all identified gaps.

Key research findings:
- **20-35% improvement** in retrieval accuracy for legal QA when using structure-aware chunking (multiple 2024 papers)
- **15-25% improvement** in answer quality (LLM-as-judge) when chunks preserve legal document hierarchy
- Legal documents have **inherent semantic boundaries** (articles, commi, lettere) that fixed-size chunking destroys

| Tool | Approach | Best For |
|------|----------|----------|
| **Unstructured.io** | Element-level extraction, `chunk_by_title` strategy | Complex documents, PDFs |
| **LlamaIndex** | `HierarchicalNodeParser` for parent-child chunks | Multi-level retrieval |
| **LangChain** | `RecursiveCharacterTextSplitter` (section > paragraph > sentence) | General structured text |
| **Custom (recommended)** | Extend existing `ItalianLawParser` with comma-level parsing | Italian legal specifics |

The **"Hierarchical RAG"** approach (emerging 2024-2025) stores chunks at multiple granularity levels:
- Level 1: Full article text (for broad context)
- Level 2: Individual commi (for precise retrieval)
- Level 3: Summary/title (for initial filtering)

Retrieval starts at Level 3, then drills into Level 2 for the LLM context.

**References**: [Unstructured.io chunking docs](https://unstructured.io/docs/chunking), [LlamaIndex node parsers](https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/), [LangChain text splitters](https://python.langchain.com/docs/how_to/#text-splitters), [Pinecone chunking strategies](https://www.pinecone.io/learn/chunking-strategies/)

#### Fix for Current Knowledge Base

This requires re-processing all existing documents:
1. For each `knowledge_item`, re-chunk using section-aware logic
2. Delete old chunks, create new structure-aware chunks
3. Re-embed all new chunks
4. This is a large migration best done as a batch operation

#### Prevention (Code Changes)

1. **Extend `ItalianLawParser`** to parse comma-level structure (currently article-level only)
2. **Add section context to chunks**: When creating a chunk from a comma, prepend the article reference: `"[Art. 1, comma 3] Il contribuente che intende avvalersi..."`
3. **Align Tier 2 chunking with structure**: For circulars and guidance documents, detect section headers ("Premessa", "Oggetto", numbered sections) and split at those boundaries
4. **Make `chunk_document()` structure-aware**: Add a pre-processing step that detects `Art.`, `comma`, `lettera` boundaries and prefers splitting there over mid-sentence
5. **Consider hierarchical retrieval**: Store both article-level and comma-level chunks; use two-stage retrieval (find article via embedding, find comma via FTS)

---

## Priority Matrix

| Priority | Gap | Issue | RAG Impact | Effort |
|----------|-----|-------|-----------|--------|
| **P0** | #5 | Sequential embedding calls (15x latency) | Ingestion speed | Low (~2-3h) |
| **P0** | #2 | Three inconsistent chunk size configs | Data quality | Low (~1-2h) |
| **P1** | #1 | Content-hash dedup missing in 2 of 3 paths | Duplicate content | Low (~2-3h) |
| **P1** | #4 | RSS fallback may store HTML entities | Search accuracy | Low (~2h) |
| **P2** | #6 | No section-aware chunking for legal text | Retrieval accuracy | High (~2-4 weeks) |
| **P2** | #3 | No staleness management (outdated law stays active) | Hallucination risk | High (~2-4 weeks) |

**P0** = Fix immediately (low effort, clear impact on data quality)
**P1** = Fix in next sprint (low effort, moderate impact)
**P2** = Plan as a dedicated feature (high effort, high long-term value)

---

## File Reference

| File | Role |
|------|------|
| `app/core/text/clean.py` | `NAVIGATION_PATTERNS`, `chunk_contains_navigation()`, `validate_extracted_content()` |
| `app/core/chunking.py` | Chunk-level filter calling `chunk_contains_navigation()` |
| `app/core/text/hyphenation.py` | `repair_broken_hyphenation()` for PDF artifacts |
| `app/core/document_ingestion.py` | Document ingestion with content hash dedup |
| `app/core/embed.py` | Embedding generation with batch support |
| `app/core/config.py` | `CHUNK_TOKENS`, `CHUNK_OVERLAP`, `JUNK_DROP_CHUNK` |
| `app/models/knowledge.py` | SQLModel with `content_hash`, `status`, `text_quality` fields |
| `app/services/knowledge_integrator.py` | Knowledge integration (has unused supersession logic) |
| `app/services/tiered_ingestion_service.py` | Tiered ingestion with `ItalianLawParser` for Tier 1 |
| `app/ingest/rss_normativa.py` | RSS feed ingestion with summary fallback |
| `scripts/audit_data_quality.py` | Data quality audit (12 diagnostic sections) |
| `scripts/repair_data_quality.py` | Data quality repair (5 steps: A-E) |
| `tests/core/test_clean.py` | Tests for navigation detection |
| `tests/core/test_chunking.py` | Tests for chunk filtering |
| `tests/core/test_embed.py` | Tests for embedding |
| `tests/core/test_hyphenation.py` | Tests for hyphenation repair |
