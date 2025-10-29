"""
Comprehensive test suite for RAG STEP 132 — RSS Monitor.

Tests the orchestrator function that initiates RSS feed monitoring for Italian
regulatory sources and CCNL updates, following MASTER_GUARDRAILS TDD methodology.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional

from app.orchestrators.kb import step_132__rssmonitor


class TestStep132RSSMonitorUnit:
    """Unit tests for Step 132 RSSMonitor orchestrator function."""

    @pytest.fixture
    def sample_rss_monitor_context(self):
        """Sample context for RSS monitoring operation."""
        return {
            'request_id': 'rss-monitor-test-132',
            'monitor_type': 'italian',
            'sources': ['agenzia_entrate', 'inps', 'gazzetta_ufficiale'],
            'last_check': '2024-01-15T10:00:00Z',
            'monitoring_config': {
                'check_interval_hours': 2,
                'max_concurrent_feeds': 10,
                'include_ccnl_specific': True,
                'content_languages': ['it'],
                'feed_timeout_seconds': 30
            }
        }

    @pytest.fixture
    def sample_feed_results(self):
        """Sample RSS feed monitoring results."""
        return [
            {
                'feed_name': 'agenzia_entrate_circolari',
                'authority': 'Agenzia delle Entrate',
                'feed_type': 'circolari',
                'url': 'https://www.agenziaentrate.gov.it/portale/rss/circolari.xml',
                'items_found': 5,
                'new_items': 2,
                'status': 'success',
                'last_updated': '2024-01-15T12:00:00Z',
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
                ]
            },
            {
                'feed_name': 'inps_messaggi',
                'authority': 'INPS',
                'feed_type': 'messaggi',
                'url': 'https://www.inps.it/rss/messaggi.xml',
                'items_found': 3,
                'new_items': 1,
                'status': 'success',
                'last_updated': '2024-01-15T11:45:00Z',
                'items': [
                    {
                        'title': 'Messaggio n. 150 del 15/01/2024',
                        'link': 'https://www.inps.it/circolari-messaggi/messaggio-numero-150-del-15-01-2024.html',
                        'published': '2024-01-15T11:30:00Z',
                        'summary': 'Aggiornamenti contributi previdenziali',
                        'document_number': '150',
                        'document_type': 'messaggio'
                    }
                ]
            }
        ]

    @pytest.mark.asyncio
    async def test_successful_rss_monitoring_initiation(self, sample_rss_monitor_context, sample_feed_results):
        """Test successful RSS monitoring orchestration."""
        with patch('app.orchestrators.kb.rag_step_log') as mock_log, \
             patch('app.orchestrators.kb.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.kb._coordinate_rss_monitoring') as mock_monitor:

            # Setup mocks
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_monitor.return_value = {
                'status': 'completed',
                'has_new_items': True,
                'feeds': sample_feed_results,
                'new_item_count': 3,
                'feed_sources': ['agenzia_entrate', 'inps']
            }

            # Execute step
            result = await step_132__rssmonitor(ctx=sample_rss_monitor_context)

            # Verify orchestration
            assert result is not None
            assert result['step'] == 132
            assert result['status'] == 'completed'
            assert result['monitoring_result']['has_new_items'] == True

            # Verify monitoring results
            assert result['monitoring_result']['new_item_count'] == 3
            assert 'feeds' in result['monitoring_result']

            # Verify routing to next step
            assert result['next_step'] == 133  # FetchFeeds
            assert result['next_step_context'] is not None

            # Verify observability
            mock_log.assert_called()
            mock_timer.assert_called_with(132, 'RAG.kb.rss.monitor', 'RSSMonitor', stage="start")

    @pytest.mark.asyncio
    async def test_rss_monitoring_with_no_new_items(self):
        """Test RSS monitoring when no new items are found."""
        ctx = {
            'request_id': 'rss-test-no-items',
            'monitor_type': 'ccnl',
            'sources': ['ccnl_feeds']
        }

        with patch('app.orchestrators.kb.rag_step_log') as mock_log, \
             patch('app.orchestrators.kb.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.kb._coordinate_rss_monitoring') as mock_monitor:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_monitor.return_value = {
                'status': 'completed',
                'has_new_items': False,
                'feeds': [],
                'new_item_count': 0,
                'feed_sources': ['ccnl_feeds']
            }

            result = await step_132__rssmonitor(ctx=ctx)

            # Should still succeed but not route to next step
            assert result['status'] == 'completed'
            assert result['monitoring_result']['new_item_count'] == 0
            assert result['next_step'] is None

    @pytest.mark.asyncio
    async def test_rss_monitoring_with_partial_failures(self):
        """Test handling of partial RSS feed failures."""
        ctx = {
            'request_id': 'rss-test-partial-fail',
            'monitor_type': 'italian',
            'sources': ['agenzia_entrate', 'failed_source']
        }

        with patch('app.orchestrators.kb.rag_step_log') as mock_log, \
             patch('app.orchestrators.kb.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.kb._coordinate_rss_monitoring') as mock_monitor:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_monitor.return_value = {
                'status': 'completed',
                'has_new_items': True,
                'feeds': [
                    {
                        'feed_name': 'agenzia_entrate_circolari',
                        'status': 'success',
                        'items_found': 3,
                        'new_items': 1
                    }
                ],
                'new_item_count': 1,
                'feed_sources': ['agenzia_entrate'],
                'errors': [
                    'Connection timeout'
                ]
            }

            result = await step_132__rssmonitor(ctx=ctx)

            # Should still succeed with partial results
            assert result['status'] == 'completed'
            assert result['monitoring_result']['new_item_count'] == 1
            assert result['next_step'] == 133
            assert result['monitoring_result']['errors'] is not None

    @pytest.mark.asyncio
    async def test_missing_monitor_configuration(self):
        """Test handling of missing monitoring configuration."""
        ctx = {
            'request_id': 'rss-test-no-config',
            # Missing monitor_type - should default to 'all'
        }

        with patch('app.orchestrators.kb.rag_step_log') as mock_log, \
             patch('app.orchestrators.kb._coordinate_rss_monitoring') as mock_monitor:

            mock_monitor.return_value = {
                'status': 'completed',
                'has_new_items': False,
                'feeds': [],
                'new_item_count': 0,
                'feed_sources': []
            }

            result = await step_132__rssmonitor(ctx=ctx)

            assert result is not None
            assert result['status'] == 'completed'
            # With default monitor_type='all', it should still work
            assert result['monitoring_result']['has_new_items'] == False

    @pytest.mark.asyncio
    async def test_rss_monitoring_service_exception(self):
        """Test handling of RSS monitoring service exceptions."""
        ctx = {
            'request_id': 'rss-test-exception',
            'monitor_type': 'italian',
            'sources': ['agenzia_entrate']
        }

        with patch('app.orchestrators.kb.rag_step_log') as mock_log, \
             patch('app.orchestrators.kb.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.kb._coordinate_rss_monitoring') as mock_monitor:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Simulate service exception
            mock_monitor.side_effect = Exception("RSS service unavailable")

            result = await step_132__rssmonitor(ctx=ctx)

            assert result is not None
            assert result['status'] == 'error'
            assert 'error' in result
            assert 'rss service unavailable' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_different_monitor_types(self):
        """Test RSS monitoring with different monitor types."""
        test_cases = [
            ('italian', ['agenzia_entrate', 'inps', 'gazzetta_ufficiale']),
            ('ccnl', ['ccnl_feeds']),
            ('all', ['regulatory', 'ccnl'])
        ]

        for monitor_type, sources in test_cases:
            ctx = {
                'request_id': f'rss-test-{monitor_type}',
                'monitor_type': monitor_type,
                'sources': sources
            }

            with patch('app.orchestrators.kb.rag_step_log'), \
                 patch('app.orchestrators.kb.rag_step_timer') as mock_timer, \
                 patch('app.orchestrators.kb._coordinate_rss_monitoring') as mock_monitor:

                mock_timer.return_value.__enter__ = MagicMock()
                mock_timer.return_value.__exit__ = MagicMock()

                mock_monitor.return_value = {
                    'status': 'completed',
                    'has_new_items': True,
                    'feeds': [],
                    'new_item_count': 2,
                    'feed_sources': sources
                }

                result = await step_132__rssmonitor(ctx=ctx)

                assert result['status'] == 'completed'
                assert result['monitoring_result']['new_item_count'] == 2


class TestStep132RSSMonitorIntegration:
    """Integration tests for Step 132 in the RAG workflow."""

    @pytest.mark.asyncio
    async def test_rss_monitor_to_fetch_feeds_flow(self):
        """Test integration from RSSMonitor step to FetchFeeds step."""
        # Context as would be triggered by background scheduler
        scheduler_ctx = {
            'request_id': 'integration-rss-001',
            'trigger': 'scheduled',
            'monitor_type': 'italian',
            'sources': ['agenzia_entrate', 'inps'],
            'scheduling_info': {
                'last_run': '2024-01-15T08:00:00Z',
                'next_scheduled': '2024-01-15T10:00:00Z',
                'interval_hours': 2
            }
        }

        with patch('app.orchestrators.kb.rag_step_log'), \
             patch('app.orchestrators.kb.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.kb._coordinate_rss_monitoring') as mock_monitor:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_monitor.return_value = {
                'status': 'completed',
                'has_new_items': True,
                'feeds': [
                    {
                        'feed_name': 'agenzia_entrate_circolari',
                        'new_items': 3,
                        'items': [
                            {'title': 'Circolare n. 1/E', 'link': 'https://...'},
                            {'title': 'Circolare n. 2/E', 'link': 'https://...'},
                            {'title': 'Circolare n. 3/E', 'link': 'https://...'}
                        ]
                    }
                ],
                'new_item_count': 3,
                'feed_sources': ['agenzia_entrate', 'inps']
            }

            result = await step_132__rssmonitor(ctx=scheduler_ctx)

            # Verify flow progression to FetchFeeds
            assert result['step'] == 132
            assert result['next_step'] == 133  # FetchFeeds

            # Verify data preparation for FetchFeeds step
            assert result['next_step_context'] is not None
            assert result['next_step_context']['new_item_count'] == 3

    @pytest.mark.asyncio
    async def test_background_rss_monitoring_workflow(self):
        """Test complete background RSS monitoring workflow."""
        # Background monitoring context
        background_ctx = {
            'request_id': 'background-rss-002',
            'trigger': 'background',
            'monitor_type': 'all',
            'sources': ['regulatory', 'ccnl'],
            'monitoring_config': {
                'deep_scan': True,
                'priority_sources': ['agenzia_entrate'],
                'content_filters': ['tax', 'ccnl', 'labor']
            }
        }

        with patch('app.orchestrators.kb.rag_step_log') as mock_log, \
             patch('app.orchestrators.kb.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.kb._coordinate_rss_monitoring') as mock_monitor:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_monitor.return_value = {
                'status': 'completed',
                'has_new_items': True,
                'feeds': [
                    {
                        'feed_name': 'agenzia_entrate_circolari',
                        'priority': 'high',
                        'new_items': 5,
                        'filtered_items': 3
                    },
                    {
                        'feed_name': 'ccnl_updates',
                        'priority': 'medium',
                        'new_items': 2,
                        'filtered_items': 2
                    }
                ],
                'new_item_count': 7,
                'feed_sources': ['regulatory', 'ccnl']
            }

            result = await step_132__rssmonitor(ctx=background_ctx)

            # Verify background workflow execution
            assert result['status'] == 'completed'
            assert result['monitoring_result']['new_item_count'] == 7
            assert result['next_step'] == 133

    @pytest.mark.asyncio
    async def test_manual_triggered_rss_monitoring(self):
        """Test manually triggered RSS monitoring workflow."""
        manual_ctx = {
            'request_id': 'manual-rss-003',
            'trigger': 'manual',
            'monitor_type': 'italian',
            'sources': ['gazzetta_ufficiale'],
            'user_initiated': True,
            'target_date_range': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-15'
            }
        }

        with patch('app.orchestrators.kb.rag_step_log'), \
             patch('app.orchestrators.kb.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.kb._coordinate_rss_monitoring') as mock_monitor:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_monitor.return_value = {
                'status': 'completed',
                'has_new_items': True,
                'feeds': [
                    {
                        'feed_name': 'gazzetta_ufficiale_serie_generale',
                        'date_range_filtered': True,
                        'new_items': 12,
                        'date_filtered_items': 8
                    }
                ],
                'new_item_count': 8,
                'feed_sources': ['gazzetta_ufficiale']
            }

            result = await step_132__rssmonitor(ctx=manual_ctx)

            # Verify manual trigger handling
            assert result['status'] == 'completed'
            assert result['monitoring_result']['new_item_count'] == 8


class TestStep132RSSMonitorParity:
    """Parity tests to ensure behavioral consistency."""

    @pytest.mark.asyncio
    async def test_rss_service_behavior_preservation(self):
        """Verify orchestrator preserves RSS service behavior exactly."""
        ctx = {
            'request_id': 'parity-test-001',
            'monitor_type': 'italian',
            'sources': ['agenzia_entrate', 'inps']
        }

        with patch('app.services.rss_feed_monitor.RSSFeedMonitor') as MockRSSMonitor, \
             patch('app.orchestrators.kb.rag_step_log'), \
             patch('app.orchestrators.kb.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.kb._coordinate_rss_monitoring') as mock_monitor:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Setup mock RSS service
            mock_service = MagicMock()
            mock_service.get_all_italian_feeds.return_value = {
                'agenzia_entrate_circolari': 'https://www.agenziaentrate.gov.it/portale/rss/circolari.xml',
                'inps_messaggi': 'https://www.inps.it/rss/messaggi.xml'
            }
            MockRSSMonitor.return_value = mock_service

            mock_monitor.return_value = {
                'status': 'completed',
                'has_new_items': False,
                'feeds': [],
                'new_item_count': 0,
                'feed_sources': []
            }

            result = await step_132__rssmonitor(ctx=ctx)

            # Verify orchestrator doesn't modify service behavior
            mock_monitor.assert_called_once_with(monitor_type='italian')
            assert result['status'] == 'completed'

    @pytest.mark.asyncio
    async def test_error_handling_consistency(self):
        """Verify error handling behavior matches expectations."""
        ctx = {
            'request_id': 'parity-error-test',
            'monitor_type': 'invalid_type',
            'sources': ['unknown_source']
        }

        with patch('app.orchestrators.kb.rag_step_log'), \
             patch('app.orchestrators.kb.rag_step_timer') as mock_timer, \
             patch('app.orchestrators.kb._coordinate_rss_monitoring') as mock_monitor:

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Simulate service error
            mock_monitor.side_effect = ValueError("Invalid monitor type")

            result = await step_132__rssmonitor(ctx=ctx)

            # Verify consistent error structure
            assert result['status'] == 'error'
            assert 'error' in result

    @pytest.mark.asyncio
    async def test_output_structure_consistency(self):
        """Verify output structure is consistent across different inputs."""
        test_scenarios = [
            {'monitor_type': 'italian', 'expected_feeds': 2},
            {'monitor_type': 'ccnl', 'expected_feeds': 1},
            {'monitor_type': 'all', 'expected_feeds': 3}
        ]

        for scenario in test_scenarios:
            ctx = {
                'request_id': f'parity-structure-{scenario["monitor_type"]}',
                'monitor_type': scenario['monitor_type'],
                'sources': ['test_source']
            }

            with patch('app.orchestrators.kb.rag_step_log'), \
                 patch('app.orchestrators.kb.rag_step_timer') as mock_timer, \
                 patch('app.orchestrators.kb._coordinate_rss_monitoring') as mock_monitor:

                mock_timer.return_value.__enter__ = MagicMock()
                mock_timer.return_value.__exit__ = MagicMock()

                mock_monitor.return_value = {
                    'status': 'completed',
                    'has_new_items': False,
                    'feeds': [],
                    'new_item_count': 0,
                    'feed_sources': []
                }

                result = await step_132__rssmonitor(ctx=ctx)

                # Verify consistent output structure
                required_keys = [
                    'step', 'status', 'monitoring_result'
                ]
                for key in required_keys:
                    assert key in result, f"Missing required key: {key} for type {scenario['monitor_type']}"

                assert result['step'] == 132
                assert result['status'] == 'completed'


if __name__ == '__main__':
    pytest.main([__file__])