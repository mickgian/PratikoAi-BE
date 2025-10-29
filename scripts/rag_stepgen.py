#!/usr/bin/env python3
"""
RAG Step Generator - Parses Mermaid diagram and generates step registry and documentation.

Usage:
    python scripts/rag_stepgen.py --write    # Generate all outputs
    python scripts/rag_stepgen.py --dry-run  # Preview without writing
    python scripts/rag_stepgen.py --verbose  # Detailed output
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import yaml


class MermaidParser:
    """Parse Mermaid flowchart and extract nodes."""
    
    def __init__(self, content: str):
        self.content = content
        self.nodes: Dict[str, Dict] = {}
        self.node_order: List[str] = []
        self.class_mappings: Dict[str, str] = {}
        
    def parse(self) -> Dict[str, Dict]:
        """Parse Mermaid content and return nodes."""
        # First pass: extract class mappings
        self._parse_class_assignments()
        
        # Second pass: extract nodes
        self._parse_nodes()
        
        # Third pass: apply class overrides
        self._apply_class_overrides()
        
        return self.nodes
    
    def _parse_class_assignments(self):
        """Parse class assignments like 'class A,B,C startEnd'."""
        pattern = r'^\s*class\s+([\w,\s]+)\s+(\w+)\s*$'
        
        for line in self.content.split('\n'):
            match = re.match(pattern, line)
            if match:
                node_list = match.group(1)
                class_name = match.group(2)
                
                # Map class names to types
                type_map = {
                    'startEnd': 'startEnd',
                    'process': 'process',
                    'decision': 'decision',
                    'error': 'error',
                    'database': 'database'
                }
                
                if class_name in type_map:
                    for node_id in node_list.split(','):
                        node_id = node_id.strip()
                        if node_id:
                            self.class_mappings[node_id] = type_map[class_name]
    
    def _parse_nodes(self):
        """Extract nodes from Mermaid syntax."""
        seen = set()
        
        # More comprehensive patterns to handle all node definitions in connections
        # Pattern to match node definitions with labels in various formats
        node_patterns = [
            # NodeId[Label] - square brackets (process)
            (r'(\w+)\s*\[([^\]]+)\]', 'process'),
            # NodeId{Label} - curly braces (decision)  
            (r'(\w+)\s*\{([^\}]+)\}', 'decision'),
            # NodeId([Label]) or NodeId(Label) - parentheses (startEnd/process)
            (r'(\w+)\s*\(\[([^\]]+)\]\)', 'startEnd'),  # With square brackets inside
            (r'(\w+)\s*\(([^\)]+)\)', 'process'),  # Without square brackets
            # NodeId[(Label)] - database
            (r'(\w+)\s*\[\(([^\)]+)\)\]', 'database'),
        ]
        
        for line in self.content.split('\n'):
            line = line.strip()
            
            # Skip comments, empty lines, and style definitions
            if not line or line.startswith('%%') or line.startswith('classDef') or line.startswith('flowchart'):
                continue
            
            # Skip class assignments (we handle those separately)
            if line.startswith('class '):
                continue
                
            # Look for node definitions anywhere in the line (including in connections)
            for pattern, node_type in node_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    node_id = match.group(1)
                    label = match.group(2)
                    
                    # Clean label
                    label = self._clean_label(label)
                    
                    # Only add if not seen before (first occurrence wins)
                    if node_id not in seen:
                        seen.add(node_id)
                        self.node_order.append(node_id)
                        self.nodes[node_id] = {
                            'node_id': node_id,
                            'node_label': label,
                            'type': node_type
                        }
    
    def _clean_label(self, label: str) -> str:
        """Clean HTML and whitespace from label."""
        # Convert <br/> to space
        label = re.sub(r'<br\s*/?\s*>', ' ', label)
        # Remove other HTML tags
        label = re.sub(r'<[^>]+>', '', label)
        # Collapse whitespace
        label = ' '.join(label.split())
        return label
    
    def _apply_class_overrides(self):
        """Apply class-based type overrides."""
        for node_id, override_type in self.class_mappings.items():
            if node_id in self.nodes:
                # Skip database nodes - they should be excluded
                if override_type != 'database':
                    self.nodes[node_id]['type'] = override_type
                else:
                    # Mark for exclusion
                    self.nodes[node_id]['exclude'] = True


class StepRegistry:
    """Manage the append-only step registry."""
    
    def __init__(self, registry_path: Path):
        self.registry_path = registry_path
        self.steps: List[Dict] = []
        self.existing_ids: Set[str] = set()
        self.max_step_num = 0
        
    def load_existing(self):
        """Load existing registry if it exists."""
        if self.registry_path.exists():
            with open(self.registry_path, 'r') as f:
                data = yaml.safe_load(f) or {}
                self.steps = data.get('steps', [])
                
                # Track existing IDs and max step number
                for step in self.steps:
                    self.existing_ids.add(step['node_id'])
                    self.max_step_num = max(self.max_step_num, step['step'])
    
    def add_new_nodes(self, nodes: Dict[str, Dict], node_order: List[str]) -> List[Dict]:
        """Add new nodes to registry, preserving existing entries."""
        new_steps = []
        
        for node_id in node_order:
            if node_id not in nodes:
                continue
                
            node = nodes[node_id]
            
            # Skip excluded nodes (database)
            if node.get('exclude'):
                continue
            
            # Skip if already in registry
            if node_id in self.existing_ids:
                continue
            
            # Assign next step number
            self.max_step_num += 1
            
            # Infer category
            category = self._infer_category(node['node_label'], node_id)
            
            # Generate stable ID
            stable_id = self._generate_stable_id(category, node['node_label'], node_id)
            
            step_entry = {
                'step': self.max_step_num,
                'id': stable_id,
                'node_id': node_id,
                'node_label': node['node_label'],
                'type': node['type'],
                'category': category,
                'nodes': [node_id],
                'code_owner': 'TBD'
            }
            
            self.steps.append(step_entry)
            new_steps.append(step_entry)
            self.existing_ids.add(node_id)
        
        return new_steps
    
    def _infer_category(self, label: str, node_id: str) -> str:
        """Infer category from label and node_id."""
        text = (label + ' ' + node_id).lower()
        
        # Category rules (order matters - first match wins)
        rules = [
            (['privacy', 'anonymize', 'gdpr'], 'privacy'),
            (['fact', 'canonical'], 'facts'),
            (['attach', 'pre', 'fingerprint', 'signature'], 'preflight'),
            (['golden', 'faq'], 'golden'),
            (['kb', 'knowledge', 'rss'], 'kb'),
            (['classify', 'domain', 'score', 'confidence', 'llm fallback'], 'classify'),
            (['prompt', 'system', 'template'], 'prompting'),
            (['provider', 'route', 'cost', 'failover'], 'providers'),
            (['cache', 'redis', 'hash', 'epoch'], 'cache'),
            (['llm'], 'llm'),
            (['tool type?'], 'routing'),
            (['ccnl'], 'ccnl'),
            (['doc', 'parser', 'ocr', 'blob', 'provenance'], 'docs'),
            (['stream', 'sse'], 'streaming'),
            (['metric', 'usage', 'collect'], 'metrics'),
            (['feedback'], 'feedback'),
            (['response', 'final', 'processmsg'], 'response'),
        ]
        
        for keywords, category in rules:
            if any(kw in text for kw in keywords):
                return category
        
        return 'platform'
    
    def _generate_stable_id(self, category: str, label: str, node_id: str) -> str:
        """Generate stable ID: RAG.<category>.<slug>"""
        # Use label if available, otherwise node_id
        base = label if label else node_id
        
        # Convert to slug: lowercase, replace spaces/punct with dots
        slug = base.lower()
        slug = re.sub(r'[^a-z0-9]+', '.', slug)
        slug = re.sub(r'\.+', '.', slug)
        slug = slug.strip('.')
        
        return f"RAG.{category}.{slug}"
    
    def save(self):
        """Save registry to YAML file."""
        # Sort by step number
        self.steps.sort(key=lambda x: x['step'])
        
        data = {'steps': self.steps}
        
        with open(self.registry_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, width=120)


class StepDocGenerator:
    """Generate per-step documentation files."""
    
    def __init__(self, steps_dir: Path):
        self.steps_dir = steps_dir
        self.steps_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_missing_docs(self, steps: List[Dict]) -> List[Path]:
        """Generate documentation for steps that don't have files yet."""
        created = []
        
        for step in steps:
            doc_path = self._get_doc_path(step)
            
            if not doc_path.exists():
                self._create_doc(step, doc_path)
                created.append(doc_path)
        
        return created
    
    def _get_doc_path(self, step: Dict) -> Path:
        """Get path for step documentation."""
        filename = f"STEP-{step['step']}-{step['id']}.md"
        return self.steps_dir / filename
    
    def _create_doc(self, step: Dict, path: Path):
        """Create documentation file for a step."""
        template = f"""# RAG STEP {step['step']} — {step['node_label']} ({step['id']})

**Type:** {step['type']}  
**Category:** {step['category']}  
**Node ID:** `{step['node_id']}`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `{step['node_id']}` ({step['node_label']}).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ❓ Pending review (✅ Implemented / 🟡 Partial / ❌ Missing / 🔌 Not wired)
- **Behavior notes:** _TBD_

## Differences (Blueprint vs Current)
- _TBD_

## Risks / Impact
- _TBD_

## TDD Task List
- [ ] Unit tests (list specific cases)
- [ ] Integration tests (list cases)
- [ ] Implementation changes (bullets)
- [ ] Observability: add structured log line  
  `RAG STEP {step['step']} ({step['id']}): {step['node_label']} | attrs={{...}}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`
"""
        
        with open(path, 'w') as f:
            f.write(template)


