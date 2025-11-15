#!/usr/bin/env python3
"""Comprehensive check of all modified Python files for errors and warnings."""

import subprocess
import sys
from pathlib import Path


def get_modified_files():
    """Get list of modified Python files from git."""
    result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)

    files = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.strip().split()
        if len(parts) >= 2:
            file_path = parts[-1]
            if file_path.endswith(".py") and Path(file_path).exists():
                files.append(file_path)

    return files


def check_syntax(file_path):
    """Check Python file for syntax errors."""
    result = subprocess.run(["python", "-m", "py_compile", file_path], capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def check_imports(file_path):
    """Check if file imports work."""
    if file_path.startswith("alembic/"):
        # Skip alembic migrations - they're not meant to be imported
        return True, ""

    if file_path.startswith("scripts/"):
        # Skip scripts - they may have dependencies we don't want to run
        return True, ""

    if file_path.startswith("tests/"):
        # Skip tests for now
        return True, ""

    # Try to import the module
    module_path = file_path.replace("/", ".").replace(".py", "")
    if module_path.startswith("app."):
        try:
            result = subprocess.run(
                ["python", "-c", f"from {module_path} import *"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Import timeout"
        except Exception as e:
            return False, str(e)

    return True, ""


def main():
    """Check all modified files."""
    files = get_modified_files()

    print(f"Checking {len(files)} modified Python files...\n")

    syntax_errors = []
    import_errors = []

    for file_path in files:
        print(f"Checking: {file_path}")

        # Check syntax
        syntax_ok, syntax_err = check_syntax(file_path)
        if not syntax_ok:
            syntax_errors.append((file_path, syntax_err))
            print("  ❌ SYNTAX ERROR")
            continue

        print("  ✅ Syntax OK")

        # Check imports
        import_ok, import_err = check_imports(file_path)
        if not import_ok:
            import_errors.append((file_path, import_err))
            print(f"  ⚠️  Import warning: {import_err[:100]}")
        else:
            print("  ✅ Imports OK")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    if syntax_errors:
        print(f"\n❌ SYNTAX ERRORS ({len(syntax_errors)}):")
        for file_path, error in syntax_errors:
            print(f"  {file_path}")
            print(f"    {error[:200]}")

    if import_errors:
        print(f"\n⚠️  IMPORT WARNINGS ({len(import_errors)}):")
        for file_path, error in import_errors:
            print(f"  {file_path}")
            print(f"    {error[:200]}")

    if not syntax_errors and not import_errors:
        print("\n✅ All files checked successfully!")
        return 0

    return 1 if syntax_errors else 0


if __name__ == "__main__":
    sys.exit(main())
