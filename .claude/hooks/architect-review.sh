#!/bin/bash
# Architect Review Hook — blocks git commit until @egidio review is done
# Runs on: PreToolUse (Bash)
#
# Uses a marker file keyed on the MD5 of staged changes.
# After @egidio review, Claude creates the marker; retry succeeds.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only intercept git commit commands
if [[ ! "$COMMAND" =~ git[[:space:]]+commit ]]; then
    exit 0
fi

# Allow --amend (already reviewed at original commit)
if [[ "$COMMAND" =~ --amend ]]; then
    exit 0
fi

# Compute hash of staged changes
STAGED_HASH=$(git diff --cached 2>/dev/null | md5 -q 2>/dev/null || git diff --cached 2>/dev/null | md5sum 2>/dev/null | cut -d' ' -f1)

if [[ -z "$STAGED_HASH" ]]; then
    # Nothing staged — let git itself report the error
    exit 0
fi

MARKER_DIR="/tmp/claude"
MARKER_FILE="${MARKER_DIR}/architect-review-${STAGED_HASH}"

# If review marker exists for this exact set of changes, allow commit
if [[ -f "$MARKER_FILE" ]]; then
    exit 0
fi

# Collect context for the block message
STAGED_FILES=$(git diff --cached --name-only 2>/dev/null)
STAGED_COUNT=$(echo "$STAGED_FILES" | wc -l | tr -d ' ')
BRANCH=$(git branch --show-current 2>/dev/null)

echo "BLOCKED: @egidio architecture review required before commit." >&2
echo "" >&2
echo "Branch: $BRANCH" >&2
echo "Staged files ($STAGED_COUNT):" >&2
echo "$STAGED_FILES" | head -20 >&2
echo "" >&2
echo "To proceed:" >&2
echo "  1. Invoke @egidio to review the staged diff (git diff --cached)" >&2
echo "  2. Run: mkdir -p $MARKER_DIR && touch $MARKER_FILE" >&2
echo "  3. Re-run the git commit command" >&2
exit 2
