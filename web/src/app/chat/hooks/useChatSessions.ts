'use client';

import {
  useState,
  useEffect,
  useCallback,
  useRef,
  createContext,
  useContext,
} from 'react';
import React from 'react';
import { apiClient } from '../../../lib/api';
import type { Message } from '../types/chat';
import { useSharedChatState } from './useChatState';
import { messageStorageService } from '../services/MessageStorageService';

// Global flag to prevent multiple session initializations across all hook instances
let globalInitializationInProgress = false;

interface ChatSession {
  id: string;
  name: string;
  created_at: string;
  updated_at?: string;
  message_count?: number;
  isActive: boolean;
  token?: string; // Store session token for switching
}

// Helper function to check if a session is empty (no messages sent)
const isSessionEmpty = (session: ChatSession): boolean => {
  return !session.message_count || session.message_count === 0;
};

// Helper function to check if a session has at least one complete Q&A pair
// Only sessions with at least one question AND answer should show edit/delete buttons
const hasCompleteQAPair = (session: ChatSession): boolean => {
  // For old sessions (from backend), assume they have complete Q&A if message_count >= 2
  // For new sessions, message_count will be set when first AI response completes
  return session.message_count !== undefined && session.message_count >= 2;
};

interface UseChatSessionsReturn {
  // Session list management
  sessions: ChatSession[];
  isLoadingSessions: boolean;
  sessionsError: string | null;

  // Current session management
  currentSession: ChatSession | null;
  isLoadingHistory: boolean;
  historyError: string | null;

  // Actions
  loadSessions: () => Promise<void>;
  createNewSession: () => Promise<ChatSession | null>;
  startNewChat: () => void; // Clear UI state for new chat (session created lazily on first message)
  switchToSession: (sessionId: string) => Promise<Message[]>;
  loadSessionHistory: (sessionId?: string) => Promise<Message[]>;
  updateSessionName: (sessionId: string, name: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;

  // Session persistence
  initializeSession: () => Promise<Message[]>;

  // Helper functions
  isSessionEmpty: (session: ChatSession) => boolean;
  hasCompleteQAPair: (session: ChatSession) => boolean;
  markSessionAsUsed: (sessionId: string) => void;
  cleanupEmptySessions: () => Promise<void>;
}

/**
 * Custom hook for managing chat sessions
 *
 * Handles CHAT_REQUIREMENTS.md Section 17: Persistence Requirements
 * - Auto-loads sessions on mount
 * - Restores session from URL params or localStorage
 * - Provides session switching capabilities
 * - Handles session creation and updates
 */
export function useChatSessions(): UseChatSessionsReturn {
  // Get access to chat state functionality
  const { clearMessages } = useSharedChatState();

  // Session list state
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);

