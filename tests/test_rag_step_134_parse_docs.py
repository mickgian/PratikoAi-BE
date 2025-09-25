"""
Comprehensive test suite for RAG STEP 134 — Extract text and metadata.

Tests the orchestrator function that extracts text and metadata from parsed RSS feeds,
following MASTER_GUARDRAILS TDD methodology.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional

from app.orchestrators.docs import step_134__parse_docs


class TestStep134ParseDocsUnit:
    """Unit tests for Step 134 ParseDocs orchestrator function."""

    @pytest.fixture
    def sample_parsed_feeds_context(self):
        """Sample context from Step 133 with parsed feeds."""
        return {
            'request_id': 'parse-docs-test-134',
            'parsed_feeds': [
                {
                    'feed_url': 'https://www.agenziaentrate.gov.it/portale/rss/circolari.xml',
                    'feed_name': 'agenzia_entrate_circolari',
                    'authority': 'Agenzia delle Entrate',
                    'items': [
                        {
                            'title': 'Circolare n. 1/E del 15/01/2024',
                            'link': 'https://www.agenziaentrate.gov.it/portale/documents/20143/5823152/Circolare+n.+1+E+del+15012024.pdf',
                            'published': '2024-01-15T10:30:00Z',
                            'summary': 'Chiarimenti su detrazioni fiscali 2024',
                            'document_number': '1/E',
                            'document_type': 'circolare'
                        },
                        {
                            'title': 'Circolare n. 2/E del 15/01/2024',
                            'link': 'https://www.agenziaentrate.gov.it/portale/documents/20143/5823152/Circolare+n.+2+E+del+15012024.pdf',
                            'published': '2024-01-15T11:15:00Z',
                            'summary': 'Novità IVA per il 2024',
                            'document_number': '2/E',
                            'document_type': 'circolare'
                        }
                    ],
                    'parsing_status': 'success',
                    'items_parsed': 2
                },
                {
                    'feed_url': 'https://www.inps.it/rss/messaggi.xml',
                    'feed_name': 'inps_messaggi',
                    'authority': 'INPS',
                    'items': [
                        {
                            'title': 'Messaggio n. 150 del 15/01/2024',
                            'link': 'https://www.inps.it/circolari-messaggi/messaggio-numero-150-del-15-01-2024.html',
                            'published': '2024-01-15T11:30:00Z',
                            'summary': 'Aggiornamenti contributi previdenziali',
                            'document_number': '150',
                            'document_type': 'messaggio'
                        }
                    ],
                    'parsing_status': 'success',
                    'items_parsed': 1
                }
            ],
            'total_items_parsed': 3,
            'feed_sources': ['agenzia_entrate', 'inps'],
            'previous_step': 133
        }

    @pytest.fixture
    def sample_extracted_documents(self):
        """Sample extracted document results."""
        return [
            {
                'url': 'https://www.agenziaentrate.gov.it/portale/documents/20143/5823152/Circolare+n.+1+E+del+15012024.pdf',
                'title': 'Circolare n. 1/E del 15/01/2024',
                'content': 'L\'articolo 1 del decreto legislativo 15 dicembre 1997, n. 446, stabilisce che...',
                'content_hash': 'abc123def456',
                'document_type': 'pdf',
                'metadata': {
                    'document_number': '1/E',
                    'document_type': 'circolare',
                    'authority': 'Agenzia delle Entrate',
                    'published_date': '2024-01-15T10:30:00Z',
                    'word_count': 1250,
                    'language': 'it',
                    'keywords': ['detrazioni', 'fiscali', '2024'],
                    'legal_references': ['D.Lgs. 446/1997']
                },
                'processing_stats': {
                    'content_length': 5234,
                    'word_count': 1250,
                    'processing_time': '2024-01-15T12:00:00Z',
                    'extraction_method': 'pdf'
                },
                'success': True
            },
            {
                'url': 'https://www.agenziaentrate.gov.it/portale/documents/20143/5823152/Circolare+n.+2+E+del+15012024.pdf',
                'title': 'Circolare n. 2/E del 15/01/2024',
                'content': 'La disciplina IVA prevista dal decreto del Presidente della Repubblica...',
                'content_hash': 'def456ghi789',
                'document_type': 'pdf',
                'metadata': {
                    'document_number': '2/E',
                    'document_type': 'circolare',
                    'authority': 'Agenzia delle Entrate',
                    'published_date': '2024-01-15T11:15:00Z',
                    'word_count': 980,
                    'language': 'it',
                    'keywords': ['IVA', '2024', 'disciplina'],
                    'legal_references': ['D.P.R. 633/1972']
                },
                'processing_stats': {
                    'content_length': 4123,
                    'word_count': 980,
                    'processing_time': '2024-01-15T12:05:00Z',
                    'extraction_method': 'pdf'
                },
                'success': True
            },
            {
                'url': 'https://www.inps.it/circolari-messaggi/messaggio-numero-150-del-15-01-2024.html',
                'title': 'Messaggio n. 150 del 15/01/2024',
                'content': 'Si comunica che a decorrere dal 1° marzo 2024 i contributi previdenziali...',
                'content_hash': 'ghi789jkl012',
                'document_type': 'html',
                'metadata': {
                    'document_number': '150',
                    'document_type': 'messaggio',
                    'authority': 'INPS',
                    'published_date': '2024-01-15T11:30:00Z',
                    'word_count': 750,
                    'language': 'it',
                    'keywords': ['contributi', 'previdenziali', 'marzo'],
                    'legal_references': ['Legge 104/1992']
                },
                'processing_stats': {
                    'content_length': 3456,
                    'word_count': 750,
                    'processing_time': '2024-01-15T12:10:00Z',
                    'extraction_method': 'html'
                },
                'success': True
            }
        ]

    @pytest.mark.asyncio
    async def test_successful_document_parsing_and_extraction(self, sample_parsed_feeds_context, sample_extracted_documents):
        """Test successful document parsing and text/metadata extraction."""
        with patch('app.orchestrators.docs.rag_step_log') as mock_log, \
             patch('app.orchestrators.docs.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.docs._extract_text_and_metadata') as mock_extract:

            # Setup mocks
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_extract.return_value = {
                'status': 'completed',
                'documents_processed': 3,
                'successful_extractions': 3,
                'failed_extractions': 0,
                'documents_extracted': sample_extracted_documents,
                'processing_summary': {
                    'successful_extractions': 3,
                    'failed_extractions': 0,
                    'total_content_length': 12813,
                    'total_word_count': 2980,
                    'processing_time_seconds': 15.2
                }
            }

            # Execute step
            result = await step_134__parse_docs(ctx=sample_parsed_feeds_context)

            # Verify orchestration
            assert result is not None
            assert result['step'] == 134
            assert result['status'] == 'completed'
            assert result['documents_processed'] == 3
            assert result['successful_extractions'] == 3

            # Verify extracted documents
            assert 'extracted_documents' in result
            assert len(result['extracted_documents']) == 3

            # Verify routing to next step (KnowledgeStore)
            assert result['next_step'] == 'KnowledgeStore'
            assert result['next_step_context'] is not None

            # Verify observability
            mock_log.assert_called()
            mock_timer.assert_called_with(134, 'RAG.docs.extract.text.and.metadata', 'ParseDocs', stage="start")

    @pytest.mark.asyncio
    async def test_document_parsing_with_no_feeds_provided(self):
        """Test handling when no parsed feeds are provided."""
        ctx = {
            'request_id': 'parse-test-no-feeds',
            'parsed_feeds': [],
            'total_items_parsed': 0,
            'feed_sources': []
        }

        with patch('app.orchestrators.docs.rag_step_log') as mock_log, \
             patch('app.orchestrators.docs.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            result = await step_134__parse_docs(ctx=ctx)

            # Should complete without error but no processing
            assert result['status'] == 'completed'
            assert result['documents_processed'] == 0
            assert result['successful_extractions'] == 0
            assert result['next_step'] is None  # No routing to next step

    @pytest.mark.asyncio
    async def test_document_parsing_with_extraction_failures(self):
        """Test handling of partial document extraction failures."""
        ctx = {
            'request_id': 'parse-test-partial-fail',
            'parsed_feeds': [
                {
                    'feed_name': 'agenzia_entrate_circolari',
                    'items': [
                        {
                            'title': 'Valid Document',
                            'link': 'https://www.agenziaentrate.gov.it/portale/documents/valid.pdf',
                            'summary': 'Valid document content'
                        },
                        {
                            'title': 'Invalid Document',
                            'link': 'https://invalid-url.example.com/nonexistent.pdf',
                            'summary': 'Invalid document'
                        }
                    ],
                    'items_parsed': 2
                }
            ],
            'total_items_parsed': 2,
            'feed_sources': ['agenzia_entrate']
        }

        with patch('app.orchestrators.docs.rag_step_log') as mock_log, \
             patch('app.orchestrators.docs.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.docs._extract_text_and_metadata') as mock_extract:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_extract.return_value = {
                'status': 'completed',
                'documents_processed': 2,
                'successful_extractions': 1,
                'failed_extractions': 1,
                'documents_extracted': [
                    {
                        'url': 'https://www.agenziaentrate.gov.it/portale/documents/valid.pdf',
                        'title': 'Valid Document',
                        'success': True,
                        'content': 'Valid document content...',
                        'metadata': {'word_count': 100}
                    }
                ],
                'processing_summary': {
                    'successful_extractions': 1,
                    'failed_extractions': 1
                },
                'errors': ['Failed to extract from invalid URL']
            }

            result = await step_134__parse_docs(ctx=ctx)

            # Should succeed with partial results
            assert result['status'] == 'completed'
            assert result['documents_processed'] == 2
            assert result['successful_extractions'] == 1
            assert result['failed_extractions'] == 1
            assert result['next_step'] == 'KnowledgeStore'
            assert 'processing_errors' in result

    @pytest.mark.asyncio
    async def test_document_processing_service_exception(self):
        """Test handling of document processing service exceptions."""
        ctx = {
            'request_id': 'parse-test-exception',
            'parsed_feeds': [
                {
                    'feed_name': 'agenzia_entrate_circolari',
                    'items': [
                        {
                            'title': 'Test Document',
                            'link': 'https://www.agenziaentrate.gov.it/portale/documents/test.pdf',
                            'summary': 'Test document'
                        }
                    ],
                    'items_parsed': 1
                }
            ],
            'total_items_parsed': 1,
            'feed_sources': ['agenzia_entrate']
        }

        with patch('app.orchestrators.docs.rag_step_log') as mock_log, \
             patch('app.orchestrators.docs.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.docs._extract_text_and_metadata') as mock_extract:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Simulate service exception
            mock_extract.side_effect = Exception("Document processing service unavailable")

            result = await step_134__parse_docs(ctx=ctx)

            assert result is not None
            assert result['status'] == 'error'
            assert 'error' in result
            assert 'document processing service unavailable' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_different_document_types_processing(self):
        """Test document processing with different document types."""
        test_cases = [
            ('pdf', 'https://example.com/doc.pdf'),
            ('html', 'https://example.com/doc.html'),
            ('xml', 'https://example.com/doc.xml')
        ]

        for doc_type, doc_url in test_cases:
            ctx = {
                'request_id': f'parse-test-{doc_type}',
                'parsed_feeds': [
                    {
                        'feed_name': f'test_{doc_type}',
                        'items': [
                            {
                                'title': f'Test {doc_type.upper()} Document',
                                'link': doc_url,
                                'summary': f'Test {doc_type} content'
                            }
                        ],
                        'items_parsed': 1
                    }
                ],
                'total_items_parsed': 1,
                'feed_sources': ['test_source']
            }

            with patch('app.orchestrators.docs.rag_step_log'), \
                 patch('app.orchestrators.docs.rag_step_timer') as mock_timer, \
                 patch('app.orchestrators.docs._extract_text_and_metadata') as mock_extract:

                mock_timer.return_value.__enter__ = MagicMock()
                mock_timer.return_value.__exit__ = MagicMock()

                mock_extract.return_value = {
                    'status': 'completed',
                    'documents_processed': 1,
                    'successful_extractions': 1,
                    'failed_extractions': 0,
                    'documents_extracted': [
                        {
                            'url': doc_url,
                            'document_type': doc_type,
                            'success': True,
                            'content': f'Test {doc_type} content...',
                            'metadata': {'document_type': doc_type}
                        }
                    ],
                    'processing_summary': {
                        'successful_extractions': 1,
                        'failed_extractions': 0
                    }
                }

                result = await step_134__parse_docs(ctx=ctx)

                assert result['status'] == 'completed'
                assert result['documents_processed'] == 1
                assert result['successful_extractions'] == 1


class TestStep134ParseDocsIntegration:
    """Integration tests for Step 134 in the RAG workflow."""

    @pytest.mark.asyncio
    async def test_step133_to_step134_to_knowledgestore_flow(self):
        """Test integration from Step 133 to Step 134 to KnowledgeStore."""
        # Context as would be passed from Step 133
        step133_output = {
            'request_id': 'integration-parse-001',
            'previous_step': 133,
            'parsed_feeds': [
                {
                    'feed_name': 'agenzia_entrate_circolari',
                    'items': [
                        {
                            'title': 'Circolare Fiscale',
                            'link': 'https://www.agenziaentrate.gov.it/portale/documents/circolare.pdf',
                            'summary': 'Normativa fiscale aggiornata'
                        }
                    ],
                    'items_parsed': 1
                }
            ],
            'total_items_parsed': 1,
            'feed_sources': ['agenzia_entrate']
        }

        with patch('app.orchestrators.docs.rag_step_log'), \
             patch('app.orchestrators.docs.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.docs._extract_text_and_metadata') as mock_extract:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_extract.return_value = {
                'status': 'completed',
                'documents_processed': 1,
                'successful_extractions': 1,
                'failed_extractions': 0,
                'documents_extracted': [
                    {
                        'url': 'https://www.agenziaentrate.gov.it/portale/documents/circolare.pdf',
                        'title': 'Circolare Fiscale',
                        'content': 'Normativa fiscale dettagliata...',
                        'metadata': {'authority': 'Agenzia delle Entrate', 'word_count': 500},
                        'success': True
                    }
                ],
                'processing_summary': {'successful_extractions': 1}
            }

            result = await step_134__parse_docs(ctx=step133_output)

            # Verify flow progression to KnowledgeStore
            assert result['step'] == 134
            assert result['next_step'] == 'KnowledgeStore'
            assert result['next_step_context'] is not None

            # Verify data preparation for KnowledgeStore
            assert 'extracted_documents' in result['next_step_context']
            assert result['next_step_context']['documents_count'] == 1

    @pytest.mark.asyncio
    async def test_background_scheduled_document_processing(self):
        """Test document processing in background scheduled context."""
        scheduled_ctx = {
            'request_id': 'scheduled-parse-002',
            'trigger': 'scheduled',
            'parsed_feeds': [
                {
                    'feed_name': 'agenzia_entrate_circolari',
                    'items': [
                        {
                            'title': 'High Priority Document',
                            'link': 'https://www.agenziaentrate.gov.it/documents/high-priority.pdf',
                            'priority': 'high'
                        },
                        {
                            'title': 'Regular Document',
                            'link': 'https://www.agenziaentrate.gov.it/documents/regular.pdf',
                            'priority': 'normal'
                        }
                    ],
                    'items_parsed': 2
                }
            ],
            'total_items_parsed': 2,
            'feed_sources': ['agenzia_entrate'],
            'processing_config': {
                'priority_processing': True,
                'max_concurrent_documents': 5,
                'timeout_seconds': 60
            }
        }

        with patch('app.orchestrators.docs.rag_step_log'), \
             patch('app.orchestrators.docs.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.docs._extract_text_and_metadata') as mock_extract:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_extract.return_value = {
                'status': 'completed',
                'documents_processed': 2,
                'successful_extractions': 2,
                'failed_extractions': 0,
                'documents_extracted': [
                    {'url': 'https://www.agenziaentrate.gov.it/documents/high-priority.pdf', 'success': True},
                    {'url': 'https://www.agenziaentrate.gov.it/documents/regular.pdf', 'success': True}
                ],
                'processing_summary': {
                    'successful_extractions': 2,
                    'failed_extractions': 0,
                    'total_processing_time_seconds': 25.8
                }
            }

            result = await step_134__parse_docs(ctx=scheduled_ctx)

            # Verify scheduled processing
            assert result['status'] == 'completed'
            assert result['documents_processed'] == 2
            assert result['next_step'] == 'KnowledgeStore'

    @pytest.mark.asyncio
    async def test_manual_triggered_document_processing(self):
        """Test manually triggered document processing workflow."""
        manual_ctx = {
            'request_id': 'manual-parse-003',
            'trigger': 'manual',
            'parsed_feeds': [
                {
                    'feed_name': 'gazzetta_ufficiale_serie_generale',
                    'items': [
                        {
                            'title': 'Decreto Ministeriale',
                            'link': 'https://www.gazzettaufficiale.it/decreto-ministeriale-2024.pdf',
                            'user_requested': True,
                            'processing_options': {
                                'full_text_extraction': True,
                                'enhanced_metadata': True,
                                'legal_reference_extraction': True
                            }
                        }
                    ],
                    'items_parsed': 1
                }
            ],
            'total_items_parsed': 1,
            'feed_sources': ['gazzetta_ufficiale']
        }

        with patch('app.orchestrators.docs.rag_step_log'), \
             patch('app.orchestrators.docs.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.docs._extract_text_and_metadata') as mock_extract:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_extract.return_value = {
                'status': 'completed',
                'documents_processed': 1,
                'successful_extractions': 1,
                'failed_extractions': 0,
                'documents_extracted': [
                    {
                        'url': 'https://www.gazzettaufficiale.it/decreto-ministeriale-2024.pdf',
                        'title': 'Decreto Ministeriale',
                        'enhanced_extraction': True,
                        'metadata': {
                            'legal_references': ['D.M. 123/2024'],
                            'enhanced': True
                        },
                        'success': True
                    }
                ],
                'processing_summary': {'successful_extractions': 1}
            }

            result = await step_134__parse_docs(ctx=manual_ctx)

            # Verify manual trigger handling
            assert result['status'] == 'completed'
            assert result['documents_processed'] == 1


class TestStep134ParseDocsParity:
    """Parity tests to ensure behavioral consistency."""

    @pytest.mark.asyncio
    async def test_document_service_behavior_preservation(self):
        """Verify orchestrator preserves document service behavior exactly."""
        ctx = {
            'request_id': 'parity-test-001',
            'parsed_feeds': [
                {
                    'feed_name': 'agenzia_entrate_circolari',
                    'items': [
                        {
                            'title': 'Test Document',
                            'link': 'https://www.agenziaentrate.gov.it/portale/documents/test.pdf',
                            'summary': 'Test document for parity'
                        }
                    ],
                    'items_parsed': 1
                }
            ],
            'total_items_parsed': 1,
            'feed_sources': ['agenzia_entrate']
        }

        with patch('app.services.document_processor.DocumentProcessor') as MockDocProcessor, \
             patch('app.orchestrators.docs.rag_step_log'), \
             patch('app.orchestrators.docs.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.docs._extract_text_and_metadata') as mock_extract:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Setup mock document service to return expected data
            mock_service = MagicMock()
            mock_service.process_document.return_value = {
                'url': 'https://www.agenziaentrate.gov.it/portale/documents/test.pdf',
                'content': 'Extracted document content...',
                'metadata': {'word_count': 100},
                'success': True
            }
            MockDocProcessor.return_value = mock_service

            mock_extract.return_value = {
                'status': 'completed',
                'documents_processed': 1,
                'successful_extractions': 1,
                'failed_extractions': 0,
                'documents_extracted': [mock_service.process_document.return_value],
                'processing_summary': {'successful_extractions': 1}
            }

            result = await step_134__parse_docs(ctx=ctx)

            # Verify orchestrator doesn't modify service behavior
            mock_extract.assert_called_once()
            assert result['status'] == 'completed'

    @pytest.mark.asyncio
    async def test_error_handling_consistency(self):
        """Verify error handling behavior matches expectations."""
        ctx = {
            'request_id': 'parity-error-test',
            'parsed_feeds': [
                {
                    'feed_name': 'invalid_feed',
                    'items': [
                        {
                            'title': 'Invalid Document',
                            'link': 'https://invalid-url.example.com/nonexistent.pdf',
                            'summary': 'Invalid document'
                        }
                    ],
                    'items_parsed': 1
                }
            ],
            'total_items_parsed': 1,
            'feed_sources': ['invalid_source']
        }

        with patch('app.orchestrators.docs.rag_step_log'), \
             patch('app.orchestrators.docs.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.docs._extract_text_and_metadata') as mock_extract:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Simulate service error
            mock_extract.side_effect = ValueError("Invalid document URL")

            result = await step_134__parse_docs(ctx=ctx)

            # Verify consistent error structure
            assert result['status'] == 'error'
            assert 'error' in result

    @pytest.mark.asyncio
    async def test_output_structure_consistency(self):
        """Verify output structure is consistent across different inputs."""
        test_scenarios = [
            {'docs': 1, 'content': 100, 'source': 'agenzia_entrate'},
            {'docs': 3, 'content': 300, 'source': 'inps'},
            {'docs': 5, 'content': 500, 'source': 'gazzetta_ufficiale'}
        ]

        for scenario in test_scenarios:
            ctx = {
                'request_id': f'parity-structure-{scenario["source"]}',
                'parsed_feeds': [
                    {
                        'feed_name': f'{scenario["source"]}_feed',
                        'items': [
                            {
                                'title': f'Document {i}',
                                'link': f'https://{scenario["source"]}.example.com/doc_{i}.pdf',
                                'summary': f'Document {i} content'
                            }
                            for i in range(scenario['docs'])
                        ],
                        'items_parsed': scenario['docs']
                    }
                ],
                'total_items_parsed': scenario['docs'],
                'feed_sources': [scenario['source']]
            }

            with patch('app.orchestrators.docs.rag_step_log'), \
                 patch('app.orchestrators.docs.rag_step_timer') as mock_timer, \
                 patch('app.orchestrators.docs._extract_text_and_metadata') as mock_extract:

                mock_timer.return_value.__enter__ = MagicMock()
                mock_timer.return_value.__exit__ = MagicMock()

                mock_extract.return_value = {
                    'status': 'completed',
                    'documents_processed': scenario['docs'],
                    'successful_extractions': scenario['docs'],
                    'failed_extractions': 0,
                    'documents_extracted': [],
                    'processing_summary': {
                        'successful_extractions': scenario['docs'],
                        'failed_extractions': 0
                    }
                }

                result = await step_134__parse_docs(ctx=ctx)

                # Verify consistent output structure
                required_keys = [
                    'step', 'status', 'documents_processed', 'successful_extractions'
                ]
                for key in required_keys:
                    assert key in result, f"Missing required key: {key} for scenario {scenario}"

                assert result['step'] == 134
                assert result['status'] == 'completed'
                assert result['documents_processed'] == scenario['docs']


if __name__ == '__main__':
    pytest.main([__file__])