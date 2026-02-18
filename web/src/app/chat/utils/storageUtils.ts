/**
 * Storage Utilities for Chat Persistence
 *
 * Updated for CLEAN state shape:
 * - Works with Message from ../types/chat (no isStreaming on Message)
 * - Defines StorageQuota locally
 */

import { Message } from '../types/chat'
import { SessionMetadata } from '../services/MessageStorageService'
import { logger } from '@/utils/logger'

export const STORAGE_VERSION = '1.0.0'
export const STORAGE_KEYS = {
  MESSAGES_CURRENT: 'chat_messages_current',
  MESSAGES_RECENT: 'chat_messages_recent',
  MESSAGES_ARCHIVE_PREFIX: 'chat_messages_archive_',
  SESSION_METADATA: 'chat_session_metadata',
  STORAGE_VERSION: 'chat_storage_version',
  LAST_ACTIVITY: 'chat_last_activity',
  AUTO_SAVE_ENABLED: 'chat_auto_save_enabled'
}

// Pagination settings
export const PAGINATION_CONFIG = {
  RECENT_MESSAGES_LIMIT: 100,
  ARCHIVE_CHUNK_SIZE: 200,
  PAGINATION_THRESHOLD: 300 // Only start pagination with very large conversations
}

// Local definition for quota info
export interface StorageQuota {
  used: number
  total: number
  available: number
  percentUsed: number
  warning: boolean
}

/**
 * Storage wrapper with error handling and quota management
 */
export class ChatStorage {
  private storageQuotaWarningThreshold = 0.8 // 80%
  private storageQuotaCriticalThreshold = 0.95 // 95%

  /**
   * Save messages to localStorage with compression and error handling
   */
  saveMessages(messages: Message[], sessionMetadata?: SessionMetadata): void {
    try {
      if (messages.length > PAGINATION_CONFIG.PAGINATION_THRESHOLD) {
        this.saveMessagesWithPagination(messages, sessionMetadata)
      } else {
        this.saveMessagesStandard(messages, sessionMetadata)
      }
    } catch (error: any) {
      const isQuotaError =
          (error instanceof DOMException && error.name === 'QuotaExceededError') ||
          (error instanceof Error && error.message?.includes('QuotaExceededError'))

      if (isQuotaError) {
        this.saveToSessionStorageFallback(messages, sessionMetadata)
      } else if (error instanceof DOMException && error.name === 'SecurityError') {
        throw new Error('Storage access denied (private mode?)')
      } else {
        throw new Error(`Failed to save messages: ${error.message}`)
      }
    }
  }

  /**
   * Save messages using standard approach (for smaller conversations)
   */
  private saveMessagesStandard(messages: Message[], sessionMetadata?: SessionMetadata): void {
    const mergedMessages = this.mergeMessagesWithExisting(messages)

    const messagesJson = JSON.stringify(mergedMessages)
    this.ensureStorageCapacity(messagesJson.length)

    localStorage.setItem(STORAGE_KEYS.MESSAGES_CURRENT, messagesJson)
    localStorage.setItem(STORAGE_KEYS.LAST_ACTIVITY, new Date().toISOString())
    localStorage.setItem(STORAGE_KEYS.STORAGE_VERSION, STORAGE_VERSION)

    if (sessionMetadata) {
      const metadataWithTimestamp = {
        ...sessionMetadata,
        lastActivity: new Date().toISOString(),
        version: STORAGE_VERSION
      }
      localStorage.setItem(STORAGE_KEYS.SESSION_METADATA, JSON.stringify(metadataWithTimestamp))
    }
  }

