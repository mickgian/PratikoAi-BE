# ADR-018: Normative Matching Engine Architecture

**Status:** PROPOSED
**Date:** 2025-12-15
**Decision Makers:** PratikoAI Architect (Egidio), Michele Giannone (Stakeholder)
**Context Review:** PratikoAI 2.0 - FR-003 Automatic Normative Matching

---

## Context

### The Vision

PratikoAI 2.0 introduces **proactive assistance** where the system automatically identifies which regulations, deadlines, and opportunities are relevant to each client based on their profile (regime fiscale, ATECO code, CCNL, etc.).

Example scenario:
1. **Client Profile**: Mario Rossi, P.IVA, Regime Forfettario, ATECO 62.01 (software development)
2. **New Regulation**: "Rottamazione Quater estesa ai forfettari"
3. **Match**: System automatically identifies Mario Rossi as affected
4. **Proactive Suggestion**: "Hai 3 clienti che potrebbero beneficiare della rottamazione"

### Requirements

1. **Automatic matching**: No manual rule configuration for MVP
2. **Multiple criteria**: Match by regime, ATECO, tipo cliente, CCNL, location
3. **Scalability**: 100 clients × 1000+ regulations = 100K+ potential matches
4. **Real-time**: Match during chat when discussing a regulation
5. **Background**: Batch matching when new regulations are ingested

### Current RAG Pipeline

The existing 134-step LangGraph pipeline processes queries through:
- Step 31-38: Domain classification (identifies fiscale/lavoro/etc.)
- Step 39: Knowledge search (BM25 + vector + recency)
- Step 40: Context building (merges facts + KB documents)

The matching engine must integrate without disrupting this flow.

---

## Decision

### ADOPT: Hybrid Architecture (Inline Node + Background Service)

We will implement matching using two complementary approaches:

1. **Inline Matching Node**: During chat, after domain classification
2. **Background Matching Job**: After new regulation ingestion

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph RAG Pipeline                       │
├─────────────────────────────────────────────────────────────────┤
│ Step 35: Domain Classification                                  │
│ Step 36: [NEW] Client Matching Node ◄───────────────────┐       │
│ Step 39: Knowledge Search                               │       │
│ Step 40: Context Building (+ matched clients)           │       │
│ Step 104: Response (+ proactive suggestions)            │       │
└─────────────────────────────────────────────────────────────────┘
                                                           │
                                                           │
┌──────────────────────────────────────────────────────────┼──────┐
│                Background Matching Service               │      │
├──────────────────────────────────────────────────────────┼──────┤
│ Trigger: New regulation ingested                         │      │
│ Action: Scan all clients for matches ─────────────────────┘      │
│ Output: ProactiveSuggestion records                             │
└─────────────────────────────────────────────────────────────────┘
```

### Component 1: Inline Matching Node

**File:** `app/core/langgraph/nodes/client_matching_node.py`

```python
class ClientMatchingNode:
    """
    LangGraph node that identifies which clients are affected
    by the current query topic.

    Inserted after domain classification (step 35).
    Only activates when:
    - User belongs to a studio with clients
    - Query relates to a matchable domain (fiscale, lavoro, previdenziale)
    """

    async def __call__(self, state: RAGState) -> RAGState:
        if not self._should_match(state):
            return state

        # Extract matching criteria from query
        criteria = self._extract_criteria(state.domain_classification)

        # Query clients matching criteria
        matched_clients = await self._find_matching_clients(
            studio_id=state.user.studio_id,
            criteria=criteria
        )

        # Add to state for context building
        state.matched_clients = matched_clients
        return state

    def _extract_criteria(self, classification: DomainClassification) -> MatchCriteria:
        """
        Extract matching criteria from domain classification.

        Examples:
        - "rottamazione forfettari" -> regime_fiscale = FORFETTARIO
        - "bonus assunzioni under 30" -> tipo_cliente = AZIENDA
        - "CCNL metalmeccanici" -> ccnl = "METALMECCANICI"
        """
        return MatchCriteria(
            regime_fiscale=self._infer_regime(classification.keywords),
            codice_ateco=self._infer_ateco(classification.keywords),
            ccnl=self._infer_ccnl(classification.keywords),
            tipo_cliente=self._infer_tipo(classification.keywords)
        )
