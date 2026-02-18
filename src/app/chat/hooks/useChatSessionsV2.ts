/**
 * @file Chat Sessions Hook V2 (Hybrid Storage Integration)
 * @description Integrates useChatSessions with useChatStorageV2 for hybrid storage
 * Wraps existing session management with PostgreSQL + IndexedDB fallback
 */

'use client';

import { useMemo } from 'react';
import { useChatSessions } from './useChatSessions';
import { useChatStorageV2 } from './useChatStorageV2';

/**
 * Extended hook interface with migration support
 */
export interface UseChatSessionsV2Return
  extends ReturnType<typeof useChatSessions> {
  /** Whether migration from IndexedDB to backend is needed */
  migrationNeeded: boolean;
  /** Trigger migration to backend */
  migrateToBackend: () => Promise<void>;
  /** Storage error (if backend unavailable, using IndexedDB fallback) */
  storageError: string | null;
}

/**
 * Chat Sessions Hook V2 with Hybrid Storage
 *
 * Integrates existing session management (useChatSessions) with hybrid storage (useChatStorageV2).
 * Provides migration detection and backend sync capabilities.
 *
 * **Architecture:**
 * - useChatSessions handles session list and backend API calls
 * - useChatStorageV2 provides hybrid storage (PostgreSQL + IndexedDB fallback)
 * - This hook combines both for seamless integration
 *
 * @example
 * ```tsx
 * function ChatComponent() {
 *   const {
 *     currentSession,
 *     loadSessionHistory,
 *     migrationNeeded,
 *     migrateToBackend
 *   } = useChatSessionsV2();
 *
 *   if (migrationNeeded) {
 *     return <MigrationBanner onSync={migrateToBackend} />;
 *   }
 *
 *   return <ChatMessages />;
 * }
 * ```
 */
export function useChatSessionsV2(): UseChatSessionsV2Return {
  // Get existing session management
  const sessionsHook = useChatSessions();

  // Get hybrid storage for current session
  const sessionId = sessionsHook.currentSession?.id || '';
  const storageHook = useChatStorageV2(sessionId);

  // Combine into extended interface
  const combined = useMemo(
    () => ({
      ...sessionsHook,
      migrationNeeded: storageHook.migrationNeeded,
      migrateToBackend: storageHook.migrateToBackend,
      storageError: storageHook.error,
    }),
    [sessionsHook, storageHook]
  );

  return combined;
}
