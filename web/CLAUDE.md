# CLAUDE.md - PratikoAI Frontend Code Guidelines

This file provides guidelines for Claude Code when working on the PratikoAI frontend codebase.

---

## CRITICAL RULES (Never Violate)

1. **NO TODOs or incomplete code** - Always complete implementations. No "will implement later" patterns.
2. **Use @mario for requirements** - When task affects 3+ files, API changes, or unclear requirements
3. **Use @egidio for architecture** - For any architectural decision. Has veto power.
4. **Context API ONLY** - NO Redux/Zustand (ADR-008)
5. **Radix UI ONLY** - NO Material-UI (ADR-009)
6. **TDD mandatory** - Write tests FIRST, then implement (ADR-013)
7. **Italian for ALL user-facing text** - All UI text, buttons, labels, error messages must be in Italian
8. **Pre-commit hooks must pass** - ESLint, Prettier, Jest

---

## Project Paths

| Project      | Path                                            |
| ------------ | ----------------------------------------------- |
| **Frontend** | `/Users/micky/WebstormProjects/PratikoAiWebApp` |
| **Backend**  | `/Users/micky/PycharmProjects/PratikoAi-BE`     |

---

## Technology Stack

| Technology   | Version | Notes                 |
| ------------ | ------- | --------------------- |
| Next.js      | 15.5.7  | App Router, Turbopack |
| React        | 19.1.0  | Server Components     |
| TypeScript   | 5.x     | Strict mode           |
| Tailwind CSS | 4.x     | With shadcn/ui        |
| Radix UI     | Latest  | Headless primitives   |
| Jest         | 30.x    | Unit testing          |
| Playwright   | 1.55.x  | E2E testing           |

---

## Subagent Quick Reference

| Agent         | When to Use                                                    | Tools                               |
| ------------- | -------------------------------------------------------------- | ----------------------------------- |
| **@mario**    | 3+ files, API changes, unclear requirements                    | Read, Grep, Glob, AskUserQuestion   |
| **@egidio**   | Architecture decisions, ADRs, veto situations (HAS VETO POWER) | Read, Grep, Glob, WebFetch          |
| **@livia**    | Frontend implementation (Next.js, React, Tailwind)             | Read, Write, Edit, Bash, Grep, Glob |
| **@ezio**     | Backend API changes needed                                     | Read, Write, Edit, Bash, Grep, Glob |
| **@clelia**   | Test generation, coverage improvement                          | Read, Write, Edit, Bash, Grep, Glob |
| **@severino** | Security audits, GDPR compliance                               | Read, Bash, Grep, Glob, WebFetch    |
| **@valerio**  | Performance optimization                                       | Read, Bash, Grep, Glob, WebFetch    |
| **@tiziano**  | Debugging, error investigation                                 | Read, Write, Edit, Bash, Grep, Glob |

### Development Workflow

```
User Request
    |
    v
@mario (Requirements + Impact Analysis)
    |
    v
@egidio (Architecture Review - Can VETO)
    |
    v
@livia (Frontend Implementation with TDD)
    |
    v
@clelia (Test Validation)
```

---

## Project Structure

```
src/
├── app/                    # Next.js App Router pages (<100 lines each)
│   ├── page.tsx           # Home/landing page
│   ├── layout.tsx         # Root layout with providers
│   ├── providers.tsx      # Context providers wrapper
│   ├── globals.css        # Global Tailwind/CSS
│   ├── chat/              # Chat feature (most complex)
│   │   ├── page.tsx
│   │   ├── components/    # Chat-specific components
│   │   ├── hooks/         # Chat-specific hooks
│   │   ├── utils/         # Chat utilities
│   │   └── types/         # Chat types
│   └── [other routes]/    # Auth, FAQ, policies, etc.
├── components/            # Reusable components
│   ├── ui/               # shadcn/ui components (Radix-based)
│   └── [feature]/        # Feature-specific components
├── contexts/             # Context API providers (<100 lines each)
│   └── AuthContext.tsx   # Authentication state
├── hooks/                # Global custom hooks (<50 lines each)
├── lib/                  # Utility functions and API clients
│   ├── api.ts           # Main API client (singleton)
│   ├── api/             # API sub-clients
│   └── hooks/           # Utility hooks
├── types/               # TypeScript type definitions
├── utils/               # Pure utility functions
└── middleware.ts        # Next.js middleware
```

---

## Code Size Guidelines

| Component         | Max Lines | Guidance                     |
| ----------------- | --------- | ---------------------------- |
| Page files        | 100       | Delegate to components       |
| React components  | 150       | Extract sub-components       |
| Custom hooks      | 50        | Single concern               |
| API clients       | 100       | One resource per file        |
| Context providers | 100       | useReducer for complex state |

---

## Common Commands

```bash
# Development
npm run dev                    # Start dev server (Turbopack)
npm run build                  # Production build
npm run start                  # Start production server

# Testing
npm run test                   # Run Jest tests
npm run test:watch            # Watch mode
npm run test:coverage         # With coverage report
npm run test:e2e              # Playwright E2E tests
npm run test:e2e:ui           # Interactive E2E test UI

# Code Quality
npm run lint                   # ESLint
npm run type-check            # TypeScript check

# Documentation
npm run docs:generate          # Regenerate docs index
```

---

## Testing Requirements

### Coverage Thresholds

| Metric     | Threshold |
| ---------- | --------- |
| Branches   | ≥58%      |
| Functions  | ≥70%      |
| Lines      | ≥69.5%    |
| Statements | ≥70%      |

### Test Conventions