```

### Component 2: Background Matching Service

**File:** `app/services/normative_matching_service.py`

```python
class NormativeMatchingService:
    """
    Background service that matches new regulations against all clients.

    Triggered by:
    - RSS feed ingestion (new regulation detected)
    - Manual trigger via API
    - Scheduled daily scan
    """

    async def match_regulation(self, knowledge_item_id: UUID) -> list[ClientMatch]:
        """
        Match a single regulation against all clients.

        Returns list of ClientMatch records.
        """
        regulation = await self._get_regulation(knowledge_item_id)
        criteria = self._extract_criteria_from_regulation(regulation)

        # Query all studios with clients matching criteria
        matches = []
        async for studio in self._iterate_studios():
            studio_matches = await self._match_studio_clients(
                studio_id=studio.id,
                criteria=criteria,
                regulation=regulation
            )
            matches.extend(studio_matches)

        # Create proactive suggestion records
        await self._create_suggestions(matches)
        return matches

    async def daily_scan(self):
        """
        Daily scan for new matches.

        Runs against regulations ingested in last 24 hours.
        """
        recent_regulations = await self._get_recent_regulations(hours=24)
        for regulation in recent_regulations:
            await self.match_regulation(regulation.id)
```

### Matching Rules (Pre-configured)

**File:** `app/data/matching_rules.json`

```json
[
  {
    "id": "rule_rottamazione_forfettari",
    "name": "Rottamazione per forfettari",
    "keywords": ["rottamazione", "forfettario", "quater"],
    "criteria": {
      "regime_fiscale": ["FORFETTARIO"]
    },
    "priority": 1
  },
  {
    "id": "rule_bonus_sud",
    "name": "Bonus Sud assunzioni",
    "keywords": ["bonus", "sud", "mezzogiorno", "assunzioni"],
    "criteria": {
      "regione": ["CAMPANIA", "CALABRIA", "SICILIA", "PUGLIA", "BASILICATA", "SARDEGNA", "MOLISE", "ABRUZZO"]
    },
    "priority": 2
  },
  {
    "id": "rule_ccnl_metalmeccanici",
    "name": "CCNL Metalmeccanici",
    "keywords": ["metalmeccanici", "ccnl", "federmeccanica"],
    "criteria": {
      "ccnl": ["METALMECCANICI"]
    },
    "priority": 3
  }
]
```

### Database Models

**ClientProfile Vector for Semantic Matching:**

```python
class ClientProfile(SQLModel, table=True):
    __tablename__ = "client_profile"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    client_id: UUID = Field(foreign_key="client.id", unique=True)

    # Structured criteria
    codice_ateco: str | None = Field(max_length=10, index=True)
    regime_fiscale: RegimeFiscale | None = Field(index=True)
    ccnl: str | None = Field(max_length=100)
    n_dipendenti: int | None = Field(default=0)

    # Semantic matching vector
    profile_vector: list[float] | None = Field(
        sa_column=Column(Vector(1536))  # OpenAI embedding dimension
    )
```

**ClientMatch for Recording Matches:**

```python
class ClientMatch(SQLModel, table=True):
    __tablename__ = "client_match"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    client_id: UUID = Field(foreign_key="client.id", index=True)
    knowledge_item_id: UUID = Field(foreign_key="knowledge_items.id", index=True)

    match_score: float = Field(ge=0.0, le=1.0)
    match_reason: str = Field(max_length=500)  # "regime_fiscale=FORFETTARIO"
    matched_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))

    # Status tracking
    is_notified: bool = Field(default=False)
    notification_sent_at: datetime | None = None
```

---

## Alternatives Considered

### 1. Pure Rule-Based Matching (REJECTED for MVP)

```python
# User defines custom rules
rules = [
    Rule(
        condition="regime == 'FORFETTARIO' AND fatturato > 50000",
        action="notify_rottamazione"
    )
]
```

**Pros:**
- Maximum flexibility
- Users control matching logic

**Cons:**
- Complex UI for rule builder
- Users don't want to configure rules (stakeholder feedback)
- Error-prone

**Decision:** Defer to post-MVP. MVP uses pre-configured rules only.

### 2. Pure Vector Similarity Matching (REJECTED)

```python
# Match profile vector against regulation vector
similarity = cosine(client.profile_vector, regulation.embedding)
if similarity > 0.8:
    return Match(client, regulation)
```

**Pros:**
- Semantic understanding
- No rule configuration needed

**Cons:**
- Less explainable ("why was I matched?")
- May miss obvious matches (forfettario ≠ vector match)
- Embeddings may not capture fiscal nuances

### 3. Hybrid: Structured + Vector (SELECTED)

```python
# First pass: Structured criteria (fast, explainable)
candidates = filter_by_criteria(clients, regulation.criteria)

# Second pass: Vector similarity for ambiguous cases
if not candidates:
    candidates = filter_by_vector(clients, regulation.embedding, threshold=0.75)