  // Current session state
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(
    null
  );
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);

  // Prevent multiple initialization calls
  const initializationRef = useRef(false);

  /**
   * Load all user sessions from backend
   */
  const loadSessions = useCallback(async (): Promise<void> => {
    console.log('🔄 useChatSessions: loadSessions called');
    console.log('🔐 Authentication check:', apiClient.isAuthenticated());

    try {
      console.log('⏳ Setting loading state to true');
      setIsLoadingSessions(true);
      setSessionsError(null);

      console.log('📡 Calling apiClient.getUserSessions()...');
      const sessionList = await apiClient.getUserSessions();
      console.log(
        '✅ Sessions received from API:',
        sessionList?.length || 0,
        'sessions'
      );
      console.log('🔍 Raw session list from API:', sessionList);

      // Check each session structure
      sessionList.forEach((session, index) => {
        console.log(`🔍 Session ${index}:`, {
          id: session.session_id,
          name: session.name,
          hasToken: !!session.token,
          tokenPreview: session.token
            ? session.token.access_token?.substring(0, 20) + '...'
            : 'NO TOKEN',
        });
      });

      const formattedSessions: ChatSession[] = sessionList.map(session => ({
        id: session.session_id,
        name: session.name || 'Nuova Conversazione',
        created_at: session.created_at || new Date().toISOString(),
        // updated_at is not available from API, use created_at for now
        updated_at: session.created_at,
        // CRITICAL: For old sessions with actual names (not empty), assume they have complete Q&A
        // For sessions with default/empty names, they're likely new and empty
        message_count:
          session.name &&
          session.name.trim() &&
          session.name !== 'Nuova Conversazione'
            ? 2
            : 0,
        isActive: false, // Will be set when switching sessions
        token: session.token?.access_token, // Store session token for switching
      }));

      console.log('📝 Formatted sessions:', formattedSessions);

      // Sort by updated_at (most recent first) or created_at if no updated_at
      formattedSessions.sort((a, b) => {
        const aTime = a.updated_at || a.created_at;
        const bTime = b.updated_at || b.created_at;
        return new Date(bTime).getTime() - new Date(aTime).getTime();
      });

      console.log(
        '📊 Setting sessions state with',
        formattedSessions.length,
        'sessions'
      );
      setSessions(formattedSessions);

      // Run cleanup after setting sessions (with slight delay to ensure state is updated)
      setTimeout(() => {
        if (formattedSessions.filter(s => isSessionEmpty(s)).length > 1) {
          console.log(
            '🧹 Multiple empty sessions detected, will cleanup after state update'
          );
        }
      }, 100);
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Errore durante il caricamento delle sessioni';
      console.error('❌ Failed to load sessions:', error);
      console.log('💥 Setting sessions error:', errorMessage);
      setSessionsError(errorMessage);
    } finally {
      console.log('🏁 Setting loading state to false');
      setIsLoadingSessions(false);
    }
  }, []);

  /**
   * Save current session ID to localStorage for persistence
   */
  const saveSessionToLocalStorage = useCallback((sessionId: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('current_session_id', sessionId);
      console.log('💾 Saved session to localStorage:', sessionId);
    }
  }, []);

  /**
   * Create a new chat session
   */
  const createNewSession =
    useCallback(async (): Promise<ChatSession | null> => {
      console.log('🆕 useChatSessions: createNewSession called');
      console.log('🔐 Authentication check:', apiClient.isAuthenticated());

      try {
        console.log('⏳ Setting loading state to true for session creation');
        setIsLoadingSessions(true);

        console.log('📡 Calling apiClient.createSession()...');
        const newSessionResponse = await apiClient.createSession();
        console.log('✅ New session created:', newSessionResponse);

        const newSession: ChatSession = {
          id: newSessionResponse.session_id,
          name: newSessionResponse.name || 'Nuova Conversazione',
          created_at: newSessionResponse.created_at || new Date().toISOString(),
          message_count: 0, // New session starts empty
          isActive: true,
          token: newSessionResponse.token.access_token,
        };

        console.log('📝 Formatted new session:', newSession);

        // Set as current session
        console.log('🔧 Setting current session in API client');
        apiClient.setCurrentSession(
          newSessionResponse.session_id,
          newSessionResponse.token.access_token
        );
        console.log('🎯 Setting current session in state');
        setCurrentSession(newSession);

        // Add to sessions list
        console.log('📊 Adding session to sessions list');
        setSessions(prevSessions => {
          const updatedSessions = prevSessions.map(s => ({
            ...s,
            isActive: false,
          }));
          return [newSession, ...updatedSessions];
        });

        // Save to localStorage for persistence
        saveSessionToLocalStorage(newSession.id);

        console.log('✅ New session created, saved, and set as current');
        return newSession;
      } catch (error) {
        const errorMessage =
          error instanceof Error
            ? error.message
            : 'Errore durante la creazione della sessione';
        console.error('❌ Failed to create new session:', error);
        console.log('💥 Setting sessions error:', errorMessage);
        setSessionsError(errorMessage);
        return null;
      } finally {
        console.log('🏁 Setting loading state to false after session creation');
        setIsLoadingSessions(false);
      }
    }, [saveSessionToLocalStorage]);

  /**
   * Start a new chat - clears UI state WITHOUT creating a session
   * Session will be created lazily when user sends first message
   *
   * This implements the DEV-FE-003 lazy session creation requirement:
   * Chat history items should only appear AFTER user sends first message
   */
  const startNewChat = useCallback((): void => {
    console.log(
      '🆕 useChatSessions: startNewChat called - clearing UI state only'
    );

    // Clear current session (session will be created lazily on first message send)
    setCurrentSession(null);

    // Deselect all sessions in sidebar
    setSessions(prevSessions =>
      prevSessions.map(s => ({ ...s, isActive: false }))
    );

    // Clear chat messages
    clearMessages();

    // Clear from localStorage
    if (typeof window !== 'undefined') {
      localStorage.removeItem('current_session_id');
    }

    console.log(
      '✅ New chat state prepared - session will be created on first message send'
    );
  }, [clearMessages]);

  /**
   * Load chat history for a specific session
   */
  const loadSessionHistory = useCallback(
    async (sessionId?: string): Promise<Message[]> => {
      console.log(
        '📚 loadSessionHistory: Starting to load history for session:',
        sessionId
      );
      try {
        setIsLoadingHistory(true);
        setHistoryError(null);

        // Always make real API call to get actual messages
        console.log(
          '📡 loadSessionHistory: Calling apiClient.getChatHistory()...'
        );
        const currentApiSession = apiClient.getCurrentSession();
        console.log('📡 loadSessionHistory: Current API client state:', {
          isAuthenticated: apiClient.isAuthenticated(),
          hasSession: !!currentApiSession,
          currentSessionId: currentApiSession?.sessionId,
          hasToken: !!currentApiSession?.sessionToken,
        });

        // Check if we have a valid session before trying to get history
        if (!currentApiSession?.sessionToken) {
          console.warn(
            '⚠️ loadSessionHistory: No valid session token, returning empty history'
          );
          return [];
        }

        const history = await apiClient.getChatHistory();
        console.log('📡 loadSessionHistory: API returned:', history);
        console.log(
          '📡 loadSessionHistory: API response type:',
          typeof history
        );
        console.log(
          '📡 loadSessionHistory: API messages count:',
          history?.messages?.length || 0
        );
        console.log(
          '📡 loadSessionHistory: API messages preview:',
          history?.messages?.map(msg => ({
            role: msg.role,
            contentPreview: msg.content.substring(0, 100),
            contentLength: msg.content.length,
          })) || []
        );
        console.log(
          '📡 loadSessionHistory: API response keys:',
          Object.keys(history || {})
        );
        console.log(
          '📡 loadSessionHistory: Raw messages from API:',
          history.messages
        );
        console.log(
          '📡 loadSessionHistory: Messages type:',
          typeof history.messages
        );
        console.log(
          '📡 loadSessionHistory: Messages is array:',
          Array.isArray(history.messages)
        );
        console.log(
          '📡 loadSessionHistory: Messages count from API:',
          history.messages?.length || 0
        );

        // Log each message structure
        if (history.messages && Array.isArray(history.messages)) {
          history.messages.forEach((msg, index) => {
            console.log(`📡 Message ${index} structure:`, {
              type: typeof msg,
              keys: Object.keys(msg || {}),
              content: msg,
            });
          });
        }

        if (!history.messages || history.messages.length === 0) {
          console.log('⚠️ loadSessionHistory: No messages returned from API');
          return [];
        }

        // Convert API messages to UI message format
        // CRITICAL FIX: Generate stable, deterministic IDs based on content and position
        // This ensures same messages get same IDs across session switches
        const uiMessages: Message[] = history.messages.map((apiMsg, index) => {
          console.log(`📝 Converting message ${index}:`, apiMsg);

          // Generate stable ID based on session, index, and content hash
          const contentHash = apiMsg.content
            .substring(0, 20)
            .replace(/[^a-zA-Z0-9]/g, '');
          const stableId = `${sessionId || 'unknown'}-${index}-${contentHash}`;

          const convertedMsg: Message = {
            id: stableId,
            type: apiMsg.role === 'user' ? ('user' as const) : ('ai' as const),
            content: apiMsg.content,
            timestamp: new Date().toISOString(),
          };

          // DEV-007 Issue 3: Parse attachments from history response
          // This ensures attachment chips persist across page refreshes
          if (apiMsg.attachments && apiMsg.attachments.length > 0) {
            convertedMsg.attachments = apiMsg.attachments.map(att => ({
              id: att.id,
              filename: att.filename,
              type: att.type,
            }));
            console.log(
              `📎 Loaded ${convertedMsg.attachments.length} attachments for message ${index}:`,
              convertedMsg.attachments.map(a => a.filename)
            );
          }

          // DEV-242: Preserve structured_sources for citations display after refresh
          // IMPORTANT: Do NOT remove this - without it, the "Fonti" section will be empty
          // after page refresh because structured_sources won't be copied to the UI Message
          if (
            apiMsg.structured_sources &&
            apiMsg.structured_sources.length > 0
          ) {
            convertedMsg.structured_sources = apiMsg.structured_sources;
            console.log(
              `📚 Loaded ${convertedMsg.structured_sources.length} sources for message ${index}`
            );
          }

          // DEV-244: Preserve kb_source_urls for Fonti section after refresh
          // These are deterministic KB source URLs from retrieval (independent of LLM output)
          if (apiMsg.kb_source_urls && apiMsg.kb_source_urls.length > 0) {
            convertedMsg.kb_source_urls = apiMsg.kb_source_urls;
            console.log(
              `📗 Loaded ${convertedMsg.kb_source_urls.length} KB sources for message ${index}`
            );
          }

          console.log(
            `✅ Converted message ${index} with stable ID:`,
            convertedMsg.id
          );
          return convertedMsg;
        });

        console.log('📦 loadSessionHistory: Final UI messages:', uiMessages);
        console.log(
          '📦 loadSessionHistory: Returning',
          uiMessages.length,
          'messages'
        );
        return uiMessages;
      } catch (error) {
        const errorMessage =
          error instanceof Error
            ? error.message
            : 'Errore durante il caricamento della cronologia';
        console.error('❌ loadSessionHistory: Error loading history:', error);
        setHistoryError(errorMessage);
        return [];
      } finally {
        console.log('🏁 loadSessionHistory: Setting loading state to false');
        setIsLoadingHistory(false);
      }
    },
    []
  );

  /**
   * Switch to a different session and load its history
   */
  const switchToSession = useCallback(
    async (sessionId: string): Promise<Message[]> => {
      console.log('🔄 useChatSessions: switchToSession called for:', sessionId);
      console.log(
        '📊 Available sessions:',
        sessions.map(s => ({ id: s.id, name: s.name, active: s.isActive }))
      );

      const targetSession = sessions.find(s => s.id === sessionId);
      console.log('🎯 Target session found:', targetSession);

      if (!targetSession) {
        console.error('❌ Session not found in sessions list');
        throw new Error('Sessione non trovata');
      }

      try {
        console.log('⏳ Setting loading state for history');
        setIsLoadingHistory(true);
        setHistoryError(null);

        // Update active session in state
        console.log('🎯 Updating session active state');
        setSessions(prevSessions =>
          prevSessions.map(s => ({ ...s, isActive: s.id === sessionId }))
        );
        setCurrentSession({ ...targetSession, isActive: true });

        // Save to localStorage for persistence
        saveSessionToLocalStorage(sessionId);

        // Set session token in API client
        if (targetSession.token) {
          console.log(
            '🔧 Setting session token in API client for session:',
            sessionId
          );
          console.log(
            '🔧 Token preview:',
            targetSession.token.substring(0, 20) + '...'
          );
          apiClient.setCurrentSession(sessionId, targetSession.token);
        } else {
          console.warn('⚠️ No session token available for session:', sessionId);
          throw new Error('Session token not available for this session');
        }

        // Load history for this session
        console.log('📚 Loading session history...');
        const messages = await loadSessionHistory(sessionId);
        console.log(
          '📨 Session history loaded:',
          messages?.length || 0,
          'messages'
        );
        console.log('📨 Messages returned from loadSessionHistory:', messages);
        console.log(
          '📨 First message preview:',
          messages[0]
            ? `${messages[0].type}: ${messages[0].content.substring(0, 50)}...`
            : 'none'
        );

        console.log(
          '🔄 switchToSession: About to return messages:',
          messages.length,
          'messages'
        );
        return messages;
      } catch (error) {
        const errorMessage =
          error instanceof Error
            ? error.message
            : 'Errore durante il cambio sessione';
        console.error('❌ Failed to switch session:', error);
        setHistoryError(errorMessage);
        throw error;
      } finally {
        console.log('🏁 Setting loading state to false');
        setIsLoadingHistory(false);
      }
    },
    [sessions, loadSessionHistory, saveSessionToLocalStorage]
  );

  /**
   * Update session name
   */
  const updateSessionName = useCallback(
    async (sessionId: string, name: string): Promise<void> => {
      try {
        // Find the session to get its token
        const sessionToUpdate = sessions.find(s => s.id === sessionId);
        const sessionToken = sessionToUpdate?.token;

        console.log(
          '✏️ [HOOK_DEBUG] Updating session name:',
          sessionId,
          'to:',
          name
        );
        console.log('✏️ [HOOK_DEBUG] Session token available:', !!sessionToken);
        console.log('✏️ [HOOK_DEBUG] Session to update:', sessionToUpdate);

        // OPTIMISTIC UPDATE: Update local state immediately for instant UI feedback
        setSessions(prevSessions =>
          prevSessions.map(s => (s.id === sessionId ? { ...s, name } : s))
        );

        if (currentSession?.id === sessionId) {
          setCurrentSession(prev => (prev ? { ...prev, name } : prev));
        }

        // Then update backend (without await, so it doesn't block)
        apiClient
          .updateSessionName(sessionId, name, sessionToken)
          .catch(error => {
            console.error('Failed to update session name on backend:', error);
            // Optionally revert the optimistic update on failure
            // For now, we keep the local change since it's not critical
          });
      } catch (error) {
        const errorMessage =
          error instanceof Error
            ? error.message
            : "Errore durante l'aggiornamento del nome";
        console.error('Failed to update session name:', error);
        throw new Error(errorMessage);
      }
    },
    [sessions, currentSession]
  );

  /**
   * Delete a session
   */
  const deleteSession = useCallback(
    async (sessionId: string): Promise<void> => {
      try {
        // Find the session to get its token
        const sessionToDelete = sessions.find(s => s.id === sessionId);
        const sessionToken = sessionToDelete?.token;

        console.log('🗑️ [HOOK_DEBUG] Deleting session:', sessionId);
        console.log('🗑️ [HOOK_DEBUG] Session token available:', !!sessionToken);
        console.log('🗑️ [HOOK_DEBUG] Session to delete:', sessionToDelete);

        await apiClient.deleteSession(sessionId, sessionToken);

        // Remove from local state
        setSessions(prevSessions =>
          prevSessions.filter(s => s.id !== sessionId)
        );

        // If deleted session was current, clear state (lazy creation - new session created on first message)
        if (currentSession?.id === sessionId) {
          console.log('🗑️ Deleted session was current, clearing state...');
          localStorage.removeItem('current_session_id');

          // Clear the chat area to ensure clean slate
          console.log('🧹 Clearing chat messages for deleted session');
          clearMessages();
          setCurrentSession(null);
          // No createNewSession() - user must send message to create new session (lazy creation)
        }
      } catch (error) {
        const errorMessage =
          error instanceof Error
            ? error.message
            : "Errore durante l'eliminazione della sessione";
        console.error('Failed to delete session:', error);
        throw new Error(errorMessage);
      }
    },
    [sessions, currentSession, clearMessages]
  );

  /**
   * Mark a session as used (has messages) to enable edit/delete actions
   * This is called when AI completes a response, creating a complete Q&A pair
   */
  const markSessionAsUsed = useCallback(
    (sessionId: string): void => {
      console.log(
        '📊 [SESSION_DEBUG] Marking session as used (complete Q&A pair):',
        sessionId
      );

      // Update sessions list - increment by 2 to represent complete Q&A pair
      setSessions(prevSessions =>
        prevSessions.map(s =>
          s.id === sessionId
            ? { ...s, message_count: Math.max((s.message_count || 0) + 2, 2) } // Ensure at least 2 for complete Q&A
            : s
        )
      );

      // Update current session if it matches
      if (currentSession?.id === sessionId) {
        setCurrentSession(prev =>
          prev
            ? {
                ...prev,
                message_count: Math.max((prev.message_count || 0) + 2, 2), // Ensure at least 2 for complete Q&A
              }
            : prev
        );
      }

      console.log(
        '✅ [SESSION_DEBUG] Session marked as having complete Q&A pair, edit/delete now enabled'
      );
    },
    [currentSession]
  );

  /**
   * Clean up empty duplicate sessions (keep only one empty session)
   */
  const cleanupEmptySessions = useCallback(async (): Promise<void> => {
    console.log('🧹 [CLEANUP] Starting empty session cleanup...');

    const emptySessions = sessions.filter(s => isSessionEmpty(s));
    console.log(`🧹 [CLEANUP] Found ${emptySessions.length} empty sessions`);

    if (emptySessions.length > 1) {
      // Keep the most recent empty session, delete the rest
      const sessionsToDelete = emptySessions.slice(1); // Skip the first (most recent)
      console.log(
        `🧹 [CLEANUP] Deleting ${sessionsToDelete.length} duplicate empty sessions`
      );

      for (const session of sessionsToDelete) {
        try {
          console.log(`🗑️ [CLEANUP] Deleting empty session: ${session.id}`);
          await deleteSession(session.id);
        } catch (error) {
          console.warn(
            `⚠️ [CLEANUP] Failed to delete session ${session.id}:`,
            error
          );
        }
      }

      console.log('✅ [CLEANUP] Empty session cleanup completed');
    } else {
      console.log('✅ [CLEANUP] No duplicate empty sessions found');
    }
  }, [sessions, isSessionEmpty, deleteSession]);

  /**
   * Initialize session on mount - handles page refresh persistence
   */
  const initializeSession = useCallback(async (): Promise<Message[]> => {
    console.log('🚀 useChatSessions: initializeSession called');
    console.log(
      '🔒 Checking local initialization lock:',
      initializationRef.current
    );
    console.log(
      '🌍 Checking global initialization lock:',
      globalInitializationInProgress
    );

    if (initializationRef.current || globalInitializationInProgress) {
      console.log(
        '⚠️ Initialize session already called (local or global), skipping'
      );
      return [];
    }

    // Set both locks
    initializationRef.current = true;
    globalInitializationInProgress = true;

    try {
      console.log('🔐 Authentication check:', apiClient.isAuthenticated());

      // Load all sessions first to show in sidebar
      console.log('📊 Loading all sessions...');
      await loadSessions();

      // CRITICAL FIX: Wait for sessions state to update after loadSessions
      // We need to access the fresh sessions data, not the stale state
      console.log('⏳ Waiting for sessions state to update...');

      // Get fresh session data by calling the API again (loadSessions already cached it)
      const freshSessionList = await apiClient.getUserSessions();
      console.log(
        '🔍 Fresh session list from API:',
        freshSessionList?.length || 0,
        'sessions'
      );

      const formattedFreshSessions: ChatSession[] = freshSessionList.map(
        session => ({
          id: session.session_id,
          name: session.name || 'Nuova Conversazione',
          created_at: session.created_at || new Date().toISOString(),
          updated_at: session.created_at,
          message_count: undefined, // Will be determined by checking actual history
          isActive: false,
          token: session.token?.access_token,
        })
      );

      // DEV-003 FIX: Always clear localStorage session on initialization
      // After sign-in, always show empty chat - user must explicitly click a chat from sidebar
      console.log(
        '🧹 Clearing any saved session from localStorage (DEV-003 fix)'
      );
      if (typeof window !== 'undefined') {
        localStorage.removeItem('current_session_id');
        localStorage.removeItem('current_session_token');
      }

      // Always set currentSession to null - show empty chat state
      console.log(
        '🎯 Setting currentSession to null - empty chat state (DEV-003 fix)'
      );
      setCurrentSession(null);

      // Clear messages to show empty state
      console.log('🧹 Clearing messages to show empty chat (DEV-003 fix)');
      clearMessages();

      // Session will be created lazily when user sends first message
      console.log(
        '✅ Initialization complete - showing empty chat placeholder'
      );
      console.log(
        '📋 Sessions loaded in sidebar:',
        formattedFreshSessions.length,
        'sessions'
      );
      console.log(
        '🎯 User can click a chat from sidebar to load it, or send a message to create new session'
      );

      return []; // No session active, no messages - empty state
    } catch (error) {
      console.error('❌ Failed to initialize session:', error);
      console.log('💥 Setting history error');
      setHistoryError(
        error instanceof Error
          ? error.message
          : "Errore durante l'inizializzazione"
      );
      return [];
    } finally {
      // Release global lock after completion or failure
      console.log('🔓 Releasing global initialization lock');
      globalInitializationInProgress = false;
    }
  }, [loadSessions, clearMessages]);

  // Initialize sessions on mount - CRITICAL FIX: Prevent multiple initializations
  useEffect(() => {
    if (typeof window !== 'undefined' && apiClient.isAuthenticated()) {
      console.log('🎯 useEffect triggered for session initialization');
      console.log('🔍 initializationRef.current:', initializationRef.current);

      // Double-check initialization hasn't already started
      if (!initializationRef.current) {
        console.log('✅ Starting session initialization from useEffect');
        initializeSession().catch(console.error);
      } else {
        console.log('⏭️ Skipping session initialization - already started');
      }
    }
  }, []); // Empty dependency array for mount-only execution

  return {
    // Session list management
    sessions,
    isLoadingSessions,
    sessionsError,

    // Current session management
    currentSession,
    isLoadingHistory,
    historyError,

    // Actions
    loadSessions,
    createNewSession,
    startNewChat,
    switchToSession,
    loadSessionHistory,
    updateSessionName,
    deleteSession,

    // Session persistence
    initializeSession,

    // Helper functions
    isSessionEmpty,
    hasCompleteQAPair,
    markSessionAsUsed,
    cleanupEmptySessions,
  };
}

// Context setup for shared session state
type ChatSessionsContextType = ReturnType<typeof useChatSessions>;
const ChatSessionsContext = createContext<ChatSessionsContextType | null>(null);

/**
 * Provider component for shared chat sessions state
 * CRITICAL: This ensures only ONE instance of useChatSessions exists,
 * preventing duplicate session creation across multiple components
 */
export function ChatSessionsProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const chatSessionsValue = useChatSessions();

  return React.createElement(
    ChatSessionsContext.Provider,
    { value: chatSessionsValue },
    children
  );
}

/**
 * Hook to access shared chat sessions state from context
 * Use this instead of useChatSessions() directly in components
 */
export function useSharedChatSessions(): ChatSessionsContextType {
  const context = useContext(ChatSessionsContext);
  if (!context) {
    throw new Error(
      'useSharedChatSessions must be used within a ChatSessionsProvider'
    );
  }
  return context;
}