class ConformanceDashboard:
    """Generate conformance dashboard."""
    
    def __init__(self, dashboard_path: Path):
        self.dashboard_path = dashboard_path
    
    def generate(self, steps: List[Dict]):
        """Generate the conformance dashboard."""
        content = """# RAG Conformance Dashboard

This dashboard tracks the implementation status of each step in the PratikoAI RAG blueprint. 
It is automatically generated from the Mermaid diagram using append-only step numbering. 
Each step should be audited and its documentation filled during the conformance review.

## Step Registry

| Step | ID | Node | Type | Category | Owner | Doc |
|------|----|----|------|----------|-------|-----|
"""
        
        # Sort by step number
        sorted_steps = sorted(steps, key=lambda x: x['step'])
        
        for step in sorted_steps:
            doc_link = f"[📄](steps/STEP-{step['step']}-{step['id']}.md)"
            row = f"| {step['step']} | {step['id']} | {step['node_id']} | {step['type']} | {step['category']} | {step['code_owner']} | {doc_link} |\n"
            content += row
        
        content += """
## How to Update

1. **Edit the Mermaid diagram**: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
2. **Regenerate registry and docs**: `python scripts/rag_stepgen.py --write`
3. **Fill/update per-step documentation**: Edit files in `docs/architecture/steps/`
4. **Review changes**: Check git diff to ensure only intended changes

## Statistics

"""
        
        # Add statistics
        type_counts = {}
        category_counts = {}
        
        for step in steps:
            type_counts[step['type']] = type_counts.get(step['type'], 0) + 1
            category_counts[step['category']] = category_counts.get(step['category'], 0) + 1
        
        content += f"- **Total Steps**: {len(steps)}\n"
        content += "- **By Type**: " + ", ".join(f"{t}: {c}" for t, c in sorted(type_counts.items())) + "\n"
        content += "- **By Category**: " + ", ".join(f"{cat}: {c}" for cat, c in sorted(category_counts.items())) + "\n"
        
        with open(self.dashboard_path, 'w') as f:
            f.write(content)