```

**Pros:**
- Explainable matches for clear criteria
- Fallback to semantic for ambiguous cases
- Best of both approaches

---

## Consequences

### Positive

1. **Explainable**: "Matched because regime_fiscale=FORFETTARIO"
2. **Scalable**: Structured query < 100ms for 100 clients
3. **Proactive**: Background job catches new regulations automatically
4. **Integrated**: Inline node enriches chat responses

### Negative

1. **Maintenance**: Pre-configured rules need periodic updates
2. **Complexity**: Two matching paths (inline + background)
3. **False positives**: May match clients who already know about regulation

### Mitigations

1. **Rule versioning**: Rules have `valid_from`/`valid_to` dates
2. **Clear separation**: Inline for real-time, background for batch
3. **User control**: "Non mostrare più" option for suggestions

---

## Performance Considerations

### Inline Node Latency

| Operation | Target | Notes |
|-----------|--------|-------|
| Extract criteria | <10ms | Rule-based, no LLM |
| Query clients | <50ms | Indexed by studio_id + criteria |
| Total added latency | <100ms | Acceptable in 134-step pipeline |

### Background Job Throughput

| Metric | Target | Notes |
|--------|--------|-------|
| Clients per second | 1000 | Batch query optimization |
| Studios processed | 100/min | Sequential per studio |
| Daily scan duration | <10 min | For 10K total clients |

### Index Strategy

```sql
-- Composite indexes for fast matching
CREATE INDEX idx_client_profile_regime ON client_profile(codice_ateco, regime_fiscale);
CREATE INDEX idx_client_profile_ccnl ON client_profile(ccnl) WHERE ccnl IS NOT NULL;

-- HNSW vector index for semantic fallback
CREATE INDEX idx_client_profile_vector ON client_profile
    USING hnsw (profile_vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

---

## Integration Points

### LangGraph Pipeline Integration

Insert after step 35 (domain classification):

```python
# app/core/langgraph/graph.py

from app.core.langgraph.nodes.client_matching_node import ClientMatchingNode

graph_builder.add_node("client_matching", ClientMatchingNode())
graph_builder.add_edge("domain_classification", "client_matching")
graph_builder.add_edge("client_matching", "knowledge_search")
```

### Response Enrichment

```python
# app/core/langgraph/nodes/response_formatter_node.py

def format_response(state: RAGState) -> str:
    response = state.llm_response

    if state.matched_clients:
        suggestion = f"\n\n**Suggerimento proattivo:** {len(state.matched_clients)} "
        suggestion += "dei tuoi clienti potrebbero essere interessati da questa normativa."
        response += suggestion

    return response
```

---

## Testing Strategy

### Unit Tests

```python
# tests/services/test_normative_matching_service.py

def test_match_forfettario_regulation():
    """Forfettario clients matched by regime_fiscale."""
    client = create_client(regime_fiscale=RegimeFiscale.FORFETTARIO)
    regulation = create_regulation(keywords=["rottamazione", "forfettario"])

    matches = matching_service.match_regulation(regulation.id)

    assert len(matches) == 1
    assert matches[0].client_id == client.id
    assert "regime_fiscale=FORFETTARIO" in matches[0].match_reason

def test_no_match_ordinario():
    """Ordinario clients NOT matched for forfettario regulations."""
    client = create_client(regime_fiscale=RegimeFiscale.ORDINARIO)
    regulation = create_regulation(keywords=["rottamazione", "forfettari"])

    matches = matching_service.match_regulation(regulation.id)

    assert len(matches) == 0
```

### Integration Tests

```python
# tests/integration/test_matching_node.py

async def test_inline_matching_enriches_response():
    """Chat response includes matched client suggestion."""
    # Setup: Studio with 3 forfettario clients
    studio = create_studio_with_clients(
        clients=[
            {"regime_fiscale": "FORFETTARIO"},
            {"regime_fiscale": "FORFETTARIO"},
            {"regime_fiscale": "ORDINARIO"}
        ]
    )

    # Query about rottamazione
    response = await chat(user=studio.owner, query="Cosa cambia con la rottamazione quater per i forfettari?")

    # Should mention 2 matched clients
    assert "2 dei tuoi clienti" in response
```

---

## References

- ADR-017: Multi-Tenancy Architecture (provides `studio_id` isolation)
- ADR-019: Communication Generation (uses matching results)
- `app/core/langgraph/graph.py` - RAG pipeline integration point
- `app/services/search_service.py` - Hybrid search patterns
- docs/tasks/PRATIKO_2.0.md - Phase 2 tasks (DEV-2.0-021 to DEV-2.0-030)

---

## Revision History

- 2025-12-15: Initial version - Hybrid matching architecture
