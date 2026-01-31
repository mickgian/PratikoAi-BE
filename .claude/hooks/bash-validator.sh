#!/bin/bash
# Bash Validator Hook - Blocks dangerous commands
# Runs on: PreToolUse (Bash)

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Exit early if no command
if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Dangerous command patterns to block
BLOCKED_PATTERNS=(
    "rm -rf /"
    "rm -rf /*"
    "rm -rf ~"
    "DROP DATABASE"
    "DROP TABLE"
    "> /dev/sda"
    "mkfs"
    "dd if=/dev"
    ":(){ :|:& };:"
    "chmod -R 777 /"
    "git push.*--force.*main"
    "git push.*--force.*master"
    "git reset --hard origin/main"
    "git reset --hard origin/master"
    "git clean -fdx /"
)

COMMAND_LOWER=$(echo "$COMMAND" | tr '[:upper:]' '[:lower:]')

for pattern in "${BLOCKED_PATTERNS[@]}"; do
    PATTERN_LOWER=$(echo "$pattern" | tr '[:upper:]' '[:lower:]')
    if echo "$COMMAND_LOWER" | grep -q "$PATTERN_LOWER"; then
        echo "BLOCKED: Dangerous command detected" >&2
        echo "Command: $COMMAND" >&2
        echo "Pattern matched: '$pattern'" >&2
        exit 2
    fi
done

exit 0
