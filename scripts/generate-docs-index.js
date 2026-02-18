#!/usr/bin/env node
/**
 * Automated Documentation Index Generator for PratikoAI Frontend
 *
 * Scans all markdown files in the repository and generates hierarchical
 * documentation indexes for easy navigation.
 *
 * Usage:
 *     node scripts/generate-docs-index.js
 *     npm run docs:generate
 *
 * Generates:
 *     - DOCUMENTATION_INDEX.md (root master index)
 *     - docs/INDEX.md (docs directory index)
 */

const fs = require('fs');
const path = require('path');

class DocumentationIndexer {
  constructor(rootDir) {
    this.rootDir = rootDir;
    this.allDocs = [];
    this.docsByDirectory = new Map();
  }

  /**
   * Scan all markdown files in repository
   */
  scanDocuments() {
    const excludePatterns = ['node_modules', '.next', '.git', 'dist', 'build'];

    console.log(`📂 Scanning ${this.rootDir} for markdown files...`);

    this.scanDirectory(this.rootDir, excludePatterns);

    console.log(`✅ Found ${this.allDocs.length} markdown files`);
    console.log(`📁 Across ${this.docsByDirectory.size} directories\n`);
  }

  scanDirectory(dir, excludePatterns) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);

      // Skip excluded directories
      if (excludePatterns.some(pattern => fullPath.includes(pattern))) {
        continue;
      }

      if (entry.isDirectory()) {
        this.scanDirectory(fullPath, excludePatterns);
      } else if (entry.isFile() && entry.name.endsWith('.md')) {
        const doc = this.parseMarkdownFile(fullPath);
        this.allDocs.push(doc);

        // Group by directory
        const parentDir = path.relative(this.rootDir, path.dirname(fullPath));
        if (!this.docsByDirectory.has(parentDir)) {
          this.docsByDirectory.set(parentDir, []);
        }
        this.docsByDirectory.get(parentDir).push(doc);
      }
    }
  }

  parseMarkdownFile(filePath) {
    const content = fs.readFileSync(filePath, 'utf-8');
    const stats = fs.statSync(filePath);
    const relativePath = path.relative(this.rootDir, filePath);

    return {
      path: filePath,
      relativePath,
      title: this.extractTitle(content, path.basename(filePath)),
      description: this.extractDescription(content),
      status: this.extractStatus(content),
      lastModified: stats.mtime,
      category: this.categorizeFile(relativePath),
    };
  }

  extractTitle(content, filename) {
    const lines = content.split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('# ')) {
        return trimmed.substring(2).trim();
      }
    }
    // Fallback to filename
    return filename.replace('.md', '').replace(/[-_]/g, ' ');
  }

  extractDescription(content) {
    const lines = content.split('\n');
    let foundTitle = false;
    let description = [];

    for (const line of lines) {
      const trimmed = line.trim();

      // Skip until we find the title
      if (trimmed.startsWith('# ')) {
        foundTitle = true;
        continue;
      }

      if (!foundTitle) continue;

      // Skip empty lines
      if (!trimmed) {
        if (description.length > 0) break;
        continue;
      }

      // Skip other headings, horizontal rules, blockquotes
      if (
        trimmed.startsWith('#') ||
        trimmed.startsWith('---') ||
        trimmed.startsWith('***') ||
        trimmed.startsWith('>')
      ) {
        if (description.length > 0) break;
        continue;
      }

      // Collect description
      description.push(trimmed);

      // Limit to first 150 characters
      if (description.join(' ').length > 150) {
        break;
      }
    }

    const fullDesc = description.join(' ');
    return fullDesc.length > 150
      ? fullDesc.substring(0, 147) + '...'
      : fullDesc;
  }

  extractStatus(content) {
    const lowerContent = content.toLowerCase();

    if (
      lowerContent.includes('✅') ||
      lowerContent.includes('production ready') ||
      lowerContent.includes('complete') ||
      lowerContent.includes('implemented')
    ) {
      return '✅ Current';
    }
    if (
      lowerContent.includes('📚 historical') ||
      lowerContent.includes('deprecated') ||
      lowerContent.includes('obsolete') ||
      lowerContent.includes('summary')
    ) {
      return '📚 Historical';
    }
    if (
      lowerContent.includes('🚧') ||
      lowerContent.includes('wip') ||
      lowerContent.includes('work in progress') ||
      lowerContent.includes('draft')
    ) {
      return '🚧 WIP';
    }
    if (
      lowerContent.includes('⚠️') ||
      lowerContent.includes('warning') ||
      lowerContent.includes('caution')
    ) {
      return '⚠️ Deprecated';
    }

    return '✅ Current';
  }

  categorizeFile(relativePath) {
    if (relativePath.includes('getting-started')) return 'getting-started';
    if (relativePath.includes('development')) return 'development';
    if (relativePath.includes('troubleshooting')) return 'troubleshooting';
    if (relativePath.includes('meta')) return 'meta';
    return 'root';
  }

  /**
   * Generate root DOCUMENTATION_INDEX.md
   */
  generateRootIndex() {
    console.log('📝 Generating DOCUMENTATION_INDEX.md...');

    const gettingStartedDocs =
      this.docsByDirectory.get('docs/getting-started') || [];
    const developmentDocs = this.docsByDirectory.get('docs/development') || [];
    const troubleshootingDocs =
      this.docsByDirectory.get('docs/troubleshooting') || [];
    const metaDocs = this.docsByDirectory.get('docs/meta') || [];

    return `# Master Documentation Index

**Auto-generated:** ${new Date().toISOString().split('T')[0]} ${new Date().toTimeString().slice(0, 5)}
**Total Documents:** ${this.allDocs.length} markdown files

> 💡 This index is automatically generated. To update, run: \`npm run docs:generate\`

---

## 🚀 Quick Start (New Users)

**Start here if you're new to the project:**

1. **[README](README.md)** - Project overview and setup
2. **[Backend Integration Guide](docs/getting-started/BACKEND_INTEGRATION_GUIDE.md)** - Connect to PratikoAI backend
3. **[Testing Guide](docs/getting-started/TESTING.md)** - Run tests and understand test structure
4. **[Chat Requirements](docs/development/CHAT_REQUIREMENTS.md)** - Complete chat system specification

---

## 📚 By Audience

### 👨‍💻 Frontend Developers
- **Getting Started:** [docs/getting-started/](docs/getting-started/)
- **Development Guides:** [docs/development/](docs/development/)
- **Chat System:** [Chat Requirements](docs/development/CHAT_REQUIREMENTS.md)
- **Testing:** [Testing Guide](docs/getting-started/TESTING.md)

### 🎨 UI/UX Designers
- **Design System:** [Design System Guide](docs/development/DESIGN_SYSTEM.md)
- **Figma Setup:** [Figma Integration](docs/development/FIGMA_SETUP.md)
- **Component Matching:** [Figma Matching Guide](docs/development/FIGMA_MATCHING_GUIDE.md)

### 🏗️ DevOps / SRE
- **Deployment:** [Deployment Guide](docs/getting-started/DEPLOYMENT.md)
- **Backend Integration:** [Integration Guide](docs/getting-started/BACKEND_INTEGRATION_GUIDE.md)

### 🧪 QA / Testing
- **Testing:** [Testing Guide](docs/getting-started/TESTING.md)
- **Troubleshooting:** [docs/troubleshooting/](docs/troubleshooting/)

---

## 🗂️ Documentation by Category

### Getting Started (${gettingStartedDocs.length} docs)
${gettingStartedDocs
  .map(
    doc => `- **[${doc.title}](${doc.relativePath})** ${doc.status}
  ${doc.description ? `  - ${doc.description}` : ''}`
  )
  .join('\n')}

### Development Guides (${developmentDocs.length} docs)
${developmentDocs
  .map(
    doc => `- **[${doc.title}](${doc.relativePath})** ${doc.status}
  ${doc.description ? `  - ${doc.description}` : ''}`
  )
  .join('\n')}

### Troubleshooting (${troubleshootingDocs.length} docs)
${troubleshootingDocs
  .map(
    doc => `- **[${doc.title}](${doc.relativePath})** ${doc.status}
  ${doc.description ? `  - ${doc.description}` : ''}`
  )
  .join('\n')}

### Meta Documentation (${metaDocs.length} docs)
${metaDocs
  .map(
    doc => `- **[${doc.title}](${doc.relativePath})** ${doc.status}
  ${doc.description ? `  - ${doc.description}` : ''}`
  )
  .join('\n')}

---

## 🔍 Quick Find

**Common Documentation Needs:**

- **How do I set up the project?** → [README](README.md)
- **How do I connect to the backend?** → [Backend Integration Guide](docs/getting-started/BACKEND_INTEGRATION_GUIDE.md)
- **How does the chat system work?** → [Chat Requirements](docs/development/CHAT_REQUIREMENTS.md)
- **How do I run tests?** → [Testing Guide](docs/getting-started/TESTING.md)
- **How do I deploy?** → [Deployment Guide](docs/getting-started/DEPLOYMENT.md)
- **What's the design system?** → [Design System Guide](docs/development/DESIGN_SYSTEM.md)
- **How do I use Figma?** → [Figma Setup](docs/development/FIGMA_SETUP.md)

---

## 🛠️ Maintenance

This index is **automatically generated** from all markdown files in the repository.

**To regenerate:**
\`\`\`bash
npm run docs:generate
\`\`\`

**Pre-commit hook:**
The index is automatically regenerated on commit if markdown files change.

---

## 📊 Documentation Statistics

- **Total Documents:** ${this.allDocs.length}
- **Getting Started:** ${gettingStartedDocs.length}
- **Development Guides:** ${developmentDocs.length}
- **Troubleshooting:** ${troubleshootingDocs.length}
- **Meta/Historical:** ${metaDocs.length}

---

**Last Updated:** ${new Date().toISOString().split('T')[0]} ${new Date().toTimeString().slice(0, 5)}
**Generator:** \`scripts/generate-docs-index.js\`
`;
  }

  /**
   * Generate docs/INDEX.md
   */
  generateDocsIndex() {
    console.log('📝 Generating docs/INDEX.md...');

    const gettingStartedDocs =
      this.docsByDirectory.get('docs/getting-started') || [];
    const developmentDocs = this.docsByDirectory.get('docs/development') || [];
    const troubleshootingDocs =
      this.docsByDirectory.get('docs/troubleshooting') || [];
    const metaDocs = this.docsByDirectory.get('docs/meta') || [];

    return `# Documentation Directory Index

**Auto-generated:** ${new Date().toISOString().split('T')[0]} ${new Date().toTimeString().slice(0, 5)}

> 💡 This directory contains all technical documentation for the PratikoAI frontend application.

---

## 📁 Directory Structure

\`\`\`
docs/
├── getting-started/    # Setup, deployment, and integration guides
├── development/        # Development guides, specs, and design system
├── troubleshooting/    # Debugging and problem-solving guides
└── meta/              # Summaries, verifications, and historical docs
\`\`\`

---

## 🚀 Getting Started (${gettingStartedDocs.length} docs)

Essential guides for setting up and deploying the application:

${gettingStartedDocs
  .map(
    doc => `- **[${doc.title}](getting-started/${path.basename(doc.relativePath)})** ${doc.status}
  ${doc.description ? `  - ${doc.description}` : ''}`
  )
  .join('\n')}

---

## 💻 Development Guides (${developmentDocs.length} docs)

Comprehensive development documentation and specifications:

${developmentDocs
  .map(
    doc => `- **[${doc.title}](development/${path.basename(doc.relativePath)})** ${doc.status}
  ${doc.description ? `  - ${doc.description}` : ''}`
  )
  .join('\n')}

---

## 🔧 Troubleshooting (${troubleshootingDocs.length} docs)

Debugging guides and issue resolution:

${troubleshootingDocs
  .map(
    doc => `- **[${doc.title}](troubleshooting/${path.basename(doc.relativePath)})** ${doc.status}
  ${doc.description ? `  - ${doc.description}` : ''}`
  )
  .join('\n')}

---

## 📚 Meta Documentation (${metaDocs.length} docs)

Implementation summaries, verifications, and historical documentation:

${metaDocs
  .map(
    doc => `- **[${doc.title}](meta/${path.basename(doc.relativePath)})** ${doc.status}
  ${doc.description ? `  - ${doc.description}` : ''}`
  )
  .join('\n')}

---

## 📊 Statistics

- **Getting Started Guides:** ${gettingStartedDocs.length}
- **Development Docs:** ${developmentDocs.length}
- **Troubleshooting Guides:** ${troubleshootingDocs.length}
- **Meta/Historical Docs:** ${metaDocs.length}
- **Total:** ${gettingStartedDocs.length + developmentDocs.length + troubleshootingDocs.length + metaDocs.length}

---

**Last Updated:** ${new Date().toISOString().split('T')[0]} ${new Date().toTimeString().slice(0, 5)}
`;
  }

  /**
   * Write all indexes to files
   */
  writeIndexes() {
    console.log('------------------------------------------------------------');
    console.log('Generating indexes...');
    console.log(
      '------------------------------------------------------------\n'
    );

    const indexes = {
      [path.join(this.rootDir, 'DOCUMENTATION_INDEX.md')]:
        this.generateRootIndex(),
      [path.join(this.rootDir, 'docs', 'INDEX.md')]: this.generateDocsIndex(),
    };

    for (const [filePath, content] of Object.entries(indexes)) {
      const dir = path.dirname(filePath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      fs.writeFileSync(filePath, content, 'utf-8');
      console.log(`✅ Generated: ${path.relative(this.rootDir, filePath)}`);
    }

    console.log('\n' + '='.repeat(60));
    console.log('✅ ALL DOCUMENTATION INDEXES GENERATED');
    console.log('='.repeat(60));
    console.log(
      `\nTotal files created/updated: ${Object.keys(indexes).length}`
    );
    console.log('\nNext steps:');
    console.log('1. Review generated indexes');
    console.log('2. Run: git add DOCUMENTATION_INDEX.md docs/INDEX.md');
    console.log('3. Commit changes');
  }
}

function main() {
  console.log('='.repeat(60));
  console.log('📚 AUTOMATED DOCUMENTATION INDEX GENERATION');
  console.log('='.repeat(60));
  console.log();

  const rootDir = path.resolve(__dirname, '..');
  const indexer = new DocumentationIndexer(rootDir);

  indexer.scanDocuments();
  indexer.writeIndexes();
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = { DocumentationIndexer };
