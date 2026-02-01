#!/bin/bash
# GitHub Issue Context Hook
# Runs on: UserPromptSubmit (web only)
# Purpose: Detect GitHub issue references and inject context

# ============================================================
# WEB-ONLY CHECK
# ============================================================
if [ "$CLAUDE_CODE_REMOTE" != "true" ]; then
    exit 0
fi

# ============================================================
# CONFIGURATION
# ============================================================
REPOS=("mickgian/PratikoAi-BE" "mickgian/PratikoAIWebApp" "mickgian/PratikoAI-KMP")
DEFAULT_REPO="mickgian/PratikoAi-BE"

# ============================================================
# READ USER PROMPT
# ============================================================
if [ -t 0 ]; then
    exit 0
fi

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)

if [ -z "$PROMPT" ]; then
    exit 0
fi

# ============================================================
# DETECT GITHUB ISSUE REFERENCES
# ============================================================
ISSUE_NUM=""
REPO=""

# Pattern 1: Full GitHub URL - github.com/owner/repo/issues/123
if [[ "$PROMPT" =~ github\.com/([^/]+/[^/]+)/issues/([0-9]+) ]]; then
    REPO="${BASH_REMATCH[1]}"
    ISSUE_NUM="${BASH_REMATCH[2]}"

# Pattern 2: Repo#number - PratikoAi-BE#123 or PratikoAIWebApp#456
elif [[ "$PROMPT" =~ (PratikoAi-BE|PratikoAIWebApp|PratikoAI-KMP)#([0-9]+) ]]; then
    REPO_NAME="${BASH_REMATCH[1]}"
    ISSUE_NUM="${BASH_REMATCH[2]}"
    REPO="mickgian/$REPO_NAME"

# Pattern 3: Simple #123 or GH-123
elif [[ "$PROMPT" =~ (^|[[:space:]])(GH-|#)([0-9]+)([[:space:]]|$) ]]; then
    ISSUE_NUM="${BASH_REMATCH[3]}"
    REPO="$DEFAULT_REPO"
fi

# No issue detected
if [ -z "$ISSUE_NUM" ]; then
    exit 0
fi

# ============================================================
# FETCH ISSUE DETAILS
# ============================================================
ISSUE_DATA=$(gh issue view "$ISSUE_NUM" --repo "$REPO" --json title,body,labels,state 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$ISSUE_DATA" ]; then
    echo "Could not fetch issue #$ISSUE_NUM from $REPO" >&2
    exit 0
fi

TITLE=$(echo "$ISSUE_DATA" | jq -r '.title // "N/A"')
BODY=$(echo "$ISSUE_DATA" | jq -r '.body // "No description"')
STATE=$(echo "$ISSUE_DATA" | jq -r '.state // "unknown"')
LABELS=$(echo "$ISSUE_DATA" | jq -r '.labels[]?.name // empty' 2>/dev/null | tr '\n' ', ' | sed 's/, $//')

# ============================================================
# CHECK BRANCH STATUS
# ============================================================
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
HAS_CHANGES=$(git status --porcelain 2>/dev/null | head -1)

# Generate suggested branch name
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]' '-' | sed 's/^-//;s/-$//' | cut -c1-40)
SUGGESTED_BRANCH="feature/${ISSUE_NUM}-${SLUG}"

# ============================================================
# OUTPUT CONTEXT FOR CLAUDE
# ============================================================
cat << EOF

## GitHub Issue Detected: #${ISSUE_NUM}

**Repository:** $REPO
**Title:** $TITLE
**State:** $STATE
**Labels:** ${LABELS:-None}

### Description:
$BODY

---

### Branch Recommendation
EOF

if [ -n "$HAS_CHANGES" ]; then
    echo "You have uncommitted changes. Please commit or stash them first."
fi

if [ "$CURRENT_BRANCH" != "develop" ]; then
    echo "NOTE: You are on '$CURRENT_BRANCH', not 'develop'."
fi

cat << EOF

**Suggested workflow:**
1. \`git checkout develop && git pull\`
2. \`git checkout -b $SUGGESTED_BRANCH\`
3. Implement following the issue description above
4. Follow TDD (ADR-013): Write tests FIRST

---
EOF
