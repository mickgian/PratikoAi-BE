#!/usr/bin/env python3
"""
RAG Backlog - Create GitHub issues from step documentation.

Usage:
    python scripts/rag_backlog.py --create-github               # Create GitHub Issues
    python scripts/rag_backlog.py --create-github --assignee username
    python scripts/rag_backlog.py --dry-run                     # Preview without creating
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
import yaml


class RAGBacklogGenerator:
    """Create GitHub issues from RAG step documentation."""
    
    def __init__(self, base_dir: Path, verbose: bool = False):
        self.base_dir = base_dir
        self.verbose = verbose
        self.steps_dir = base_dir / 'docs/architecture/steps'
        self.steps_registry = base_dir / 'docs/architecture/rag_steps.yml'
        
        # Status to GitHub label mapping
        self.status_labels = {
            '✅': 'status/implemented',
            '🟡': 'status/partial', 
            '🔌': 'status/not-wired',
            '❌': 'status/missing',
            '❓': 'status/unknown'
        }
        
    def load_steps_registry(self) -> Dict[int, Dict]:
        """Load the steps registry for metadata."""
        if not self.steps_registry.exists():
            return {}
            
        with open(self.steps_registry, 'r') as f:
            data = yaml.safe_load(f)
            steps = data.get('steps', [])
            
        # Index by step number
        return {step['step']: step for step in steps}
    
    def parse_step_doc(self, doc_path: Path) -> Optional[Dict]:
        """Parse a step documentation file."""
        if not doc_path.exists():
            return None
            
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            if self.verbose:
                print(f"Failed to read {doc_path}: {e}")
            return None
        
        # Extract title (first # line)
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        if not title_match:
            return None
        title = title_match.group(1)
        
        # Parse step number from title
        step_match = re.search(r'RAG STEP (\d+)', title)
        if not step_match:
            return None
        step_num = int(step_match.group(1))
        
        # Extract type and category from **Type:** and **Category:** lines  
        type_match = re.search(r'\*\*Type:\*\* (\w+)', content)
        category_match = re.search(r'\*\*Category:\*\* (\w+)', content)
        node_id_match = re.search(r'\*\*Node ID:\*\* `([^`]+)`', content)
        
        # Extract AUTO-AUDIT block
        audit_block = self._extract_audit_block(content)
        
        return {
            'step': step_num,
            'title': title,
            'type': type_match.group(1) if type_match else 'unknown',
            'category': category_match.group(1) if category_match else 'unknown', 
            'node_id': node_id_match.group(1) if node_id_match else 'unknown',
            'doc_path': doc_path,
            'audit': audit_block
        }
    
    def _extract_audit_block(self, content: str) -> Dict:
        """Extract AUTO-AUDIT block information."""
        audit_match = re.search(
            r'<!-- AUTO-AUDIT:BEGIN -->(.*?)<!-- AUTO-AUDIT:END -->', 
            content, 
            re.DOTALL
        )
        
        if not audit_match:
            return {
                'status': '❓',
                'confidence': 0.0,
                'suggestions': []
            }
        
        audit_content = audit_match.group(1)
        
        # Extract status and confidence
        status_match = re.search(r'Status: ([✅🟡🔌❌❓])\s*\|\s*Confidence: ([\d.]+)', audit_content)
        status = status_match.group(1) if status_match else '❓'
        confidence = float(status_match.group(2)) if status_match else 0.0
        
        # Extract TDD suggestions
        suggestions = []
        suggestion_section = re.search(
            r'Suggested next TDD actions:(.*?)(?=\n\n|\n<!--|\Z)', 
            audit_content, 
            re.DOTALL
        )
        
        if suggestion_section:
            suggestion_lines = suggestion_section.group(1).strip().split('\n')
            for line in suggestion_lines:
                line = line.strip()
                if line.startswith('- '):
                    suggestions.append(line[2:])
        
        return {
            'status': status,
            'confidence': confidence,  
            'suggestions': suggestions
        }
    
    def _check_existing_issue(self, title: str) -> bool:
        """Check if an open GitHub issue with the same title already exists."""
        try:
            # List open issues and search for matching title
            result = subprocess.run([
                'gh', 'issue', 'list', 
                '--state', 'open',
                '--json', 'title',
                '--limit', '1000'  # Reasonable limit
            ], check=True, capture_output=True, text=True, cwd=self.base_dir)
            
            issues = json.loads(result.stdout)
            existing_titles = [issue['title'] for issue in issues]
            
            return title in existing_titles
            
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            if self.verbose:
                print(f"Warning: Could not check existing issues: {e}")
            return False  # Assume it doesn't exist if we can't check
    
    def create_github_issues(self, assignee: Optional[str] = None, labels: Optional[List[str]] = None) -> List[str]:
        """Create GitHub issues from step documentation."""
        created_issues = []
        skipped_issues = []
        
        # Check if GitHub CLI is available
        try:
            subprocess.run(['gh', '--version'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("ERROR: GitHub CLI (gh) not found. Please install it to create issues.")
            return []
        
        # Check if we're in a git repo with GitHub remote
        try:
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                  check=True, capture_output=True, text=True, cwd=self.base_dir)
            remote_url = result.stdout.strip()
            if 'github.com' not in remote_url:
                print("ERROR: Origin remote is not a GitHub repository")
                return []
        except subprocess.CalledProcessError:
            print("ERROR: No git origin remote found")
            return []
        
        # Load steps registry
        registry = self.load_steps_registry()
        
        # Process all step docs directly
        step_docs = list(self.steps_dir.glob('STEP-*.md'))
        step_docs.sort()
        
        for doc_path in step_docs:
            step_data = self.parse_step_doc(doc_path)
            if not step_data:
                continue
                
            title = step_data['title']
            step_num = step_data['step']
            status = step_data['audit']['status']
            suggestions = step_data['audit']['suggestions']
            confidence = step_data['audit']['confidence']
            
            # Skip already implemented steps
            if status == '✅':
                if self.verbose:
                    print(f"Skipping implemented step: {title}")
                continue
            
            # Check if issue already exists
            if self._check_existing_issue(title):
                if self.verbose:
                    print(f"Issue already exists, skipping: {title}")
                skipped_issues.append(title)
                continue
            
            # Get step metadata
            step_meta = registry.get(step_num, {})
            step_id = step_meta.get('id', 'unknown')
            category = step_data['category']
            
            # Build issue body
            body = f"""## Context
