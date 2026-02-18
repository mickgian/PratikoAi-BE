# Figma Code Connect Setup Guide

## 📋 Prerequisites

- Node.js 18+ installed
- Figma account with access to your PratikoAI project
- Admin access to your Figma team/organization

---

## 🚀 Installation Commands

### 1. Install Figma Code Connect globally

```bash
npm install -g @figma/code-connect
```

### 2. Install project dependencies

```bash
cd pratiko-ai-webapp
npm install @figma/code-connect @figma/rest-api-spec
```

### 3. Install optional development dependencies

```bash
npm install -D @types/figma @figma/plugin-typings
```

---

## 🔑 Figma Access Token Setup

### Step 1: Generate Personal Access Token

1. **Go to Figma Settings**
   - Open Figma in your browser
   - Click your profile picture (top right)
   - Select "Settings"

2. **Navigate to Personal Access Tokens**
   - Scroll down to "Personal access tokens"
   - Click "Create new token"

3. **Configure Token Permissions**

   ```
   Token Name: PratikoAI Code Connect

   Required Scopes:
   ✅ File content (read)
   ✅ Library analytics (read)
   ✅ Webhooks (write) - optional for real-time sync

   Expiration: Set to your preference (90 days recommended)
   ```

4. **Copy the Token**
   - **IMPORTANT**: Copy immediately - you won't see it again!
   - Store securely in your password manager

### Step 2: Find Your Figma File ID

From your Figma URL:

```
https://www.figma.com/make/zH5cQQ19Zq59XtffCzW4sB/PratikoAI-Landing-Page
                        ^^^^^^^^^^^^^^^^^^^^^^^^^
                        This is your File ID
```

**Your File ID**: `zH5cQQ19Zq59XtffCzW4sB`

---

## ⚙️ Environment Configuration

### 1. Create your environment file

```bash
cp .env.template .env.local
```

### 2. Fill in your credentials

```bash
# Edit .env.local with your actual values
FIGMA_ACCESS_TOKEN=figd_your_actual_token_here
FIGMA_FILE_ID=zH5cQQ19Zq59XtffCzW4sB
```

---

## 🔧 Project Configuration

### 1. Update package.json scripts

Add these scripts to your `package.json`:

```json
{
  "scripts": {
    "figma:connect": "figma connect",
    "figma:publish": "figma connect publish",
    "figma:dev": "figma connect dev",
    "figma:sync": "figma connect sync",
    "figma:validate": "figma connect validate"
  }
}
```

### 2. Update tsconfig.json

Add path mapping for better imports:

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"],
      "@/components/*": ["./src/components/*"],
      "@/ui/*": ["./src/components/ui/*"]
    }
  }
}
```

---

## 🏃‍♂️ Getting Started

### 1. Initialize Code Connect

```bash
npm run figma:connect init
```

### 2. Validate configuration

```bash
npm run figma:validate
```

### 3. Start development server

```bash
npm run figma:dev
```

### 4. Sync components with Figma

```bash
npm run figma:sync
```

---

## 📁 Project Structure After Setup

```
pratiko-ai-webapp/
├── .env.local                 # Your credentials (DO NOT COMMIT)
├── .env.template             # Template for team members
├── figma.config.json         # Figma Code Connect configuration
├── tokens.json               # Design tokens
├── FIGMA_SETUP.md           # This setup guide
├── .figma/                   # Generated Figma artifacts
│   ├── components/
│   └── tokens/
├── src/
│   ├── types/
│   │   └── figma.d.ts       # Generated TypeScript types
│   └── components/
└── docs/
    └── components/           # Auto-generated component docs
```

---

## 🔒 Security Best Practices

### 1. Environment Variables

- ✅ Use `.env.local` for local development
- ✅ Use `.env.template` for team sharing
- ❌ **NEVER** commit `.env.local` to version control

### 2. Token Management

- 🔄 Rotate tokens every 90 days
- 🔐 Store in secure password manager
- 👥 Use team tokens for production environments

### 3. Git Configuration

Add to your `.gitignore`:

```
# Figma credentials
.env.local
.figma-cache/

# Generated files (optional - team preference)
.figma/
src/types/figma.d.ts
```

---

## 🚨 Troubleshooting

### Common Issues

1. **"Invalid token" error**

   ```bash
   # Verify token in environment
   echo $FIGMA_ACCESS_TOKEN

   # Test token manually
   curl -H "X-Figma-Token: $FIGMA_ACCESS_TOKEN" https://api.figma.com/v1/me
   ```

2. **"File not found" error**
   - Verify file ID in URL
   - Check file permissions (must be readable by token owner)
   - Ensure file isn't in private team

3. **MCP Integration Issues**

   ```bash
   # Check if MCP server is running
   claude mcp list

   # Restart MCP with updated config
   claude mcp restart "Framelink-Figma-MCP"
   ```

### Getting Help

- 📖 [Figma Code Connect Docs](https://www.figma.com/developers/code-connect)
- 🎯 [API Reference](https://www.figma.com/developers/api)
- 💬 [Community Forum](https://forum.figma.com/c/developers-api)

---

## ✅ Verification Checklist

- [ ] Figma Code Connect installed globally
- [ ] Personal access token generated
- [ ] `.env.local` configured with credentials
- [ ] `figma.config.json` points to correct file ID
- [ ] MCP integration configured (if using Claude)
- [ ] `npm run figma:validate` passes
- [ ] Can connect to Figma API successfully

---

**🎉 You're ready to use Figma Code Connect with your PratikoAI project!**
