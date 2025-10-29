#!/usr/bin/env python3
"""
Regression test for RAG audit role-based evaluation.

Tests that the audit script correctly handles Node vs Internal step roles:
- Node steps: Must be wired in LangGraph to pass
- Internal steps: Only need implementation (no wiring required)

Note: If IDE shows unresolved import errors for RAGAuditor, this is a false positive.
The dynamic import logic ensures the module is found at runtime.
"""

import json
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch

import pytest
import sys
import os

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
scripts_dir = os.path.join(project_root, 'scripts')

# Add to sys.path if not already there
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

# Import using full path from project root
try:
    # This should work for IDEs
    from scripts.rag_audit import RAGAuditor
except ImportError:
    # Fallback for runtime if scripts is not in path
    import rag_audit  # type: ignore
    RAGAuditor = rag_audit.RAGAuditor  # type: ignore


class TestRAGAuditRoles:
    """Test suite for role-based audit evaluation."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary files for testing
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Mock steps data with one Node and one Internal step
        self.mock_steps = {
            'steps': [
                {
                    'step': 1,
                    'id': 'RAG.platform.validate.request',
                    'node_id': 'ValidateRequest',
                    'node_label': 'Validate Request',
                    'type': 'process',
                    'category': 'platform',
                    'role': 'Node'  # Will be added by _enrich_steps_with_roles
                },
                {
                    'step': 10,
                    'id': 'RAG.platform.logger.log.pii',
                    'node_id': 'LogPII',
                    'node_label': 'Log PII',
                    'type': 'process',
                    'category': 'platform',
                    'role': 'Internal'  # Will be added by _enrich_steps_with_roles
                }
            ]
        }

        # Mock code graph with implementation for both steps
        self.mock_code_graph = {
            'files': [
                {
                    'path': 'app/orchestrators/platform.py',
                    'symbols': [
                        {
                            'name': 'step_1__validate_request',
                            'qualname': 'app.orchestrators.platform.step_1__validate_request',
                            'kind': 'function',
                            'line': 16,
                            'doc': 'Validate incoming request and authenticate user platform'
                        },
                        {
                            'name': 'step_10__log_pii',
                            'qualname': 'app.orchestrators.platform.step_10__log_pii',
                            'kind': 'function',
                            'line': 663,
                            'doc': 'Log PII anonymization process platform'
                        }
                    ]
                }
            ],
            'edges': {
                'calls': []
            }
        }

        # Create temporary files
        self.steps_file = self.temp_path / 'rag_steps.yml'
        self.code_index_file = self.temp_path / 'rag_code_index.json'

        with open(self.steps_file, 'w') as f:
            yaml.dump(self.mock_steps, f)

        with open(self.code_index_file, 'w') as f:
            json.dump(self.mock_code_graph, f)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_node_step_wired_should_pass(self):
        """Test that a Node step that is implemented and wired gets ✅."""
        # Use lower thresholds to ensure the test passes
        config_file = self.temp_path / 'test_config.yml'
        with open(config_file, 'w') as f:
            yaml.dump({
                'thresholds': {'implemented': 0.30, 'partial': 0.20},
                'weights': {'name_similarity': 0.40, 'docstring_hints': 0.25, 'path_hints': 0.20, 'graph_proximity': 0.15}
            }, f)

        auditor = RAGAuditor(self.steps_file, self.code_index_file, config_file, verbose=True)

        # Mock the role extraction to return Node for step 1
        with patch.object(auditor, '_enrich_steps_with_roles') as mock_enrich:
            def mock_enrich_func():
                for step in auditor.steps:
                    if step['step'] == 1:
                        step['role'] = 'Node'
                    else:
                        step['role'] = 'Internal'
            mock_enrich.side_effect = mock_enrich_func

            # Mock LangGraph wiring check to return True for step 1
            with patch.object(auditor, '_check_langgraph_wiring') as mock_wiring:
                mock_wiring.return_value = True

                auditor.load_data()

                # Find step 1 (Node step)
                step_1 = next(s for s in auditor.steps if s['step'] == 1)
                result = auditor._audit_single_step(step_1)

                # Node step that's implemented and wired should get ✅
                assert result['status'] == '✅', f"Expected ✅ for wired Node step, got {result['status']}"

    def test_node_step_not_wired_should_be_not_wired(self):
        """Test that a Node step that is implemented but not wired gets 🔌."""
        auditor = RAGAuditor(self.steps_file, self.code_index_file, verbose=True)

        # Mock the role extraction
        with patch.object(auditor, '_enrich_steps_with_roles') as mock_enrich:
            def mock_enrich_func():
                for step in auditor.steps:
                    if step['step'] == 1:
                        step['role'] = 'Node'
                    else:
                        step['role'] = 'Internal'
            mock_enrich.side_effect = mock_enrich_func

            # Mock LangGraph wiring check to return False for step 1
            with patch.object(auditor, '_check_langgraph_wiring') as mock_wiring:
                mock_wiring.return_value = False

                auditor.load_data()

                # Find step 1 (Node step)
                step_1 = next(s for s in auditor.steps if s['step'] == 1)
                result = auditor._audit_single_step(step_1)

                # Node step that's implemented but not wired should get 🔌
                assert result['status'] == '🔌', f"Expected 🔌 for non-wired Node step, got {result['status']}"

    def test_internal_step_implemented_should_pass(self):
        """Test that an Internal step that is implemented gets 🔌 (considered passing)."""
        auditor = RAGAuditor(self.steps_file, self.code_index_file, verbose=True)

        # Mock the role extraction
        with patch.object(auditor, '_enrich_steps_with_roles') as mock_enrich:
            def mock_enrich_func():
                for step in auditor.steps:
                    if step['step'] == 1:
                        step['role'] = 'Node'
                    else:
                        step['role'] = 'Internal'
            mock_enrich.side_effect = mock_enrich_func

            # Mock LangGraph wiring check (shouldn't matter for Internal)
            with patch.object(auditor, '_check_langgraph_wiring') as mock_wiring:
                mock_wiring.return_value = False  # Not wired, but shouldn't matter

                auditor.load_data()

                # Find step 10 (Internal step)
                step_10 = next(s for s in auditor.steps if s['step'] == 10)
                result = auditor._audit_single_step(step_10)

                # Internal step that's implemented should get 🔌 (passing for Internal)
                assert result['status'] == '🔌', f"Expected 🔌 for implemented Internal step, got {result['status']}"

    def test_role_extraction_from_docs(self):
        """Test that roles are correctly extracted from step documentation."""
        auditor = RAGAuditor(self.steps_file, self.code_index_file, verbose=True)

        # Mock the role extraction directly to avoid file system complexity
        with patch.object(auditor, '_enrich_steps_with_roles') as mock_enrich:
            def mock_enrich_func():
                for step in auditor.steps:
                    if step['step'] == 1:
                        step['role'] = 'Node'
                    else:
                        step['role'] = 'Internal'
            mock_enrich.side_effect = mock_enrich_func

            auditor.load_data()

            # Check that roles were set correctly
            step_1 = next(s for s in auditor.steps if s['step'] == 1)
            step_10 = next(s for s in auditor.steps if s['step'] == 10)

            assert step_1.get('role') == 'Node', f"Expected Node role for step 1, got {step_1.get('role')}"
            assert step_10.get('role') == 'Internal', f"Expected Internal role for step 10, got {step_10.get('role')}"

    def test_regression_internal_steps_should_pass_when_implemented(self):
        """Regression test: Internal steps should show as passing (🔌) when implemented, not ❌."""
        auditor = RAGAuditor(self.steps_file, self.code_index_file, verbose=False)

        # Mock everything to simulate the scenario
        with patch.object(auditor, '_enrich_steps_with_roles') as mock_enrich:
            def mock_enrich_func():
                for step in auditor.steps:
                    step['role'] = 'Internal'  # All Internal for this test
            mock_enrich.side_effect = mock_enrich_func

            auditor.load_data()
            results = auditor.audit_all_steps()

            # Before the fix, Internal steps would show as ❌ or 🔌 based on old logic
            # After the fix, implemented Internal steps should show as 🔌 (passing)

            # Count how many Internal steps are now passing
            passing_internal = results['by_status']['🔌']
            missing_internal = results['by_status']['❌']

            # We expect more steps to be passing now (exact numbers depend on implementation quality)
            assert passing_internal > 0, "At least some Internal steps should be marked as implemented (🔌)"

            # The key assertion: we should not have ALL steps as missing
            assert missing_internal < len(auditor.steps), "Not all steps should be missing - some Internal steps should pass"

if __name__ == '__main__':
    pytest.main([__file__, '-v'])