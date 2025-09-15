#!/usr/bin/env python3
"""
RAG Code Graph Smoke Test - Validates the code graph builder produces valid output.

Usage:
    python scripts/rag_code_graph_test.py
"""

import json
import sys
import subprocess
from pathlib import Path


def run_smoke_test() -> bool:
    """Run smoke test for the code graph builder."""
    base_dir = Path(__file__).parent.parent
    graph_script = base_dir / 'scripts/rag_code_graph.py'
    output_file = base_dir / 'build/rag_code_index.json'
    
    print("🧪 Running RAG Code Graph Smoke Test")
    
    # 1. Run the code graph builder
    print("📊 Building code graph...")
    try:
        result = subprocess.run([
            sys.executable, str(graph_script), '--write'
        ], capture_output=True, text=True, cwd=base_dir)
        
        if result.returncode != 0:
            print(f"❌ Code graph builder failed:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Failed to run code graph builder: {e}")
        return False
    
    # 2. Check output file exists
    if not output_file.exists():
        print(f"❌ Output file not created: {output_file}")
        return False
    
    print(f"✅ Output file created: {output_file}")
    
    # 3. Load and validate JSON
    try:
        with open(output_file, 'r') as f:
            graph = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load JSON: {e}")
        return False
    
    print("✅ JSON is valid")
    
    # 4. Validate structure
    required_keys = ['files', 'edges']
    for key in required_keys:
        if key not in graph:
            print(f"❌ Missing required key: {key}")
            return False
    
    # 5. Check files array
    files = graph['files']
    if not isinstance(files, list):
        print("❌ 'files' should be a list")
        return False
    
    if len(files) == 0:
        print("❌ No files found in graph")
        return False
    
    print(f"✅ Found {len(files)} files")
    
    # 6. Check file structure
    for file_data in files[:3]:  # Check first 3 files
        required_file_keys = ['path', 'imports', 'symbols']
        for key in required_file_keys:
            if key not in file_data:
                print(f"❌ File missing required key: {key}")
                return False
    
    # 7. Count symbols
    total_symbols = sum(len(f['symbols']) for f in files)
    if total_symbols == 0:
        print("❌ No symbols found in graph")
        return False
    
    print(f"✅ Found {total_symbols} symbols")
    
    # 8. Check symbol structure
    symbol_found = False
    for file_data in files:
        if file_data['symbols']:
            symbol = file_data['symbols'][0]
            required_symbol_keys = ['kind', 'name', 'qualname', 'line']
            for key in required_symbol_keys:
                if key not in symbol:
                    print(f"❌ Symbol missing required key: {key}")
                    return False
            symbol_found = True
            break
    
    if not symbol_found:
        print("❌ No symbols with required structure found")
        return False
    
    print("✅ Symbol structure is valid")
    
    # 9. Check edges
    edges = graph['edges']
    if not isinstance(edges, dict):
        print("❌ 'edges' should be a dict")
        return False
    
    required_edge_keys = ['imports', 'calls']
    for key in required_edge_keys:
        if key not in edges:
            print(f"❌ Edges missing required key: {key}")
            return False
        
        if not isinstance(edges[key], list):
            print(f"❌ edges['{key}'] should be a list")
            return False
    
    print(f"✅ Found {len(edges['imports'])} import edges and {len(edges['calls'])} call edges")
    
    # 10. Basic sanity checks
    app_files = [f for f in files if f['path'].startswith('app/')]
    if len(app_files) < 5:  # Should have at least 5 files in app/
        print(f"⚠️  Warning: Only found {len(app_files)} files in app/ directory")
    else:
        print(f"✅ Found {len(app_files)} files in app/ directory")
    
    # 11. Check for expected patterns
    expected_patterns = ['service', 'model', 'api', 'core']
    found_patterns = set()
    
    for file_data in files:
        path = file_data['path'].lower()
        for pattern in expected_patterns:
            if pattern in path:
                found_patterns.add(pattern)
    
    print(f"✅ Found expected patterns: {', '.join(sorted(found_patterns))}")
    
    print("\n🎉 All smoke tests passed!")
    print(f"📈 Summary:")
    print(f"   - Files: {len(files)}")
    print(f"   - Symbols: {total_symbols}")
    print(f"   - Import edges: {len(edges['imports'])}")
    print(f"   - Call edges: {len(edges['calls'])}")
    
    return True


def main():
    """Main entry point."""
    success = run_smoke_test()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())