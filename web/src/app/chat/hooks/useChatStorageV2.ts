/**
 * @file Chat Storage Hook V2 (Hybrid Backend + IndexedDB)
 * @description Hybrid storage hook with PostgreSQL backend as primary source
 * and IndexedDB as offline fallback. Implements multi-device sync.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { getChatHistory, importChatHistory } from '@/lib/api/chat-history';
import { messageStorageService } from '../services/MessageStorageService';
import type { Message } from '../types/chat';
import {
  convertBackendToFrontend,
  convertFrontendToBackendImport,
} from './useChatStorageV2.utils';

/**
 * Hook return interface
 */
export interface UseChatStorageV2Return {
  /** Chat messages (from backend or IndexedDB fallback) */
  messages: Message[];
  /** Loading state */
  isLoading: boolean;
  /** Error message if any */
  error: string | null;
  /** Whether migration from IndexedDB to backend is needed */
  migrationNeeded: boolean;
  /** Trigger migration to backend */
  migrateToBackend: () => Promise<void>;
  /** Reload messages from backend */
  reload: () => Promise<void>;
}

/**
 * Hybrid chat storage hook with PostgreSQL backend + IndexedDB fallback
 *
 * **PRIMARY:** Backend PostgreSQL (source of truth, multi-device sync)
 * **FALLBACK:** IndexedDB (offline cache, graceful degradation)
 *
 * @param sessionId - Current session ID
 * @returns Chat storage interface with migration detection
 *
 * @example
 * ```tsx
 * function ChatComponent() {
 *   const { messages, isLoading, migrationNeeded, migrateToBackend } =
 *     useChatStorageV2('session-123');
 *
 *   if (migrationNeeded) {
 *     return <MigrationBanner onSync={migrateToBackend} />;
 *   }
 *
 *   return <ChatMessages messages={messages} />;
 * }
 * ```
 */
export function useChatStorageV2(sessionId: string): UseChatStorageV2Return {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [migrationNeeded, setMigrationNeeded] = useState(false);

  /**
   * Load messages from backend or IndexedDB fallback
   */
  const loadMessages = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // PRIMARY: Try backend PostgreSQL first
      const backendMessages = await getChatHistory(sessionId);

      // Convert backend format to frontend format
      const frontendMessages: Message[] = [];
      backendMessages.forEach(chatMsg => {
        frontendMessages.push(...convertBackendToFrontend(chatMsg));
      });

      setMessages(frontendMessages);

      // Check if migration needed
      try {
        const indexedDBMessages =
          await messageStorageService.loadSession(sessionId);

        // Migration needed if IndexedDB has more messages than backend
        const indexedDBPairCount = Math.floor(indexedDBMessages.length / 2);
        const backendPairCount = backendMessages.length;

        if (indexedDBPairCount > backendPairCount) {
          setMigrationNeeded(true);
        } else {
          setMigrationNeeded(false);
        }
      } catch (_indexedDBError) {
        // IndexedDB check failed, no migration needed
        setMigrationNeeded(false);
      }

      setIsLoading(false);
    } catch (backendError) {
      // FALLBACK: Backend failed, try IndexedDB
      console.warn(
        'Backend unavailable, falling back to IndexedDB:',
        backendError
      );
      setError(`Backend unavailable: ${(backendError as Error).message}`);

      try {
        const indexedDBMessages =
          await messageStorageService.loadSession(sessionId);
        setMessages(indexedDBMessages);
        setMigrationNeeded(indexedDBMessages.length > 0); // Has local data to migrate
      } catch (_indexedDBError) {
        console.error('IndexedDB also failed');
        setMessages([]);
      }

      setIsLoading(false);
    }
  }, [sessionId]);

  /**
   * Migrate IndexedDB messages to backend PostgreSQL
   */
  const migrateToBackend = useCallback(async () => {
    try {
      setError(null);

      // Load messages from IndexedDB
      const indexedDBMessages =
        await messageStorageService.loadSession(sessionId);

      if (indexedDBMessages.length === 0) {
        setMigrationNeeded(false);
        return;
      }

      // Convert to backend import format
      const importMessages = convertFrontendToBackendImport(
        indexedDBMessages,
        sessionId
      );

      if (importMessages.length === 0) {
        setMigrationNeeded(false);
        return;
      }

      // Import to backend
      const result = await importChatHistory(importMessages);

      console.log(
        `Migration complete: imported ${result.imported_count}, skipped ${result.skipped_count}`
      );

      // Reload from backend to get updated state
      await loadMessages();
    } catch (_migrationError) {
      console.error('Migration failed:', _migrationError);
      setError(`Migration failed: ${(_migrationError as Error).message}`);
      // Keep migrationNeeded=true so user can retry
    }
  }, [sessionId, loadMessages]);

  /**
   * Reload messages from backend
   */
  const reload = useCallback(async () => {
    await loadMessages();
  }, [loadMessages]);

  /**
   * Load messages on mount and when sessionId changes
   */
  useEffect(() => {
    loadMessages();
  }, [loadMessages]);

  return {
    messages,
    isLoading,
    error,
    migrationNeeded,
    migrateToBackend,
    reload,
  };
}