class RAGStepGenerator:
    """Main orchestrator for RAG step generation."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.mermaid_path = base_dir / 'docs/architecture/diagrams/pratikoai_rag_hybrid.mmd'
        self.registry_path = base_dir / 'docs/architecture/rag_steps.yml'
        self.steps_dir = base_dir / 'docs/architecture/steps'
        self.dashboard_path = base_dir / 'docs/architecture/rag_conformance.md'
        
    def run(self, write: bool = True, verbose: bool = False) -> Dict:
        """Run the generation process."""
        results = {
            'parsed_nodes': 0,
            'total_steps': 0,
            'new_steps': 0,
            'created_docs': [],
            'type_counts': {},
            'sample_nodes': []
        }
        
        # Check Mermaid file exists
        if not self.mermaid_path.exists():
            print(f"ERROR: Mermaid file not found: {self.mermaid_path}")
            sys.exit(1)
        
        # Parse Mermaid
        if verbose:
            print(f"Parsing Mermaid from: {self.mermaid_path}")
        
        with open(self.mermaid_path, 'r') as f:
            content = f.read()
        
        parser = MermaidParser(content)
        nodes = parser.parse()
        
        # Filter out excluded nodes
        valid_nodes = {k: v for k, v in nodes.items() if not v.get('exclude')}
        results['parsed_nodes'] = len(valid_nodes)
        
        if results['parsed_nodes'] == 0:
            print("ERROR: No nodes parsed from Mermaid file")
            sys.exit(1)
        
        # Count by type
        for node in valid_nodes.values():
            node_type = node['type']
            results['type_counts'][node_type] = results['type_counts'].get(node_type, 0) + 1
        
        # Load/create registry
        registry = StepRegistry(self.registry_path)
        registry.load_existing()
        
        # Add new nodes
        new_steps = registry.add_new_nodes(valid_nodes, parser.node_order)
        results['new_steps'] = len(new_steps)
        results['total_steps'] = len(registry.steps)
        
        # Sample nodes for dry-run
        results['sample_nodes'] = new_steps[:10]
        
        if write:
            # Save registry
            if verbose:
                print(f"Writing registry to: {self.registry_path}")
            registry.save()
            
            # Generate missing docs
            doc_gen = StepDocGenerator(self.steps_dir)
            created_docs = doc_gen.generate_missing_docs(registry.steps)
            results['created_docs'] = created_docs
            
            if verbose and created_docs:
                print(f"Created {len(created_docs)} new step documentation files")
            
            # Generate dashboard
            if verbose:
                print(f"Writing dashboard to: {self.dashboard_path}")
            dashboard = ConformanceDashboard(self.dashboard_path)
            dashboard.generate(registry.steps)
        
        return results


def print_summary(results: Dict, write: bool, base_dir: Path):
    """Print execution summary."""
    print("\n" + "="*60)
    print("RAG STEP GENERATOR SUMMARY")
    print("="*60)
    
    print(f"\n📊 Parsing Results:")
    print(f"  - Total parsed nodes: {results['parsed_nodes']}")
    print(f"  - Node types: {', '.join(f'{t}: {c}' for t, c in sorted(results['type_counts'].items()))}")
    
    print(f"\n📝 Registry Status:")
    print(f"  - Total steps: {results['total_steps']}")
    print(f"  - New steps added: {results['new_steps']}")
    
    if not write:
        print("\n🔍 DRY RUN MODE - No files written")
        if results['sample_nodes']:
            print(f"\nSample new nodes (up to 10):")
            for step in results['sample_nodes']:
                print(f"  Step {step['step']}: {step['node_id']} ({step['node_label'][:40]}...)")
    else:
        print("\n✅ FILES WRITTEN")
        
        # Show registry preview
        registry_path = base_dir / 'docs/architecture/rag_steps.yml'
        if registry_path.exists():
            print(f"\n📄 Registry Preview (first 20 lines of {registry_path}):")
            with open(registry_path, 'r') as f:
                lines = f.readlines()[:20]
                for line in lines:
                    print(f"  {line.rstrip()}")
        
        # Show created docs
        if results['created_docs']:
            print(f"\n📚 Created {len(results['created_docs'])} new step documentation files:")
            # Show first and mid-range
            if len(results['created_docs']) > 0:
                print(f"  - {results['created_docs'][0]}")
            if len(results['created_docs']) > 1:
                mid_idx = len(results['created_docs']) // 2
                print(f"  - {results['created_docs'][mid_idx]}")
            if len(results['created_docs']) > 2:
                print(f"  - ... and {len(results['created_docs']) - 2} more")
        
        # Show dashboard preview
        dashboard_path = base_dir / 'docs/architecture/rag_conformance.md'
        if dashboard_path.exists():
            print(f"\n📊 Dashboard Preview (first 20 lines of {dashboard_path}):")
            with open(dashboard_path, 'r') as f:
                lines = f.readlines()[:20]
                for line in lines:
                    print(f"  {line.rstrip()}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate RAG step registry and documentation from Mermaid diagram')
    parser.add_argument('--write', action='store_true', default=False,
                        help='Write files (default is dry-run)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without writing files')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Handle conflicting flags
    if args.dry_run:
        write = False
    else:
        write = args.write
    
    # Get base directory (parent of scripts/)
    base_dir = Path(__file__).parent.parent
    
    # Run generator
    generator = RAGStepGenerator(base_dir)
    results = generator.run(write=write, verbose=args.verbose)
    
    # Print summary
    print_summary(results, write, base_dir)
    
    if write:
        print("\n🔍 Git status:")
        import subprocess
        try:
            result = subprocess.run(['git', 'status', '--short'], 
                                    capture_output=True, text=True, cwd=base_dir)
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    print(f"  {line}")
            else:
                print("  No changes detected")
        except:
            print("  Unable to get git status")
    
    print("\n✨ Done!")
    return 0


if __name__ == '__main__':
    sys.exit(main())