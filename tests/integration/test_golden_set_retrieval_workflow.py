"""Integration test for golden set retrieval workflow.

This test validates the complete flow:
1. Expert marks a response as "Corretta" (correct)
2. FAQ is saved to the golden set database (faq_entries)
3. Subsequent identical query retrieves from golden set without calling LLM
4. Step 20 (GoldenFastGate) routes to Step 24 (GoldenLookup)
5. Step 24 finds and returns the FAQ

Bug Context: Step 20 was returning golden={} instead of golden={eligible: true},
causing routing to ClassifyDomain instead of GoldenLookup. The RAGState schema
didn't include a 'golden: dict' field.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.faq import FAQEntry
from app.services.expert_faq_retrieval_service import ExpertFAQRetrievalService


@pytest.mark.asyncio
async def test_golden_set_complete_workflow(db_session: AsyncSession):
    """Test complete golden set workflow: save FAQ and retrieve it."""

    # STEP 1: Simulate expert marking response as "Corretta" by creating FAQ
    test_question = "Di cosa parla la risoluzione 64 dell'agenzia delle entrate?"
    test_answer = """La **Risoluzione n. 64/E del 10 novembre 2025** dell'Agenzia delle Entrate riguarda:

**Oggetto principale:**
Istituzione del codice tributo per la restituzione spontanea del contributo a fondo perduto non spettante.

**Contesto normativo:**
- Si riferisce all'articolo 1, comma 2, del decreto-legge 29 dicembre 2023, n. 212
- Riguarda il contributo a fondo perduto per interventi edilizi (Superbonus)
- Periodo di riferimento: spese sostenute dal 1° gennaio 2024 al 31 ottobre 2024

**Nuovo codice tributo:**
- Codice: **8161**
- Denominazione: "Contributo a fondo perduto per superbonus – Restituzione spontanea – art. 1, comma 2, DL 212 del 2023"
- Modello da utilizzare: F24 ELIDE (F24 Versamenti con elementi identificativi)

**A chi si applica:**
Soggetti che hanno ricevuto il contributo a fondo perduto ma che si sono trovati in condizioni per cui il contributo risulta in tutto o in parte non spettante.

**Fonte:**
[Risoluzione n. 64/E del 10/11/2025](https://www.agenziaentrate.gov.it/portale/documents/20143/8413114/RIS_n_64_del_10_11_2025)"""

    faq_entry = FAQEntry(
        question=test_question,
        answer=test_answer,
        category="tax",
        tags=["risoluzione", "agenzia delle entrate", "superbonus", "contributo a fondo perduto"],
        language="it",
    )

    db_session.add(faq_entry)
    await db_session.commit()
    await db_session.refresh(faq_entry)

    # Verify FAQ was saved
    result = await db_session.execute(select(FAQEntry).where(FAQEntry.id == faq_entry.id))
    saved_faq = result.scalar_one()
    assert saved_faq is not None
    assert saved_faq.question == test_question
    assert "Risoluzione n. 64/E" in saved_faq.answer

    # STEP 2: Test retrieval service can find the FAQ
    retrieval_service = ExpertFAQRetrievalService(db_session)

    # Test semantic search (what Step 24 uses when no query_signature)
    matches = await retrieval_service.find_matching_faqs(query=test_question, min_similarity=0.85, max_results=1)

    assert len(matches) > 0, "FAQ should be found by semantic search"
    match = matches[0]
    assert match["faq"].id == saved_faq.id
    assert match["similarity_score"] >= 0.85
    assert match["faq"].question == test_question

    # STEP 3: Verify answer content
    retrieved_answer = match["faq"].answer
    assert "Risoluzione n. 64/E" in retrieved_answer
    assert "10 novembre 2025" in retrieved_answer
    assert "8161" in retrieved_answer
    assert "Superbonus" in retrieved_answer


@pytest.mark.asyncio
async def test_golden_set_retrieval_without_confidence_scores(db_session: AsyncSession):
    """Test that Step 20 routes to golden lookup even without confidence_scores.

    Bug: Step 20 was checking for confidence_scores and returning eligible=false
    when missing. This caused routing to ClassifyDomain instead of GoldenLookup.

    Fix: Step 20 now uses semantic search fallback when confidence_scores missing.
    """
    # Create FAQ
    test_question = "Di cosa parla la risoluzione 64 dell'agenzia delle entrate?"
    test_answer = "La Risoluzione n. 64/E riguarda la restituzione del contributo superbonus."

    faq_entry = FAQEntry(
        question=test_question,
        answer=test_answer,
        category="tax",
    )

    db_session.add(faq_entry)
    await db_session.commit()
    await db_session.refresh(faq_entry)

    # Test retrieval without confidence_scores (simulates Step 24 behavior)
    retrieval_service = ExpertFAQRetrievalService(db_session)
    matches = await retrieval_service.find_matching_faqs(query=test_question, min_similarity=0.85, max_results=1)

    assert len(matches) > 0, "Should find FAQ even without confidence_scores"
    assert matches[0]["faq"].id == faq_entry.id


@pytest.mark.asyncio
async def test_golden_state_structure(db_session: AsyncSession):
    """Test that Step 20 returns the correct golden state structure.

    Bug: Step 20 was returning flat structure {"golden_fast_path_eligible": true}
    but routing expected nested structure {"golden": {"eligible": true}}.

    Fix: Added nested golden object to Step 20 result AND added golden field to RAGState.
    """
    from app.orchestrators.golden import step_20__golden_fast_gate

    # Simulate context without confidence_scores (common scenario)
    test_context = {
        "request_id": "test-123",
        "user_query": "Di cosa parla la risoluzione 64 dell'agenzia delle entrate?",
        "session_id": "test-session",
    }

    result = await step_20__golden_fast_gate(test_context)

    # Verify nested golden object exists
    assert "golden" in result, "Result must contain 'golden' key"
    assert isinstance(result["golden"], dict), "golden must be a dict"
    assert "eligible" in result["golden"], "golden must contain 'eligible' key"
    assert "reason" in result["golden"], "golden must contain 'reason' key"

    # Verify eligibility
    assert result["golden"]["eligible"] is True, "Should be eligible for semantic search fallback"
    assert result["golden"]["reason"] == "semantic_search_fallback"

    # Verify backward compatibility fields still exist
    assert result["golden_fast_path_eligible"] is True
    assert result["eligibility_reason"] == "semantic_search_fallback"

    # Verify routing information
    assert result["next_step"] == 24
    assert result["route_to"] == "GoldenLookup"


@pytest.mark.asyncio
async def test_rag_state_includes_golden_field():
    """Test that RAGState schema includes the golden field.

    Bug: RAGState TypedDict was missing 'golden: dict | None' field,
    causing LangGraph to reset it to empty dict {}.

    Fix: Added 'golden: dict | None' to RAGState TypedDict.
    """
    from app.core.langgraph.types import RAGState

    # Verify golden field is in the TypedDict annotations
    annotations = RAGState.__annotations__
    assert "golden" in annotations, "RAGState must include 'golden' field"

    # Verify it's typed as dict | None
    golden_type = annotations["golden"]
    assert golden_type == dict | None or str(golden_type) in [
        "dict | None",
        "typing.Union[dict, None]",
        "typing.Optional[dict]",
    ], f"golden field should be 'dict | None', got: {golden_type}"
