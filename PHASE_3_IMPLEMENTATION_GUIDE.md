# Phase 3: Chat History Storage Migration - Implementation Guide

## Overview

**Status:** ✅ COMPLETE
**Date:** 2025-11-29
**Branch:** `DEV-FE-005-chat-history-migration`

Phase 3 integrates the hybrid storage system (PostgreSQL + IndexedDB) into the chat pages with migration banner support.

---

## What Was Implemented

### 1. New Components & Hooks

#### **`useChatSessionsV2` Hook** (`src/app/chat/hooks/useChatSessionsV2.ts`)

- Extends `useChatSessions` with hybrid storage capabilities
- Exposes `migrationNeeded`, `migrateToBackend`, and `storageError`
- Combines session management with storage migration detection

**Usage:**

```typescript
import { useChatSessionsV2 } from '@/app/chat/hooks/useChatSessionsV2';

function ChatComponent() {
  const {
    currentSession,
    migrationNeeded,
    migrateToBackend,
    storageError
  } = useChatSessionsV2();

  if (migrationNeeded) {
    return <MigrationBanner onSync={migrateToBackend} />;
  }

  return <ChatMessages />;
}
```

#### **`ChatLayoutV2` Component** (`src/app/chat/components/ChatLayoutV2.tsx`)

- Enhanced `ChatLayout` with migration banner support
- Displays `MigrationBanner` when IndexedDB migration needed
- Handles migration completion and data refresh

**Features:**

- Migration banner (fixed position, above content)
- Hybrid storage integration
- Automatic data refresh after migration
- Backward compatible with existing layout

#### **`page-v2.tsx`** (`src/app/chat/page-v2.tsx`)

- V2 version of chat page using `ChatLayoutV2`
- Drop-in replacement for original `page.tsx`
- No breaking changes to existing functionality

---

## Migration Path

### Option 1: Gradual Migration (Recommended)

Keep both versions and switch gradually:

```typescript
// src/app/chat/page.tsx
import { ChatLayout } from './components/ChatLayout';        // Original
import { ChatLayoutV2 } from './components/ChatLayoutV2';    // New with migration

export default function ChatPage() {
  // Use feature flag to switch
  const useV2 = process.env.NEXT_PUBLIC_USE_HYBRID_STORAGE === 'true';

  return (
    <ChatStateProvider>
      <ChatSessionsProvider>
        {useV2 ? <ChatLayoutV2 /> : <ChatLayout />}
      </ChatSessionsProvider>
    </ChatStateProvider>
  );
}
```

### Option 2: Direct Replacement

Replace original with V2:

```bash
# Backup original
cp src/app/chat/page.tsx src/app/chat/page.original.tsx
cp src/app/chat/components/ChatLayout.tsx src/app/chat/components/ChatLayout.original.tsx

# Use V2
cp src/app/chat/page-v2.tsx src/app/chat/page.tsx
```

---

## Testing

### Test Coverage

**Total Coverage:** 71.97% (exceeds 69.5% threshold)

**New Tests Added:**

1. `useChatSessionsV2.test.ts` - 7 tests (unit tests for hook)
2. `useChatSessionsIntegration.test.ts` - 4 tests (integration tests)
3. `ChatLayoutV2.test.tsx` - 7 tests (component tests)

**Total New Tests:** 18 tests

### Run Tests

```bash
# Run all V2 tests
npm test -- --testNamePattern="V2|useChatStorageV2|MigrationBanner"

# Run full test suite
npm test

# Run with coverage
npm test -- --coverage
```

---

## How It Works

### Architecture Flow

```
User Opens Chat
      ↓
useChatSessionsV2 Hook
      ↓
┌─────────────────────┐
│  useChatSessions    │ (Session management)
│  + useChatStorageV2 │ (Hybrid storage)
└─────────────────────┘
      ↓
  Check Migration Needed?
      ↓
  ┌────────┴────────┐
  YES              NO
  ↓                ↓
Show Migration   Display Chat
  Banner          Messages
  ↓
User Clicks "Sync Now"
  ↓
migrateToBackend()
  ↓
Import IndexedDB → PostgreSQL
  ↓
Reload Messages
  ↓
Hide Banner
```

### Data Priority

1. **Primary Source:** PostgreSQL (backend API)
2. **Fallback:** IndexedDB (offline cache)
3. **Migration:** IndexedDB → PostgreSQL (user-triggered)

