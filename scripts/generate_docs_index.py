#!/usr/bin/env python3
"""
Automated Documentation Index Generator

Scans all markdown files in the repository and generates hierarchical
documentation indexes for easy navigation.

Usage:
    python scripts/generate_docs_index.py

Generates:
    - DOCUMENTATION_INDEX.md (root master index)
    - docs/INDEX.md (docs directory index)
    - docs/architecture/INDEX.md (architecture overview)
    - docs/architecture/steps/INDEX.md (RAG steps index)
    - monitoring/INDEX.md (monitoring docs index)
    - [other subsystem indexes]
"""

import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
)


class MarkdownFile:
    """Represents a markdown file with metadata."""

    def __init__(self, path: Path, root_dir: Path):
        self.path = path
        self.root_dir = root_dir
        self.relative_path = path.relative_to(root_dir)
        self.title = self._extract_title()
        self.description = self._extract_description()
        self.status = self._extract_status()
        self.last_modified = datetime.fromtimestamp(path.stat().st_mtime)

    def _extract_title(self) -> str:
        """Extract title from first # heading or filename."""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("# "):
                        return line[2:].strip()
                    # Skip YAML frontmatter
                    if line == "---":
                        continue
                    # If we hit content without finding title, use filename
                    if line and not line.startswith("#"):
                        break
        except Exception:
            pass
        # Fallback to filename
        return self.path.stem.replace("_", " ").replace("-", " ").title()

    def _extract_description(self) -> str:
        """Extract first paragraph or sentence as description."""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                in_frontmatter = False
                found_title = False
                description_lines = []

                for line in lines:
                    line = line.strip()

                    # Handle YAML frontmatter
                    if line == "---":
                        in_frontmatter = not in_frontmatter
                        continue
                    if in_frontmatter:
                        continue

                    # Skip title
                    if line.startswith("# "):
                        found_title = True
                        continue

                    # Skip empty lines until we find content
                    if not line:
                        if description_lines:
                            break
                        continue

                    # Skip other headings
                    if line.startswith("#"):
                        if description_lines:
                            break
                        continue

                    # Skip horizontal rules
                    if line.startswith("---") or line.startswith("***"):
                        continue

                    # Skip blockquotes for description
                    if line.startswith(">"):
                        continue

                    # Collect description
                    if found_title or not line.startswith("#"):
                        description_lines.append(line)
                        # Stop after first paragraph or sentence
                        if len(description_lines) >= 2 or len(line) > 100:
                            break

                if description_lines:
                    desc = " ".join(description_lines)
                    # Truncate if too long
                    if len(desc) > 150:
                        desc = desc[:147] + "..."
                    return desc
        except Exception:
            pass
        return ""

    def _extract_status(self) -> str:
        """Extract status indicator from document."""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                content = f.read(500)  # Check first 500 chars
                if "✅" in content or "Status:** ✅" in content or "COMPLETE" in content:
                    return "✅ Current"
                if "📚" in content or "Historical" in content:
                    return "📚 Historical"
                if "⚠️" in content or "Deprecated" in content:
                    return "⚠️ Deprecated"
                if "🚧" in content or "WIP" in content or "In Progress" in content:
                    return "🚧 WIP"
        except Exception:
            pass
        return "✅ Current"