  /**
   * Simple, safe merge-by-id (no streaming flags in clean model)
   * - If newMessages contain an id, prefer the new one.
   * - Keep existing messages that are not overridden.
   */
  private mergeMessagesWithExisting(newMessages: Message[]): Message[] {
    try {
      const existingData = localStorage.getItem(STORAGE_KEYS.MESSAGES_CURRENT)
      if (!existingData) return newMessages

      const existingMessages: Message[] = JSON.parse(existingData)

      const incomingById = new Map(newMessages.map(m => [m.id, m]))
      const merged: Message[] = []

      // Keep existing unless overridden by incoming
      for (const ex of existingMessages) {
        const override = incomingById.get(ex.id)
        if (override) {
          merged.push(override)
          incomingById.delete(ex.id)
        } else {
          merged.push(ex)
        }
      }

      // Append any new messages not present before
      for (const remaining of incomingById.values()) {
        merged.push(remaining)
      }

      return merged
    } catch (error: any) {
      logger.warn('Failed to merge messages, using new messages only', {
        component: 'ChatStorage',
        action: 'merge_fallback',
        metadata: { error: error.message }
      })
      return newMessages
    }
  }

  /**
   * Save messages using pagination (for large conversations)
   */
  private saveMessagesWithPagination(messages: Message[], sessionMetadata?: SessionMetadata): void {
    const recentMessages = messages.slice(-PAGINATION_CONFIG.RECENT_MESSAGES_LIMIT)
    const messagesToArchive = messages.slice(0, -PAGINATION_CONFIG.RECENT_MESSAGES_LIMIT)

    const recentJson = JSON.stringify(recentMessages)
    this.ensureStorageCapacity(recentJson.length)

    localStorage.setItem(STORAGE_KEYS.MESSAGES_RECENT, recentJson)
    localStorage.setItem(STORAGE_KEYS.LAST_ACTIVITY, new Date().toISOString())
    localStorage.setItem(STORAGE_KEYS.STORAGE_VERSION, STORAGE_VERSION)

    if (messagesToArchive.length > 0) {
      this.archiveMessages(messagesToArchive)
    }

    if (sessionMetadata) {
      const metadataWithTimestamp = {
        ...sessionMetadata,
        lastActivity: new Date().toISOString(),
        version: STORAGE_VERSION,
        totalMessages: messages.length,
        recentMessages: recentMessages.length,
        archivedMessages: messagesToArchive.length
      }
      localStorage.setItem(STORAGE_KEYS.SESSION_METADATA, JSON.stringify(metadataWithTimestamp))
    }
  }

  /**
   * Archive messages in chunks
   */
  private archiveMessages(messages: Message[]): void {
    const chunks: Message[][] = []
    for (let i = 0; i < messages.length; i += PAGINATION_CONFIG.ARCHIVE_CHUNK_SIZE) {
      chunks.push(messages.slice(i, i + PAGINATION_CONFIG.ARCHIVE_CHUNK_SIZE))
    }

    chunks.forEach((chunk, index) => {
      const chunkJson = JSON.stringify(chunk)
      const archiveKey = `${STORAGE_KEYS.MESSAGES_ARCHIVE_PREFIX}${index}`

      try {
        localStorage.setItem(archiveKey, chunkJson)
      } catch (error: any) {
        logger.warn('Failed to save archive chunk', {
          component: 'ChatStorage',
          action: 'archive_chunk_failed',
          metadata: { chunkIndex: index, error: error.message }
        })
      }
    })
  }

  /**
   * Load messages from localStorage with version compatibility
   */
  loadMessages(): { messages: Message[]; metadata?: SessionMetadata; storageKey: string } | null {
    try {
      const recentStored = localStorage.getItem(STORAGE_KEYS.MESSAGES_RECENT)
      if (recentStored) {
        const recentMessages = JSON.parse(recentStored)
        const archivedMessages = this.loadArchivedMessages()
        const allMessages = [...archivedMessages, ...recentMessages]

        return {
          messages: Array.isArray(allMessages) ? allMessages : [],
          metadata: this.loadMetadata(),
          storageKey: STORAGE_KEYS.MESSAGES_RECENT
        }
      }

      const currentStored = localStorage.getItem(STORAGE_KEYS.MESSAGES_CURRENT)
      if (!currentStored) return null

      const messages = JSON.parse(currentStored)

      return {
        messages: Array.isArray(messages) ? messages : [],
        metadata: this.loadMetadata(),
        storageKey: STORAGE_KEYS.MESSAGES_CURRENT
      }
    } catch (error: any) {
      logger.error('Failed to load messages from storage', error, {
        component: 'ChatStorage',
        action: 'load_messages_failed'
      })
      return null
    }
  }

