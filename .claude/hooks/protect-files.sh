#!/bin/bash
# Protect Files Hook - Blocks edits to sensitive files
# Runs on: PreToolUse (Edit|Write)

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Exit early if no file path
if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# Protected file patterns
PROTECTED_PATTERNS=(
    ".env"
    ".env.local"
    ".env.production"
    "alembic/versions/"
    ".git/"
    "package-lock.json"
    "uv.lock"
    "poetry.lock"
)

for pattern in "${PROTECTED_PATTERNS[@]}"; do
    if [[ "$FILE_PATH" == *"$pattern"* ]]; then
        echo "BLOCKED: Cannot edit protected file: $FILE_PATH" >&2
        echo "Pattern matched: '$pattern'" >&2
        echo "" >&2
        echo "Protected files should be edited manually for safety." >&2
        exit 2
    fi
done

exit 0
