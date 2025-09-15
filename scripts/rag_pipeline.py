#!/usr/bin/env python3
"""
RAG Pipeline - Coordinate audit and backlog generation.

Usage:
    python scripts/rag_pipeline.py                          # Run audit + generate index
    python scripts/rag_pipeline.py --verbose                # Verbose output
    python scripts/rag_pipeline.py --create-issues          # Also create GitHub issues
    python scripts/rag_pipeline.py --create-issues --assignee username
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, description: str, verbose: bool = False) -> bool:
    """Run a command and return True if successful."""
    if verbose:
        print(f"🔄 {description}...")
        print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=not verbose, text=True)
        if verbose and result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run RAG pipeline: audit + backlog generation')
    
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--create-issues', action='store_true',
                        help='Create GitHub issues after backlog generation')
    parser.add_argument('--assignee', type=str,
                        help='GitHub username to assign issues to')
    parser.add_argument('--labels', type=str, nargs='*',
                        help='Additional labels for GitHub issues')
    parser.add_argument('--skip-audit', action='store_true',
                        help='Skip audit step, only generate backlog')
    
    args = parser.parse_args()
    
    base_dir = Path(__file__).parent.parent
    
    print("🚀 RAG Pipeline Starting...")
    
    success = True
    
    # Step 1: Run audit (unless skipped)
    if not args.skip_audit:
        audit_cmd = ['python', 'scripts/rag_audit.py', '--write']
        if args.verbose:
            audit_cmd.append('--verbose')
        
        if not run_command(audit_cmd, "Running RAG audit", args.verbose):
            success = False
    else:
        print("⏭️  Skipping audit step")
    
    # Step 2: Create GitHub issues if requested
    if args.create_issues and success:
        issue_cmd = ['python', 'scripts/rag_backlog.py', '--create-github']
        
        if args.assignee:
            issue_cmd.extend(['--assignee', args.assignee])
        
        if args.labels:
            issue_cmd.extend(['--labels'] + args.labels)
        
        if args.verbose:
            issue_cmd.append('--verbose')
        
        if not run_command(issue_cmd, "Creating GitHub issues", args.verbose):
            success = False
    
    if success:
        print("✅ RAG Pipeline completed successfully")
        
        if not args.verbose:
            print("\nOutput files:")
            print("  - docs/architecture/rag_conformance.md (updated)")
            if args.create_issues:
                print("  - GitHub issues (created)")
    else:
        print("❌ RAG Pipeline failed")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())