class DocumentationIndexer:
    """Generates hierarchical documentation indexes."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.all_docs: List[MarkdownFile] = []
        self.docs_by_directory: Dict[str, List[MarkdownFile]] = defaultdict(list)

    def scan_documents(self, exclude_patterns: List[str] = None):
        """Scan all markdown files in repository."""
        if exclude_patterns is None:
            exclude_patterns = [
                "node_modules",
                ".venv",
                ".git",
                "__pycache__",
                ".pytest_cache",
                "build",
                "dist",
            ]

        print(f"📂 Scanning {self.root_dir} for markdown files...")

        for md_file in self.root_dir.rglob("*.md"):
            # Skip excluded directories
            if any(pattern in str(md_file) for pattern in exclude_patterns):
                continue

            doc = MarkdownFile(md_file, self.root_dir)
            self.all_docs.append(doc)

            # Group by directory
            parent_dir = str(md_file.parent.relative_to(self.root_dir))
            self.docs_by_directory[parent_dir].append(doc)

        print(f"✅ Found {len(self.all_docs)} markdown files")
        print(f"📁 Across {len(self.docs_by_directory)} directories")

    def generate_root_index(self) -> str:
        """Generate DOCUMENTATION_INDEX.md (master index)."""
        print("📝 Generating DOCUMENTATION_INDEX.md...")

        # Get docs from getting-started, operations, and meta directories
        getting_started_docs = self.docs_by_directory.get("docs/getting-started", [])
        operations_docs = self.docs_by_directory.get("docs/operations", [])
        meta_docs = self.docs_by_directory.get("docs/meta", [])

        # Sort each category
        getting_started_docs.sort(key=lambda x: x.title)
        operations_docs.sort(key=lambda x: x.title)
        meta_docs.sort(key=lambda x: x.title)

        # Count subsystems
        subsystems = {
            "docs/": len(self.docs_by_directory.get("docs", [])),
            "docs/architecture": len(self.docs_by_directory.get("docs/architecture", [])),
            "docs/architecture/steps": len(self.docs_by_directory.get("docs/architecture/steps", [])),
            "monitoring/": len([d for d in self.all_docs if "monitoring" in str(d.relative_path)]),
            "deployment-orchestration/": len(
                [d for d in self.all_docs if "deployment-orchestration" in str(d.relative_path)]
            ),
            "feature-flags/": len([d for d in self.all_docs if "feature-flags" in str(d.relative_path)]),
            "mcp-servers/": len([d for d in self.all_docs if "mcp-servers" in str(d.relative_path)]),
            "version-management/": len([d for d in self.all_docs if "version-management" in str(d.relative_path)]),
        }

        content = f"""# Master Documentation Index

**Auto-generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Documents:** {len(self.all_docs)} markdown files

> 💡 This index is automatically generated. To update, run: `python scripts/generate_docs_index.py`

---

## 🚀 Quick Start (New Users)

**Start here if you're new to the project:**

1. **[Hybrid RAG Implementation](docs/getting-started/HYBRID_RAG_IMPLEMENTATION.md)** - Core RAG system architecture
2. **[RAG Architecture Overview](docs/architecture/INDEX.md)** - Complete system design
3. **[SSE Streaming Guide](docs/getting-started/SSE_STREAMING_COMPLETE_GUIDE.md)** - Real-time streaming implementation
4. **[Testing Status](docs/getting-started/TESTING_IMPLEMENTATION_STATUS.md)** - Test coverage and guidelines

---

## 📚 By Audience

### 👨‍💻 Developers
- **Getting Started:** [Hybrid RAG Implementation](docs/getting-started/HYBRID_RAG_IMPLEMENTATION.md)
- **Architecture:** [docs/architecture/](docs/architecture/INDEX.md)
- **Streaming:** [SSE Streaming Guide](docs/getting-started/SSE_STREAMING_COMPLETE_GUIDE.md)
- **Testing:** [Testing Implementation Status](docs/getting-started/TESTING_IMPLEMENTATION_STATUS.md)
- **Feature Flags:** [feature-flags/](feature-flags/INDEX.md)

### 🏗️ DevOps / SRE
- **Deployment:** [deployment-orchestration/](deployment-orchestration/INDEX.md)
- **Monitoring:** [monitoring/](monitoring/INDEX.md)
- **Alerts:** [monitoring/ALERTS.md](monitoring/ALERTS.md)
- **Runbooks:** [monitoring/RUNBOOKS.md](monitoring/RUNBOOKS.md)
- **Rollback:** [rollback-system/](rollback-system/INDEX.md)

### 🏛️ Architects
- **System Design:** [docs/architecture/](docs/architecture/INDEX.md)
- **RAG Pipeline:** [docs/architecture/steps/](docs/architecture/steps/INDEX.md) ({subsystems['docs/architecture/steps']} steps)
- **Policy Gated Autonomy:** [docs/architecture/POLICY_GATED_AUTONOMY_INTEGRATION.md](docs/architecture/POLICY_GATED_AUTONOMY_INTEGRATION.md)

### 🧪 QA / Testing
- **Test Coverage:** [Testing Implementation Status](docs/getting-started/TESTING_IMPLEMENTATION_STATUS.md)
- **Test Documents:** [tests/test_documents/](tests/test_documents/INDEX.md)

---

## 🗂️ Documentation by Subsystem

