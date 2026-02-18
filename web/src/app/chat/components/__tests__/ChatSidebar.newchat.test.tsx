/**
 * @jest-environment jsdom
 *
 * TDD Tests for DEV-FE-003: Lazy Session Creation
 *
 * UPDATED: Tests now verify LAZY session creation behavior:
 * 1. "New Chat" button should NOT create session immediately - only clears UI state
 * 2. Session is created LAZILY when user sends first message
 * 3. No empty sessions appear in sidebar (prevents clutter)
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatSidebar } from '../ChatSidebar';

// Mock the hooks
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

describe('ChatSidebar - Lazy Session Creation (DEV-FE-003)', () => {
  const mockStartNewChat = jest.fn();
  const mockCreateNewSession = jest.fn();
  const mockClearMessages = jest.fn();
  const mockLoadSession = jest.fn();
  const mockSwitchToSession = jest.fn();
  const mockUpdateSessionName = jest.fn();
  const mockDeleteSession = jest.fn();
  const mockIsSessionEmpty = jest.fn().mockReturnValue(false);
  const mockHasCompleteQAPair = jest.fn().mockReturnValue(true);
  const mockCleanupEmptySessions = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();

    // Mock a successful session creation (called lazily from message send)
    mockCreateNewSession.mockResolvedValue({
      id: 'new-session-123',
      name: 'Nuova conversazione',
      created_at: new Date().toISOString(),
      isActive: true,
      message_count: 0,
      token: 'mock-token-123',
    });

    mockUseSharedChatSessions.mockReturnValue({
      sessions: [],
      currentSession: null,
      isLoadingSessions: false,
      sessionsError: null,
      isLoadingHistory: false,
      historyError: null,
      loadSessions: jest.fn(),
      createNewSession: mockCreateNewSession,
      startNewChat: mockStartNewChat, // NEW: Lazy creation function
      switchToSession: mockSwitchToSession,
      loadSessionHistory: jest.fn(),
      updateSessionName: mockUpdateSessionName,
      deleteSession: mockDeleteSession,
      initializeSession: jest.fn(),
      isSessionEmpty: mockIsSessionEmpty,
      hasCompleteQAPair: mockHasCompleteQAPair,
      markSessionAsUsed: jest.fn(),
      cleanupEmptySessions: mockCleanupEmptySessions,
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
  });

  describe('✅ Lazy Creation Behavior', () => {
    it('should call startNewChat() when "New Chat" button is clicked (NOT createNewSession)', async () => {
      render(<ChatSidebar />);

      const newChatButton = screen.getByRole('button', {
        name: /Inizia nuova conversazione/i,
      });
      fireEvent.click(newChatButton);

      await waitFor(
        () => {
          // NEW BEHAVIOR: Should call startNewChat (clears UI only)
          expect(mockStartNewChat).toHaveBeenCalledTimes(1);
          // Should NOT create session immediately
          expect(mockCreateNewSession).not.toHaveBeenCalled();
        },
        { timeout: 3000 }
      );
    });

    it('should NOT create session immediately - only clear UI state', async () => {
      render(<ChatSidebar />);

      const newChatButton = screen.getByRole('button', {
        name: /Inizia nuova conversazione/i,
      });
      fireEvent.click(newChatButton);

      await waitFor(
        () => {
          // NEW BEHAVIOR: No session created yet
          expect(mockCreateNewSession).not.toHaveBeenCalled();
          // UI state cleared via startNewChat
          expect(mockStartNewChat).toHaveBeenCalledTimes(1);
        },
        { timeout: 3000 }
      );
    });

    it('should clear UI state multiple times if "New Chat" clicked multiple times', async () => {
      // Start with one existing session
      mockUseSharedChatSessions.mockReturnValue({
        sessions: [
          {
            id: 'session-1',
            name: 'First chat',
            created_at: new Date().toISOString(),
            isActive: false,
            message_count: 2,
          },
        ],
        currentSession: {
          id: 'session-1',
          name: 'First chat',
          created_at: new Date().toISOString(),
          isActive: true,
          message_count: 2,
        },
        isLoadingSessions: false,
        sessionsError: null,
        isLoadingHistory: false,
        historyError: null,
        loadSessions: jest.fn(),
        createNewSession: mockCreateNewSession,
        startNewChat: mockStartNewChat,
        switchToSession: mockSwitchToSession,
        loadSessionHistory: jest.fn(),
        updateSessionName: mockUpdateSessionName,
        deleteSession: mockDeleteSession,
        initializeSession: jest.fn(),
        isSessionEmpty: mockIsSessionEmpty,
        hasCompleteQAPair: mockHasCompleteQAPair,
        markSessionAsUsed: jest.fn(),
        cleanupEmptySessions: mockCleanupEmptySessions,
      } as any);

      render(<ChatSidebar />);

      const newChatButton = screen.getByRole('button', {
        name: /Inizia nuova conversazione/i,
      });

      // Click twice
      fireEvent.click(newChatButton);
      fireEvent.click(newChatButton);

      await waitFor(
        () => {
          // NEW BEHAVIOR: startNewChat called twice, no sessions created
          expect(mockStartNewChat).toHaveBeenCalledTimes(2);
          expect(mockCreateNewSession).not.toHaveBeenCalled();
        },
        { timeout: 3000 }
      );
    });

    it('should call startNewChat which clears UI (session created later on message send)', async () => {
      render(<ChatSidebar />);

      const newChatButton = screen.getByRole('button', {
        name: /Inizia nuova conversazione/i,
      });
      fireEvent.click(newChatButton);

      await waitFor(
        () => {
          // NEW BEHAVIOR: Only UI clearing, no immediate session creation
          expect(mockStartNewChat).toHaveBeenCalled();
          expect(mockCreateNewSession).not.toHaveBeenCalled();
          // Session will be created when user sends first message (tested elsewhere)
        },
        { timeout: 3000 }
      );
    });
  });

  describe('Acceptance Criteria Verification', () => {
    it('ACCEPTANCE: User clicks "New Chat" → UI cleared (NO session created yet)', async () => {
      render(<ChatSidebar />);

      const newChatButton = screen.getByRole('button', {
        name: /Inizia nuova conversazione/i,
      });
      fireEvent.click(newChatButton);

      await waitFor(() => {
        // NEW BEHAVIOR: UI cleared via startNewChat, session NOT created
        expect(mockStartNewChat).toHaveBeenCalledTimes(1);
        expect(mockCreateNewSession).not.toHaveBeenCalled();
      });
    });

    it('ACCEPTANCE: After clearing UI, session list in sidebar stays unchanged', async () => {
      // Start with existing session
      const existingSession = {
        id: 'session-1',
        name: 'Previous conversation',
        created_at: new Date().toISOString(),
        isActive: true,
        message_count: 2,
      };

      mockUseSharedChatSessions.mockReturnValue({
        sessions: [existingSession],
        currentSession: existingSession,
        isLoadingSessions: false,
        sessionsError: null,
        isLoadingHistory: false,
        historyError: null,
        loadSessions: jest.fn(),
        createNewSession: mockCreateNewSession,
        startNewChat: mockStartNewChat,
        switchToSession: mockSwitchToSession,
        loadSessionHistory: jest.fn(),
        updateSessionName: mockUpdateSessionName,
        deleteSession: mockDeleteSession,
        initializeSession: jest.fn(),
        isSessionEmpty: mockIsSessionEmpty,
        hasCompleteQAPair: mockHasCompleteQAPair,
        markSessionAsUsed: jest.fn(),
        cleanupEmptySessions: mockCleanupEmptySessions,
      } as any);

      render(<ChatSidebar />);

      // Session should be visible before clicking "New Chat"
      expect(screen.getByText('Previous conversation')).toBeInTheDocument();

      const newChatButton = screen.getByRole('button', {
        name: /Inizia nuova conversazione/i,
      });
      fireEvent.click(newChatButton);

      await waitFor(() => {
        // UI cleared but NO new empty session added to sidebar
        expect(mockStartNewChat).toHaveBeenCalled();
        expect(mockCreateNewSession).not.toHaveBeenCalled();
      });

      // Previous session still visible (no empty session added)
      expect(screen.getByText('Previous conversation')).toBeInTheDocument();
    });

    it('ACCEPTANCE: User clicks "New Chat" multiple times → No empty sessions created', async () => {
      render(<ChatSidebar />);

      const newChatButton = screen.getByRole('button', {
        name: /Inizia nuova conversazione/i,
      });

      // Click multiple times
      fireEvent.click(newChatButton);
      fireEvent.click(newChatButton);
      fireEvent.click(newChatButton);

      await waitFor(() => {
        // NEW BEHAVIOR: startNewChat called 3 times, zero sessions created
        expect(mockStartNewChat).toHaveBeenCalledTimes(3);
        expect(mockCreateNewSession).not.toHaveBeenCalled();
      });
    });

    it('ACCEPTANCE: Multiple sessions remain visible (from past conversations with messages)', async () => {
      // Multiple sessions with messages (created when user sent messages)
      const session1 = {
        id: 'session-1',
        name: 'First question',
        created_at: new Date().toISOString(),
        isActive: false,
        message_count: 2,
      };

      const session2 = {
        id: 'session-2',
        name: 'Second question',
        created_at: new Date().toISOString(),
        isActive: true,
        message_count: 4,
      };

      mockUseSharedChatSessions.mockReturnValue({
        sessions: [session2, session1], // Newest first
        currentSession: session2,
        isLoadingSessions: false,
        sessionsError: null,
        isLoadingHistory: false,
        historyError: null,
        loadSessions: jest.fn(),
        createNewSession: mockCreateNewSession,
        startNewChat: mockStartNewChat,
        switchToSession: mockSwitchToSession,
        loadSessionHistory: jest.fn(),
        updateSessionName: mockUpdateSessionName,
        deleteSession: mockDeleteSession,
        initializeSession: jest.fn(),
        isSessionEmpty: mockIsSessionEmpty,
        hasCompleteQAPair: mockHasCompleteQAPair,
        markSessionAsUsed: jest.fn(),
        cleanupEmptySessions: mockCleanupEmptySessions,
      } as any);

      render(<ChatSidebar />);

      // Both sessions should be visible (both have messages)
      expect(screen.getByText('First question')).toBeInTheDocument();
      expect(screen.getByText('Second question')).toBeInTheDocument();

      // Session 2 should be active (indicator visible)
      const activeIndicators = screen.getAllByLabelText('Sessione attiva');
      expect(activeIndicators).toHaveLength(1);
    });
  });
});
