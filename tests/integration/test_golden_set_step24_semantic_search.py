"""TDD test for Step 24 (GoldenLookup) semantic search functionality.

This test validates that Step 24 can find FAQs using vector embeddings for semantic search.

Bug: Step 24 returns similarity_score=0.0 because faq_entries table is missing
the question_embedding column required for vector semantic search.

Expected behavior after fix:
1. FAQs have question_embedding vector when saved
2. Step 24 semantic search finds matching FAQs
3. Similarity scores are >= 0.85 for matching questions
4. Step 25 sets golden.hit = true and serves golden answer
"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.faq import FAQEntry
from app.services.expert_faq_retrieval_service import ExpertFAQRetrievalService


@pytest.mark.asyncio
async def test_faq_entry_has_embedding_column(db_session: AsyncSession):
    """Test that faq_entries table has question_embedding column for vector search.

    Bug: Column doesn't exist, causing semantic search to fail with similarity_score=0.0
    Fix: Run Alembic migration 20251126_add_question_embedding_to_faq.py
    """
    # Check if question_embedding column exists
    result = await db_session.execute(
        text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'faq_entries'
            AND column_name = 'question_embedding'
        """)
    )
    column = result.fetchone()

    assert column is not None, "question_embedding column must exist in faq_entries table"
    assert column[1] == "USER-DEFINED", f"question_embedding should be vector type, got: {column[1]}"


@pytest.mark.asyncio
async def test_faq_entry_has_embedding_after_save(db_session: AsyncSession):
    """Test that FAQ entries have embeddings generated when saved.

    Verifies that the question_embedding vector is populated after FAQ creation.
    """
    test_question = "Come si calcola l'IMU per la prima casa?"
    test_answer = (
        "L'IMU per la prima casa è generalmente esente, salvo per le abitazioni di lusso (categorie A/1, A/8, A/9)."
    )

    faq_entry = FAQEntry(
        question=test_question,
        answer=test_answer,
        category="tax",
        tags=["IMU", "prima casa", "tasse"],
        language="it",
    )

    db_session.add(faq_entry)
    await db_session.commit()
    await db_session.refresh(faq_entry)

    # Check if embedding was generated
    result = await db_session.execute(
        text("""
            SELECT question_embedding IS NOT NULL as has_embedding,
                   array_length(question_embedding, 1) as embedding_dimension
            FROM faq_entries
            WHERE id = :faq_id
        """),
        {"faq_id": faq_entry.id},
    )
    row = result.fetchone()

    assert row is not None, "FAQ entry should exist in database"
    assert row[0] is True, "FAQ entry must have question_embedding populated"
    assert row[1] > 0, f"Embedding dimension should be > 0, got: {row[1]}"
    # OpenAI text-embedding-3-small typically has 1536 dimensions
    assert row[1] == 1536, f"Expected 1536 dimensions, got: {row[1]}"

    # Cleanup
    await db_session.delete(faq_entry)
    await db_session.commit()


