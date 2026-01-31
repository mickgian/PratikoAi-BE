#!/bin/bash
# TDD Check Hook - Warns when editing app/ without tests
# Runs on: PreToolUse (Edit|Write)

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Exit early if no file path
if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# Only check app/ Python files (not tests, not __init__.py)
if [[ "$FILE_PATH" != *"/app/"* ]]; then
    exit 0
fi

if [[ "$FILE_PATH" == *"__init__.py" ]]; then
    exit 0
fi

if [[ "$FILE_PATH" != *.py ]]; then
    exit 0
fi

# Convert app path to expected test path
# app/services/foo.py -> tests/services/test_foo.py
TEST_PATH=$(echo "$FILE_PATH" | sed 's|/app/|/tests/|' | sed 's|/\([^/]*\)\.py$|/test_\1.py|')

# Check if test file exists
if [[ ! -f "$TEST_PATH" ]]; then
    # Output as additional context (warning, not blocking)
    cat << EOF
{
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": "TDD REMINDER (ADR-013): No test file at $TEST_PATH\\n\\nBest practice: Write failing tests FIRST, then implement.\\nConsider creating: $TEST_PATH"
    }
}
EOF
fi

exit 0
