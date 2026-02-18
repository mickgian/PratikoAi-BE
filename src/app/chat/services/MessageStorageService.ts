'use client';

import type { Message, ChatState } from '../types/chat';

/**
 * IndexedDB-based message storage service
 * Implements CHAT_REQUIREMENTS.md Section 17.1 requirements:
 * - Auto-save after each message completion
 * - Format preservation for HTML content
 * - Character encoding support for Italian characters
 * - Large content support (up to 100KB per message)
 * - IndexedDB for message content (not localStorage)
 */

export interface SessionMetadata {
  sessionId: string;
  title: string;
  lastUpdated: string;
  messageCount: number;
  createdAt: string;
}

export interface StorageMetrics {
  totalSessions: number;
  totalMessages: number;
  storageUsed: number;
  lastCleanup: string;
}

class MessageStorageService {
  private dbName = 'PratikoAI_Messages';
  private dbVersion = 1;
  private db: IDBDatabase | null = null;
  private isInitialized = false;

  /**
   * Initialize IndexedDB connection
   */
  async initialize(): Promise<void> {
    if (this.isInitialized && this.db) return;

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onerror = () => {
        reject(
          new Error(`Failed to open IndexedDB: ${request.error?.message}`)
        );
      };

      request.onsuccess = () => {
        this.db = request.result;
        this.isInitialized = true;
        resolve();
      };

      request.onupgradeneeded = event => {
        const db = (event.target as IDBOpenDBRequest).result;

        // Messages store - main message content
        if (!db.objectStoreNames.contains('messages')) {
          const messageStore = db.createObjectStore('messages', {
            keyPath: 'id',
          });
          messageStore.createIndex('sessionId', 'sessionId', { unique: false });
          messageStore.createIndex('timestamp', 'timestamp', { unique: false });
          messageStore.createIndex('type', 'type', { unique: false });
        }

        // Sessions store - session metadata
        if (!db.objectStoreNames.contains('sessions')) {
          const sessionStore = db.createObjectStore('sessions', {
            keyPath: 'sessionId',
          });
          sessionStore.createIndex('lastUpdated', 'lastUpdated', {
            unique: false,
          });
          sessionStore.createIndex('createdAt', 'createdAt', { unique: false });
        }
      };
    });
  }

  /**
   * Ensure database is initialized
   */
  private async ensureInitialized(): Promise<void> {
    if (!this.isInitialized) {
      await this.initialize();
    }
    if (!this.db) {
      throw new Error('Database not initialized');
    }
  }

  /**
   * Save a single message to IndexedDB
   * Auto-saves after message completion per Section 17.1
   */
  async saveMessage(message: Message, sessionId: string): Promise<void> {
    await this.ensureInitialized();

    // Add sessionId to message for indexing
    const messageWithSession = { ...message, sessionId };

    return new Promise<void>((resolve, reject) => {
      const transaction = this.db!.transaction(
        ['messages', 'sessions'],
        'readwrite'
      );
      const messageStore = transaction.objectStore('messages');
      const sessionStore = transaction.objectStore('sessions');

      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);

      // Save message
      messageStore.put(messageWithSession);

      // Get current message count for this session
      const countRequest = messageStore.index('sessionId').count(sessionId);
      countRequest.onsuccess = () => {
        const messageCount = countRequest.result;

        // Generate session title from first message
        let title = `Session ${sessionId.substring(0, 8)}`;
        if (message.type === 'user') {
          title = message.content.substring(0, 50).trim();
          if (message.content.length > 50) {
            title += '...';
          }
        }

        // Update session metadata
        const sessionMetadata: SessionMetadata = {
          sessionId,
          title,
          lastUpdated: new Date().toISOString(),
          messageCount,
          createdAt: message.timestamp, // Use message timestamp as created date for first message
        };

        sessionStore.put(sessionMetadata);
      };
    });
  }

  /**
   * Save entire chat state (batch operation)
   */
  async saveChatState(chatState: ChatState, sessionId: string): Promise<void> {
    await this.ensureInitialized();

    return new Promise<void>((resolve, reject) => {
      const transaction = this.db!.transaction(
        ['messages', 'sessions'],
        'readwrite'
      );
      const messageStore = transaction.objectStore('messages');
      const sessionStore = transaction.objectStore('sessions');

      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);

      // Save all messages
      for (const message of chatState.sessionMessages) {
        const messageWithSession = { ...message, sessionId };
        messageStore.put(messageWithSession);
      }

      // Generate session title from first user message
      const firstUserMessage = chatState.sessionMessages.find(
        m => m.type === 'user'
      );
      let title = `Session ${sessionId.substring(0, 8)}`;
      if (firstUserMessage) {
        title = firstUserMessage.content.substring(0, 50).trim();
        if (firstUserMessage.content.length > 50) {
          title += '...';
        }
      }

      // Update session metadata
      const sessionMetadata: SessionMetadata = {
        sessionId,
        title,
        lastUpdated: new Date().toISOString(),
        messageCount: chatState.sessionMessages.length,
        createdAt:
          chatState.sessionMessages[0]?.timestamp || new Date().toISOString(),
      };

      sessionStore.put(sessionMetadata);
    });
  }

  /**
   * Load messages for a specific session
   */
  async loadSession(sessionId: string): Promise<Message[]> {
    await this.ensureInitialized();

    const transaction = this.db!.transaction(['messages'], 'readonly');
    const store = transaction.objectStore('messages');
    const index = store.index('sessionId');

    return new Promise((resolve, reject) => {
      const request = index.getAll(sessionId);
      request.onsuccess = () => {
        const messages = request.result
          .map(item => {
            // Remove sessionId before returning Message
            const { sessionId: _, ...message } = item;
            return message as Message;
          })
          .sort(
            (a, b) =>
              new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
          );

        resolve(messages);
      };
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Get all available sessions
   */
  async getAllSessions(): Promise<SessionMetadata[]> {
    await this.ensureInitialized();

    const transaction = this.db!.transaction(['sessions'], 'readonly');
    const store = transaction.objectStore('sessions');

    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => {
        const sessions = request.result.sort(
          (a, b) =>
            new Date(b.lastUpdated).getTime() -
            new Date(a.lastUpdated).getTime()
        );
        resolve(sessions);
      };
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Delete a session and all its messages
   */
  async deleteSession(sessionId: string): Promise<void> {
    await this.ensureInitialized();

    const transaction = this.db!.transaction(
      ['messages', 'sessions'],
      'readwrite'
    );
    const messageStore = transaction.objectStore('messages');
    const sessionStore = transaction.objectStore('sessions');

    // Delete all messages for this session
    const messageIndex = messageStore.index('sessionId');
    const messageRequest = messageIndex.openCursor(sessionId);

    await new Promise<void>((resolve, reject) => {
      messageRequest.onsuccess = event => {
        const cursor = (event.target as IDBRequest).result;
        if (cursor) {
          cursor.delete();
          cursor.continue();
        } else {
          resolve();
        }
      };
      messageRequest.onerror = () => reject(messageRequest.error);
    });

    // Delete session metadata
    await new Promise<void>((resolve, reject) => {
      const request = sessionStore.delete(sessionId);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Get storage metrics for monitoring
   */
  async getStorageMetrics(): Promise<StorageMetrics> {
    await this.ensureInitialized();

    const transaction = this.db!.transaction(
      ['messages', 'sessions'],
      'readonly'
    );
    const messageStore = transaction.objectStore('messages');
    const sessionStore = transaction.objectStore('sessions');

    const [messageCount, sessionCount] = await Promise.all([
      new Promise<number>((resolve, reject) => {
        const request = messageStore.count();
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      }),
      new Promise<number>((resolve, reject) => {
        const request = sessionStore.count();
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      }),
    ]);

    // Estimate storage usage (rough calculation)
    const estimatedStorageUsed = await this.estimateStorageUsage();

    return {
      totalSessions: sessionCount,
      totalMessages: messageCount,
      storageUsed: estimatedStorageUsed,
      lastCleanup: localStorage.getItem('PratikoAI_LastCleanup') || 'never',
    };
  }

  /**
   * Cleanup old sessions to prevent storage bloat
   * Implements Section 18.2 resource limits
   */
  async cleanupOldSessions(maxSessions: number = 100): Promise<void> {
    const sessions = await this.getAllSessions();

    if (sessions.length > maxSessions) {
      const sessionsToDelete = sessions.slice(maxSessions);

      for (const session of sessionsToDelete) {
        await this.deleteSession(session.sessionId);
      }

      localStorage.setItem('PratikoAI_LastCleanup', new Date().toISOString());
    }
  }

  /**
   * Recovery from corrupted data - Section 17.3
   */
  async recoverCorruptedData(): Promise<{ recovered: number; lost: number }> {
    await this.ensureInitialized();

    let recovered = 0;
    let lost = 0;

    const transaction = this.db!.transaction(['messages'], 'readwrite');
    const store = transaction.objectStore('messages');

    return new Promise((resolve, reject) => {
      const request = store.openCursor();
      request.onsuccess = event => {
        const cursor = (event.target as IDBRequest).result;
        if (cursor) {
          try {
            const message = cursor.value;
            // Validate message structure
            if (this.isValidMessage(message)) {
              recovered++;
            } else {
              // Remove corrupted message
              cursor.delete();
              lost++;
            }
          } catch (error) {
            cursor.delete();
            lost++;
          }
          cursor.continue();
        } else {
          resolve({ recovered, lost });
        }
      };
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Helper: Estimate storage usage
   */
  private async estimateStorageUsage(): Promise<number> {
    if (!navigator.storage?.estimate) {
      return 0;
    }

    try {
      const estimate = await navigator.storage.estimate();
      return estimate.usage || 0;
    } catch {
      return 0;
    }
  }

  /**
   * Helper: Validate message structure for recovery
   */
  private isValidMessage(obj: any): boolean {
    return (
      typeof obj === 'object' &&
      obj !== null &&
      typeof obj.id === 'string' &&
      obj.id.length > 0 &&
      (obj.type === 'user' || obj.type === 'ai') &&
      typeof obj.content === 'string' &&
      typeof obj.timestamp === 'string'
    );
  }

  /**
   * Close database connection
   */
  close(): void {
    if (this.db) {
      this.db.close();
      this.db = null;
      this.isInitialized = false;
    }
  }
}

// Export singleton instance
export const messageStorageService = new MessageStorageService();

// Auto-initialize on import
if (typeof window !== 'undefined') {
  messageStorageService.initialize().catch(console.error);
}