**Step Number**: {step_num}  
**Status**: {status} (Confidence: {confidence:.2f})  
**Type**: {step_data['type']}  
**Category**: {category}  
**Node ID**: `{step_data['node_id']}`

This step is part of the PratikoAI RAG blueprint implementation. The audit system has classified it as **{status}** based on code analysis.

## Implementation Checklist

"""
            
            # Add TDD suggestions as checklist
            if suggestions:
                for suggestion in suggestions:
                    body += f"- [ ] {suggestion}\n"
            else:
                body += "- [ ] Implementation needed (see step documentation for details)\n"
            
            body += f"""
## Links
- [Step Documentation](docs/architecture/steps/STEP-{step_num}-{step_id}.md)
- [RAG Conformance Dashboard](docs/architecture/rag_conformance.md)
- [RAG Diagram](docs/architecture/diagrams/pratikoai_rag.mmd)
"""
            
            # Build labels
            issue_labels = [
                'rag',
                f'step/{step_num}', 
                f'area/{category}',
                self.status_labels.get(status, 'status/unknown')
            ]
            
            # Add any additional labels passed in
            if labels:
                issue_labels.extend(labels)
            
            # Create issue
            try:
                cmd = [
                    'gh', 'issue', 'create',
                    '--title', title,
                    '--body', body,
                    '--label', ','.join(issue_labels)
                ]
                
                if assignee:
                    cmd.extend(['--assignee', assignee])
                
                result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=self.base_dir)
                issue_url = result.stdout.strip()
                created_issues.append(issue_url)
                
                if self.verbose:
                    print(f"Created issue: {issue_url}")
                    
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr if e.stderr else str(e)
                print(f"Failed to create issue for step {step_num}: {error_msg}")
        
        if skipped_issues and self.verbose:
            print(f"\nSkipped {len(skipped_issues)} existing issues")
            
        return created_issues
    
    def get_summary(self) -> Dict:
        """Get summary statistics."""
        step_docs = list(self.steps_dir.glob('STEP-*.md'))
        
        # Count by status
        status_counts = {'✅': 0, '🟡': 0, '🔌': 0, '❌': 0, '❓': 0}
        category_counts = {}
        
        for doc_path in step_docs:
            step_data = self.parse_step_doc(doc_path)
            if not step_data:
                continue
                
            status = step_data['audit']['status']
            category = step_data['category']
            
            status_counts[status] = status_counts.get(status, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            'total_steps': len(step_docs),
            'by_status': status_counts,
            'by_category': category_counts
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Create GitHub issues from RAG step documentation')
    
    parser.add_argument('--create-github', action='store_true',
                        help='Create GitHub issues')
    parser.add_argument('--assignee', type=str,
                        help='GitHub username to assign issues to')
    parser.add_argument('--labels', type=str, nargs='*',
                        help='Additional labels for GitHub issues')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without creating issues')
    
    args = parser.parse_args()
    
    # Get base directory
    base_dir = Path(__file__).parent.parent
    
    # Run generator
    generator = RAGBacklogGenerator(base_dir, verbose=args.verbose)
    
    if args.dry_run:
        print("🔍 DRY RUN - No issues created")
        summary = generator.get_summary()
        print(f"\n📊 Would process {summary['total_steps']} steps")
        print(f"  ✅ Implemented: {summary['by_status']['✅']} (skipped)")
        print(f"  🟡 Partial: {summary['by_status']['🟡']}")
        print(f"  🔌 Not wired: {summary['by_status']['🔌']}")
        print(f"  ❌ Missing: {summary['by_status']['❌']}")
        return 0
    
    # Create GitHub issues
    if args.create_github:
        print("🚀 Creating GitHub issues...")
        created_issues = generator.create_github_issues(
            assignee=args.assignee, 
            labels=args.labels
        )
        print(f"✅ Created {len(created_issues)} GitHub issues")
        
        if created_issues and args.verbose:
            print("\nCreated issues:")
            for url in created_issues[:5]:  # Show first 5
                print(f"  {url}")
            if len(created_issues) > 5:
                print(f"  ... and {len(created_issues) - 5} more")
    else:
        # Show help if no action specified
        print("Usage: python scripts/rag_backlog.py --create-github")
        print("       python scripts/rag_backlog.py --dry-run")
    
    # Print summary
    summary = generator.get_summary()
    print(f"\n📊 Summary:")
    print(f"  Total steps: {summary['total_steps']}")
    print(f"  ✅ Implemented: {summary['by_status']['✅']}")
    print(f"  🟡 Partial: {summary['by_status']['🟡']}")
    print(f"  🔌 Not wired: {summary['by_status']['🔌']}")
    print(f"  ❌ Missing: {summary['by_status']['❌']}")
    
    # Show top categories
    if args.verbose:
        print("\nBy Category:")
        for category, count in sorted(summary['by_category'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {category}: {count} steps")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())