@pytest.mark.asyncio
async def test_step24_finds_faq_with_vector_embedding(db_session: AsyncSession):
    """Test that Step 24 semantic search finds FAQ using vector embeddings.

    Bug: Step 24 returns match_found=false, similarity_score=0.0
    Fix: After migration, semantic search should find FAQ with high similarity
    """
    # Create FAQ with a specific question
    test_question = "Di cosa parla la risoluzione 64 dell'agenzia delle entrate?"
    test_answer = """La **Risoluzione n. 64/E del 10 novembre 2025** dell'Agenzia delle Entrate riguarda:

**Oggetto principale:**
Istituzione del codice tributo per la restituzione spontanea del contributo a fondo perduto non spettante.

**Contesto normativo:**
- Si riferisce all'articolo 1, comma 2, del decreto-legge 29 dicembre 2023, n. 212
- Riguarda il contributo a fondo perduto per interventi edilizi (Superbonus)

**Nuovo codice tributo:** 8161
"""

    faq_entry = FAQEntry(
        question=test_question,
        answer=test_answer,
        category="tax",
        tags=["risoluzione", "agenzia delle entrate", "superbonus"],
        language="it",
    )

    db_session.add(faq_entry)
    await db_session.commit()
    await db_session.refresh(faq_entry)

    # Verify FAQ was saved with embedding
    result = await db_session.execute(
        text("""
            SELECT question_embedding IS NOT NULL as has_embedding
            FROM faq_entries
            WHERE id = :faq_id
        """),
        {"faq_id": faq_entry.id},
    )
    row = result.fetchone()
    assert row[0] is True, "FAQ must have embedding before testing semantic search"

    # Test semantic search using the retrieval service (what Step 24 uses)
    retrieval_service = ExpertFAQRetrievalService(db_session)

    # Search with same question (should have very high similarity)
    matches = await retrieval_service.find_matching_faqs(query=test_question, min_similarity=0.85, max_results=1)

    assert len(matches) > 0, "Semantic search must find the FAQ"
    match = matches[0]
    assert match["faq"].id == faq_entry.id, "Should find the exact FAQ we created"
    assert match["similarity_score"] >= 0.85, f"Similarity should be >= 0.85, got: {match['similarity_score']}"

    # Cleanup
    await db_session.delete(faq_entry)
    await db_session.commit()


@pytest.mark.asyncio
async def test_step24_similarity_score_above_threshold(db_session: AsyncSession):
    """Test that Step 24 returns similarity scores above the 0.85 threshold.

    This test verifies that semantically similar questions (not exact matches)
    still return similarity scores high enough for Step 25 to consider them hits.
    """
    # Create FAQ
    original_question = "Come funziona il Superbonus 110%?"
    test_answer = "Il Superbonus 110% è un'agevolazione fiscale per la riqualificazione energetica."

    faq_entry = FAQEntry(
        question=original_question,
        answer=test_answer,
        category="tax",
        tags=["superbonus", "agevolazioni"],
        language="it",
    )

    db_session.add(faq_entry)
    await db_session.commit()
    await db_session.refresh(faq_entry)

    # Test with semantically similar but not identical question
    similar_question = "Qual è il funzionamento del Superbonus al 110 percento?"

    retrieval_service = ExpertFAQRetrievalService(db_session)
    matches = await retrieval_service.find_matching_faqs(query=similar_question, min_similarity=0.85, max_results=1)

    # Should find FAQ even though question is not identical
    assert len(matches) > 0, "Should find semantically similar FAQ"
    match = matches[0]
    assert match["faq"].id == faq_entry.id
    assert (
        match["similarity_score"] >= 0.85
    ), f"Similarity should be >= 0.85 for similar questions, got: {match['similarity_score']}"

    # Cleanup
    await db_session.delete(faq_entry)
    await db_session.commit()


@pytest.mark.asyncio
async def test_step24_no_match_for_different_topic(db_session: AsyncSession):
    """Test that Step 24 doesn't return matches for unrelated topics.

    Verifies that semantic search correctly filters out FAQs with low similarity.
    """
    # Create FAQ about one topic
    faq_entry = FAQEntry(
        question="Come si calcola l'IRPEF?",
        answer="L'IRPEF si calcola applicando aliquote progressive al reddito imponibile.",
        category="tax",
        tags=["IRPEF", "imposte"],
        language="it",
    )

    db_session.add(faq_entry)
    await db_session.commit()
    await db_session.refresh(faq_entry)

    # Search for completely different topic
    unrelated_question = "Quali sono le migliori ricette di pizza napoletana?"

    retrieval_service = ExpertFAQRetrievalService(db_session)
    matches = await retrieval_service.find_matching_faqs(query=unrelated_question, min_similarity=0.85, max_results=1)

    # Should NOT find FAQ for unrelated topic
    assert len(matches) == 0, "Should not find FAQ for completely different topic"

    # Cleanup
    await db_session.delete(faq_entry)
    await db_session.commit()