| Subsystem | Documents | Primary Index |
|-----------|-----------|---------------|
| **RAG Architecture** | {subsystems['docs/architecture/steps']} steps | [docs/architecture/](docs/architecture/INDEX.md) |
| **Core Docs** | {subsystems['docs/']} docs | [docs/](docs/INDEX.md) |
| **Monitoring** | {subsystems['monitoring/']} docs | [monitoring/](monitoring/INDEX.md) |
| **Deployment** | {subsystems['deployment-orchestration/']} docs | [deployment-orchestration/](deployment-orchestration/INDEX.md) |
| **MCP Servers** | {subsystems['mcp-servers/']} docs | [mcp-servers/](mcp-servers/INDEX.md) |
| **Feature Flags** | {subsystems['feature-flags/']} docs | [feature-flags/](feature-flags/INDEX.md) |
| **Version Management** | {subsystems['version-management/']} docs | [version-management/](version-management/INDEX.md) |
| **Rollback System** | 3 docs | [rollback-system/](rollback-system/INDEX.md) |
| **Failure Recovery** | 1 doc | [failure-recovery-system/](failure-recovery-system/INDEX.md) |

---

## 📖 Documentation by Category

### Getting Started ({len(getting_started_docs)} docs)
"""
        for doc in getting_started_docs:
            content += f"- **[{doc.title}]({doc.relative_path})** {doc.status}\n"
            if doc.description:
                content += f"  - {doc.description}\n"

        if operations_docs:
            content += f"\n### Operations ({len(operations_docs)} docs)\n"
            for doc in operations_docs:
                content += f"- **[{doc.title}]({doc.relative_path})** {doc.status}\n"
                if doc.description:
                    content += f"  - {doc.description}\n"

        if meta_docs:
            content += f"\n### Meta Documentation ({len(meta_docs)} docs)\n"
            for doc in meta_docs:
                content += f"- **[{doc.title}]({doc.relative_path})** {doc.status}\n"
                if doc.description:
                    content += f"  - {doc.description}\n"

        content += """
---

## 🔍 Quick Find

**Common Documentation Needs:**

- **How does streaming work?** → [SSE Streaming Complete Guide](docs/getting-started/SSE_STREAMING_COMPLETE_GUIDE.md)
- **How to set up pgvector?** → [pgVector Setup Guide](docs/getting-started/PGVECTOR_SETUP_GUIDE.md)
- **What are the RAG steps?** → [docs/architecture/steps/](docs/architecture/steps/INDEX.md)
- **How to add tests?** → [Testing Implementation Status](docs/getting-started/TESTING_IMPLEMENTATION_STATUS.md)
- **How to deploy?** → [deployment-orchestration/](deployment-orchestration/INDEX.md)
- **How to monitor?** → [monitoring/](monitoring/INDEX.md)
- **Troubleshooting?** → Check subsystem's TROUBLESHOOTING.md

---

## 🛠️ Maintenance

This index is **automatically generated** from all markdown files in the repository.

**To regenerate:**
```bash
python scripts/generate_docs_index.py
```

**Pre-commit hook:**
The index is automatically regenerated on commit if markdown files change.

---

## 📊 Documentation Statistics

- **Total Documents:** {len(self.all_docs)}
- **Root Level:** {len(root_docs)}
- **Architecture Steps:** {subsystems['docs/architecture/steps']}
- **Subsystems with Docs:** {len([k for k, v in subsystems.items() if v > 0])}

---

**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Generator:** `scripts/generate_docs_index.py`
"""

        return content

    def generate_docs_readme(self) -> str:
        """Generate docs/INDEX.md."""
        print("📝 Generating docs/INDEX.md...")

        # Get docs in docs/ directory (not subdirectories)
        docs_files = self.docs_by_directory.get("docs", [])
        docs_files.sort(key=lambda x: x.title)

        # Get architecture docs
        arch_count = len([d for d in self.all_docs if "docs/architecture" in str(d.relative_path)])

        # Categorize
        feature_docs = [
            d
            for d in docs_files
            if any(
                term in d.title.lower() for term in ["faq", "gdpr", "atomic", "subscription", "encryption", "expert"]
            )
        ]
        db_docs = [
            d
            for d in docs_files
            if any(term in d.title.lower() for term in ["postgres", "vector", "search", "schema", "quality"])
        ]
        ops_docs = [d for d in docs_files if any(term in d.title.lower() for term in ["load", "retry", "testing"])]
        other_docs = [d for d in docs_files if d not in feature_docs + db_docs + ops_docs]

        content = f"""# Documentation Directory Index

**Auto-generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

> 💡 This directory contains {len(docs_files)} technical documentation files plus {arch_count} architecture documents.

---

## 🏗️ Architecture

**Complete system architecture and RAG pipeline documentation:**

- **[Architecture Overview](architecture/INDEX.md)** - Main architecture index
  - RAG flow implementation documents
  - Policy gated autonomy
  - {arch_count} total architecture documents including 135 detailed steps

