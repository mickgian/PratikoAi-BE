#!/usr/bin/env python3
"""
RAG Code Audit - Match RAG steps to code implementation using graph analysis.

Usage:
    python scripts/rag_audit.py --write    # Update step docs and dashboard (default)
    python scripts/rag_audit.py --dry-run  # Preview without writing
    python scripts/rag_audit.py --verbose  # Detailed output
"""

import argparse
import json
import re
import subprocess
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from difflib import SequenceMatcher


class RAGAuditor:
    """Audit RAG steps against code implementation."""
    
    # Default keywords for hint matching by category
    DEFAULT_HINT_KEYWORDS = {
        'faq': ['faq', 'golden', 'question', 'answer'],
        'golden': ['golden', 'faq', 'expert', 'feedback'],
        'kb': ['kb', 'knowledge', 'search', 'vector', 'retrieve'],
        'rss': ['rss', 'feed', 'monitor', 'parse'],
        'cache': ['cache', 'redis', 'epoch', 'hash', 'key'],
        'doc': ['doc', 'document', 'ingest', 'parse', 'ocr', 'blob'],
        'vector': ['vector', 'embedding', 'pinecone', 'search'],
        'ccnl': ['ccnl', 'labor', 'agreement', 'calculator'],
        'provider': ['provider', 'llm', 'anthropic', 'openai'],
        'retry': ['retry', 'failover', 'circuit', 'breaker'],
        'stream': ['stream', 'sse', 'chunk', 'async'],
        'metric': ['metric', 'usage', 'track', 'cost'],
        'feedback': ['feedback', 'expert', 'validation'],
        'privacy': ['privacy', 'gdpr', 'anonymize', 'pii'],
        'auth': ['auth', 'validate', 'request', 'user'],
        'classify': ['classify', 'domain', 'action', 'confidence'],
        'prompt': ['prompt', 'system', 'template', 'message']
    }
    
    # Default path hints by category
    DEFAULT_PATH_HINTS = {
        'cache': ['/cache/', '/redis/'],
        'kb': ['/knowledge/', '/search/', '/vector/'],
        'faq': ['/faq/', '/golden/'],
        'docs': ['/document/', '/doc/', '/ingest/', '/parse/'],
        'providers': ['/provider/', '/llm/', '/anthropic/', '/openai/'],
        'ccnl': ['/ccnl/', '/labor/'],
        'prompt': ['/prompt/', '/template/'],
        'privacy': ['/privacy/', '/gdpr/', '/anonymize/'],
        'auth': ['/auth/', '/security/'],
        'streaming': ['/stream/', '/sse/'],
        'metrics': ['/metric/', '/usage/', '/track/']
    }
    
    def __init__(self, steps_file: Path, code_index_file: Path, config_file: Path = None, verbose: bool = False):
        self.steps_file = steps_file
        self.code_index_file = code_index_file
        self.config_file = config_file or Path(__file__).parent / 'rag_audit_config.yml'
        self.verbose = verbose
        self.steps = []
        self.code_graph = {}
        self.symbol_index = {}  # qualname -> symbol
        self.audit_results = {}
        self.config = self._load_config()
        self.wiring_registry = None  # Will be loaded once in load_data()
        
    def _load_config(self) -> Dict:
        """Load configuration file if it exists."""
        if not self.config_file.exists():
            if self.verbose:
                print(f"Config file not found: {self.config_file}, using defaults")
            return {
                'thresholds': {'implemented': 0.80, 'partial': 0.50, 'not_wired_callers_min': 1},
                'weights': {'name_similarity': 0.40, 'docstring_hints': 0.25, 'path_hints': 0.20, 'graph_proximity': 0.15},
                'synonyms': {},
                'path_bias': {}
            }
        
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
                if self.verbose:
                    print(f"Loaded config from: {self.config_file}")
                return config
        except Exception as e:
            if self.verbose:
                print(f"Failed to load config: {e}, using defaults")
            return {
                'thresholds': {'implemented': 0.80, 'partial': 0.50, 'not_wired_callers_min': 1},
                'weights': {'name_similarity': 0.40, 'docstring_hints': 0.25, 'path_hints': 0.20, 'graph_proximity': 0.15},
                'synonyms': {},
                'path_bias': {}
            }

    def _load_graph_wiring_registry(self) -> dict[int, dict]:
        """Load graph wiring registry from lightweight module."""
        try:
            # Import lightweight registry to avoid heavy initialization
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from app.core.langgraph.wiring_registry import get_wired_nodes_snapshot

            registry = get_wired_nodes_snapshot() or {}
            if self.verbose:
                print(f"[audit] loaded {len(registry)} nodes from wiring registry")
            return registry
        except Exception as e:
            if self.verbose:
                print(f"[audit] wiring registry unavailable: {e}")
            return {}

    def load_data(self):
        """Load steps registry and code graph."""
        # Load wiring registry once at the start
        self.wiring_registry = self._load_graph_wiring_registry()

        # Load steps
        with open(self.steps_file, 'r') as f:
            data = yaml.safe_load(f)
            self.steps = data.get('steps', [])

        # Enrich steps with Role information from individual docs
        self._enrich_steps_with_roles()

        # Load code graph
        with open(self.code_index_file, 'r') as f:
            self.code_graph = json.load(f)

        # Build symbol index
        for file_data in self.code_graph['files']:
            for symbol in file_data['symbols']:
                self.symbol_index[symbol['qualname']] = {
                    **symbol,
                    'file_path': file_data['path']
                }

    def _enrich_steps_with_roles(self):
        """Extract Role information from individual step documentation files."""
        base_dir = Path(__file__).parent.parent
        steps_dir = base_dir / 'docs/architecture/steps'

        for step in self.steps:
            step_num = step['step']
            step_id = step['id']
            doc_path = steps_dir / f"STEP-{step_num}-{step_id}.md"

            # Default to Internal if we can't determine
            step['role'] = 'Internal'

            if doc_path.exists():
                try:
                    with open(doc_path, 'r') as f:
                        content = f.read()

                    # Look for Role: Node or Role: Internal pattern
                    role_match = re.search(r'- \*\*Role:\*\* (Node|Internal)', content)
                    if role_match:
                        step['role'] = role_match.group(1)
                    elif '**Role:** Node' in content:
                        step['role'] = 'Node'
                    elif '**Role:** Internal' in content:
                        step['role'] = 'Internal'

                    if self.verbose:
                        print(f"Step {step_num}: Role={step['role']}")

                except Exception as e:
                    if self.verbose:
                        print(f"Warning: Could not extract role for step {step_num}: {e}")

    def _check_langgraph_wiring(self, step: Dict) -> bool:
        """Check if a step is wired in the LangGraph implementation."""
        if self.wiring_registry is None:
            self.wiring_registry = self._load_graph_wiring_registry()
        step_num = step['step']
        return int(step_num) in self.wiring_registry

    def audit_all_steps(self) -> Dict[str, Any]:
        """Audit all RAG steps."""
        results = {
            'by_status': {'✅': 0, '🟡': 0, '🔌': 0, '❌': 0},
            'by_category': {},
            'examples': {'✅': [], '🟡': [], '🔌': [], '❌': []},
            'total_steps': len(self.steps)
        }
        
        for step in self.steps:
            audit_result = self._audit_single_step(step)
            status = audit_result['status']
            category = step['category']
            
            # Update counts
            results['by_status'][status] += 1
            results['by_category'][category] = results['by_category'].get(category, {})
            results['by_category'][category][status] = results['by_category'][category].get(status, 0) + 1
            
            # Add examples (first 5 per status)
            if len(results['examples'][status]) < 5:
                results['examples'][status].append({
                    'step': step['step'],
                    'node_id': step['node_id'],
                    'top_candidate': audit_result['candidates'][0] if audit_result['candidates'] else None
                })
            
            self.audit_results[step['step']] = audit_result
        
        return results
    
    def _audit_single_step(self, step: Dict) -> Dict[str, Any]:
        """Audit a single RAG step."""
        query_tokens = self._build_query_tokens(step)
        candidates = []
        
        # Score all symbols
        for qualname, symbol in self.symbol_index.items():
            score = self._score_symbol(symbol, query_tokens, step)
            if score >= 0.1:  # Minimum threshold
                candidates.append({
                    'path': symbol['file_path'],
                    'symbol': symbol['name'],
                    'qualname': qualname,
                    'line': symbol['line'],
                    'score': score,
                    'snippet': self._make_snippet(symbol)
                })
        
        # Sort by score
        candidates.sort(key=lambda x: x['score'], reverse=True)
        candidates = candidates[:10]  # Top 10
        
        # Apply graph proximity boost (simple one iteration)
        if candidates:
            self._apply_proximity_boost(candidates)
            candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Determine status
        status = self._determine_status(candidates, step)
        confidence = candidates[0]['score'] if candidates else 0.0
        
        # Generate suggestions
        suggestions = self._generate_tdd_suggestions(step, candidates, status)
        
        return {
            'status': status,
            'confidence': round(confidence, 2),
            'candidates': candidates[:5],  # Top 5 for display
            'suggestions': suggestions,
            'notes': self._generate_notes(step, candidates, status)
        }
    
    def _build_query_tokens(self, step: Dict) -> Set[str]:
        """Build query tokens from step metadata."""
        tokens = set()
        
        # From node label and ID
        text = f"{step['node_label']} {step['node_id']}"
        tokens.update(self._tokenize(text))
        
        # Add synonyms from config
        synonyms = self.config.get('synonyms', {})
        node_label = step['node_label']
        if node_label in synonyms:
            for synonym in synonyms[node_label]:
                tokens.update(self._tokenize(synonym))
        
        # Add category-specific hints
        category = step['category']
        hint_keywords = {**self.DEFAULT_HINT_KEYWORDS, **self.config.get('path_bias', {})}
        if category in hint_keywords:
            tokens.update(hint_keywords[category])
        
        return tokens

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase words.

        - Split on underscores, slashes, and dots
        - Split CamelCase
        - Keep only a–z0–9 tokens, length > 2
        """
        # Split CamelCase: "GoldenFastPath" -> "Golden Fast Path"
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

        # Normalize common separators so they act like spaces
        text = text.replace('_', ' ').replace('/', ' ').replace('.', ' ')

        # Extract alphanumeric tokens
        tokens = re.findall(r'[a-z0-9]+', text.lower())
        return [t for t in tokens if len(t) > 2]

    def _score_symbol(self, symbol: Dict, query_tokens: Set[str], step: Dict) -> float:
        """Score a symbol for relevance to the step."""
        weights = self.config.get('weights', {
            'name_similarity': 0.40, 'docstring_hints': 0.25, 
            'path_hints': 0.20, 'graph_proximity': 0.15
        })
        
        scores = []
        
        # 1. Name similarity
        name_score = self._name_similarity(symbol, query_tokens)
        scores.append(('name', name_score, weights.get('name_similarity', 0.40)))
        
        # 2. Docstring/comment hints
        hint_score = self._hint_score(symbol, step['category'])
        scores.append(('hint', hint_score, weights.get('docstring_hints', 0.25)))
        
        # 3. Path hints
        path_score = self._path_hint_score(symbol['file_path'], step['category'])
        scores.append(('path', path_score, weights.get('path_hints', 0.20)))
        
        # 4. Type relevance (remaining weight)
        remaining_weight = 1.0 - sum(w for _, _, w in scores)
        type_score = self._type_relevance(symbol, step['type'])
        scores.append(('type', type_score, remaining_weight))
        
        # Calculate weighted average
        total_score = sum(score * weight for _, score, weight in scores)
        
        if self.verbose:
            print(f"Scoring {symbol['qualname']}: "
                  f"name={name_score:.2f}, hint={hint_score:.2f}, "
                  f"path={path_score:.2f}, type={type_score:.2f} -> {total_score:.2f}")
        
        return total_score
    
    def _name_similarity(self, symbol: Dict, query_tokens: Set[str]) -> float:
        """Calculate name similarity using Jaccard + Levenshtein."""
        # Get symbol name tokens
        symbol_tokens = set(self._tokenize(symbol['name'] + ' ' + symbol['qualname']))
        
        # Jaccard similarity
        intersection = query_tokens & symbol_tokens
        union = query_tokens | symbol_tokens
        jaccard = len(intersection) / len(union) if union else 0
        
        # Best Levenshtein match
        best_lev = 0
        for query_token in query_tokens:
            for symbol_token in symbol_tokens:
                similarity = SequenceMatcher(None, query_token, symbol_token).ratio()
                best_lev = max(best_lev, similarity)
        
        # Combine scores
        return (jaccard * 0.7) + (best_lev * 0.3)
    
    def _hint_score(self, symbol: Dict, category: str) -> float:
        """Score based on docstring and comment hints."""
        # Use path_bias from config if available, otherwise default
        path_bias = self.config.get('path_bias', {})
        hints = path_bias.get(category, self.DEFAULT_HINT_KEYWORDS.get(category, []))
        if not hints:
            return 0.0
        
        # Check docstring
        doc_text = (symbol.get('doc') or '').lower()
        
        # Count hint matches
        matches = sum(1 for hint in hints if hint in doc_text)
        return min(matches / len(hints), 1.0)
    
    def _path_hint_score(self, file_path: str, category: str) -> float:
        """Score based on file path hints."""
        # Use path_bias from config if available, otherwise default
        path_bias = self.config.get('path_bias', {})
        path_hints = path_bias.get(category, self.DEFAULT_PATH_HINTS.get(category, []))
        if not path_hints:
            return 0.0
        
        file_path_lower = file_path.lower()
        matches = sum(1 for hint in path_hints if hint in file_path_lower)
        return min(matches / len(path_hints), 1.0)
    
    def _type_relevance(self, symbol: Dict, step_type: str) -> float:
        """Score based on symbol type vs step type."""
        symbol_kind = symbol['kind']
        
        # Type mapping
        if step_type == 'process':
            if symbol_kind in ['function', 'method']:
                return 1.0
            elif symbol_kind == 'class':
                return 0.7
        elif step_type == 'decision':
            if symbol_kind in ['function', 'method']:
                return 1.0
            elif symbol_kind == 'class':
                return 0.5
        elif step_type == 'startEnd':
            if symbol_kind in ['function', 'class']:
                return 1.0
            elif symbol_kind == 'method':
                return 0.8
        
        return 0.3  # Default
    
    def _apply_proximity_boost(self, candidates: List[Dict]):
        """Apply graph proximity boost to candidates."""
        if not candidates:
            return
        
        # Get call graph
        call_edges = self.code_graph['edges']['calls']
        call_graph = {}
        
        for caller, callee in call_edges:
            if caller not in call_graph:
                call_graph[caller] = set()
            call_graph[caller].add(callee)
        
        # Apply boost to highly scored candidates
        high_confidence = [c for c in candidates if c['score'] >= 0.7]
        
        for candidate in candidates:
            boost = 0.0
            qualname = candidate['qualname']
            
            # Check if calls or is called by high-confidence symbols
            for high_conf in high_confidence:
                if qualname != high_conf['qualname']:
                    # Check if candidate calls high-confidence symbol
                    if qualname in call_graph and high_conf['qualname'] in call_graph[qualname]:
                        boost += 0.1
                    # Check if high-confidence symbol calls candidate
                    if high_conf['qualname'] in call_graph and qualname in call_graph[high_conf['qualname']]:
                        boost += 0.1
            
            candidate['score'] = min(candidate['score'] + boost, 1.0)
    
    def _determine_status(self, candidates: List[Dict], step: Dict) -> str:
        """Determine implementation status based on Role (Node vs Internal)."""
        step_role = step.get('role', 'Internal')

        # Check if step has any implemented code_refs (relaxed threshold)
        has_implementation = bool(candidates and candidates[0]['score'] >= 0.30)

        if step_role == 'Node':
            # Node steps: Must be wired in LangGraph to pass
            is_wired = self._check_langgraph_wiring(step)

            if is_wired:
                return '✅'  # Implemented & Wired
            elif has_implementation:
                return '🔌'  # Implemented but not wired
            else:
                return '❌'  # Missing

        else:  # Internal steps
            # Internal steps: Only need implementation
            if has_implementation:
                return '🔌'  # Implemented (internal)
            else:
                return '❌'  # Missing
    
    def _make_snippet(self, symbol: Dict) -> str:
        """Create a short snippet for display."""
        doc = symbol.get('doc', '').strip()
        if doc:
            return doc[:80] + ('...' if len(doc) > 80 else '')
        return f"{symbol['kind']}: {symbol['name']}"
    
    def _generate_tdd_suggestions(self, step: Dict, candidates: List[Dict], status: str) -> List[str]:
        """Generate TDD suggestions based on step and status."""
        suggestions = []
        step_type = step['type']
        category = step['category']
        
        if status == '❌':
            suggestions.extend([
                f"Create {step_type} implementation for {step['node_id']}",
                "Add unit tests covering happy path and edge cases",
                "Wire into the RAG pipeline flow"
            ])
        elif status == '🔌':
            suggestions.extend([
                "Connect existing implementation to RAG workflow",
                "Add integration tests for end-to-end flow",
                "Verify error handling and edge cases"
            ])
        elif status == '🟡':
            suggestions.extend([
                "Complete partial implementation",
                "Add missing error handling",
                "Expand test coverage",
                "Add performance benchmarks if needed"
            ])
        else:  # ✅
            suggestions.extend([
                "Verify complete test coverage",
                "Add observability logging",
                "Performance optimization if needed"
            ])
        
        # Category-specific suggestions
        if category == 'cache':
            suggestions.append("Add cache invalidation and TTL tests")
        elif category == 'privacy':
            suggestions.append("Test PII detection and anonymization")
        elif category == 'providers':
            suggestions.append("Test failover and retry mechanisms")
        elif category == 'docs':
            suggestions.append("Test document parsing and validation")
        
        return suggestions[:6]  # Limit to 6
    
    def _generate_notes(self, step: Dict, candidates: List[Dict], status: str) -> List[str]:
        """Generate audit notes."""
        notes = []
        
        if not candidates:
            notes.append("No matching symbols found in codebase")
        elif status == '✅':
            notes.append("Strong implementation match found")
        elif status == '🟡':
            notes.append("Partial implementation identified")
        elif status == '🔌':
            notes.append("Implementation exists but may not be wired correctly")
        else:
            notes.append("Weak or missing implementation")
        
        # Add specific observations
        if candidates:
            top = candidates[0]
            if 'test' in top['path']:
                notes.append("Top match is in test files")
            if top['score'] < 0.5:
                notes.append("Low confidence in symbol matching")
        
        return notes
    
    def update_step_docs(self, base_dir: Path):
        """Update step documentation with audit results."""
        steps_dir = base_dir / 'docs/architecture/steps'
        
        for step in self.steps:
            step_num = step['step']
            step_id = step['id']
            doc_path = steps_dir / f"STEP-{step_num}-{step_id}.md"
            
            if not doc_path.exists():
                continue
            
            # Read existing content
            with open(doc_path, 'r') as f:
                content = f.read()
            
            # Generate audit block
            audit_result = self.audit_results[step_num]
            audit_block = self._generate_audit_block(audit_result)
            
            # Replace or add audit block
            if '<!-- AUTO-AUDIT:BEGIN -->' in content:
                # Replace existing block
                pattern = r'<!-- AUTO-AUDIT:BEGIN -->.*?<!-- AUTO-AUDIT:END -->'
                content = re.sub(pattern, audit_block, content, flags=re.DOTALL)
            else:
                # Add at the end
                content += '\n\n' + audit_block
            
            # Write back
            with open(doc_path, 'w') as f:
                f.write(content)
    
    def _generate_audit_block(self, audit_result: Dict) -> str:
        """Generate the AUTO-AUDIT block."""
        status = audit_result['status']
        confidence = audit_result['confidence']
        candidates = audit_result['candidates']
        suggestions = audit_result['suggestions']
        notes = audit_result['notes']

        # Find the step to get role information
        step_role = 'Unknown'
        step_num = None
        for step in self.steps:
            if step['step'] in self.audit_results and self.audit_results[step['step']] == audit_result:
                step_role = step.get('role', 'Unknown')
                step_num = step['step']
                break

        # Status interpretation based on role
        status_explanation = ""
        if step_role == 'Node':
            if status == '✅':
                status_explanation = " (Implemented & Wired)"
            elif status == '🔌':
                status_explanation = " (Implemented but Not Wired)"
            elif status == '❌':
                status_explanation = " (Missing)"
        elif step_role == 'Internal':
            if status == '🔌':
                status_explanation = " (Implemented - internal)"
            elif status == '❌':
                status_explanation = " (Missing)"

        lines = [
            '<!-- AUTO-AUDIT:BEGIN -->',
            f'Role: {step_role}  |  Status: {status}{status_explanation}  |  Confidence: {confidence:.2f}',
            '',
            'Top candidates:'
        ]

        if candidates:
            for i, candidate in enumerate(candidates, 1):
                evidence = f"Score {candidate['score']:.2f}, {candidate['snippet']}"
                lines.append(f'{i}) {candidate["path"]}:{candidate["line"]} — {candidate["qualname"]} (score {candidate["score"]:.2f})')
                lines.append(f'   Evidence: {evidence}')
        else:
            lines.append('No candidates found')

        lines.extend(['', 'Notes:'])
        for note in notes:
            lines.append(f'- {note}')

        # Add role-specific notes
        if step_role == 'Node' and status == '✅':
            # For wired nodes, include neighbor information
            if self.wiring_registry is None:
                self.wiring_registry = self._load_graph_wiring_registry()
            if step_num and int(step_num) in self.wiring_registry:
                node_info = self.wiring_registry[int(step_num)]
                incoming = node_info.get('incoming', [])
                outgoing = node_info.get('outgoing', [])
                lines.append('- Wired via graph registry ✅')
                lines.append(f'- Incoming: {incoming}, Outgoing: {outgoing}')
        elif step_role == 'Node' and status == '🔌':
            lines.append('- Detected Node but not in runtime registry')
        elif step_role == 'Internal' and status == '🔌':
            lines.append('- Implemented (internal) - no wiring required')

        lines.extend(['', 'Suggested next TDD actions:'])
        for suggestion in suggestions:
            lines.append(f'- {suggestion}')

        lines.append('<!-- AUTO-AUDIT:END -->')

        return '\n'.join(lines)
    
    def update_conformance_dashboard(self, base_dir: Path):
        """Update the conformance dashboard with current audit results."""
        dashboard_path = base_dir / 'docs/architecture/rag_conformance.md'
        
        # Read existing content
        with open(dashboard_path, 'r') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Find and update the table
        updated_lines = []
        in_table = False
        table_updated = False
        
        for i, line in enumerate(lines):
            if not table_updated and '| Step | Name | Type | Category |' in line:
                # Found table header - ensure proper "Status" column
                if 'Owner' in line:
                    line = line.replace('Owner', 'Status')
                updated_lines.append(line)
                in_table = True
            elif in_table and line.startswith('|') and '---' in line:
                # Table separator row
                updated_lines.append(line)
            elif in_table and line.startswith('|') and ' | ' in line:
                # Table data row
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 7 and parts[1].isdigit():  # Valid step row
                    step_num = int(parts[1])
                    if step_num in self.audit_results:
                        # Update status column (index 6, accounting for empty first/last parts)
                        parts[6] = self.audit_results[step_num]['status']
                updated_lines.append('| ' + ' | '.join(parts[1:-1]) + ' |')
            elif in_table and not line.startswith('|'):
                # End of table
                in_table = False
                table_updated = True
                updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        # Replace the entire Audit Summary section
        final_lines = []
        skip_section = False
        
        for line in updated_lines:
            if line.startswith('## Audit Summary'):
                # Start replacement - add new summary
                final_lines.extend(self._generate_dashboard_summary())
                skip_section = True
                continue
            elif skip_section and line.startswith('## '):
                # Hit next section - stop skipping
                skip_section = False
                final_lines.append(line)
            elif not skip_section:
                # Normal line outside audit summary
                final_lines.append(line)
        
        # If no Audit Summary section found, append it
        if not any('## Audit Summary' in line for line in updated_lines):
            final_lines.extend(['', ''])
            final_lines.extend(self._generate_dashboard_summary())
        
        # Write back
        with open(dashboard_path, 'w') as f:
            f.write('\n'.join(final_lines))
    
    def _generate_dashboard_summary(self) -> List[str]:
        """Generate dashboard summary section."""
        summary = self.audit_all_steps()

        # Calculate role-based statistics
        node_stats = {'✅': 0, '🔌': 0, '❌': 0, 'total': 0}
        internal_stats = {'🔌': 0, '❌': 0, 'total': 0}

        for step in self.steps:
            step_num = step['step']
            if step_num in self.audit_results:
                status = self.audit_results[step_num]['status']
                role = step.get('role', 'Internal')

                if role == 'Node':
                    node_stats[status] = node_stats.get(status, 0) + 1
                    node_stats['total'] += 1
                else:  # Internal
                    internal_stats[status] = internal_stats.get(status, 0) + 1
                    internal_stats['total'] += 1

        lines = [
            '## Audit Summary',
            '',
            f'**Implementation Status Overview (Tiered Graph Hybrid):**',
            '',
            f'**Node Steps** (Runtime boundaries - must be wired):',
            f'- ✅ Implemented & Wired: {node_stats["✅"]} steps',
            f'- 🔌 Not Wired: {node_stats["🔌"]} steps',
            f'- ❌ Missing: {node_stats["❌"]} steps',
            f'- Total Node steps: {node_stats["total"]}',
            '',
            f'**Internal Steps** (Pure transforms - implementation only):',
            f'- 🔌 Implemented: {internal_stats["🔌"]} steps',
            f'- ❌ Missing: {internal_stats["❌"]} steps',
            f'- Total Internal steps: {internal_stats["total"]}',
            '',
            f'**Overall Statistics:**',
            f'- ✅ Fully Functional: {summary["by_status"]["✅"]} steps',
            f'- 🔌 Implemented (internal) or Not Wired: {summary["by_status"]["🔌"]} steps',
            f'- ❌ Missing: {summary["by_status"]["❌"]} steps',
            f'- Total steps: {summary["total_steps"]}',
            '',
            '**By Category:**'
        ]

        for category, statuses in sorted(summary['by_category'].items()):
            total = sum(statuses.values())
            impl = statuses.get('✅', 0)
            internal_impl = statuses.get('🔌', 0)
            lines.append(f'- **{category}**: {impl} wired + {internal_impl} internal / {total} total')

        return lines


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Audit RAG steps against code implementation')
    parser.add_argument('--write', action='store_true', default=True,
                        help='Update documentation (default)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without writing')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Handle conflicting flags
    if args.dry_run:
        write = False
    else:
        write = args.write
    
    # Get paths
    base_dir = Path(__file__).parent.parent
    steps_file = base_dir / 'docs/architecture/rag_steps.yml'
    code_index_file = base_dir / 'build/rag_code_index.json'
    
    # Check dependencies
    if not steps_file.exists():
        print(f"ERROR: Steps file not found: {steps_file}")
        print("Run: python scripts/rag_stepgen.py --write")
        return 1
    
    if not code_index_file.exists():
        print(f"ERROR: Code index not found: {code_index_file}")
        print("Run: python scripts/rag_code_graph.py --write")
        return 1
    
    # Run audit
    print("🔍 Starting RAG audit...")
    auditor = RAGAuditor(steps_file, code_index_file, verbose=args.verbose)
    auditor.load_data()
    
    results = auditor.audit_all_steps()
    
    # Update documentation
    if write:
        print("📝 Updating step documentation...")
        auditor.update_step_docs(base_dir)
        
        print("📊 Updating conformance dashboard...")
        auditor.update_conformance_dashboard(base_dir)
        
        print("✅ Documentation updated")
    else:
        print("🔍 DRY RUN - No files updated")
    
    # Print summary
    print(f"\n📊 Audit Results:")
    print(f"  Total steps: {results['total_steps']}")
    print(f"  ✅ Implemented: {results['by_status']['✅']}")
    print(f"  🟡 Partial: {results['by_status']['🟡']}")
    print(f"  🔌 Not wired: {results['by_status']['🔌']}")
    print(f"  ❌ Missing: {results['by_status']['❌']}")
    
    # Show examples
    if args.verbose:
        for status, examples in results['examples'].items():
            if examples:
                print(f"\n{status} Examples:")
                for ex in examples[:3]:
                    candidate_info = ""
                    if ex['top_candidate']:
                        candidate_info = f" -> {ex['top_candidate']['qualname']} ({ex['top_candidate']['score']:.2f})"
                    print(f"  Step {ex['step']}: {ex['node_id']}{candidate_info}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())