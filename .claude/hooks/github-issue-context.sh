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
INPUT=$(cat)
USER_PROMPT=$(echo "$INPUT" | jq -r '.prompt // .message // .content // empty' 2>/dev/null)

if [[ -z "$USER_PROMPT" ]]; then
    exit 0
fi

# ============================================================
# DETECT GITHUB ISSUE REFERENCES
# ============================================================

# Pattern 1: Full GitHub URL (github.com/owner/repo/issues/123)
GITHUB_URL_MATCH=$(echo "$USER_PROMPT" | grep -oE 'github\.com/[^/]+/[^/]+/issues/[0-9]+' | head -1)

# Pattern 2: Repo#123 format (PratikoAi-BE#123)
REPO_ISSUE_MATCH=$(echo "$USER_PROMPT" | grep -oE '(PratikoAi-BE|PratikoAIWebApp|PratikoAI-KMP)#[0-9]+' | head -1)

# Pattern 3: Simple #123 or GH-123 format
SIMPLE_ISSUE_MATCH=$(echo "$USER_PROMPT" | grep -oE '(#|GH-|gh-)[0-9]+' | head -1)

# ============================================================
# DETERMINE REPO AND ISSUE NUMBER
# ============================================================
REPO=""
ISSUE_NUM=""

if [[ -n "$GITHUB_URL_MATCH" ]]; then
    # Extract from full URL: github.com/owner/repo/issues/123
    REPO=$(echo "$GITHUB_URL_MATCH" | sed 's|github\.com/||' | sed 's|/issues/.*||')
    ISSUE_NUM=$(echo "$GITHUB_URL_MATCH" | grep -oE '[0-9]+$')
elif [[ -n "$REPO_ISSUE_MATCH" ]]; then
    # Extract from Repo#123 format
    REPO_NAME=$(echo "$REPO_ISSUE_MATCH" | sed 's/#.*//')
    ISSUE_NUM=$(echo "$REPO_ISSUE_MATCH" | grep -oE '[0-9]+')
    REPO="mickgian/$REPO_NAME"
elif [[ -n "$SIMPLE_ISSUE_MATCH" ]]; then
    # Simple #123 - use default repo based on current directory
    ISSUE_NUM=$(echo "$SIMPLE_ISSUE_MATCH" | grep -oE '[0-9]+')

    # Detect repo from current directory
    CURRENT_DIR=$(basename "$(pwd)")
    case "$CURRENT_DIR" in
        *PratikoAi-BE*) REPO="mickgian/PratikoAi-BE" ;;
        *PratikoAIWebApp*) REPO="mickgian/PratikoAIWebApp" ;;
        *PratikoAI-KMP*) REPO="mickgian/PratikoAI-KMP" ;;
        *) REPO="$DEFAULT_REPO" ;;
    esac
fi

# Exit if no issue found
if [[ -z "$ISSUE_NUM" ]] || [[ -z "$REPO" ]]; then
    exit 0
fi

# ============================================================
# FETCH ISSUE DETAILS
# ============================================================
ISSUE_DATA=$(gh issue view "$ISSUE_NUM" --repo "$REPO" --json title,body,labels,state,assignees 2>/dev/null)

if [[ -z "$ISSUE_DATA" ]] || [[ "$ISSUE_DATA" == "null" ]]; then
    echo "⚠️ Could not fetch issue #$ISSUE_NUM from $REPO" >&2
    exit 0
fi

ISSUE_TITLE=$(echo "$ISSUE_DATA" | jq -r '.title // "No title"')
ISSUE_BODY=$(echo "$ISSUE_DATA" | jq -r '.body // "No description"')
ISSUE_STATE=$(echo "$ISSUE_DATA" | jq -r '.state // "unknown"')
ISSUE_LABELS=$(echo "$ISSUE_DATA" | jq -r '.labels[]?.name // empty' | tr '\n' ', ' | sed 's/,$//')

# ============================================================
# CHECK BRANCH STATUS
# ============================================================
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
HAS_CHANGES=$(git status --porcelain 2>/dev/null | head -1)
DEVELOP_EXISTS=$(git branch -a 2>/dev/null | grep -E '(^|\s)develop$|origin/develop' | head -1)

BRANCH_WARNING=""
if [[ -n "$HAS_CHANGES" ]]; then
    BRANCH_WARNING="⚠️ WARNING: You have uncommitted changes!"
fi

if [[ "$CURRENT_BRANCH" != "develop" ]] && [[ -n "$DEVELOP_EXISTS" ]]; then
    BRANCH_WARNING="$BRANCH_WARNING
⚠️ NOTE: You are on '$CURRENT_BRANCH', not 'develop'."
fi

# Suggest branch name
SLUG=$(echo "$ISSUE_TITLE" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-' | cut -c1-40)
SUGGESTED_BRANCH="feature/${ISSUE_NUM}-${SLUG}"

# ============================================================
# OUTPUT CONTEXT FOR CLAUDE
# ============================================================
cat << EOF
{
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": "
## 📋 GitHub Issue Detected: #${ISSUE_NUM}

**Repository:** ${REPO}
**Title:** ${ISSUE_TITLE}
**State:** ${ISSUE_STATE}
**Labels:** ${ISSUE_LABELS:-None}

### Description
${ISSUE_BODY}

---

### 🌿 Branch Recommendation
${BRANCH_WARNING}

**Suggested workflow:**
1. Ensure you're on develop: \`git checkout develop && git pull\`
2. Create feature branch: \`git checkout -b ${SUGGESTED_BRANCH}\`
3. Implement following the issue description above
4. Follow TDD (ADR-013): Write tests FIRST

---

**IMPORTANT:** Follow the issue description above during implementation.
"
    }
}
EOF

exit 0
