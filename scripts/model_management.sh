#!/bin/bash
# =============================================================================
# PratikoAI Model Management Script
# =============================================================================
# Manage HuggingFace Hub models for intent classification.
#
# Usage:
#   ./scripts/model_management.sh list                   # List model versions
#   ./scripts/model_management.sh current                # Show current model
#   ./scripts/model_management.sh promote <model-id>     # Set model for production
# =============================================================================

set -euo pipefail

HF_ORG="${HF_ORG:-pratikoai}"
HF_REPO_PREFIX="${HF_REPO_PREFIX:-intent-classifier}"

usage() {
    echo "PratikoAI Model Management"
    echo ""
    echo "Usage: $0 <command> [args]"
    echo ""
    echo "Commands:"
    echo "  list                    List available model versions on HF Hub"
    echo "  current                 Show the current model configured"
    echo "  promote <model-id>     Update docker-compose.production.yml with model"
    echo "  push <local-path> <version>  Push local model to HF Hub"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 promote ${HF_ORG}/${HF_REPO_PREFIX}-v1.2"
    echo "  $0 push ./models/intent-classifier v1.3"
}

cmd_list() {
    echo "Available models on HuggingFace Hub (org: $HF_ORG):"
    echo ""

    if ! command -v huggingface-cli &> /dev/null; then
        echo "huggingface-cli not found. Install with: pip install huggingface_hub"
        echo ""
        echo "Manual check: https://huggingface.co/${HF_ORG}"
        exit 1
    fi

    huggingface-cli repo list --organization "$HF_ORG" 2>/dev/null | grep "$HF_REPO_PREFIX" || echo "No models found with prefix '$HF_REPO_PREFIX'"
}

cmd_current() {
    echo "Current model configuration:"
    echo ""

    # Check docker-compose files
    for f in docker-compose.yml docker-compose.qa.yml docker-compose.production.yml; do
        if [ -f "$f" ]; then
            MODEL=$(grep -oP 'HF_INTENT_MODEL[=:]\s*\K[^\s}]+' "$f" 2>/dev/null || echo "not set")
            echo "  $f: $MODEL"
        fi
    done

    # Check env var
    echo "  ENV HF_INTENT_MODEL: ${HF_INTENT_MODEL:-not set}"
}

cmd_promote() {
    local model_id="${1:?Usage: $0 promote <model-id>}"
    local target_file="docker-compose.production.yml"

    echo "Promoting model to production: $model_id"
    echo "File: $target_file"
    echo ""

    if [ ! -f "$target_file" ]; then
        echo "ERROR: $target_file not found."
        exit 1
    fi

    # Update the HF_INTENT_MODEL in the production compose file
    sed -i.bak "s|HF_INTENT_MODEL:-[^}]*|HF_INTENT_MODEL:-${model_id}|g" "$target_file"
    rm -f "${target_file}.bak"

    echo "Updated $target_file with HF_INTENT_MODEL=$model_id"
    echo ""
    echo "Next steps:"
    echo "  1. Commit the change"
    echo "  2. Merge to master to trigger production deployment"
    echo "  3. The model will be downloaded during Docker image build"
}

cmd_push() {
    local local_path="${1:?Usage: $0 push <local-path> <version>}"
    local version="${2:?Usage: $0 push <local-path> <version>}"
    local repo_name="${HF_ORG}/${HF_REPO_PREFIX}-v${version}"

    echo "Pushing model to HuggingFace Hub:"
    echo "  Local path: $local_path"
    echo "  HF repo:    $repo_name"
    echo ""

    if ! command -v huggingface-cli &> /dev/null; then
        echo "huggingface-cli not found. Install with: pip install huggingface_hub"
        exit 1
    fi

    huggingface-cli upload "$repo_name" "$local_path" --private
    echo ""
    echo "Model pushed to: https://huggingface.co/${repo_name}"
    echo ""
    echo "To use in QA:  export HF_INTENT_MODEL=${repo_name}"
    echo "To promote:    $0 promote ${repo_name}"
}

# --- Main ---
case "${1:-help}" in
    list)    cmd_list ;;
    current) cmd_current ;;
    promote) cmd_promote "${2:-}" ;;
    push)    cmd_push "${2:-}" "${3:-}" ;;
    help|*)  usage ;;
esac