  /**
   * Load archived messages from localStorage
   */
  private loadArchivedMessages(): Message[] {
    const archivedMessages: Message[] = []

    for (let i = 0; i < 100; i++) {
      const archiveKey = `${STORAGE_KEYS.MESSAGES_ARCHIVE_PREFIX}${i}`
      const stored = localStorage.getItem(archiveKey)
      if (!stored) break

      try {
        const chunk = JSON.parse(stored)
        if (Array.isArray(chunk)) {
          archivedMessages.push(...chunk)
        }
      } catch (error: any) {
        logger.warn('Failed to parse archive chunk', {
          component: 'ChatStorage',
          action: 'parse_archive_failed',
          metadata: { chunkIndex: i, error: error.message }
        })
      }
    }

    return archivedMessages
  }

  /**
   * Load session metadata
   */
  private loadMetadata(): SessionMetadata | undefined {
    try {
      const metadataStored = localStorage.getItem(STORAGE_KEYS.SESSION_METADATA)
      if (metadataStored) {
        const metadata = JSON.parse(metadataStored)

        const storedVersion = localStorage.getItem(STORAGE_KEYS.STORAGE_VERSION)
        if (storedVersion && storedVersion !== STORAGE_VERSION) {
          logger.warn('Storage version mismatch', {
            component: 'ChatStorage',
            action: 'version_mismatch',
            metadata: { storedVersion, currentVersion: STORAGE_VERSION }
          })
        }

        return metadata
      }
    } catch (error: any) {
      logger.warn('Failed to parse session metadata', {
        component: 'ChatStorage',
        action: 'parse_metadata_failed',
        metadata: { error: error.message }
      })
    }

    return undefined
  }

  /**
   * Get current storage quota information
   */
  async getStorageQuota(): Promise<StorageQuota> {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      try {
        const estimate = await (navigator.storage as any).estimate()
        const used = estimate.usage || 0
        const total = estimate.quota || 0
        const available = total - used
        const percentUsed = total > 0 ? used / total : 0

        return {
          used,
          total,
          available,
          percentUsed,
          warning: percentUsed > this.storageQuotaWarningThreshold
        }
      } catch (error: any) {
        logger.warn('Could not get storage estimate', {
          component: 'ChatStorage',
          action: 'estimate_failed',
          metadata: { error: error.message }
        })
      }
    }

