#!/usr/bin/env python3
"""
RAG Code Graph Builder - Scans Python files to build a code graph for audit.

Usage:
    python scripts/rag_code_graph.py --write    # Generate code index (default)
    python scripts/rag_code_graph.py --dry-run  # Preview without writing
    python scripts/rag_code_graph.py --verbose  # Detailed output
"""

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class CodeGraphBuilder:
    """Build a code graph from Python AST analysis."""

    EXCLUDE_DIRS = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        "migrations",
        "__pycache__",
        "tests",
        "scripts",
    }

    def __init__(self, root_dir: Path, verbose: bool = False):
        self.root_dir = root_dir
        self.verbose = verbose
        self.files_data = []
        self.import_edges = []
        self.call_edges = []
        self.ast_failures = []

    def scan(self) -> dict[str, Any]:
        """Scan all Python files and build the graph."""
        py_files = self._find_python_files()

        if self.verbose:
            print(f"Found {len(py_files)} Python files to analyze")

        for py_file in py_files:
            self._process_file(py_file)

        return {"files": self.files_data, "edges": {"imports": self.import_edges, "calls": self.call_edges}}

    def _find_python_files(self) -> list[Path]:
        """Find all Python files, excluding certain directories."""
        py_files = []

        for root, dirs, files in os.walk(self.root_dir):
            # Remove excluded directories from traversal
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]

            for file in files:
                if file.endswith(".py"):
                    py_files.append(Path(root) / file)

        return sorted(py_files)

    def _process_file(self, file_path: Path):
        """Process a single Python file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self.ast_failures.append((str(file_path), f"Read error: {e}"))
            return

        # Get relative path
        try:
            rel_path = file_path.relative_to(self.root_dir)
        except ValueError:
            rel_path = file_path

        # Parse AST
        try:
            tree = ast.parse(content, str(file_path))
        except Exception as e:
            self.ast_failures.append((str(rel_path), f"Parse error: {e}"))
            return

        # Extract data
        module_path = str(rel_path)
        imports = self._extract_imports(tree, module_path)
        symbols = self._extract_symbols(tree, module_path, content)

        # Extract leading comments and string literals
        comments = self._extract_comments(content)
        literals = self._extract_string_literals(tree)

        file_data = {
            "path": module_path,
            "imports": imports,
            "symbols": symbols,
            "comments": comments[:5],  # First 5 comments
            "literals": literals[:3],  # First 3 string literals
        }

        self.files_data.append(file_data)

    def _extract_imports(self, tree: ast.AST, module_path: str) -> list[dict]:
        """Extract import statements."""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_name = alias.name
                    imports.append({"type": "import", "name": import_name, "as": alias.asname})
                    # Add import edge
                    self.import_edges.append([module_path, import_name])

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        item_name = alias.name
                        imports.append({"type": "from", "module": node.module, "name": item_name, "as": alias.asname})
                        # Add import edge
                        self.import_edges.append([module_path, node.module])

        return imports

    def _extract_symbols(self, tree: ast.AST, module_path: str, content: str) -> list[dict]:
        """Extract classes, functions, and methods."""
        symbols = []
        content.split("\n")

        # Module-level docstring
        module_doc = ast.get_docstring(tree)
        if module_doc:
            symbols.append(
                {
                    "kind": "module",
                    "name": Path(module_path).stem,
                    "qualname": module_path.replace(".py", "").replace("/", "."),
                    "line": 1,
                    "doc": module_doc[:200],  # Truncate long docstrings
                    "calls": [],
                }
            )

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_qualname = f"{module_path.replace('.py', '').replace('/', '.')}.{node.name}"
                class_doc = ast.get_docstring(node) or ""

                # Extract class-level calls
                class_calls = self._extract_calls(node)

                symbols.append(
                    {
                        "kind": "class",
                        "name": node.name,
                        "qualname": class_qualname,
                        "line": node.lineno,
                        "doc": class_doc[:200],
                        "calls": class_calls,
                    }
                )

                # Extract methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_qualname = f"{class_qualname}.{item.name}"
                        method_doc = ast.get_docstring(item) or ""
                        method_calls = self._extract_calls(item)

                        symbols.append(
                            {
                                "kind": "method",
                                "name": item.name,
                                "qualname": method_qualname,
                                "line": item.lineno,
                                "doc": method_doc[:200],
                                "calls": method_calls,
                            }
                        )

                        # Add call edges
                        for call in method_calls:
                            self.call_edges.append([method_qualname, call["name"]])

            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                func_qualname = f"{module_path.replace('.py', '').replace('/', '.')}.{node.name}"
                func_doc = ast.get_docstring(node) or ""
                func_calls = self._extract_calls(node)

                symbols.append(
                    {
                        "kind": "function",
                        "name": node.name,
                        "qualname": func_qualname,
                        "line": node.lineno,
                        "doc": func_doc[:200],
                        "calls": func_calls,
                    }
                )

                # Add call edges
                for call in func_calls:
                    self.call_edges.append([func_qualname, call["name"]])

        return symbols

    def _extract_calls(self, node: ast.AST) -> list[dict]:
        """Extract function/method calls from a node."""
        calls = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._get_call_name(child.func)
                if call_name:
                    # Try to get qualified name
                    qual = ""
                    if isinstance(child.func, ast.Attribute):
                        qual = self._get_qualified_name(child.func)

                    calls.append({"name": call_name, "qual": qual or call_name})

        return calls

    def _get_call_name(self, node: ast.AST) -> str | None:
        """Get the name of a function being called."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _get_qualified_name(self, node: ast.AST) -> str:
        """Try to get the qualified name of an attribute access."""
        parts = []
        current = node

        while current:
            if isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            elif isinstance(current, ast.Name):
                parts.append(current.id)
                break
            else:
                break

        return ".".join(reversed(parts))

    def _extract_comments(self, content: str) -> list[str]:
        """Extract comment lines from source."""
        comments = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("#"):
                comments.append(line[1:].strip())
        return comments

    def _extract_string_literals(self, tree: ast.AST) -> list[str]:
        """Extract string literals that might contain hints."""
        literals = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value.strip()
                # Skip empty, single char, or very long strings
                if 2 < len(value) < 100 and not value.startswith("__"):
                    literals.append(value)

        return literals

    def get_summary(self) -> dict:
        """Get summary statistics."""
        total_symbols = sum(len(f["symbols"]) for f in self.files_data)

        symbol_counts = {"module": 0, "class": 0, "function": 0, "method": 0}
        for file_data in self.files_data:
            for symbol in file_data["symbols"]:
                kind = symbol["kind"]
                symbol_counts[kind] = symbol_counts.get(kind, 0) + 1

        return {
            "files_scanned": len(self.files_data),
            "ast_failures": len(self.ast_failures),
            "total_symbols": total_symbols,
            "symbol_counts": symbol_counts,
            "import_edges": len(self.import_edges),
            "call_edges": len(self.call_edges),
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build code graph for RAG audit")
    parser.add_argument("--write", action="store_true", default=True, help="Write graph to file (default)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Handle conflicting flags
    if args.dry_run:
        write = False
    else:
        write = args.write

    # Get repo root
    repo_root = Path(__file__).parent.parent

    # Build graph
    print("🔍 Building code graph...")
    builder = CodeGraphBuilder(repo_root, verbose=args.verbose)
    graph = builder.scan()

    # Get summary
    summary = builder.get_summary()

    # Write or preview
    if write:
        # Create build directory
        build_dir = repo_root / "build"
        build_dir.mkdir(exist_ok=True)

        # Write graph
        output_path = build_dir / "rag_code_index.json"
        with open(output_path, "w") as f:
            json.dump(graph, f, indent=2)

        print(f"✅ Wrote code graph to: {output_path}")
    else:
        print("🔍 DRY RUN - No files written")

    # Print summary
    print("\n📊 Summary:")
    print(f"  Files scanned: {summary['files_scanned']}")
    print(f"  AST failures: {summary['ast_failures']}")
    print(f"  Total symbols: {summary['total_symbols']}")
    print(f"    - Modules: {summary['symbol_counts'].get('module', 0)}")
    print(f"    - Classes: {summary['symbol_counts'].get('class', 0)}")
    print(f"    - Functions: {summary['symbol_counts'].get('function', 0)}")
    print(f"    - Methods: {summary['symbol_counts'].get('method', 0)}")
    print(f"  Import edges: {summary['import_edges']}")
    print(f"  Call edges: {summary['call_edges']}")

    # Show failures if any
    if args.verbose and builder.ast_failures:
        print("\n⚠️ AST Failures:")
        for path, error in builder.ast_failures[:10]:
            print(f"  {path}: {error}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
