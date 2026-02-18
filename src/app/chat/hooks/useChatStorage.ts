'use client'

import { useCallback, useEffect, useRef } from 'react'
import { nanoid } from 'nanoid'
import type { Message, ChatState } from '../types/chat'
import { messageStorageService, type SessionMetadata } from '../services/MessageStorageService'

/**
 * Hook for integrating chat state with IndexedDB storage
 * Implements CHAT_REQUIREMENTS.md Section 17 persistence requirements
 */

interface UseChatStorageReturn {
  saveMessage: (message: Message, sessionId?: string) => Promise<void>
  saveChatState: (chatState: ChatState) => Promise<void>
  loadSession: (sessionId: string) => Promise<Message[]>
  loadAllSessions: () => Promise<SessionMetadata[]>
  deleteSession: (sessionId: string) => Promise<void>
  getCurrentSessionId: () => string
  createNewSession: () => string
  autoSaveEnabled: boolean
  setAutoSaveEnabled: (enabled: boolean) => void
}

export function useChatStorage(): UseChatStorageReturn {
  const currentSessionIdRef = useRef<string | null>(null)
  const autoSaveEnabledRef = useRef(true)

  /**
   * Get or create current session ID
   */
  const getCurrentSessionId = useCallback((): string => {
    if (!currentSessionIdRef.current) {
      currentSessionIdRef.current = nanoid()
      // Store in localStorage for session recovery
      localStorage.setItem('PratikoAI_CurrentSession', currentSessionIdRef.current)
    }
    return currentSessionIdRef.current
  }, [])

  /**
   * Create new session
   */
  const createNewSession = useCallback((): string => {
    const newSessionId = nanoid()
    currentSessionIdRef.current = newSessionId
    localStorage.setItem('PratikoAI_CurrentSession', newSessionId)
    return newSessionId
  }, [])

  /**
   * Save individual message with auto-save
   * Implements Section 17.1 auto-save after message completion
   */
  const saveMessage = useCallback(async (message: Message, sessionId?: string): Promise<void> => {
    if (!autoSaveEnabledRef.current) return

    const targetSessionId = sessionId || getCurrentSessionId()
    
    try {
      await messageStorageService.saveMessage(message, targetSessionId)
    } catch (error) {
      console.error('Failed to save message:', error)
      // Don't throw - allow chat to continue even if storage fails
    }
  }, [getCurrentSessionId])

  /**
   * Save entire chat state
   */
  const saveChatState = useCallback(async (chatState: ChatState): Promise<void> => {
    if (!autoSaveEnabledRef.current) return

    const sessionId = chatState.currentSessionId || getCurrentSessionId()
    
    try {
      await messageStorageService.saveChatState(chatState, sessionId)
    } catch (error) {
      console.error('Failed to save chat state:', error)
    }
  }, [getCurrentSessionId])

  /**
   * Load messages for specific session
   * Implements Section 17.2 navigation persistence
   */
  const loadSession = useCallback(async (sessionId: string): Promise<Message[]> => {
    try {
      const messages = await messageStorageService.loadSession(sessionId)
      currentSessionIdRef.current = sessionId
      localStorage.setItem('PratikoAI_CurrentSession', sessionId)
      return messages
    } catch (error) {
      console.error('Failed to load session:', error)
      return []
    }
  }, [])

  /**
   * Load all available sessions
   */
  const loadAllSessions = useCallback(async (): Promise<SessionMetadata[]> => {
    try {
      return await messageStorageService.getAllSessions()
    } catch (error) {
      console.error('Failed to load sessions:', error)
      return []
    }
  }, [])

  /**
   * Delete session and its messages
   */
  const deleteSession = useCallback(async (sessionId: string): Promise<void> => {
    try {
      await messageStorageService.deleteSession(sessionId)
      
      // If we're deleting the current session, create a new one
      if (currentSessionIdRef.current === sessionId) {
        createNewSession()
      }
    } catch (error) {
      console.error('Failed to delete session:', error)
      throw error
    }
  }, [createNewSession])

  /**
   * Auto-save control
   */
  const setAutoSaveEnabled = useCallback((enabled: boolean) => {
    autoSaveEnabledRef.current = enabled
    localStorage.setItem('PratikoAI_AutoSave', enabled.toString())
  }, [])

  /**
   * Initialize from localStorage on mount
   * Implements Section 17.2 session recovery
   */
  useEffect(() => {
    // Restore current session ID
    const savedSessionId = localStorage.getItem('PratikoAI_CurrentSession')
    if (savedSessionId) {
      currentSessionIdRef.current = savedSessionId
    }

    // Restore auto-save setting
    const savedAutoSave = localStorage.getItem('PratikoAI_AutoSave')
    if (savedAutoSave !== null) {
      autoSaveEnabledRef.current = savedAutoSave === 'true'
    }

    // Cleanup old sessions periodically
    const lastCleanup = localStorage.getItem('PratikoAI_LastCleanup')
    const now = new Date()
    const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000)
    
    if (!lastCleanup || new Date(lastCleanup) < oneDayAgo) {
      messageStorageService.cleanupOldSessions(100).catch(console.error)
    }
  }, [])

  /**
   * Storage event listener for tab synchronization
   * Implements Section 17.2 tab synchronization
   */
  useEffect(() => {
    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === 'PratikoAI_CurrentSession' && event.newValue) {
        currentSessionIdRef.current = event.newValue
      }
    }

    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [])

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    // Close database connection when component unmounts
    // Note: This should only happen on app close, not page navigation
    const cleanup = () => {
      messageStorageService.close()
    }
    
    // Cleanup on page unload, not on component unmount
    window.addEventListener('beforeunload', cleanup)
    return () => window.removeEventListener('beforeunload', cleanup)
  }, [])

  return {
    saveMessage,
    saveChatState,
    loadSession,
    loadAllSessions,
    deleteSession,
    getCurrentSessionId,
    createNewSession,
    autoSaveEnabled: autoSaveEnabledRef.current,
    setAutoSaveEnabled
  }
}