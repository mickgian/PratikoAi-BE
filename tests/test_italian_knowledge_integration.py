"""Tests for Italian knowledge service integration with official documents."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import List

from app.services.italian_knowledge import italian_knowledge_service
from app.models.italian_data import ItalianOfficialDocument, DocumentCategory


class TestItalianKnowledgeIntegration:
    """Test Italian knowledge service integration with collected documents."""

    @pytest.fixture
    def mock_documents(self) -> List[ItalianOfficialDocument]:
        """Create mock official documents."""
        return [
            ItalianOfficialDocument(
                id=1,
                document_id="agenzia_entrate_test_001",
                title="Circolare n. 1/E del 2024 - Disposizioni IVA",
                category=DocumentCategory.CIRCOLARE,
                authority="Agenzia delle Entrate",
                source_url="https://www.agenziaentrate.gov.it/test1.pdf",
                rss_feed="https://www.agenziaentrate.gov.it/portale/rss/circolari.xml",
                summary="Nuove disposizioni in materia di IVA per il 2024",
                full_content="La presente circolare fornisce chiarimenti...",
                content_hash="hash123",
                publication_date=datetime(2024, 1, 15, 10, 0, 0),
                tax_types=["iva"],
                keywords=["iva", "imposta", "dichiarazione"],
                processing_status="completed",
                vector_id="vec_001"
            ),
            ItalianOfficialDocument(
                id=2,
                document_id="inps_test_002",
                title="Messaggio n. 500 del 2024 - Contributi previdenziali",
                category=DocumentCategory.MESSAGGIO,
                authority="INPS",
                source_url="https://www.inps.it/test2.pdf",
                rss_feed="https://www.inps.it/rss/messaggi.xml",
                summary="Aggiornamento sui contributi previdenziali",
                full_content="Il presente messaggio comunica...",
                content_hash="hash456",
                publication_date=datetime(2024, 1, 10, 14, 30, 0),
                tax_types=["previdenza"],
                keywords=["contributi", "previdenza", "versamento"],
                processing_status="completed",
                vector_id="vec_002"
            )
        ]

    @patch('app.services.database.database_service.get_session')
    async def test_search_official_documents_by_keywords(self, mock_get_session, mock_documents):
        """Test searching official documents by keywords."""
        # Mock database session
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Mock query results
        mock_session.exec.return_value = iter(mock_documents)
        
        results = await italian_knowledge_service.search_official_documents(
            keywords=["iva", "imposta"],
            use_semantic=False  # Force keyword search
        )
        
        assert len(results) == 2
        assert results[0].title == "Circolare n. 1/E del 2024 - Disposizioni IVA"

    @patch('app.services.vector_service.vector_service')
    @patch('app.services.database.database_service.get_session')
    async def test_search_official_documents_semantic(self, mock_get_session, mock_vector_service, mock_documents):
        """Test semantic search of official documents."""
        # Mock vector service
        mock_vector_service.search = AsyncMock(return_value=[
            {
                "metadata": {"document_id": "agenzia_entrate_test_001"},
                "score": 0.95
            }
        ])
        
        # Mock database session
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Mock query results
        mock_session.exec.return_value = iter([mock_documents[0]])
        
        results = await italian_knowledge_service.search_official_documents(
            keywords=["nuove disposizioni IVA"],
            use_semantic=True
        )
        
        assert len(results) == 1
        assert results[0].document_id == "agenzia_entrate_test_001"
        mock_vector_service.search.assert_called_once()

    @patch('app.services.database.database_service.get_session')  
    async def test_search_official_documents_with_authority_filter(self, mock_get_session, mock_documents):
        """Test searching documents with authority filter."""
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Filter to only return Agenzia Entrate documents
        ae_docs = [doc for doc in mock_documents if doc.authority == "Agenzia delle Entrate"]
        mock_session.exec.return_value = iter(ae_docs)
        
        results = await italian_knowledge_service.search_official_documents(
            keywords=["iva"],
            authority="Agenzia delle Entrate",
            use_semantic=False
        )
        
        assert len(results) == 1
        assert results[0].authority == "Agenzia delle Entrate"

    @patch('app.services.database.database_service.get_session')
    async def test_search_official_documents_with_category_filter(self, mock_get_session, mock_documents):
        """Test searching documents with category filter."""
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Filter to only return circolari
        circolare_docs = [doc for doc in mock_documents if doc.category == DocumentCategory.CIRCOLARE]
        mock_session.exec.return_value = iter(circolare_docs)
        
        results = await italian_knowledge_service.search_official_documents(
            keywords=["disposizioni"],
            category=DocumentCategory.CIRCOLARE,
            use_semantic=False
        )
        
        assert len(results) == 1
        assert results[0].category == DocumentCategory.CIRCOLARE

    @patch('app.services.database.database_service.get_session')
    async def test_search_official_documents_with_date_range(self, mock_get_session, mock_documents):
        """Test searching documents with date range filter."""
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Filter by recent documents
        date_from = datetime(2024, 1, 12)
        recent_docs = [doc for doc in mock_documents if doc.publication_date >= date_from]
        mock_session.exec.return_value = iter(recent_docs)
        
        results = await italian_knowledge_service.search_official_documents(
            keywords=["disposizioni"],
            date_from=date_from,
            use_semantic=False
        )
        
        assert len(results) == 1
        assert results[0].publication_date >= date_from

    @patch('app.services.database.database_service.get_session')
    async def test_search_official_documents_with_tax_types(self, mock_get_session, mock_documents):
        """Test searching documents filtered by tax types."""
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Return all documents, then filter by tax type
        mock_session.exec.return_value = iter(mock_documents)
        
        results = await italian_knowledge_service.search_official_documents(
            keywords=["disposizioni"],
            tax_types=["iva"],
            use_semantic=False
        )
        
        # Should only return documents with 'iva' in tax_types
        assert len(results) == 1
        assert "iva" in results[0].tax_types

    @patch('app.services.database.database_service.get_session')
    async def test_get_latest_documents(self, mock_get_session, mock_documents):
        """Test getting latest official documents."""
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Sort documents by publication date descending
        sorted_docs = sorted(mock_documents, key=lambda x: x.publication_date, reverse=True)
        mock_session.exec.return_value = iter(sorted_docs)
        
        results = await italian_knowledge_service.get_latest_documents(limit=5)
        
        assert len(results) == 2
        assert results[0].publication_date >= results[1].publication_date

    @patch('app.services.database.database_service.get_session')
    async def test_get_latest_documents_with_authority_filter(self, mock_get_session, mock_documents):
        """Test getting latest documents filtered by authority."""
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()  
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Filter to specific authority
        ae_docs = [doc for doc in mock_documents if doc.authority == "Agenzia delle Entrate"]
        mock_session.exec.return_value = iter(ae_docs)
        
        results = await italian_knowledge_service.get_latest_documents(
            authority="Agenzia delle Entrate",
            limit=5
        )
        
        assert len(results) == 1
        assert results[0].authority == "Agenzia delle Entrate"

    @patch('app.services.database.database_service.get_session')
    async def test_get_document_by_id(self, mock_get_session, mock_documents):
        """Test getting document by ID."""
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Mock returning specific document
        mock_session.exec.return_value.first.return_value = mock_documents[0]
        
        result = await italian_knowledge_service.get_document_by_id("agenzia_entrate_test_001")
        
        assert result is not None
        assert result.document_id == "agenzia_entrate_test_001"

    @patch('app.services.database.database_service.get_session')
    async def test_get_document_by_id_not_found(self, mock_get_session):
        """Test getting document by ID when not found."""
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Mock returning None
        mock_session.exec.return_value.first.return_value = None
        
        result = await italian_knowledge_service.get_document_by_id("nonexistent_id")
        
        assert result is None

    @patch('app.services.database.database_service.get_session')
    async def test_get_documents_by_tax_type(self, mock_get_session, mock_documents):
        """Test getting documents by tax type."""
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Filter documents with 'iva' tax type
        iva_docs = [doc for doc in mock_documents if "iva" in doc.tax_types]
        mock_session.exec.return_value = iter(iva_docs)
        
        results = await italian_knowledge_service.get_documents_by_tax_type("iva")
        
        assert len(results) == 1
        assert "iva" in results[0].tax_types

    @patch('app.services.database.database_service.get_session')
    async def test_get_documents_by_tax_type_with_date_limit(self, mock_get_session, mock_documents):
        """Test getting documents by tax type with date limitation."""
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Mock documents filtered by date and tax type
        recent_iva_docs = [
            doc for doc in mock_documents 
            if "iva" in doc.tax_types and 
            doc.publication_date >= (datetime.utcnow() - timedelta(days=90))
        ]
        mock_session.exec.return_value = iter(recent_iva_docs)
        
        results = await italian_knowledge_service.get_documents_by_tax_type(
            "iva", 
            days_back=90
        )
        
        assert len(results) == 1

    @patch('app.services.database.database_service.get_session')
    async def test_get_collection_statistics(self, mock_get_session, mock_documents):
        """Test getting collection statistics."""
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Mock different query results for statistics
        def mock_exec_side_effect(query):
            # This is a simplified mock - in reality, you'd need to 
            # analyze the query to return appropriate results
            return iter(mock_documents)
        
        mock_session.exec.side_effect = mock_exec_side_effect
        
        stats = await italian_knowledge_service.get_collection_statistics()
        
        assert "total_documents" in stats
        assert "by_authority" in stats
        assert "by_category" in stats
        assert "recent_documents_30d" in stats
        assert "processing_status" in stats
        assert "last_updated" in stats

    @patch('app.services.database.database_service.get_session')
    async def test_search_with_complex_filters(self, mock_get_session, mock_documents):
        """Test search with multiple complex filters."""
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Apply complex filtering
        filtered_docs = [
            doc for doc in mock_documents
            if doc.authority == "Agenzia delle Entrate" 
            and doc.category == DocumentCategory.CIRCOLARE
            and doc.publication_date >= datetime(2024, 1, 1)
            and any(tax_type in doc.tax_types for tax_type in ["iva"])
        ]
        mock_session.exec.return_value = iter(filtered_docs)
        
        results = await italian_knowledge_service.search_official_documents(
            keywords=["disposizioni"],
            authority="Agenzia delle Entrate",
            category=DocumentCategory.CIRCOLARE,
            tax_types=["iva"],
            date_from=datetime(2024, 1, 1),
            use_semantic=False
        )
        
        assert len(results) == 1
        assert results[0].authority == "Agenzia delle Entrate"
        assert results[0].category == DocumentCategory.CIRCOLARE

    async def test_search_documents_error_handling(self):
        """Test error handling in document search."""
        with patch('app.services.database.database_service.get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database error")
            
            results = await italian_knowledge_service.search_official_documents(
                keywords=["test"],
                use_semantic=False
            )
            
            # Should return empty list on error
            assert results == []

    async def test_get_latest_documents_error_handling(self):
        """Test error handling in get latest documents."""
        with patch('app.services.database.database_service.get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database error")
            
            results = await italian_knowledge_service.get_latest_documents()
            
            # Should return empty list on error
            assert results == []

    async def test_get_collection_statistics_error_handling(self):
        """Test error handling in collection statistics."""
        with patch('app.services.database.database_service.get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database error")
            
            stats = await italian_knowledge_service.get_collection_statistics()
            
            # Should return empty dict on error
            assert stats == {}

    @patch('app.services.vector_service.vector_service')
    async def test_semantic_search_fallback_to_keyword(self, mock_vector_service):
        """Test fallback to keyword search when semantic search fails."""
        # Mock vector service to return None/empty results
        mock_vector_service.search = AsyncMock(return_value=[])
        
        with patch('app.services.database.database_service.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_get_session.return_value = mock_context_manager
            mock_session.exec.return_value = iter([])
            
            results = await italian_knowledge_service.search_official_documents(
                keywords=["test"],
                use_semantic=True
            )
            
            # Should still attempt both semantic and keyword search
            mock_vector_service.search.assert_called_once()
            assert results == []

    def test_service_initialization(self):
        """Test that the service initializes correctly."""
        service = italian_knowledge_service
        
        assert service is not None
        assert hasattr(service, 'search_official_documents')
        assert hasattr(service, 'get_latest_documents')
        assert hasattr(service, 'get_document_by_id')
        assert hasattr(service, 'get_documents_by_tax_type')
        assert hasattr(service, 'get_collection_statistics')