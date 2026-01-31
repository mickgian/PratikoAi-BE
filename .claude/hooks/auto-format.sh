#!/bin/bash
# Auto Format Hook - Formats code after edits
# Runs on: PostToolUse (Edit|Write)

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Exit early if no file path
if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# Check if file exists
if [[ ! -f "$FILE_PATH" ]]; then
    exit 0
fi

# Python files - use ruff
if [[ "$FILE_PATH" == *.py ]]; then
    if command -v ruff &> /dev/null; then
        ruff format "$FILE_PATH" 2>/dev/null
        ruff check --fix "$FILE_PATH" 2>/dev/null
        echo "Formatted: $FILE_PATH (ruff)" >&2
    fi
fi

# TypeScript/JavaScript files - use prettier
if [[ "$FILE_PATH" == *.ts || "$FILE_PATH" == *.tsx || "$FILE_PATH" == *.js || "$FILE_PATH" == *.jsx ]]; then
    if command -v npx &> /dev/null; then
        npx prettier --write "$FILE_PATH" 2>/dev/null
        echo "Formatted: $FILE_PATH (prettier)" >&2
    fi
fi

exit 0