---

## User Experience

### Scenario 1: New User

- No IndexedDB data
- Loads messages from PostgreSQL
- No migration banner shown

### Scenario 2: Existing User with IndexedDB Data

1. Chat opens, loads from PostgreSQL
2. Hook detects IndexedDB has more messages
3. Migration banner appears at top
4. User clicks "Sync Now"
5. IndexedDB messages imported to backend
6. Data refreshes from PostgreSQL
7. Banner auto-hides after 3 seconds

### Scenario 3: Offline User

1. Backend unavailable (network error)
2. Hook falls back to IndexedDB
3. Messages displayed from local storage
4. Error message: "Backend unavailable: [error]"
5. Migration banner shown (to sync when online)

---

## API Reference

### `useChatSessionsV2`

```typescript
interface UseChatSessionsV2Return {
  // All original useChatSessions properties
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  loadSessions: () => Promise<void>;
  // ... etc

  // New properties
  migrationNeeded: boolean; // Whether migration needed
  migrateToBackend: () => Promise<void>; // Trigger migration
  storageError: string | null; // Storage error (if any)
}
```

### `ChatLayoutV2`

```typescript
function ChatLayoutV2(): JSX.Element;
```

**Props:** None (uses context providers)

**Context Required:**

- `ChatStateProvider`
- `ChatSessionsProvider`

---

## Configuration

### Environment Variables

```bash
# .env.local
NEXT_PUBLIC_USE_HYBRID_STORAGE=true  # Enable hybrid storage
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000  # Backend API
```

### Feature Flags

To enable V2 in production, use a feature flag service or environment variable.

---

## Rollback Plan

If issues occur, rollback is simple:

```typescript
// src/app/chat/page.tsx
import { ChatLayout } from './components/ChatLayout';  // Original

export default function ChatPage() {
  return (
    <ChatStateProvider>
      <ChatSessionsProvider>
        <ChatLayout />  {/* Use original */}
      </ChatSessionsProvider>
    </ChatStateProvider>
  );
}
```

---

## Performance Considerations

### Backend Load

- Migration is user-triggered (not automatic)
- Only migrates when user clicks "Sync Now"
- Batched import via `POST /api/v1/chatbot/history/import`

### Frontend Performance

- IndexedDB read: ~10-50ms
- PostgreSQL fetch: ~100-300ms (network dependent)
- Migration: ~500ms-2s (depends on message count)

### Caching

- PostgreSQL messages cached in IndexedDB
- Future loads read from IndexedDB first
- Backend sync on demand

---

## Monitoring & Metrics

### Key Metrics to Track

1. **Migration Adoption Rate**
   - % of users who trigger migration
   - Average messages migrated per user

2. **Error Rates**
   - Backend connection failures
   - Migration failures
   - IndexedDB access errors

3. **Performance**
   - Backend response time
   - Migration completion time
   - IndexedDB read/write time

### Logging

```typescript
// Migration events are logged:
console.log('Migration complete: imported X, skipped Y');
console.error('Migration failed:', error);
```

---

## Future Enhancements

### Phase 4 (Potential)

- Automatic background migration (no user action)
- Conflict resolution (IndexedDB vs PostgreSQL)
- Multi-device sync notifications
- Progressive Web App (PWA) offline support

---

## Files Changed

### New Files

- `src/app/chat/hooks/useChatSessionsV2.ts`
- `src/app/chat/components/ChatLayoutV2.tsx`
- `src/app/chat/page-v2.tsx`
- `src/app/chat/hooks/__tests__/useChatSessionsV2.test.ts`
- `src/app/chat/hooks/__tests__/useChatSessionsIntegration.test.ts`
- `src/app/chat/components/__tests__/ChatLayoutV2.test.tsx`

### Modified Files

- None (V2 approach preserves original files)

---

## Support & Troubleshooting

### Common Issues

**Issue:** Migration banner doesn't appear

- **Cause:** No IndexedDB data or already migrated
- **Solution:** Expected behavior

**Issue:** "Backend unavailable" error

- **Cause:** API server down or network issue
- **Solution:** Check backend server status, retry when online

**Issue:** Migration fails

- **Cause:** Invalid data format or backend error
- **Solution:** Check console logs, verify backend API health

---

## Contact

For questions or issues, contact the frontend development team.

---

**Phase 3 Complete** ✅