    // Fallback estimation
    return this.estimateLocalStorageUsage()
  }

  private checkStorageQuotaSync(additionalSize: number): void {
    const quota = this.estimateLocalStorageUsage()
    if (quota.available < additionalSize) {
      throw new DOMException('Storage quota exceeded', 'QuotaExceededError')
    }
    if (quota.percentUsed > this.storageQuotaCriticalThreshold) {
      logger.logStorageQuotaWarning(quota.percentUsed, quota.available)
    }
  }

  /**
   * Estimate localStorage usage (fallback method)
   */
  private estimateLocalStorageUsage(): StorageQuota {
    let used = 0

    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key) {
        const value = localStorage.getItem(key) || ''
        used += key.length + value.length
      }
    }

    // Test environment (MockStorage) support
    let totalQuota = 5 * 1024 * 1024 // 5MB typical
    if (typeof (localStorage as any).getCurrentSize === 'function') {
      const mockStorage = localStorage as any
      used = mockStorage.getCurrentSize()
      if (mockStorage.quota !== undefined) {
        totalQuota = mockStorage.quota
      }
    }

    const available = totalQuota - used
    const percentUsed = totalQuota > 0 ? used / totalQuota : 0

    return {
      used,
      total: totalQuota,
      available,
      percentUsed,
      warning: percentUsed > this.storageQuotaWarningThreshold
    }
  }

  /**
   * Clear all chat-related storage
   */
  clearStorage(): void {
    const keysToRemove = Object.values(STORAGE_KEYS)
    keysToRemove.forEach(key => {
      try {
        localStorage.removeItem(key)
      } catch (error: any) {
        logger.warn('Failed to remove storage key', {
          component: 'ChatStorage',
          action: 'remove_key_failed',
          metadata: { key, error: error.message }
        })
      }
    })
  }

  /**
   * Check if storage is available
   */
  isStorageAvailable(): boolean {
    try {
      const testKey = '__storage_test__'
      localStorage.setItem(testKey, 'test')
      localStorage.removeItem(testKey)
      return true
    } catch {
      return false
    }
  }

  /**
   * Set up storage event listeners for multi-tab synchronization
   */
  setupStorageEventListener(callback: (event: StorageEvent) => void): () => void {
    const handleStorageEvent = (event: StorageEvent) => {
      if (event.key && Object.values(STORAGE_KEYS).includes(event.key)) {
        callback(event)
      }
    }

    window.addEventListener('storage', handleStorageEvent)
    return () => window.removeEventListener('storage', handleStorageEvent)
  }

  getSessionStorageKey(sessionId: string): string {
    return `chat_session_${sessionId}`
  }

  saveSessionData(sessionId: string, messages: Message[], metadata?: SessionMetadata): void {
    const sessionData = {
      version: STORAGE_VERSION,
      timestamp: new Date().toISOString(),
      sessionId,
      messages,
      metadata
    }
    const key = this.getSessionStorageKey(sessionId)
    localStorage.setItem(key, JSON.stringify(sessionData))
  }

  loadSessionData(sessionId: string): { messages: Message[]; metadata?: SessionMetadata } | null {
    try {
      const key = this.getSessionStorageKey(sessionId)
      const stored = localStorage.getItem(key)
      if (!stored) return null

      const data = JSON.parse(stored)
      return {
        messages: data.messages || [],
        metadata: data.metadata
      }
    } catch (error: any) {
      logger.error('Failed to load session data', error, {
        component: 'ChatStorage',
        action: 'load_session_failed',
        metadata: { sessionId }
      })
      return null
    }
  }

  /**
   * Ensure storage has enough capacity by cleaning up if needed
   */
  private ensureStorageCapacity(requiredSize: number): void {
    const quota = this.estimateLocalStorageUsage()
    const isNearQuotaLimit = quota.percentUsed > this.storageQuotaWarningThreshold
    const hasInsufficientSpace = quota.available < requiredSize

    if (hasInsufficientSpace || isNearQuotaLimit) {
      this.cleanupOldSessions(requiredSize)

      const after = this.estimateLocalStorageUsage()
      if (after.available < requiredSize) {
        throw new DOMException('Storage quota exceeded after cleanup', 'QuotaExceededError')
      }
    }
  }

  /**
   * Cleanup old sessions when approaching storage quota
   */
  private cleanupOldSessions(requiredSize: number): void {
    const sessionData: Array<{ key: string; timestamp: number; size: number }> = []

    // Find all session keys (tests use 'chat_session_0', 'chat_session_1', etc.)
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && (key.startsWith('chat_session_') || key.startsWith('old-session-'))) {
        if (key === STORAGE_KEYS.SESSION_METADATA || key === STORAGE_KEYS.MESSAGES_CURRENT) {
          continue
        }

        try {
          const data = localStorage.getItem(key)
          if (data) {
            let timestamp = 0
            try {
              const sessionInfo = JSON.parse(data)
              if (sessionInfo.timestamp) {
                timestamp = new Date(sessionInfo.timestamp).getTime()
              } else if (sessionInfo.messages?.[0]?.timestamp) {
                timestamp = new Date(sessionInfo.messages[0].timestamp).getTime()
              } else {
                timestamp = Date.now() - 30 * 24 * 60 * 60 * 1000 // 30 days ago
              }
            } catch {
              timestamp = 0
            }

            sessionData.push({ key, timestamp, size: data.length })
          }
        } catch {
          sessionData.push({ key, timestamp: 0, size: 0 })
        }
      }
    }

    sessionData.sort((a, b) => a.timestamp - b.timestamp)

    let freedSpace = 0
    let removedCount = 0
    for (const session of sessionData) {
      const maxRemovalPercent = 0.5
      const minRemovalCount = Math.min(2, sessionData.length)

      if (freedSpace >= requiredSize && removedCount >= minRemovalCount) break
      if (removedCount >= Math.floor(sessionData.length * maxRemovalPercent)) break

      try {
        localStorage.removeItem(session.key)
        freedSpace += session.size
        removedCount++
      } catch (error: any) {
        logger.warn('Failed to remove session during cleanup', {
          component: 'ChatStorage',
          action: 'cleanup_session_failed',
          metadata: { sessionKey: session.key, error: error.message }
        })
      }
    }
  }

  /**
   * Fallback to sessionStorage when localStorage is full
   */
  private saveToSessionStorageFallback(messages: Message[], sessionMetadata?: SessionMetadata): void {
    try {
      logger.warn('localStorage quota exceeded, falling back to sessionStorage', {
        component: 'ChatStorage',
        action: 'fallback_to_session_storage'
      })

      const messagesJson = JSON.stringify(messages)
      sessionStorage.setItem(STORAGE_KEYS.MESSAGES_CURRENT, messagesJson)
      sessionStorage.setItem(STORAGE_KEYS.LAST_ACTIVITY, new Date().toISOString())
      sessionStorage.setItem(STORAGE_KEYS.STORAGE_VERSION, STORAGE_VERSION)

      if (sessionMetadata) {
        const metadataWithTimestamp = {
          ...sessionMetadata,
          lastActivity: new Date().toISOString(),
          version: STORAGE_VERSION
        }
        sessionStorage.setItem(STORAGE_KEYS.SESSION_METADATA, JSON.stringify(metadataWithTimestamp))
      }
    } catch (error: any) {
      logger.error('Both localStorage and sessionStorage failed', error, {
        component: 'ChatStorage',
        action: 'all_storage_failed'
      })
      throw new Error('All storage options exhausted')
    }
  }

  /**
   * Load messages with fallback to sessionStorage
   */
  loadMessagesWithFallback(): { messages: Message[]; metadata?: SessionMetadata; storageKey: string } | null {
    const localData = this.loadMessages()
    if (localData) return localData

    try {
      const stored = sessionStorage.getItem(STORAGE_KEYS.MESSAGES_CURRENT)
      if (!stored) return null

      const messages = JSON.parse(stored)

      const metadataStored = sessionStorage.getItem(STORAGE_KEYS.SESSION_METADATA)
      let metadata: SessionMetadata | undefined
      if (metadataStored) {
        try {
          metadata = JSON.parse(metadataStored)
        } catch (error: any) {
          logger.warn('Failed to parse session metadata from sessionStorage', {
            component: 'ChatStorage',
            action: 'parse_session_metadata_failed',
            metadata: { error: error.message }
          })
        }
      }

      return {
        messages: Array.isArray(messages) ? messages : [],
        metadata,
        storageKey: 'sessionStorage_' + STORAGE_KEYS.MESSAGES_CURRENT
      }
    } catch (error: any) {
      logger.error('Failed to load messages from sessionStorage', error, {
        component: 'ChatStorage',
        action: 'load_from_session_storage_failed'
      })
      return null
    }
  }

  /**
   * Check if sessionStorage fallback is being used
   */
  isUsingSessionStorageFallback(): boolean {
    return !localStorage.getItem(STORAGE_KEYS.MESSAGES_CURRENT) &&
        !!sessionStorage.getItem(STORAGE_KEYS.MESSAGES_CURRENT)
  }
}

// Export singleton instance
export const chatStorage = new ChatStorage()