---

## 🎯 Features & Capabilities

"""
        for doc in feature_docs:
            content += f"- **[{doc.title}]({doc.relative_path.name})** {doc.status}\n"
            if doc.description:
                content += f"  - {doc.description}\n"

        content += "\n## 🗄️ Database & Search\n\n"
        for doc in db_docs:
            content += f"- **[{doc.title}]({doc.relative_path.name})** {doc.status}\n"
            if doc.description:
                content += f"  - {doc.description}\n"

        content += "\n## ⚙️ Operations\n\n"
        for doc in ops_docs:
            content += f"- **[{doc.title}]({doc.relative_path.name})** {doc.status}\n"
            if doc.description:
                content += f"  - {doc.description}\n"

        if other_docs:
            content += "\n## 📚 Other\n\n"
            for doc in other_docs:
                content += f"- **[{doc.title}]({doc.relative_path.name})** {doc.status}\n"
                if doc.description:
                    content += f"  - {doc.description}\n"

        content += f"""
---

## 📊 Statistics

- **Feature Docs:** {len(feature_docs)}
- **Database/Search:** {len(db_docs)}
- **Operations:** {len(ops_docs)}
- **Architecture:** {arch_count}
- **Total:** {len(docs_files) + arch_count}

---

**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return content

    def generate_architecture_readme(self) -> str:
        """Generate docs/architecture/INDEX.md."""
        print("📝 Generating docs/architecture/INDEX.md...")

        arch_docs = [
            d
            for d in self.all_docs
            if "docs/architecture" in str(d.relative_path) and d.path.parent.name == "architecture"
        ]
        arch_docs.sort(key=lambda x: x.title)

        steps_count = len(self.docs_by_directory.get("docs/architecture/steps", []))

        # Categorize
        rag_flow_docs = [d for d in arch_docs if "RAG_FLOW" in d.path.name]
        policy_docs = [d for d in arch_docs if "POLICY" in d.path.name.upper()]
        other_docs = [d for d in arch_docs if d not in rag_flow_docs + policy_docs]

        content = f"""# RAG Architecture Documentation

**Auto-generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

> 💡 Complete documentation of the RAG (Retrieval-Augmented Generation) system architecture.

---

## 📚 Overview

This directory contains comprehensive documentation of the RAG system, including:
- High-level architecture documents
- Detailed implementation guides
- {steps_count} step-by-step pipeline documents
- Policy and conformance guidelines

---

## 🏗️ RAG Flow Implementation Series

"""
        rag_flow_docs.sort(key=lambda x: x.path.name)  # Sort by filename to get numerical order
        for doc in rag_flow_docs:
            content += f"- **[{doc.title}]({doc.relative_path.name})** {doc.status}\n"
            if doc.description:
                content += f"  - {doc.description}\n"

        if policy_docs:
            content += "\n## 🛡️ Policy & Governance\n\n"
            for doc in policy_docs:
                content += f"- **[{doc.title}]({doc.relative_path.name})** {doc.status}\n"
                if doc.description:
                    content += f"  - {doc.description}\n"

        if other_docs:
            content += "\n## 📋 Other Architecture Docs\n\n"
            for doc in other_docs:
                content += f"- **[{doc.title}]({doc.relative_path.name})** {doc.status}\n"
                if doc.description:
                    content += f"  - {doc.description}\n"

        content += f"""
---

## 🔢 Detailed Pipeline Steps

**Complete step-by-step documentation of the RAG pipeline:**

→ **[View all {steps_count} steps](steps/INDEX.md)**

The steps directory contains detailed documentation for every step in the RAG pipeline, from request validation to feedback collection.

---

## 📊 Statistics

- **Overview Docs:** {len(arch_docs)}
- **Detailed Steps:** {steps_count}
- **Total Architecture Docs:** {len(arch_docs) + steps_count}

---

**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return content

    def generate_steps_readme(self) -> str:
        """Generate docs/architecture/steps/INDEX.md."""
        print("📝 Generating docs/architecture/steps/INDEX.md...")

        steps = self.docs_by_directory.get("docs/architecture/steps", [])
        steps.sort(key=lambda x: x.path.name)

        # Group steps by phase (every 10 steps)
        phases = {
            "Initialization & Validation (1-10)": [],
            "Classification & Facts (11-20)": [],
            "Knowledge Retrieval (21-40)": [],
            "Prompting & Provider Selection (41-60)": [],
            "LLM Execution & Caching (61-80)": [],
            "Tool Execution & Document Processing (81-100)": [],
            "Response & Streaming (101-120)": [],
            "Feedback & Golden Set (121-135)": [],
        }

        for step in steps:
            # Extract step number from filename
            match = re.search(r"STEP-(\d+)", step.path.name)
            if match:
                step_num = int(match.group(1))
                if step_num <= 10:
                    phases["Initialization & Validation (1-10)"].append(step)
                elif step_num <= 20:
                    phases["Classification & Facts (11-20)"].append(step)
                elif step_num <= 40:
                    phases["Knowledge Retrieval (21-40)"].append(step)
                elif step_num <= 60:
                    phases["Prompting & Provider Selection (41-60)"].append(step)
                elif step_num <= 80:
                    phases["LLM Execution & Caching (61-80)"].append(step)
                elif step_num <= 100:
                    phases["Tool Execution & Document Processing (81-100)"].append(step)
                elif step_num <= 120:
                    phases["Response & Streaming (101-120)"].append(step)
                else:
                    phases["Feedback & Golden Set (121-135)"].append(step)

        content = f"""# RAG Pipeline Steps (1-135)

