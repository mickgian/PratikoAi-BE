# Data Cleaning & Ingestion Pipeline Audit

**Date:** 2026-02-10
**Scope:** Full RSS-to-knowledge-base pipeline analysis
**Codebase:** PratikoAi-BE

---

## Section A: Current Pipeline Flow

### End-to-End Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  1. SOURCE INGESTION                                                    │
│  ───────────────────                                                    │
│  RSS Feeds (16 feeds, 7 sources):                                      │
│    • Agenzia Entrate (2 feeds: news + normativa/prassi)                │
│    • INPS (5 feeds: news, circolari, messaggi, sentenze, comunicati)   │
│    • INAIL (2 feeds: news + eventi)                                    │
│    • MEF (2 feeds: documenti + aggiornamenti)                          │
│    • Gazzetta Ufficiale (4 feeds: SG, S1, S2, S3)                     │
│    • Ministero Lavoro (1 feed: news)                                   │
│  Web Scrapers:                                                          │
│    • Cassazione (civil + penal jurisprudence)                          │
│    • AdER (news, rules, payment plans)                                 │
│    • Gazzetta Ufficiale (archive scraping)                             │
│                                                                         │
│  Code: app/ingest/rss_normativa.py:199 (fetch_rss_feed)                │
│        app/services/scrapers/*.py                                       │
│  Scheduler: app/services/scheduler_service.py (daily at 01:00 Rome)    │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. TOPIC FILTERING (Gazzetta Ufficiale only)                          │
│  ────────────────────────────────────────────                          │
│  Whitelist: ~25 stems (tribut, fiscal, impost, lavoro, legge, etc.)   │
│  Blacklist: 6 stems (concors, nomin, graduatoria, bando, etc.)        │
│  Logic: whitelist match → KEEP; blacklist match → REJECT; else REJECT │
│                                                                         │
│  Code: app/ingest/rss_normativa.py:88 (is_relevant_for_pratikoai)      │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. DEDUPLICATION CHECK                                                 │
│  ────────────────────────                                               │
│  Checks knowledge_items.source_url for exact URL match                 │
│  No content-hash deduplication at this stage                           │
│                                                                         │
│  Code: app/core/document_ingestion.py:531 (check_document_exists)      │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. DOWNLOAD & EXTRACT                                                  │
│  ─────────────────────                                                  │
│  HTTP fetch with:                                                       │
│    • httpx.AsyncClient(timeout=30s, follow_redirects=True)             │
│    • Relaxed SSL for INAIL (SECLEVEL=1)                                │
│  Content-type routing:                                                  │
│    • application/pdf → pdfplumber + Tesseract OCR fallback             │
│    • text/html → trafilatura (primary) + BeautifulSoup (fallback)      │
│  Gazzetta special: HTML fails → extract PDF URL → download PDF         │
│  Fallback: Short page content → use RSS summary instead                │
│                                                                         │
│  Code: app/core/document_ingestion.py:265 (download_and_extract)       │
│        app/core/text/extract_pdf_plumber.py:182                         │
│        app/core/text/clean.py:86 (clean_html)                          │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  5. CONTENT VALIDATION                                                  │
│  ─────────────────────                                                  │
│  For HTML:                                                              │
│    • Min 200 chars                                                      │
│    • <3 navigation patterns                                            │
│    • Nav content ratio <10%                                            │
│    • Doesn't start with "vai al", "menu", "home", etc.                 │
│  For PDF:                                                               │
│    • text_metrics() on each page                                       │
│    • printable_ratio ≥ 0.60                                            │
│    • alpha_ratio ≥ 0.25                                                │
│    • min 20 chars, 5 words                                             │
│  is_valid_text(): min 50 chars, 50% alphanumeric                       │
│                                                                         │
│  Code: app/core/text/clean.py:48 (validate_extracted_content)          │
│        app/core/text/extract_pdf.py:37 (text_metrics)                  │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  6. TEXT CLEANING & NORMALIZATION                                       │
│  ────────────────────────────────                                       │
│  HTML cleaning (trafilatura):                                           │
│    • Strip nav, header, footer, sidebar, comments                      │
│    • Favor precision mode                                              │
│    • Include tables                                                    │
│  BeautifulSoup fallback:                                               │
│    • Remove: script, style, meta, link, nav, header, footer, aside,    │
│      noscript, iframe, form                                            │
│    • Remove: .cookie, .banner, .menu, .sidebar, .breadcrumb classes    │
│    • Find: main, article, [role=main], #content, .content selectors    │
│  Italian text cleaning:                                                 │
│    • HTML entity decoding                                              │
│    • Curly → straight quotes                                           │
│    • En-dash/em-dash → hyphen                                          │
│    • Zero-width space removal                                          │
│  Document normalization:                                                │
│    • Fix broken years: "20 25" → "2025"                                │
│    • Add month names: "30/10/2025" → "30/10/2025 (ottobre)"           │
│  Whitespace normalization:                                              │
│    • Multiple spaces → single space                                    │
│    • Multiple newlines → double newline                                │
│    • Strip per-line whitespace                                         │
│    • Remove empty lines                                                │
│                                                                         │
│  Code: app/core/text/clean.py:226 (clean_italian_text)                 │
│        app/core/text/clean.py:200 (normalize_whitespace)               │
│        app/core/document_ingestion.py:95 (normalize_document_text)     │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  7. ARTICLE METADATA EXTRACTION                                         │
│  ────────────────────────────                                           │
│  Regex-based extraction of Italian legal references:                    │
│    • Article: "Art. 1", "articolo 2-bis"                               │
│    • Comma: "comma 231", "c. 231"                                      │
│    • Comma range: "commi da 231 a 252"                                 │
│    • Lettera: "lettera a)", "lett. a)"                                 │
│    • Law: "Legge 199/2025", "D.Lgs. 633/72"                           │
│  Stored in parsing_metadata field of KnowledgeItem                     │
│                                                                         │
│  Code: app/services/article_extractor.py:323 (extract_chunk_metadata)  │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  8. FULL-DOCUMENT EMBEDDING                                             │
│  ──────────────────────────                                             │
│  Model: text-embedding-3-small (1536 dimensions)                       │
│  Input: First 30,000 chars of content (~8k tokens)                     │
│  Stored in: knowledge_items.embedding                                  │
│                                                                         │
│  Code: app/core/embed.py:26 (generate_embedding)                       │
│        app/core/document_ingestion.py:435                               │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  9. CHUNKING                                                            │
│  ────────                                                               │
│  Sentence-aware splitting (Italian abbreviation protection):            │
│    • Protected: art., D.L., D.Lgs., D.P.R., n., pag., etc. (21 abbr) │
│    • Split on: [.!?] followed by space + uppercase                     │
│  Chunk params (from config):                                            │
│    • CHUNK_TOKENS = 900 (but ingestion calls with max_tokens=512)      │
│    • CHUNK_OVERLAP = 0.12 (12%)                                        │
│    • Char estimation: ~4 chars/token                                   │
│  Quality gates per chunk:                                               │
│    • text_metrics() → quality_score, looks_junk                        │
│    • JUNK_DROP_CHUNK=true → drop junk chunks                           │
│                                                                         │
│  Code: app/core/chunking.py:60 (chunk_text)                            │
│        app/core/chunking.py:146 (split_into_sentences)                 │
│        app/core/chunking.py:203 (chunk_document)                       │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  10. CHUNK EMBEDDING                                                    │
│  ────────────────────                                                   │
│  Each chunk individually embedded (not batched)                        │
│  Model: text-embedding-3-small (1536-d)                                │
│  Sequential API calls per chunk (no batch optimization)                │
│                                                                         │
│  Code: app/core/document_ingestion.py:497                               │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  11. STORAGE                                                            │
│  ────────                                                               │
│  PostgreSQL + pgvector:                                                 │
│    knowledge_items: full document + metadata + embedding                │
│    knowledge_chunks: chunk text + embedding + tsvector (Italian FTS)    │
│  tsvector auto-maintained by database trigger                          │
│  Indexes: GIN on tsvector, IVFFlat on pgvector                         │
│                                                                         │
│  Code: app/models/knowledge.py:38 (KnowledgeItem)                      │
│        app/models/knowledge_chunk.py:29 (KnowledgeChunk)               │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  12. RETRIEVAL (at query time)                                         │
│  ────────────────────────────                                           │
│  Parallel Hybrid RAG:                                                   │
│    BM25 (0.30) + Vector (0.35) + HyDE (0.25) + Authority (0.20)       │
│    + Brave web search (0.30)                                           │
│  Reciprocal Rank Fusion (k=60)                                         │
│  Source authority boost: gazzetta 1.3×, agenzia/inps 1.2×             │
│  Document type hierarchy: legge 1.8× → guida 0.8×                     │
│  Top 25 chunks returned for LLM context                               │
│                                                                         │
│  Code: app/services/parallel_retrieval.py                               │
│        app/services/knowledge_search_service.py                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Section B: Cleaning Gap Analysis

### Stage 1: RSS Fetching

| Stage | What Should Happen | What Actually Happens | Gap | Impact |
|-------|-------------------|----------------------|-----|--------|
| RSS summary sanitization | Strip HTML from RSS `<summary>` | Raw RSS summary used as-is when page extraction fails (line 364) | RSS summaries may contain HTML tags/entities that get stored raw | **MEDIUM** |
| Feed item title cleaning | Normalize whitespace, decode entities | Titles stored as received from feedparser | Titles with `&amp;`, `&quot;`, extra spaces pass through | **LOW** |
| Attachment URL validation | Validate URL format and accessibility | Only checks `startswith("http")` (line 225) | Malformed URLs may cause silent download failures | **LOW** |

### Stage 2: Topic Filtering (Gazzetta Ufficiale)

| Stage | What Should Happen | What Actually Happens | Gap | Impact |
|-------|-------------------|----------------------|-----|--------|
| Keyword matching | Stem-aware matching to catch all forms | Simple substring `in` matching on lowercased text (line 119) | False positives: "definitiva" matches " iva" only with leading space guard; "nomine" in a tax context rejected | **MEDIUM** |
| Default behavior | Documents without keywords need policy | No whitelist match AND no blacklist match → REJECT (line 134) | Potentially misses relevant documents that use uncommon terminology | **MEDIUM** |

### Stage 3: Deduplication

| Stage | What Should Happen | What Actually Happens | Gap | Impact |
|-------|-------------------|----------------------|-----|--------|
| URL-based dedup | Catch all duplicates | Exact URL match on `source_url` (line 543) | Same document at different URLs (redirect, www vs non-www, query params) creates duplicates | **HIGH** |
| Content-based dedup | Detect re-published content | `compute_content_hash()` called but result not used (line 432) | Near-duplicate documents (minor edits, formatting changes) stored as separate items | **HIGH** |
| Updated document handling | Update existing when source republishes | Always creates new records | Superseded versions accumulate, polluting retrieval context | **MEDIUM** |

### Stage 4: Download & Extraction

| Stage | What Should Happen | What Actually Happens | Gap | Impact |
|-------|-------------------|----------------------|-----|--------|
| HTTP error handling | Structured retry with backoff | Single attempt, `try/except` returns None (line 364) | Transient network errors cause permanent ingestion failures | **MEDIUM** |
| Content-type fallback | Detect PDFs served as octet-stream | Only checks `content-type` header (line 293) | PDFs served with wrong MIME type treated as HTML, extraction fails silently | **LOW** |
| Timeout tuning | Per-source timeout | Single 30s timeout for all sources (line 286) | Large PDF downloads from slow government servers may timeout | **LOW** |
| PDF page limit | Configurable per source | Extracts ALL pages from every PDF | Multi-hundred-page Gazzetta Ufficiale supplements waste compute and produce noisy chunks | **MEDIUM** |
| RSS summary fallback | Clean HTML before using as content | Falls back to raw RSS summary if page content < 500 chars (line 362) | RSS summaries may contain HTML that becomes part of stored text | **MEDIUM** |

### Stage 5: Content Validation

| Stage | What Should Happen | What Actually Happens | Gap | Impact |
|-------|-------------------|----------------------|-----|--------|
| Navigation pattern list | Cover all Italian government sites | 14 patterns covering INPS, generic Italian (line 30-45) | Missing patterns for: Agenzia Entrate ("area riservata"), MEF, INAIL-specific navigation | **MEDIUM** |
| Min content threshold | Adequate for all document types | Fixed 200 chars for HTML, 50 chars for `is_valid_text` | Very short valid circulars (amendments, errata) may be rejected | **LOW** |
| Cookie banner detection | Strip GDPR banners | Only detects "cookie policy" in navigation patterns | Full cookie consent text often survives extraction, especially from BeautifulSoup fallback | **MEDIUM** |

### Stage 6: Text Cleaning

| Stage | What Should Happen | What Actually Happens | Gap | Impact |
|-------|-------------------|----------------------|-----|--------|
| Legal header/footer removal | Strip document boilerplate | No specific removal of repeated legal headers ("IL DIRETTORE DELL'AGENZIA", "Prot. n.", signature blocks) | Standard legal preambles dilute chunk content | **MEDIUM** |
| Page number removal | Strip from PDF extraction | No page number removal in `_clean_text()` or `normalize_document_text()` | Chunks may contain "Pagina 1 di 5", "- 3 -" artifacts | **LOW** |
| Table-of-contents removal | Strip TOC from long documents | No TOC detection or removal | Index/TOC sections create low-value chunks | **MEDIUM** |
| Watermark/stamp text | Remove "COPIA NON AUTENTICA" etc. | No watermark detection | Repeated watermark text pollutes content | **LOW** |
| Line-break repair | Fix PDF mid-word breaks | Only fixes broken years ("20 25") (line 113) | "contribu-\nto" remains broken; "Agenzia delle En-\ntrate" won't match FTS queries | **HIGH** |
| Ligature handling | Replace fi/fl ligatures | No ligature normalization | PDF-extracted "efficacia" may appear as "ecacia" (fi ligature lost) | **MEDIUM** |
| Encoding normalization | NFC/NFKC Unicode normalization | No Unicode normalization applied | "è" (e + combining accent) vs "è" (single char) may not match in FTS | **MEDIUM** |

### Stage 7: Article Metadata

| Stage | What Should Happen | What Actually Happens | Gap | Impact |
|-------|-------------------|----------------------|-----|--------|
| Metadata accuracy | Extract correct references | Regex-based, handles common patterns well | Unusual formats ("articolo duodecies", "Titolo III, Capo II") may be missed | **LOW** |
| Cross-reference linking | Link to referenced laws | Extracts reference text but no resolution to KB items | Cited laws can't be looked up during retrieval | **LOW** |

### Stage 8: Chunking

| Stage | What Should Happen | What Actually Happens | Gap | Impact |
|-------|-------------------|----------------------|-----|--------|
| Section-aware splitting | Respect document structure | Sentence-based splitting only (line 190) | Chunks split mid-article; an article's heading may be in one chunk, its content in the next | **HIGH** |
| Config inconsistency | Consistent chunk size | `CHUNK_TOKENS=900` in config, but `ingest_document_with_chunks()` calls `chunk_document(max_tokens=512)` (line 490) | Actual chunk size is 512 tokens, not the configured 900; config value is misleading | **MEDIUM** |
| Heading preservation | Include heading context in each chunk | No heading propagation to child chunks | A chunk saying "I benefici spettano..." loses context of which law/article it belongs to | **HIGH** |
| Abbreviation protection | Comprehensive Italian coverage | 21 abbreviations protected (line 157-182) | Missing: "p.es.", "All.", "Reg.", "Circ.", "Ris.", "Dir.", "Sent.", "ord." | **LOW** |
| Token estimation | Accurate for Italian text | Simple `len(text) // 4` (line 57) | Italian text averages ~3.5 chars/token; chunks may slightly exceed embedding model's window | **LOW** |

### Stage 9: Embedding

| Stage | What Should Happen | What Actually Happens | Gap | Impact |
|-------|-------------------|----------------------|-----|--------|
| Batch embedding | Batch chunks for efficiency | Each chunk embedded individually in a loop (line 497) | N API calls per document instead of ceil(N/20); slower and more expensive | **MEDIUM** |
| Embedding input cleaning | Optimal text for embedding | Raw cleaned text embedded, including month name annotations | Parenthetical "(ottobre)" additions may slightly distort semantic vector | **LOW** |
| Full-doc truncation | Intelligent truncation | First 30,000 chars used (line 435) | Documents with long preambles have embeddings biased toward boilerplate | **LOW** |
| Failed embedding handling | Retry or flag | Returns None, chunk stored without embedding (line 499) | Chunks without embeddings invisible to vector search, only found by BM25 | **MEDIUM** |

### Stage 10: Storage & Retrieval

| Stage | What Should Happen | What Actually Happens | Gap | Impact |
|-------|-------------------|----------------------|-----|--------|
| Stale content management | Expire outdated documents | No TTL or expiration logic | Superseded circulars (e.g., old tax rates) remain equally accessible | **HIGH** |
| Italian FTS configuration | Optimized Italian dictionary | tsvector maintained by DB trigger (configuration not in codebase) | Italian stemming quality depends on PostgreSQL `italian` text search config; no custom dictionary for tax/legal terms | **MEDIUM** |
| Cache invalidation | Refresh on new content | No cache invalidation on ingestion | Redis-cached LLM responses may use stale context after new documents arrive | **LOW** |

---

## Section C: Noise Samples

Based on pipeline analysis, the following types of noise are expected in the knowledge base:

### C.1: Navigation Text in Chunks (from BeautifulSoup fallback)

When trafilatura fails (e.g., heavy JavaScript sites like INPS), the BeautifulSoup fallback extracts content that may include:

```
Vai al Contenuto Vai al Menu principale Cerca nel sito INPS
Accedi a MyINPS Cedolino Pensione Cambia lingua Italiano English
Circolare INPS n. 45 del 15 marzo 2025
Oggetto: Contributi previdenziali per l'anno 2025...
```

The navigation prefix survives because `validate_extracted_content()` only rejects when
≥3 navigation patterns are found, or when nav ratio exceeds 10%. A page with 2 nav
patterns and substantial real content would pass validation.

**Code reference:** `app/core/text/clean.py:64-66`

### C.2: Broken Hyphenation from PDF Extraction

```
L'Agenzia delle En-
trate ha emanato il provvedimento relativo alla detrazion-
e per carichi di famiglia, ai sensi dell'artico-
lo 12 del TUIR.
```

The `_clean_text()` function in `extract_pdf_plumber.py:85` only normalizes whitespace
(`re.sub(r"\s+", " ", text)`), collapsing to `"L'Agenzia delle En- trate"` — the
hyphen and space remain, breaking both FTS matching and human readability.

**Code reference:** `app/core/text/extract_pdf_plumber.py:97`

### C.3: RSS Summary Fallback with HTML

When page content is too short (<500 chars), the pipeline falls back to the RSS summary:

```
<p>Con la <strong>circolare n. 12/E</strong> del 2025, l&#8217;Agenzia chiarisce
le modalit&agrave; di applicazione...</p>
```

This raw HTML/entity content is stored directly because the fallback path at
`rss_normativa.py:364` sets content without passing through `clean_italian_text()`.

**Code reference:** `app/ingest/rss_normativa.py:362-365`

### C.4: Repeated Preamble Text

Government documents consistently begin with institutional preamble:

```
IL DIRETTORE DELL'AGENZIA

In base alle attribuzioni conferitegli dalle norme riportate nel seguito del
presente provvedimento

DISPONE

1. Approvazione del modello...
```

This preamble is essentially identical across hundreds of Agenzia Entrate documents.
It wastes chunk space and can bias FTS results toward procedural language rather than
substantive content.

### C.5: Table of Contents Creating Low-Value Chunks

Long laws (e.g., Legge di Bilancio) have multi-page TOC:

```
Art. 1 - Risultati differenziali del bilancio dello Stato ... pag. 3
Art. 2 - Misure in materia di entrate ... pag. 15
Art. 3 - Fondo per la riduzione della pressione fiscale ... pag. 28
```

These TOC sections generate chunks that match many article-related queries but contain
no substantive information. They are not flagged as junk because they have adequate
printable/alpha ratios.

### C.6: Page Numbers and Headers

```
Gazzetta Ufficiale della Repubblica Italiana - Serie Generale n. 282

- 15 -

DECRETO LEGISLATIVO 25 novembre 2025, n. 189.
```

The page number "- 15 -" and running header survive extraction and may appear in chunks.

---

## Section D: Italian-Specific Issues

### D.1: Legal Reference Format Inconsistencies

The same law may be referenced in multiple ways across different source documents:

| Variant | Normalized Form |
|---------|----------------|
| `D.Lgs. 14 marzo 2013, n. 33` | Should be normalized |
| `D.Lgs. n. 33/2013` | Should be normalized |
| `decreto legislativo 33/2013` | Should be normalized |
| `Dlgs 33/2013` | Should be normalized |
| `D. Lgs. 33/2013` (extra space) | Should be normalized |

**Current handling:** The `ArticleExtractor` (`app/services/article_extractor.py:82-168`)
captures these variants via regex but does not normalize them to a canonical form.
Each variant is stored as-is, reducing FTS recall. A search for "D.Lgs. 33/2013" will
not match a chunk containing "decreto legislativo 33/2013".

**Impact:** **HIGH** — reduces cross-document citation matching.

### D.2: Date Format Handling

| Format | Where Found | Current Handling |
|--------|-------------|-----------------|
| `DD/MM/YYYY` | PDF, HTML documents | Fixed: "30/10/2025" → "30/10/2025 (ottobre)" |
| `DD mese YYYY` | Document text ("13 ottobre 2025") | Extracted by `date_parser.py` for publication_date |
| `YYYY-MM-DD` | Gazzetta URL params, RSS pubDate | Parsed in scraper/RSS code |
| `DD-MM-YYYY` | Some circulars | Not explicitly handled in normalization |
| Broken: `30/10/20 25` | PDF extraction artifact | Fixed by `normalize_document_text()` |

**Gap:** No normalization of `DD-MM-YYYY` to `DD/MM/YYYY`. Inconsistent date separators
reduce FTS matching.

### D.3: Currency Formatting

| Format | Context |
|--------|---------|
| `€ 1.234,56` | Italian standard |
| `EUR 1,234.56` | EU/English format in some EU documents |
| `1234,56 euro` | Informal usage |

**Current handling:** No currency normalization. The pipeline stores whatever format the
source document uses. This means a search for "1.000 euro" won't match "1000 euro" or
"EUR 1,000".

**Impact:** **LOW** — users typically search by concept, not exact amounts.

### D.4: Abbreviation Inconsistencies Across Sources

| Agenzia Entrate | INPS | Gazzetta Ufficiale |
|-----------------|------|-------------------|
| `art. 12` | `Art. 12` | `ARTICOLO 12` |
| `D.L. 34/2020` | `D.L. n. 34/2020` | `decreto-legge 34/2020` |
| `c. 1` | `comma 1` | `comma 1` |
| `lett. a)` | `lettera a)` | `lettera a)` |

**Current handling:** `ArticleExtractor` handles most variants. However, the extracted
text retains source-specific formatting, meaning FTS on "art. 12" won't match a chunk
containing "ARTICOLO 12" unless the Italian stemmer handles both (it does not — these are
treated as different tokens).

**Impact:** **MEDIUM** — partially mitigated by vector search, but BM25 component (45%
weight in hybrid search, 30% in parallel retrieval) is affected.

### D.5: Regional Terminology

Some documents use regional/dialectal terminology:

- "patente a crediti" (Lombardy/formal) vs "patente a punti" (colloquial)
- "lavoratore subordinato" (legal) vs "dipendente" (common)
- "emolumenti" (formal) vs "stipendio" (common)

**Current handling:** The `ItalianQueryNormalizer` (`app/services/italian_query_normalizer.py`)
handles some synonym expansion at query time, but source documents are not normalized.
This is acceptable — query-time expansion is the right approach.

### D.6: Accented Character Issues

Italian accented characters (àèéìòù) can be represented in multiple Unicode forms:

- NFC: `è` (single codepoint U+00E8)
- NFD: `e` + `̀` (base + combining accent, U+0065 + U+0300)

**Current handling:** `clean_italian_text()` removes zero-width characters but does not
perform NFC normalization (`app/core/text/clean.py:246`). PostgreSQL's `italian` text
search config handles most cases, but pgvector embeddings may see NFC and NFD forms as
different inputs.

**Impact:** **LOW** — most sources output NFC, but occasional NFD from PDF extraction is
possible.

---

## Section E: Recommendations

### Critical (Directly Impacts Answer Quality)

#### E.1: Implement PDF Line-Break Repair
**What:** Add regex to rejoin hyphenated words broken across lines.
**Where:** `app/core/text/extract_pdf_plumber.py:85` (`_clean_text()`) or new function
in `app/core/document_ingestion.py:95` (`normalize_document_text()`).
**Pattern:** `re.sub(r"(\w)-\s+(\w)", r"\1\2", text)` (with Italian letter coverage).
**Impact:** Fixes broken FTS indexing for hundreds of split words per document. Estimated
5-10% improvement in BM25 recall for affected documents.
**Effort:** Small — a single regex rule plus edge-case testing for legitimate hyphens (e.g.,
"decreto-legge" should NOT be joined).

#### E.2: Add Content-Hash Deduplication
**What:** Use the already-computed `compute_content_hash()` to check for near-duplicates
before insertion.
**Where:** `app/core/document_ingestion.py:432` — the hash is computed but never stored
or checked.
**Change:** (a) Add `content_hash` column to `knowledge_items`, (b) check before insert,
(c) optionally check first-N-chars hash for near-duplicates.
**Impact:** Prevents duplicate documents from cluttering retrieval results. Same document
at different URLs (common with government redirects) currently creates multiple entries.
**Effort:** Medium — requires migration, index, and duplicate-resolution logic.

#### E.3: Implement Document Staleness/Supersession
**What:** Add mechanism to mark documents as superseded when newer versions are ingested.
**Where:** New field on `KnowledgeItem` or status transition logic in
`app/core/document_ingestion.py:381`.
**Change:** When ingesting a new circolare/risoluzione that references superseding an older
one, mark the older document status as "superseded" and reduce its retrieval weight.
**Impact:** Prevents the system from citing outdated tax rates, deadlines, or procedures.
This is the highest-impact quality issue for a regulatory AI.
**Effort:** Large — requires reference parsing, supersession detection, and retrieval weight
adjustment.

#### E.4: Section-Aware Chunking
**What:** Detect Italian legal document structure (Articolo, Comma, Titolo, Capo) and
split at section boundaries rather than arbitrary sentence boundaries.
**Where:** `app/core/chunking.py:146` (`split_into_sentences()`) or new preprocessing
step before chunking.
**Pattern:** Detect `Art\.\s+\d+` and `TITOLO|CAPO|Sezione` as chunk boundaries. Prepend
the article heading to each sub-chunk for context.
**Impact:** Each chunk would be a self-contained legal provision rather than an arbitrary
text window. Estimated 15-20% improvement in retrieval precision for legal queries.
**Effort:** Medium — requires Italian legal document structure detection and testing across
all source formats.

### Important (Impacts Search Relevance)

#### E.5: Clean RSS Summary Fallback Content
**What:** Apply `clean_italian_text()` and `clean_html()` to RSS summaries before using
as fallback content.
**Where:** `app/ingest/rss_normativa.py:362-365`.
**Change:** Replace `extraction_result["content"] = rss_summary` with
`extraction_result["content"] = clean_italian_text(clean_html(rss_summary))`.
**Impact:** Prevents HTML tags and entities from contaminating stored text.
**Effort:** Minimal — one-line change plus import.

#### E.6: Expand Navigation Pattern List
**What:** Add source-specific navigation patterns for government sites.
**Where:** `app/core/text/clean.py:30` (`NAVIGATION_PATTERNS` list).
**Additions:**
```python
"area riservata",          # Agenzia Entrate
"cassetto fiscale",        # Agenzia Entrate
"fatture e corrispettivi", # Agenzia Entrate
"dichiarazioni",           # Agenzia Entrate nav
"servizi più utilizzati",  # INPS
"prestazioni e servizi",   # INPS
"amministrazione trasparente",  # All government sites
"note legali",             # Common Italian footer
"ufficio stampa",          # Common Italian footer
"accessibilità",           # Common Italian footer
```
**Impact:** Reduces navigation noise surviving extraction, especially from BeautifulSoup
fallback path.
**Effort:** Small — extend list and test against known pages.

#### E.7: Remove Institutional Preamble and Signature Blocks
**What:** Add regex patterns to strip repeated legal preamble and signature blocks.
**Where:** New function in `app/core/text/clean.py` or `document_ingestion.py`.
**Patterns:**
```python
# Preamble
r"IL DIRETTORE (?:DELL'AGENZIA|GENERALE).*?DISPONE"  # with re.DOTALL
# Signature blocks
r"Il (?:Direttore|Responsabile).*?(?:F\.to|firmato).*$"  # at end of document
```
**Impact:** Removes ~200-500 chars of boilerplate per document, improving chunk quality.
**Effort:** Medium — requires careful regex to avoid removing content from documents that
discuss these elements rather than contain them.

#### E.8: Add Unicode NFC Normalization
**What:** Apply `unicodedata.normalize("NFC", text)` to all extracted content.
**Where:** `app/core/text/clean.py:226` (`clean_italian_text()`), after HTML unescaping.
**Impact:** Ensures consistent Unicode representation for FTS and embedding.
**Effort:** Minimal — one line addition.

#### E.9: Fix Chunk Size Configuration Inconsistency
**What:** Align the `max_tokens` parameter passed in `ingest_document_with_chunks()` with
the `CHUNK_TOKENS` config value.
**Where:** `app/core/document_ingestion.py:490` — currently hardcodes `max_tokens=512`
despite `CHUNK_TOKENS=900`.
**Change:** Use `CHUNK_TOKENS` config value, or deliberately document the 512 override.
**Impact:** Clarifies intent and allows chunk size tuning via environment variable.
**Effort:** Minimal — remove hardcoded value or add comment.

#### E.10: Batch Chunk Embeddings
**What:** Use `generate_embeddings_batch()` instead of individual `generate_embedding()`
calls for chunks.
**Where:** `app/core/document_ingestion.py:493-499`.
**Change:** Collect all chunk texts, call `generate_embeddings_batch()` once, then assign.
**Impact:** Reduces API calls from N to ceil(N/20) per document. Faster ingestion, lower
cost, fewer rate-limit hits.
**Effort:** Small — the batch function already exists at `app/core/embed.py:53`.

### Nice-to-Have (Marginal Improvements)

#### E.11: Add Table-of-Contents Detection
**What:** Detect and flag or remove TOC sections before chunking.
**Where:** Pre-processing step in `app/core/document_ingestion.py` before `chunk_document()`.
**Pattern:** Detect blocks where most lines match `.*\.\.\.\s*\d+$` or
`Art\.\s+\d+\s*-\s*.*pag\.\s*\d+`.
**Impact:** Removes low-value chunks that match many queries but contain no answers.
**Effort:** Small.

#### E.12: Add Page Number Removal
**What:** Strip page numbers and running headers from PDF text.
**Where:** `app/core/text/extract_pdf_plumber.py:85` or document normalization.
**Patterns:**
```python
r"^\s*-\s*\d+\s*-\s*$"            # "- 15 -"
r"^Pagina\s+\d+\s+di\s+\d+$"     # "Pagina 1 di 5"
r"^Gazzetta Ufficiale.*Serie.*$"  # Running header
```
**Impact:** Removes minor noise from chunks.
**Effort:** Small.

#### E.13: Legal Reference Normalization
**What:** Normalize legal references to canonical form for better cross-document matching.
**Where:** New normalization function in `app/services/article_extractor.py`.
**Example:** "decreto legislativo 33/2013", "D.Lgs. n. 33/2013", "Dlgs 33/2013" →
all stored with canonical tag `[D.Lgs. 33/2013]`.
**Impact:** Improves cross-document citation matching for both FTS and embedding.
**Effort:** Medium — requires comprehensive regex normalization and testing.

#### E.14: Add Ligature Normalization
**What:** Replace common PDF ligatures with their constituent characters.
**Where:** `app/core/text/extract_pdf_plumber.py:85` (`_clean_text()`).
**Pattern:**
```python
LIGATURES = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
for lig, replacement in LIGATURES.items():
    text = text.replace(lig, replacement)
```
**Impact:** Fixes occasional broken words from PDF extraction.
**Effort:** Minimal.

#### E.15: HTTP Retry for Document Downloads
**What:** Add retry logic with exponential backoff for document downloads.
**Where:** `app/core/document_ingestion.py:265` (`download_and_extract_document()`).
**Impact:** Reduces permanent ingestion failures from transient network issues.
**Effort:** Small — wrap in retry loop (tenacity or manual).

---

## Summary: Priority Matrix

```
                        LOW EFFORT          MEDIUM EFFORT        HIGH EFFORT
                     ┌─────────────────┬──────────────────┬──────────────────┐
     CRITICAL        │ E.1  Line-break │ E.4  Section     │ E.3  Staleness   │
     (answer         │      repair     │      chunking    │      management  │
     quality)        │                 │ E.2  Content-    │                  │
                     │                 │      hash dedup  │                  │
                     ├─────────────────┼──────────────────┼──────────────────┤
     IMPORTANT       │ E.5  RSS clean  │ E.7  Preamble    │                  │
     (search         │ E.6  Nav list   │      removal     │                  │
     relevance)      │ E.8  NFC norm   │                  │                  │
                     │ E.9  Config fix │                  │                  │
                     │ E.10 Batch embed│                  │                  │
                     ├─────────────────┼──────────────────┼──────────────────┤
     NICE-TO-HAVE    │ E.11 TOC detect │ E.13 Legal ref   │                  │
     (marginal)      │ E.12 Page nums  │      normalize   │                  │
                     │ E.14 Ligatures  │                  │                  │
                     │ E.15 HTTP retry │                  │                  │
                     └─────────────────┴──────────────────┴──────────────────┘
```

**Recommended implementation order:**
1. **E.1** (line-break repair) — immediate, high ROI
2. **E.5** (RSS summary cleaning) — immediate, trivial fix
3. **E.9** (config fix) — immediate, removes confusion
4. **E.10** (batch embeddings) — immediate, cost savings
5. **E.8** (NFC normalization) — immediate, one line
6. **E.6** (navigation patterns) — small effort, measurable improvement
7. **E.14** (ligatures) — minimal effort, prevents rare breakage
8. **E.2** (content-hash dedup) — medium effort, high value
9. **E.4** (section-aware chunking) — medium effort, highest quality impact
10. **E.3** (staleness management) — large effort, critical for regulatory correctness

---

## Appendix: Key File Reference

| File | Purpose | Lines |
|------|---------|-------|
| `app/ingest/rss_normativa.py` | RSS ingestion pipeline entry point | 402 |
| `app/core/document_ingestion.py` | Unified download, extract, ingest | 545 |
| `app/core/text/clean.py` | HTML cleaning, validation, Italian text | 320 |
| `app/core/text/extract_pdf_plumber.py` | PDF extraction + OCR fallback | 332 |
| `app/core/text/extract_pdf.py` | Text quality metrics | 96 |
| `app/core/text/date_parser.py` | Italian date extraction | 131 |
| `app/core/chunking.py` | Sentence-aware text chunking | 280 |
| `app/core/embed.py` | OpenAI embedding generation | 174 |
| `app/core/config.py` | Pipeline configuration values | 563 |
| `app/models/knowledge.py` | KnowledgeItem SQLModel | 257 |
| `app/models/knowledge_chunk.py` | KnowledgeChunk SQLModel | 91 |
| `app/services/article_extractor.py` | Legal reference extraction | 376 |
| `app/services/parallel_retrieval.py` | Hybrid RAG retrieval | ~400 |
| `app/services/scrapers/gazzetta_scraper.py` | Gazzetta Ufficiale scraper | 906 |
| `app/services/scrapers/cassazione_scraper.py` | Supreme Court scraper | ~300 |
| `app/services/scrapers/ader_scraper.py` | AdER scraper | ~200 |
| `app/services/ingestion_report_service.py` | Daily monitoring reports | ~400 |
| `app/utils/sanitization.py` | Input sanitization + prompt guard | ~200 |
