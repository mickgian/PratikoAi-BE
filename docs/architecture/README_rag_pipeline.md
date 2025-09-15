# RAG Pipeline Documentation

The RAG (Retrieval-Augmented Generation) pipeline provides automated tools for auditing RAG implementation conformance and generating actionable backlog items.

## Quick Start

```bash
# Run audit to update conformance dashboard
python scripts/rag_pipeline.py

# Create GitHub issues from step docs
python scripts/rag_backlog.py --create-github

# Run full pipeline with issue creation
python scripts/rag_pipeline.py --create-issues
```

## Pipeline Components

### 1. RAG Audit (`scripts/rag_audit.py`)

Analyzes the codebase to match RAG blueprint steps with actual implementation:

- **Code Graph Analysis**: Scans Python files to build symbol and dependency graphs
- **Weighted Matching**: Uses configurable scoring to match steps to code symbols  
- **Auto-Audit**: Updates step documentation with implementation status and confidence scores
- **Conformance Dashboard**: Generates `docs/architecture/rag_conformance.md`

```bash
# Update all step docs with audit results
python scripts/rag_audit.py --write

# Verbose output with detailed matching info  
python scripts/rag_audit.py --write --verbose
```

### 2. GitHub Issue Creation (`scripts/rag_backlog.py`)

Creates GitHub issues directly from step documentation, using the conformance dashboard as the single source of truth.

- **GitHub Integration**: Creates issues with proper labels and assignees
- **Idempotent**: Skips existing issues and implemented steps
- **Smart Labeling**: Applies status, category, and step labels

```bash
# Create GitHub issues with assignee
python scripts/rag_backlog.py --create-github --assignee username

# Dry run to preview what would be created
python scripts/rag_backlog.py --dry-run

# Verbose output for debugging
python scripts/rag_backlog.py --create-github --verbose
```

### 3. Pipeline Coordinator (`scripts/rag_pipeline.py`)

Orchestrates the RAG audit and optional GitHub issue creation:

```bash
# Run audit only
python scripts/rag_pipeline.py

# Audit + create GitHub issues
python scripts/rag_pipeline.py --create-issues --assignee username

# Skip audit, only create issues
python scripts/rag_pipeline.py --skip-audit --create-issues
```

## File Structure

```
docs/
└── architecture/
    ├── steps/                      # Individual step documentation (single source of truth)
    │   ├── STEP-1-*.md             # Step 1 detailed docs
    │   ├── STEP-2-*.md             # Step 2 detailed docs
    │   └── ...
    ├── rag_conformance.md          # Generated conformance dashboard (backlog view)
    ├── rag_steps.yml               # Step registry and metadata
    └── rag_sprint_plan.md          # Implementation roadmap
```

## Status Indicators

- ✅ **Implemented**: Code exists and is wired correctly (confidence ≥ 0.75)
- 🟡 **Partial**: Some implementation exists but incomplete (confidence ≥ 0.55)  
- 🔌 **Not Wired**: Implementation exists but not connected to RAG flow (confidence ≥ 0.30)
- ❌ **Missing**: No implementation found (confidence < 0.30)

## GitHub Integration

When creating issues, the system:

- **Checks for duplicates**: Skips creating issues that already exist
- **Applies consistent labels**: `rag`, `step/{N}`, `area/{category}`, `status/{status}`
- **Includes actionable checklists**: TDD suggestions from audit system
- **Links to documentation**: Direct links to step docs as single source of truth

## Configuration

### Audit Configuration (`scripts/rag_audit_config.yml`)

Controls matching thresholds, scoring weights, and synonyms:

```yaml
thresholds:
  implemented: 0.75    # ✅ threshold
  partial: 0.55        # 🟡 threshold  
  not_wired: 0.30      # 🔌 threshold

scoring_weights:
  name_similarity: 0.45
  docstring_hints: 0.20
  path_hints: 0.20
  graph_proximity: 0.15

synonyms:
  cache: [redis, memory, store]
  validate: [check, verify, sanitize]
```

## Best Practices

1. **Keep step docs as single source of truth**: The `docs/architecture/steps/` files contain authoritative implementation details
2. **Use conformance dashboard for backlog view**: `docs/architecture/rag_conformance.md` provides the centralized status
3. **Regular audits**: Run audits after significant implementation changes
4. **GitHub integration**: Create issues for sprint planning and tracking
5. **Incremental updates**: The audit system preserves manual edits to step docs

## Troubleshooting

### Common Issues

**Audit timeout**: Large codebases may require increased timeout in audit configuration

**Missing GitHub CLI**: Install `gh` CLI tool for issue creation features

**Permission errors**: Ensure proper GitHub authentication for issue creation

**Low confidence scores**: Review `rag_audit_config.yml` synonyms and thresholds

### Debug Commands

```bash
# Verbose audit with detailed matching
python scripts/rag_audit.py --update --verbose

# Dry run backlog generation
python scripts/rag_backlog.py --dry-run

# Test code graph generation
python scripts/rag_code_graph_test.py
```

## Integration with Development Workflow

The pipeline integrates into standard development practices:

1. **PR Reviews**: Run audit to show implementation progress
2. **Sprint Planning**: Use backlog index for work prioritization  
3. **Issue Tracking**: Sync with GitHub for project management
4. **Documentation**: Auto-update conformance dashboard

Expected output from `python scripts/rag_pipeline.py --verbose`:
- `updated docs/architecture/rag_conformance.md`
- No backlog files created (conformance dashboard serves as the backlog view)