**Auto-generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Steps:** {len(steps)}

> 💡 This directory contains {len(steps)} detailed step documents describing the complete RAG pipeline from request to response.

---

## 📖 Overview

Each step document describes a specific operation in the RAG pipeline:
- **Purpose:** What the step does
- **Inputs:** What data it receives
- **Outputs:** What data it produces
- **Logic:** Decision points and flow control
- **Related Steps:** Dependencies and connections

---

## 🗺️ Steps by Phase

"""

        for phase_name, phase_steps in phases.items():
            if phase_steps:
                content += f"### {phase_name}\n\n"
                content += f"<details>\n<summary>View {len(phase_steps)} steps</summary>\n\n"
                for step in phase_steps:
                    # Extract step number and create short name
                    match = re.search(r"STEP-(\d+)-RAG\.(.+)\.md", step.path.name)
                    if match:
                        step_num = match.group(1)
                        step_path = match.group(2).replace(".", " → ")
                        content += f"- **[Step {step_num}]({step.path.name})** - {step_path}\n"
                content += "\n</details>\n\n"

        content += """
---

## 🔍 Quick Find

**Common Topics:**

- **Authentication:** Steps 1-5
- **Privacy/GDPR:** Steps 6-10
- **Classification:** Steps 11-42
- **Golden Set:** Steps 20-30, 127-131
- **Knowledge Retrieval:** Steps 39-40
- **LLM Providers:** Steps 48-73
- **Caching:** Steps 59-68
- **Tool Execution:** Steps 78-99
- **Streaming:** Steps 104-112
- **Feedback:** Steps 113-135
- **RSS Monitoring:** Step 132

---

## 📊 Statistics

"""
        for phase_name, phase_steps in phases.items():
            content += f"- **{phase_name}:** {len(phase_steps)} steps\n"

        content += f"""
- **Total:** {len(steps)} steps

---

**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return content

    def generate_all_indexes(self):
        """Generate all documentation indexes."""
        print("\n" + "=" * 60)
        print("📚 AUTOMATED DOCUMENTATION INDEX GENERATION")
        print("=" * 60 + "\n")

        # Scan all documents
        self.scan_documents()

        print("\n" + "-" * 60)
        print("Generating indexes...")
        print("-" * 60 + "\n")

        # Generate indexes
        indexes = {
            self.root_dir / "DOCUMENTATION_INDEX.md": self.generate_root_index(),
            self.root_dir / "docs" / "INDEX.md": self.generate_docs_readme(),
            self.root_dir / "docs" / "architecture" / "INDEX.md": self.generate_architecture_readme(),
            self.root_dir / "docs" / "architecture" / "steps" / "INDEX.md": self.generate_steps_readme(),
        }

        # Write all indexes
        for path, content in indexes.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Generated: {path.relative_to(self.root_dir)}")

        print("\n" + "=" * 60)
        print("✅ ALL DOCUMENTATION INDEXES GENERATED")
        print("=" * 60)
        print(f"\nTotal files created/updated: {len(indexes)}")
        print("\nNext steps:")
        print("1. Review generated indexes")
        print("2. Run: git add DOCUMENTATION_INDEX.md docs/INDEX.md docs/architecture/")
        print("3. Commit changes")


def main():
    """Main entry point."""
    # Find repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    # Generate indexes
    indexer = DocumentationIndexer(repo_root)
    indexer.generate_all_indexes()


if __name__ == "__main__":
    main()