- Co-located: `Component.tsx` + `Component.test.tsx`
- Or: `__tests__/` directory at same level
- Minimum 3 tests per feature: happy path + error + edge case

### Test Pattern

```typescript
describe('ComponentName', () => {
  it('should render correctly', () => {
    render(<Component />);
    expect(screen.getByText('text')).toBeInTheDocument();
  });

  it('should handle user interaction', async () => {
    const user = userEvent.setup();
    render(<Component />);
    await user.click(screen.getByRole('button'));
    expect(mock).toHaveBeenCalled();
  });
});
```

---

## ADR Quick Reference

### Frontend Architecture (ADR-007 to ADR-009)

| ADR     | Decision              | Key Rule                            |
| ------- | --------------------- | ----------------------------------- |
| **007** | Next.js 15 App Router | NOT Pages Router, Turbopack enabled |
| **008** | Context API           | NO Redux/Zustand                    |
| **009** | Radix UI              | NO Material-UI, headless + Tailwind |

### Quality & Testing

| ADR     | Decision                   | Key Rule                            |
| ------- | -------------------------- | ----------------------------------- |
| **013** | TDD mandatory              | RED-GREEN-REFACTOR for all features |
| **015** | Chat history in PostgreSQL | Server-side storage via API         |

**Full ADRs:** Backend repo `docs/architecture/decisions/`

---

## Common Patterns

### React Component

```tsx
// src/components/features/Example.tsx - <150 lines
'use client';

interface ExampleProps {
  title: string;
  onAction: () => void;
}

export function Example({ title, onAction }: ExampleProps) {
  return (
    <div>
      <ExampleHeader title={title} />
      <ExampleContent />
      <ExampleActions onAction={onAction} />
    </div>
  );
}
```

### Custom Hook

```tsx
// src/lib/hooks/useExample.ts - <50 lines
import { useState, useCallback } from 'react';
import { apiClient } from '@/lib/api';

export function useExample() {
  const [data, setData] = useState<ExampleData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await apiClient.getExample();
      setData(result);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { data, isLoading, fetch };
}
```

### Context Provider

```tsx
// src/contexts/ExampleContext.tsx - <100 lines
'use client';

import { createContext, useContext, useReducer, ReactNode } from 'react';

interface State {
  /* ... */
}
type Action = { type: 'SET_DATA'; payload: Data };

const ExampleContext = createContext<ContextValue | undefined>(undefined);

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_DATA':
      return { ...state, data: action.payload };
    default:
      return state;
  }
}

export function ExampleProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <ExampleContext.Provider value={{ state, dispatch }}>
      {children}
    </ExampleContext.Provider>
  );
}

export function useExample() {
  const context = useContext(ExampleContext);
  if (!context)
    throw new Error('useExample must be used within ExampleProvider');
  return context;
}
```

### API Client Usage

```tsx
// Using the singleton apiClient
import { apiClient } from '@/lib/api';

// Auth
await apiClient.login(email, password);
await apiClient.logout();

// Sessions
await apiClient.createSession();
await apiClient.getUserSessions();

// Chat (streaming)
await apiClient.sendChatMessageStreaming(messages, onChunk, onDone, onError);
```

---

## Styling with Tailwind

### cn() Helper

```tsx
import { cn } from '@/lib/utils';

// Merge classes with proper specificity
<div
  className={cn(
    'base-class px-4 py-2',
    condition && 'conditional-class',
    className
  )}
/>;
```

### Design Tokens

```css
/* Primary colors */
--primary: #256cdb;      /* Professional blue */
--success: #06ac2e;      /* Trust green */

/* Use via Tailwind */
bg-primary text-primary-foreground
```

---

## Italian Language Requirement

**ALL user-facing text MUST be in Italian:**

```tsx
// ✅ CORRECT
<Button>Accedi</Button>
<p>Errore durante il caricamento</p>
<label>Indirizzo email</label>

// ❌ WRONG
<Button>Sign In</Button>
<p>Error loading data</p>
<label>Email address</label>
```

---

## When to Extract

- Component >150 lines → Extract sub-components
- Logic >20 lines in JSX → Extract to hook or utility
- Repeated logic → Create custom hook
- Multiple contexts using same pattern → Create factory

---

## Edge Cases to Address

1. **Loading states:** Show skeletons/spinners during data fetch
2. **Error states:** Display Italian error messages with retry options
3. **Empty states:** Handle no-data scenarios gracefully
4. **Offline:** Graceful degradation when network unavailable
5. **Mobile:** Responsive design, touch-friendly interactions
6. **Accessibility:** Proper ARIA labels, keyboard navigation

---

## API Integration

### Backend API URL

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL; // Default: http://localhost:8000
```

### Token Management

- Access token + Refresh token in localStorage
- Session token (separate) for chat operations
- Auto-refresh on 401 with retry
- Header: `Authorization: Bearer {token}`

### Streaming (SSE)

```typescript
// Chat uses Server-Sent Events, NOT WebSocket
await apiClient.sendChatMessageStreaming(
  messages,
  frame => {
    /* onChunk */
  },
  finalFrame => {
    /* onDone */
  },
  error => {
    /* onError */
  }
);
```

---

## References

- **Backend CLAUDE.md:** `/Users/micky/PycharmProjects/PratikoAi-BE/CLAUDE.md`
- **ADRs:** Backend repo `docs/architecture/decisions/`
- **Chat requirements:** `docs/development/CHAT_REQUIREMENTS.md`
- **Design system:** `docs/development/DESIGN_SYSTEM.md`
- **Testing guide:** `docs/getting-started/TESTING.md`
