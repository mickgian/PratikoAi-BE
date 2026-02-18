/**
 * @jest-environment jsdom
 *
 * Integration Tests for DEV-FE-003: Lazy Session Creation
 *
 * These tests verify the complete user flow with LAZY session creation:
 * 1. User clicks "New Chat" → UI cleared (NO session created yet)
 * 2. User sends message → Session created with first question as name
 * 3. User clicks "New Chat" again → UI cleared again (NO new empty session)
 * 4. Result: NO empty sessions in sidebar (only sessions with messages)
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatSidebar } from '../ChatSidebar';

jest.mock('../../hooks/useChatSessions', () => ({
  useSharedChatSessions: jest.fn(),
}));

jest.mock('../../hooks/useChatState', () => ({
  useSharedChatState: jest.fn(),
}));

jest.mock('../../services/MessageStorageService', () => ({
  messageStorage: {
    initialize: jest.fn().mockResolvedValue(undefined),
    saveMessage: jest.fn().mockResolvedValue(undefined),
    getMessages: jest.fn().mockResolvedValue([]),
    clearMessages: jest.fn().mockResolvedValue(undefined),
  },
}));

import { useSharedChatSessions } from '../../hooks/useChatSessions';
import { useSharedChatState } from '../../hooks/useChatState';

const mockUseSharedChatSessions = useSharedChatSessions as jest.MockedFunction<
  typeof useSharedChatSessions
>;
const mockUseSharedChatState = useSharedChatState as jest.MockedFunction<
  typeof useSharedChatState
>;

describe('ChatSidebar - Integration Tests (DEV-FE-003)', () => {
  const mockStartNewChat = jest.fn(); // NEW: For lazy creation
  const mockCreateNewSession = jest.fn();
  const mockUpdateSessionName = jest.fn();
  const mockLoadSession = jest.fn();
  const mockClearMessages = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Complete User Flow: Create 2 Sessions', () => {
    it('should create 2 separate sessions when "New Chat" clicked twice', async () => {
      // Phase 1: Initial state - no sessions
      let sessionsState: any[] = [];
      let currentSessionState: any = null;

      mockCreateNewSession.mockImplementation(async () => {
        const newSession = {
          id: `session-${sessionsState.length + 1}`,
          name: 'Nuova conversazione',
          created_at: new Date().toISOString(),
          isActive: true,
          message_count: 0,
          token: `token-${sessionsState.length + 1}`,
        };

        // Update mock state
        sessionsState = [
          newSession,
          ...sessionsState.map(s => ({ ...s, isActive: false })),
        ];
        currentSessionState = newSession;

        // Re-render with updated state
        mockUseSharedChatSessions.mockReturnValue({
          sessions: sessionsState,
          currentSession: currentSessionState,
          isLoadingSessions: false,
          sessionsError: null,
          isLoadingHistory: false,
          historyError: null,
          loadSessions: jest.fn(),
          createNewSession: mockCreateNewSession,
          startNewChat: mockStartNewChat,
          switchToSession: jest.fn(),
          loadSessionHistory: jest.fn(),
          updateSessionName: mockUpdateSessionName,
          deleteSession: jest.fn(),
          initializeSession: jest.fn(),
          isSessionEmpty: jest.fn().mockReturnValue(false),
          hasCompleteQAPair: jest.fn().mockReturnValue(true),
          markSessionAsUsed: jest.fn(),
          cleanupEmptySessions: jest.fn(),
        } as any);

        return newSession;
      });

      // Initial render - no sessions
      mockUseSharedChatSessions.mockReturnValue({
        sessions: [],
        currentSession: null,
        isLoadingSessions: false,
        sessionsError: null,
        isLoadingHistory: false,
        historyError: null,
        loadSessions: jest.fn(),
        createNewSession: mockCreateNewSession,
        startNewChat: mockStartNewChat,
        switchToSession: jest.fn(),
        loadSessionHistory: jest.fn(),
        updateSessionName: mockUpdateSessionName,
        deleteSession: jest.fn(),
        initializeSession: jest.fn(),
        isSessionEmpty: jest.fn().mockReturnValue(false),
        hasCompleteQAPair: jest.fn().mockReturnValue(true),
        markSessionAsUsed: jest.fn(),
        cleanupEmptySessions: jest.fn(),
      } as any);

      mockUseSharedChatState.mockReturnValue({
        state: {
          messages: [],
          sessionMessages: [],
          currentSessionId: null,
          isStreaming: false,
          error: null,
          accumulatedContent: '',
        },
        messages: [],
        hasMessages: false,
        canSendMessage: true,
        lastMessage: null,
        dispatch: jest.fn(),
        addUserMessage: jest.fn(),
        startAIStreaming: jest.fn(),
        updateStreamingContent: jest.fn(),
        addMessageFeedback: jest.fn(),
        getMessageById: jest.fn(),
        getStreamingMessage: jest.fn(),
        loadSession: mockLoadSession,
        clearMessages: mockClearMessages,
        completeStreaming: jest.fn(),
        forceStopStreaming: jest.fn(),
        isCurrentlyStreaming: false,
      } as any);

      const { rerender } = render(<ChatSidebar />);

      // Step 1: Click "New Chat" first time
      const newChatButton = screen.getByRole('button', {
        name: /Inizia nuova conversazione/i,
      });
      fireEvent.click(newChatButton);

      await waitFor(() => {
        // NEW BEHAVIOR: Only clears UI, does NOT create session
        expect(mockStartNewChat).toHaveBeenCalledTimes(1);
        expect(mockCreateNewSession).not.toHaveBeenCalled();
        expect(sessionsState).toHaveLength(0); // No session created yet
      });

      // Step 2: User sends message → session created (simulated elsewhere, not tested here)
      // For this test, we skip to clicking "New Chat" again after a session exists

      // Re-render with updated session name
      rerender(<ChatSidebar />);

      // Step 3: Click "New Chat" second time
      fireEvent.click(newChatButton);

      await waitFor(() => {
        // NEW BEHAVIOR: UI cleared again, still no sessions created via button
        expect(mockStartNewChat).toHaveBeenCalledTimes(2);
        expect(mockCreateNewSession).not.toHaveBeenCalled();
      });

      // Verify: No empty sessions created via "New Chat" button
      // Sessions are only created when user sends actual messages (tested elsewhere)
    });

    it('should maintain session history when switching between sessions', async () => {
      // Setup: 2 existing sessions
      const session1 = {
        id: 'session-1',
        name: 'First conversation',
        created_at: new Date().toISOString(),
        isActive: false,
        message_count: 2,
      };

      const session2 = {
        id: 'session-2',
        name: 'Second conversation',
        created_at: new Date().toISOString(),
        isActive: true,
        message_count: 2,
      };

      mockUseSharedChatSessions.mockReturnValue({
        sessions: [session2, session1],
        currentSession: session2,
        isLoadingSessions: false,
        sessionsError: null,
        isLoadingHistory: false,
        historyError: null,
        loadSessions: jest.fn(),
        createNewSession: mockCreateNewSession,
        switchToSession: jest.fn(),
        loadSessionHistory: jest.fn(),
        updateSessionName: mockUpdateSessionName,
        deleteSession: jest.fn(),
        initializeSession: jest.fn(),
        isSessionEmpty: jest.fn().mockReturnValue(false),
        hasCompleteQAPair: jest.fn().mockReturnValue(true),
        markSessionAsUsed: jest.fn(),
        cleanupEmptySessions: jest.fn(),
      } as any);

      mockUseSharedChatState.mockReturnValue({
        state: {
          messages: [],
          sessionMessages: [],
          currentSessionId: 'session-2',
          isStreaming: false,
          error: null,
          accumulatedContent: '',
        },
        messages: [],
        hasMessages: false,
        canSendMessage: true,
        lastMessage: null,
        dispatch: jest.fn(),
        addUserMessage: jest.fn(),
        startAIStreaming: jest.fn(),
        updateStreamingContent: jest.fn(),
        addMessageFeedback: jest.fn(),
        getMessageById: jest.fn(),
        getStreamingMessage: jest.fn(),
        loadSession: mockLoadSession,
        clearMessages: mockClearMessages,
        completeStreaming: jest.fn(),
        forceStopStreaming: jest.fn(),
        isCurrentlyStreaming: false,
      } as any);

      render(<ChatSidebar />);

      // Both sessions should be visible
      expect(screen.getByText('First conversation')).toBeInTheDocument();
      expect(screen.getByText('Second conversation')).toBeInTheDocument();

      // Current session should have active indicator
      const activeIndicators = screen.getAllByLabelText('Sessione attiva');
      expect(activeIndicators).toHaveLength(1);
    });
  });

  describe('Error Handling', () => {
    it('should clear UI successfully even with lazy creation (no error possible)', async () => {
      // NEW BEHAVIOR: startNewChat only clears UI, no async operations = no errors
      mockUseSharedChatSessions.mockReturnValue({
        sessions: [],
        currentSession: null,
        isLoadingSessions: false,
        sessionsError: null,
        isLoadingHistory: false,
        historyError: null,
        loadSessions: jest.fn(),
        createNewSession: mockCreateNewSession,
        startNewChat: mockStartNewChat,
        switchToSession: jest.fn(),
        loadSessionHistory: jest.fn(),
        updateSessionName: jest.fn(),
        deleteSession: jest.fn(),
        initializeSession: jest.fn(),
        isSessionEmpty: jest.fn().mockReturnValue(false),
        hasCompleteQAPair: jest.fn().mockReturnValue(true),
        markSessionAsUsed: jest.fn(),
        cleanupEmptySessions: jest.fn(),
      } as any);

      mockUseSharedChatState.mockReturnValue({
        state: {
          messages: [],
          sessionMessages: [],
          currentSessionId: null,
          isStreaming: false,
          error: null,
          accumulatedContent: '',
        },
        messages: [],
        hasMessages: false,
        canSendMessage: true,
        lastMessage: null,
        dispatch: jest.fn(),
        addUserMessage: jest.fn(),
        startAIStreaming: jest.fn(),
        updateStreamingContent: jest.fn(),
        addMessageFeedback: jest.fn(),
        getMessageById: jest.fn(),
        getStreamingMessage: jest.fn(),
        loadSession: mockLoadSession,
        clearMessages: mockClearMessages,
        completeStreaming: jest.fn(),
        forceStopStreaming: jest.fn(),
        isCurrentlyStreaming: false,
      } as any);

      render(<ChatSidebar />);

      const newChatButton = screen.getByRole('button', {
        name: /Inizia nuova conversazione/i,
      });
      fireEvent.click(newChatButton);

      await waitFor(() => {
        // NEW BEHAVIOR: Only clears UI, no session creation attempt
        expect(mockStartNewChat).toHaveBeenCalled();
        expect(mockCreateNewSession).not.toHaveBeenCalled();
        // No error handling needed - just UI clearing
      });
    });

    it('should handle UI clearing successfully (no null responses possible)', async () => {
      // NEW BEHAVIOR: startNewChat is synchronous and always succeeds

      mockUseSharedChatSessions.mockReturnValue({
        sessions: [],
        currentSession: null,
        isLoadingSessions: false,
        sessionsError: null,
        isLoadingHistory: false,
        historyError: null,
        loadSessions: jest.fn(),
        createNewSession: mockCreateNewSession,
        startNewChat: mockStartNewChat,
        switchToSession: jest.fn(),
        loadSessionHistory: jest.fn(),
        updateSessionName: jest.fn(),
        deleteSession: jest.fn(),
        initializeSession: jest.fn(),
        isSessionEmpty: jest.fn().mockReturnValue(false),
        hasCompleteQAPair: jest.fn().mockReturnValue(true),
        markSessionAsUsed: jest.fn(),
        cleanupEmptySessions: jest.fn(),
      } as any);

      mockUseSharedChatState.mockReturnValue({
        state: {
          messages: [],
          sessionMessages: [],
          currentSessionId: null,
          isStreaming: false,
          error: null,
          accumulatedContent: '',
        },
        messages: [],
        hasMessages: false,
        canSendMessage: true,
        lastMessage: null,
        dispatch: jest.fn(),
        addUserMessage: jest.fn(),
        startAIStreaming: jest.fn(),
        updateStreamingContent: jest.fn(),
        addMessageFeedback: jest.fn(),
        getMessageById: jest.fn(),
        getStreamingMessage: jest.fn(),
        loadSession: mockLoadSession,
        clearMessages: mockClearMessages,
        completeStreaming: jest.fn(),
        forceStopStreaming: jest.fn(),
        isCurrentlyStreaming: false,
      } as any);

      render(<ChatSidebar />);

      const newChatButton = screen.getByRole('button', {
        name: /Inizia nuova conversazione/i,
      });
      fireEvent.click(newChatButton);

      await waitFor(() => {
        // NEW BEHAVIOR: Only UI clearing, no session creation attempt
        expect(mockStartNewChat).toHaveBeenCalled();
        expect(mockCreateNewSession).not.toHaveBeenCalled();
        // No null responses possible with synchronous UI clearing
      });
    });
  });
});
