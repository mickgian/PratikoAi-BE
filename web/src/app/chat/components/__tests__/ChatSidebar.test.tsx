/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatSidebar } from '../ChatSidebar';

// Mock the hooks - use the actual hook names from the component
jest.mock('../../hooks/useChatSessions', () => ({
  useSharedChatSessions: jest.fn(),
}));

jest.mock('../../hooks/useChatState', () => ({
  useSharedChatState: jest.fn(),
}));

// Mock Message Storage Service to avoid indexedDB issues
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

describe('ChatSidebar - "Nuova chat" button behavior (DEV-003) - Lazy Session Creation', () => {
  const mockStartNewChat = jest.fn();
  const mockCreateNewSession = jest.fn();
  const mockClearMessages = jest.fn();
  const mockLoadSession = jest.fn();
  const mockDeleteSession = jest.fn();
  const mockSwitchToSession = jest.fn();
  const mockUpdateSessionName = jest.fn();
  const mockIsSessionEmpty = jest.fn().mockReturnValue(false);
  const mockHasCompleteQAPair = jest.fn().mockReturnValue(true);
  const mockCompleteStreaming = jest.fn();
  const mockForceStopStreaming = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();

    // Mock successful session creation (used for lazy creation on message send)
    mockCreateNewSession.mockResolvedValue({
      id: 'new-session-123',
      name: 'Nuova conversazione',
      created_at: new Date().toISOString(),
      isActive: true,
      message_count: 0,
      token: 'mock-token-123',
    });

    // Mock useSharedChatSessions with all required properties including startNewChat
    mockUseSharedChatSessions.mockReturnValue({
      sessions: [
        {
          id: 'session-1',
          name: 'Test Session',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          isActive: true,
        },
      ],
      currentSession: {
        id: 'session-1',
        name: 'Test Session',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        isActive: true,
      },
      isLoadingSessions: false,
      sessionsError: null,
      createNewSession: mockCreateNewSession,
      startNewChat: mockStartNewChat, // NEW: For lazy creation
      switchToSession: mockSwitchToSession,
      updateSessionName: mockUpdateSessionName,
      deleteSession: mockDeleteSession,
      isSessionEmpty: mockIsSessionEmpty,
      hasCompleteQAPair: mockHasCompleteQAPair,
      refreshSessions: jest.fn(),
    } as any);

    // Mock useSharedChatState with all required properties
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
      completeStreaming: mockCompleteStreaming,
      forceStopStreaming: mockForceStopStreaming,
      isCurrentlyStreaming: false,
    } as any);
  });

  it('should call startNewChat() when "Nuova chat" button is clicked (NOT createNewSession)', async () => {
    render(<ChatSidebar />);

    // Find button by text (case-sensitive: "Nuova Chat" not "Nuova chat")
    const newChatButton = screen.getByText(/Nuova Chat/i);
    fireEvent.click(newChatButton);

    await waitFor(() => {
      // NEW BEHAVIOR: Calls startNewChat (clears UI only), NOT createNewSession
      expect(mockStartNewChat).toHaveBeenCalledTimes(1);
      expect(mockCreateNewSession).not.toHaveBeenCalled();
    });
  });

  it('should NOT create session or load session immediately when button clicked', async () => {
    render(<ChatSidebar />);

    const newChatButton = screen.getByText(/Nuova Chat/i);
    fireEvent.click(newChatButton);

    await waitFor(() => {
      // NEW BEHAVIOR: Only clears UI, no session creation or loading
      expect(mockStartNewChat).toHaveBeenCalledTimes(1);
      expect(mockCreateNewSession).not.toHaveBeenCalled();
      expect(mockLoadSession).not.toHaveBeenCalled();
    });
  });

  it('should only clear UI state - no empty session shown in sidebar', async () => {
    render(<ChatSidebar />);

    const newChatButton = screen.getByText(/Nuova Chat/i);
    fireEvent.click(newChatButton);

    await waitFor(() => {
      // NEW BEHAVIOR: UI cleared, no new session created
      expect(mockStartNewChat).toHaveBeenCalledTimes(1);
      expect(mockCreateNewSession).not.toHaveBeenCalled();
      // Session will be created when user sends first message (tested in integration tests)
    });
  });
});
