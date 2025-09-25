"""
Comprehensive test suite for RAG STEP 133 — Fetch and parse sources.

Tests the orchestrator function that fetches RSS feeds and parses their content,
following MASTER_GUARDRAILS TDD methodology.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional

from app.orchestrators.platform import step_133__fetch_feeds


class TestStep133FetchFeedsUnit:
    """Unit tests for Step 133 FetchFeeds orchestrator function."""

    @pytest.fixture
    def sample_rss_context(self):
        """Sample context from Step 132 with RSS feeds to fetch."""
        return {
            'request_id': 'fetch-feeds-test-133',
            'rss_feeds': [
                {
                    'feed_name': 'agenzia_entrate_circolari',
                    'authority': 'Agenzia delle Entrate',
                    'feed_type': 'circolari',
                    'url': 'https://www.agenziaentrate.gov.it/portale/rss/circolari.xml',
                    'items_found': 5,
                    'new_items': 2,
                    'status': 'success',
                    'last_updated': '2024-01-15T12:00:00Z'
                },
                {
                    'feed_name': 'inps_messaggi',
                    'authority': 'INPS',
                    'feed_type': 'messaggi',
                    'url': 'https://www.inps.it/rss/messaggi.xml',
                    'items_found': 3,
                    'new_items': 1,
                    'status': 'success',
                    'last_updated': '2024-01-15T11:45:00Z'
                }
            ],
            'new_item_count': 3,
            'feed_sources': ['agenzia_entrate', 'inps'],
            'previous_step': 132
        }

    @pytest.fixture
    def sample_parsed_feeds(self):
        """Sample parsed feed results."""
        return [
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
        ]

    @pytest.mark.asyncio
    async def test_successful_feed_fetching_and_parsing(self, sample_rss_context, sample_parsed_feeds):
        """Test successful RSS feed fetching and parsing orchestration."""
        with patch('app.orchestrators.platform.rag_step_log') as mock_log, \
             patch('app.orchestrators.platform.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.platform._fetch_and_parse_feeds') as mock_fetch:

            # Setup mocks
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_fetch.return_value = {
                'status': 'completed',
                'feeds_processed': 2,
                'total_items_parsed': 3,
                'parsed_feeds': sample_parsed_feeds,
                'processing_summary': {
                    'successful_feeds': 2,
                    'failed_feeds': 0,
                    'total_processing_time_seconds': 8.5
                }
            }

            # Execute step
            result = await step_133__fetch_feeds(ctx=sample_rss_context)

            # Verify orchestration
            assert result is not None
            assert result['step'] == 133
            assert result['status'] == 'completed'
            assert result['feeds_fetched'] == 2
            assert result['total_items_parsed'] == 3

            # Verify parsing results
            assert 'parsed_feeds' in result
            assert len(result['parsed_feeds']) == 2

            # Verify routing to next step
            assert result['next_step'] == 134  # ParseDocs
            assert result['next_step_context'] is not None

            # Verify observability
            mock_log.assert_called()
            mock_timer.assert_called_with(133, 'RAG.platform.fetch.and.parse.sources', 'FetchFeeds', stage="start")

    @pytest.mark.asyncio
    async def test_feed_fetching_with_no_feeds_provided(self):
        """Test handling when no RSS feeds are provided."""
        ctx = {
            'request_id': 'fetch-test-no-feeds',
            'rss_feeds': [],
            'new_item_count': 0,
            'feed_sources': []
        }

        with patch('app.orchestrators.platform.rag_step_log') as mock_log, \
             patch('app.orchestrators.platform.rag_step_timer') as mock_timer:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            result = await step_133__fetch_feeds(ctx=ctx)

            # Should complete without error but no processing
            assert result['status'] == 'completed'
            assert result['feeds_fetched'] == 0
            assert result['total_items_parsed'] == 0
            assert result['next_step'] is None  # No routing to next step

    @pytest.mark.asyncio
    async def test_feed_fetching_with_partial_failures(self):
        """Test handling of partial RSS feed fetching failures."""
        ctx = {
            'request_id': 'fetch-test-partial-fail',
            'rss_feeds': [
                {
                    'feed_name': 'agenzia_entrate_circolari',
                    'url': 'https://www.agenziaentrate.gov.it/portale/rss/circolari.xml',
                    'authority': 'Agenzia delle Entrate'
                },
                {
                    'feed_name': 'failed_feed',
                    'url': 'https://invalid-feed.example.com/rss.xml',
                    'authority': 'Invalid Authority'
                }
            ],
            'new_item_count': 2,
            'feed_sources': ['agenzia_entrate', 'failed_source']
        }

        with patch('app.orchestrators.platform.rag_step_log') as mock_log, \
             patch('app.orchestrators.platform.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.platform._fetch_and_parse_feeds') as mock_fetch:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_fetch.return_value = {
                'status': 'completed',
                'feeds_processed': 1,
                'total_items_parsed': 2,
                'parsed_feeds': [
                    {
                        'feed_name': 'agenzia_entrate_circolari',
                        'parsing_status': 'success',
                        'items_parsed': 2
                    }
                ],
                'processing_summary': {
                    'successful_feeds': 1,
                    'failed_feeds': 1
                },
                'errors': [
                    'Failed to fetch feed: https://invalid-feed.example.com/rss.xml'
                ]
            }

            result = await step_133__fetch_feeds(ctx=ctx)

            # Should succeed with partial results
            assert result['status'] == 'completed'
            assert result['feeds_fetched'] == 1
            assert result['next_step'] == 134
            assert 'processing_errors' in result

    @pytest.mark.asyncio
    async def test_feed_service_exception(self):
        """Test handling of feed service exceptions."""
        ctx = {
            'request_id': 'fetch-test-exception',
            'rss_feeds': [
                {
                    'feed_name': 'agenzia_entrate_circolari',
                    'url': 'https://www.agenziaentrate.gov.it/portale/rss/circolari.xml',
                    'authority': 'Agenzia delle Entrate'
                }
            ],
            'new_item_count': 1,
            'feed_sources': ['agenzia_entrate']
        }

        with patch('app.orchestrators.platform.rag_step_log') as mock_log, \
             patch('app.orchestrators.platform.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.platform._fetch_and_parse_feeds') as mock_fetch:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Simulate service exception
            mock_fetch.side_effect = Exception("Feed service unavailable")

            result = await step_133__fetch_feeds(ctx=ctx)

            assert result is not None
            assert result['status'] == 'error'
            assert 'error' in result
            assert 'feed service unavailable' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_different_feed_types_processing(self):
        """Test RSS feed processing with different feed types."""
        test_cases = [
            ('agenzia_entrate', ['circolari', 'risoluzioni']),
            ('inps', ['messaggi', 'circolari']),
            ('gazzetta_ufficiale', ['serie_generale'])
        ]

        for authority, feed_types in test_cases:
            ctx = {
                'request_id': f'fetch-test-{authority}',
                'rss_feeds': [
                    {
                        'feed_name': f'{authority}_{feed_type}',
                        'authority': authority.title(),
                        'feed_type': feed_type,
                        'url': f'https://{authority}.example.com/{feed_type}.xml'
                    }
                    for feed_type in feed_types
                ],
                'new_item_count': len(feed_types),
                'feed_sources': [authority]
            }

            with patch('app.orchestrators.platform.rag_step_log'), \
                 patch('app.orchestrators.platform.rag_step_timer') as mock_timer, \
                 patch('app.orchestrators.platform._fetch_and_parse_feeds') as mock_fetch:

                mock_timer.return_value.__enter__ = MagicMock()
                mock_timer.return_value.__exit__ = MagicMock()

                mock_fetch.return_value = {
                    'status': 'completed',
                    'feeds_processed': len(feed_types),
                    'total_items_parsed': len(feed_types) * 2,  # Mock 2 items per feed
                    'parsed_feeds': [],
                    'processing_summary': {
                        'successful_feeds': len(feed_types),
                        'failed_feeds': 0
                    }
                }

                result = await step_133__fetch_feeds(ctx=ctx)

                assert result['status'] == 'completed'
                assert result['feeds_fetched'] == len(feed_types)


class TestStep133FetchFeedsIntegration:
    """Integration tests for Step 133 in the RAG workflow."""

    @pytest.mark.asyncio
    async def test_step132_to_step133_to_step134_flow(self):
        """Test integration from Step 132 to Step 133 to Step 134."""
        # Context as would be passed from Step 132
        step132_output = {
            'request_id': 'integration-fetch-001',
            'previous_step': 132,
            'rss_feeds': [
                {
                    'feed_name': 'agenzia_entrate_circolari',
                    'url': 'https://www.agenziaentrate.gov.it/portale/rss/circolari.xml',
                    'authority': 'Agenzia delle Entrate',
                    'new_items': 3
                }
            ],
            'new_item_count': 3,
            'feed_sources': ['agenzia_entrate']
        }

        with patch('app.orchestrators.platform.rag_step_log'), \
             patch('app.orchestrators.platform.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.platform._fetch_and_parse_feeds') as mock_fetch:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_fetch.return_value = {
                'status': 'completed',
                'feeds_processed': 1,
                'total_items_parsed': 3,
                'parsed_feeds': [
                    {
                        'feed_name': 'agenzia_entrate_circolari',
                        'items': [
                            {'title': 'Document 1', 'link': 'https://...'},
                            {'title': 'Document 2', 'link': 'https://...'},
                            {'title': 'Document 3', 'link': 'https://...'}
                        ],
                        'items_parsed': 3
                    }
                ],
                'processing_summary': {'successful_feeds': 1}
            }

            result = await step_133__fetch_feeds(ctx=step132_output)

            # Verify flow progression to ParseDocs (Step 134)
            assert result['step'] == 133
            assert result['next_step'] == 134
            assert result['next_step_context'] is not None

            # Verify data preparation for ParseDocs step
            assert 'parsed_feeds' in result['next_step_context']
            assert result['next_step_context']['total_items_parsed'] == 3

    @pytest.mark.asyncio
    async def test_background_scheduled_feed_processing(self):
        """Test RSS feed processing in background scheduled context."""
        scheduled_ctx = {
            'request_id': 'scheduled-fetch-002',
            'trigger': 'scheduled',
            'rss_feeds': [
                {
                    'feed_name': 'agenzia_entrate_circolari',
                    'url': 'https://www.agenziaentrate.gov.it/portale/rss/circolari.xml',
                    'priority': 'high',
                    'last_processed': '2024-01-15T08:00:00Z'
                },
                {
                    'feed_name': 'inps_messaggi',
                    'url': 'https://www.inps.it/rss/messaggi.xml',
                    'priority': 'medium',
                    'last_processed': '2024-01-15T07:30:00Z'
                }
            ],
            'new_item_count': 5,
            'feed_sources': ['agenzia_entrate', 'inps'],
            'processing_config': {
                'priority_processing': True,
                'max_concurrent_feeds': 10,
                'timeout_seconds': 30
            }
        }

        with patch('app.orchestrators.platform.rag_step_log'), \
             patch('app.orchestrators.platform.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.platform._fetch_and_parse_feeds') as mock_fetch:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_fetch.return_value = {
                'status': 'completed',
                'feeds_processed': 2,
                'total_items_parsed': 5,
                'parsed_feeds': [
                    {'feed_name': 'agenzia_entrate_circolari', 'items_parsed': 3},
                    {'feed_name': 'inps_messaggi', 'items_parsed': 2}
                ],
                'processing_summary': {
                    'successful_feeds': 2,
                    'failed_feeds': 0,
                    'total_processing_time_seconds': 12.3
                }
            }

            result = await step_133__fetch_feeds(ctx=scheduled_ctx)

            # Verify scheduled processing
            assert result['status'] == 'completed'
            assert result['feeds_fetched'] == 2
            assert result['next_step'] == 134

    @pytest.mark.asyncio
    async def test_manual_triggered_feed_processing(self):
        """Test manually triggered RSS feed processing workflow."""
        manual_ctx = {
            'request_id': 'manual-fetch-003',
            'trigger': 'manual',
            'rss_feeds': [
                {
                    'feed_name': 'gazzetta_ufficiale_serie_generale',
                    'url': 'https://www.gazzettaufficiale.it/rss/serie_generale.xml',
                    'user_requested': True,
                    'processing_options': {
                        'include_historical': True,
                        'date_range': {
                            'start_date': '2024-01-01',
                            'end_date': '2024-01-15'
                        }
                    }
                }
            ],
            'new_item_count': 8,
            'feed_sources': ['gazzetta_ufficiale']
        }

        with patch('app.orchestrators.platform.rag_step_log'), \
             patch('app.orchestrators.platform.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.platform._fetch_and_parse_feeds') as mock_fetch:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_fetch.return_value = {
                'status': 'completed',
                'feeds_processed': 1,
                'total_items_parsed': 8,
                'parsed_feeds': [
                    {
                        'feed_name': 'gazzetta_ufficiale_serie_generale',
                        'items_parsed': 8,
                        'date_filtered': True
                    }
                ],
                'processing_summary': {'successful_feeds': 1}
            }

            result = await step_133__fetch_feeds(ctx=manual_ctx)

            # Verify manual trigger handling
            assert result['status'] == 'completed'
            assert result['total_items_parsed'] == 8


class TestStep133FetchFeedsParity:
    """Parity tests to ensure behavioral consistency."""

    @pytest.mark.asyncio
    async def test_feed_service_behavior_preservation(self):
        """Verify orchestrator preserves feed service behavior exactly."""
        ctx = {
            'request_id': 'parity-test-001',
            'rss_feeds': [
                {
                    'feed_name': 'agenzia_entrate_circolari',
                    'url': 'https://www.agenziaentrate.gov.it/portale/rss/circolari.xml',
                    'authority': 'Agenzia delle Entrate'
                }
            ],
            'new_item_count': 2,
            'feed_sources': ['agenzia_entrate']
        }

        with patch('app.services.rss_feed_monitor.RSSFeedMonitor') as MockRSSMonitor, \
             patch('app.orchestrators.platform.rag_step_log'), \
             patch('app.orchestrators.platform.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.platform._fetch_and_parse_feeds') as mock_fetch:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Setup mock RSS service to return expected data
            mock_service = MagicMock()
            mock_service.parse_feed_with_error_handling.return_value = [
                {'title': 'Document 1', 'link': 'https://...'},
                {'title': 'Document 2', 'link': 'https://...'}
            ]
            MockRSSMonitor.return_value = mock_service

            mock_fetch.return_value = {
                'status': 'completed',
                'feeds_processed': 1,
                'total_items_parsed': 2,
                'parsed_feeds': [],
                'processing_summary': {'successful_feeds': 1}
            }

            result = await step_133__fetch_feeds(ctx=ctx)

            # Verify orchestrator doesn't modify service behavior
            mock_fetch.assert_called_once()
            assert result['status'] == 'completed'

    @pytest.mark.asyncio
    async def test_error_handling_consistency(self):
        """Verify error handling behavior matches expectations."""
        ctx = {
            'request_id': 'parity-error-test',
            'rss_feeds': [
                {
                    'feed_name': 'invalid_feed',
                    'url': 'https://invalid-url.example.com/feed.xml',
                    'authority': 'Invalid Authority'
                }
            ],
            'new_item_count': 1,
            'feed_sources': ['invalid_source']
        }

        with patch('app.orchestrators.platform.rag_step_log'), \
             patch('app.orchestrators.platform.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.platform._fetch_and_parse_feeds') as mock_fetch:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Simulate service error
            mock_fetch.side_effect = ValueError("Invalid feed URL")

            result = await step_133__fetch_feeds(ctx=ctx)

            # Verify consistent error structure
            assert result['status'] == 'error'
            assert 'error' in result

    @pytest.mark.asyncio
    async def test_output_structure_consistency(self):
        """Verify output structure is consistent across different inputs."""
        test_scenarios = [
            {'feeds': 1, 'items': 2, 'source': 'agenzia_entrate'},
            {'feeds': 2, 'items': 5, 'source': 'inps'},
            {'feeds': 3, 'items': 8, 'source': 'gazzetta_ufficiale'}
        ]

        for scenario in test_scenarios:
            ctx = {
                'request_id': f'parity-structure-{scenario["source"]}',
                'rss_feeds': [
                    {
                        'feed_name': f'{scenario["source"]}_feed_{i}',
                        'url': f'https://{scenario["source"]}.example.com/feed_{i}.xml',
                        'authority': scenario["source"].title()
                    }
                    for i in range(scenario['feeds'])
                ],
                'new_item_count': scenario['items'],
                'feed_sources': [scenario['source']]
            }

            with patch('app.orchestrators.platform.rag_step_log'), \
                 patch('app.orchestrators.platform.rag_step_timer') as mock_timer, \
                 patch('app.orchestrators.platform._fetch_and_parse_feeds') as mock_fetch:

                mock_timer.return_value.__enter__ = MagicMock()
                mock_timer.return_value.__exit__ = MagicMock()

                mock_fetch.return_value = {
                    'status': 'completed',
                    'feeds_processed': scenario['feeds'],
                    'total_items_parsed': scenario['items'],
                    'parsed_feeds': [],
                    'processing_summary': {'successful_feeds': scenario['feeds']}
                }

                result = await step_133__fetch_feeds(ctx=ctx)

                # Verify consistent output structure
                required_keys = [
                    'step', 'status', 'feeds_fetched', 'total_items_parsed'
                ]
                for key in required_keys:
                    assert key in result, f"Missing required key: {key} for scenario {scenario}"

                assert result['step'] == 133
                assert result['status'] == 'completed'
                assert result['feeds_fetched'] == scenario['feeds']


if __name__ == '__main__':
    pytest.main([__file__])