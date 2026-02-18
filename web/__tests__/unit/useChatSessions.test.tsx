import { renderHook, act } from '@testing-library/react';
import { useChatSessions } from '@/app/chat/hooks/useChatSessions';
import { useSharedChatState } from '@/app/chat/hooks/useChatState';
import apiClient from '@/lib/api';

// Mock the API client
jest.mock('@/lib/api', () => {
  const mockClient = {
    isAuthenticated: jest.fn(),
    getUserSessions: jest.fn(),
    createSession: jest.fn(),
    getChatHistory: jest.fn(),
    getCurrentSession: jest.fn(),
    setCurrentSession: jest.fn(),
    updateSessionName: jest.fn(),
    deleteSession: jest.fn(),
  };
  return {
    __esModule: true,
    default: mockClient,
    apiClient: mockClient,
  };
});

// Mock the useChatState hook
jest.mock('@/app/chat/hooks/useChatState', () => ({
  useSharedChatState: jest.fn(),
}));

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;
const mockUseSharedChatState = useSharedChatState as jest.MockedFunction<
  typeof useSharedChatState
>;

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

// Mock URL search params
const mockURLSearchParams = jest.fn();
Object.defineProperty(window, 'URLSearchParams', {
  value: mockURLSearchParams,
});

describe.skip('useChatSessions', () => {
  const mockLoadSession = jest.fn();
  const mockClearMessages = jest.fn();

  const mockSessionResponse = {
    session_id: 'session-1',
    name: 'Test Session',
    created_at: '2023-01-01T00:00:00Z',
    token: {
      access_token: 'test-token-123',
      token_type: 'Bearer',
      expires_at: '2023-01-01T01:00:00Z',
    },
  };

  const mockChatHistory = {
    messages: [
      { role: 'user' as const, content: 'Hello' },
      { role: 'assistant' as const, content: 'Hi there!' },
    ],
  };

  beforeEach(() => {
    jest.clearAllMocks();

    // Setup default mocks
    mockUseSharedChatState.mockReturnValue({
      loadSession: mockLoadSession,
      clearMessages: mockClearMessages,
    } as any);

    // Mock API client to prevent initialization during tests
    mockApiClient.isAuthenticated.mockReturnValue(false); // Start with false to prevent useEffect
    mockApiClient.getUserSessions.mockResolvedValue([mockSessionResponse]);
    mockApiClient.createSession.mockResolvedValue(mockSessionResponse);
    mockApiClient.getChatHistory.mockResolvedValue(mockChatHistory);
    mockApiClient.getCurrentSession.mockReturnValue({
      sessionId: 'session-1',
      sessionToken: 'test-token-123',
    });

    mockLocalStorage.getItem.mockReturnValue(null);
    mockURLSearchParams.mockImplementation(() => ({
      get: jest.fn().mockReturnValue(null),
    }));

    // Reset any global state
    global.console.log = jest.fn();
    global.console.error = jest.fn();
    global.console.warn = jest.fn();
  });

  // Helper to render hook without complex context for most tests
  const renderHookDirectly = () => renderHook(() => useChatSessions());

  describe('initialization', () => {
    test('should initialize with empty state', () => {
      const { result } = renderHookDirectly();

      console.log('Result.current:', result.current);
      console.log('Result.current type:', typeof result.current);

      expect(result.current).not.toBeNull();
      expect(result.current.sessions).toEqual([]);
      expect(result.current.currentSession).toBeNull();
      expect(result.current.isLoadingSessions).toBe(false);
      expect(result.current.isLoadingHistory).toBe(false);
      expect(result.current.sessionsError).toBeNull();
      expect(result.current.historyError).toBeNull();
    });

    test('should provide helper functions', () => {
      const { result } = renderHookDirectly();

      expect(typeof result.current.isSessionEmpty).toBe('function');
      expect(typeof result.current.hasCompleteQAPair).toBe('function');
      expect(typeof result.current.loadSessions).toBe('function');
      expect(typeof result.current.createNewSession).toBe('function');
    });
  });

  describe('loadSessions', () => {
    test('should load sessions from API successfully', async () => {
      const { result } = renderHookDirectly();

      await act(async () => {
        await result.current.loadSessions();
      });

      expect(mockApiClient.getUserSessions).toHaveBeenCalled();
      expect(result.current.sessions).toHaveLength(1);
      expect(result.current.sessions[0]).toMatchObject({
        id: 'session-1',
        name: 'Test Session',
        isActive: false,
      });
    });

    test('should handle API errors gracefully', async () => {
      mockApiClient.getUserSessions.mockRejectedValue(new Error('API Error'));

      const { result } = renderHookDirectly();

      await act(async () => {
        await result.current.loadSessions();
      });

      expect(result.current.sessionsError).toBe('API Error');
      expect(result.current.sessions).toEqual([]);
    });

    test('should set loading state during API call', async () => {
      let resolveApiCall: () => void;
      const apiPromise = new Promise<any>(resolve => {
        resolveApiCall = () => resolve([mockSessionResponse]);
      });
      mockApiClient.getUserSessions.mockReturnValue(apiPromise);

      const { result } = renderHookDirectly();

      const loadPromise = act(async () => {
        await result.current.loadSessions();
      });

      // Check loading state is true
      expect(result.current.isLoadingSessions).toBe(true);

      // Resolve the API call
      resolveApiCall!();
      await loadPromise;

      // Check loading state is false
      expect(result.current.isLoadingSessions).toBe(false);
    });
  });

  describe('createNewSession', () => {
    test('should create new session successfully', async () => {
      const { result } = renderHookDirectly();

      let newSession: any;
      await act(async () => {
        newSession = await result.current.createNewSession();
      });

      expect(mockApiClient.createSession).toHaveBeenCalled();
      expect(mockApiClient.setCurrentSession).toHaveBeenCalledWith(
        'session-1',
        'test-token-123'
      );
      expect(newSession).toMatchObject({
        id: 'session-1',
        name: 'Test Session',
        isActive: true,
      });
      expect(result.current.currentSession).toEqual(newSession);
    });

    test('should handle session creation errors', async () => {
      mockApiClient.createSession.mockRejectedValue(
        new Error('Creation failed')
      );

      const { result } = renderHookDirectly();

      let newSession: any;
      await act(async () => {
        newSession = await result.current.createNewSession();
      });

      expect(newSession).toBeNull();
      expect(result.current.sessionsError).toBe('Creation failed');
    });

    test('should add new session to sessions list', async () => {
      const { result } = renderHookDirectly();

      // First load existing sessions
      await act(async () => {
        await result.current.loadSessions();
      });

      expect(result.current.sessions).toHaveLength(1);

      // Create a new session
      const newSessionResponse = {
        ...mockSessionResponse,
        session_id: 'session-2',
        name: 'New Session',
      };
      mockApiClient.createSession.mockResolvedValue(newSessionResponse);

      await act(async () => {
        await result.current.createNewSession();
      });

      expect(result.current.sessions).toHaveLength(2);
      expect(result.current.sessions[0].id).toBe('session-2'); // New session at top
    });
  });

  describe('loadSessionHistory', () => {
    test('should load session history successfully', async () => {
      const { result } = renderHookDirectly();

      let history: any;
      await act(async () => {
        history = await result.current.loadSessionHistory('session-1');
      });

      expect(mockApiClient.getChatHistory).toHaveBeenCalled();
      expect(history).toHaveLength(2);
      expect(history[0]).toMatchObject({
        type: 'user',
        content: 'Hello',
      });
      expect(history[1]).toMatchObject({
        type: 'ai',
        content: 'Hi there!',
      });
    });

    test('should handle empty chat history', async () => {
      mockApiClient.getChatHistory.mockResolvedValue({ messages: [] });

      const { result } = renderHookDirectly();

      let history: any;
      await act(async () => {
        history = await result.current.loadSessionHistory('session-1');
      });

      expect(history).toEqual([]);
    });

    test('should handle missing session token', async () => {
      mockApiClient.getCurrentSession.mockReturnValue({
        sessionId: 'session-1',
        sessionToken: null,
      });

      const { result } = renderHookDirectly();

      let history: any;
      await act(async () => {
        history = await result.current.loadSessionHistory('session-1');
      });

      expect(history).toEqual([]);
      expect(mockApiClient.getChatHistory).not.toHaveBeenCalled();
    });
  });

  describe('switchToSession', () => {
    test('should switch to existing session successfully', async () => {
      const { result } = renderHookDirectly();

      // Load initial sessions
      await act(async () => {
        await result.current.loadSessions();
      });

      let history: any;
      await act(async () => {
        history = await result.current.switchToSession('session-1');
      });

      expect(mockApiClient.setCurrentSession).toHaveBeenCalledWith(
        'session-1',
        'test-token-123'
      );
      expect(result.current.currentSession?.id).toBe('session-1');
      expect(result.current.currentSession?.isActive).toBe(true);
      expect(history).toHaveLength(2);
    });

    test('should throw error for non-existent session', async () => {
      const { result } = renderHookDirectly();

      await act(async () => {
        await result.current.loadSessions();
      });

      await act(async () => {
        await expect(
          result.current.switchToSession('non-existent')
        ).rejects.toThrow('Sessione non trovata');
      });
    });

    test('should update session active state', async () => {
      const multipleSessionsResponse = [
        mockSessionResponse,
        { ...mockSessionResponse, session_id: 'session-2', name: 'Session 2' },
      ];
      mockApiClient.getUserSessions.mockResolvedValue(multipleSessionsResponse);

      const { result } = renderHookDirectly();

      await act(async () => {
        await result.current.loadSessions();
      });

      expect(result.current.sessions).toHaveLength(2);

      await act(async () => {
        await result.current.switchToSession('session-2');
      });

      const activeSession = result.current.sessions.find(s => s.isActive);
      const inactiveSession = result.current.sessions.find(s => !s.isActive);

      expect(activeSession?.id).toBe('session-2');
      expect(inactiveSession?.id).toBe('session-1');
    });
  });

  describe('updateSessionName', () => {
    test('should update session name optimistically', async () => {
      const { result } = renderHookDirectly();

      await act(async () => {
        await result.current.loadSessions();
      });

      await act(async () => {
        await result.current.updateSessionName('session-1', 'Updated Name');
      });

      const updatedSession = result.current.sessions.find(
        s => s.id === 'session-1'
      );
      expect(updatedSession?.name).toBe('Updated Name');
    });

    test('should update current session name if it matches', async () => {
      const { result } = renderHookDirectly();

      await act(async () => {
        await result.current.loadSessions();
        await result.current.switchToSession('session-1');
      });

      expect(result.current.currentSession?.name).toBe('Test Session');

      await act(async () => {
        await result.current.updateSessionName('session-1', 'New Current Name');
      });

      expect(result.current.currentSession?.name).toBe('New Current Name');
    });
  });

  describe('deleteSession', () => {
    test('should delete session successfully', async () => {
      const { result } = renderHookDirectly();

      await act(async () => {
        await result.current.loadSessions();
      });

      expect(result.current.sessions).toHaveLength(1);

      await act(async () => {
        await result.current.deleteSession('session-1');
      });

      expect(mockApiClient.deleteSession).toHaveBeenCalledWith(
        'session-1',
        'test-token-123'
      );
      expect(result.current.sessions).toHaveLength(0);
    });

    test('should create new session when deleting current session', async () => {
      const { result } = renderHookDirectly();

      // Load and set current session
      await act(async () => {
        await result.current.loadSessions();
        await result.current.switchToSession('session-1');
      });

      expect(result.current.currentSession?.id).toBe('session-1');

      // Delete the current session
      await act(async () => {
        await result.current.deleteSession('session-1');
      });

      expect(mockClearMessages).toHaveBeenCalled();
      expect(mockApiClient.createSession).toHaveBeenCalled();
    });
  });

  describe('session helpers', () => {
    test('isSessionEmpty should correctly identify empty sessions', () => {
      const { result } = renderHookDirectly();

      const emptySession = { message_count: 0 } as any;
      const usedSession = { message_count: 2 } as any;
      const undefinedSession = { message_count: undefined } as any;

      expect(result.current.isSessionEmpty(emptySession)).toBe(true);
      expect(result.current.isSessionEmpty(usedSession)).toBe(false);
      expect(result.current.isSessionEmpty(undefinedSession)).toBe(true);
    });

    test('hasCompleteQAPair should correctly identify sessions with Q&A', () => {
      const { result } = renderHookDirectly();

      const emptySession = { message_count: 0 } as any;
      const singleMessageSession = { message_count: 1 } as any;
      const completeSession = { message_count: 2 } as any;
      const undefinedSession = { message_count: undefined } as any;

      expect(result.current.hasCompleteQAPair(emptySession)).toBe(false);
      expect(result.current.hasCompleteQAPair(singleMessageSession)).toBe(
        false
      );
      expect(result.current.hasCompleteQAPair(completeSession)).toBe(true);
      expect(result.current.hasCompleteQAPair(undefinedSession)).toBe(false);
    });

    test('markSessionAsUsed should update message count', async () => {
      const { result } = renderHookDirectly();

      await act(async () => {
        await result.current.loadSessions();
        await result.current.switchToSession('session-1');
      });

      act(() => {
        result.current.markSessionAsUsed('session-1');
      });

      const updatedSession = result.current.sessions.find(
        s => s.id === 'session-1'
      );
      const currentSession = result.current.currentSession;

      expect(updatedSession?.message_count).toBeGreaterThanOrEqual(2);
      expect(currentSession?.message_count).toBeGreaterThanOrEqual(2);
    });
  });

  describe('localStorage integration', () => {
    test('should save session ID to localStorage when switching', async () => {
      const { result } = renderHookDirectly();

      await act(async () => {
        await result.current.loadSessions();
        await result.current.switchToSession('session-1');
      });

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'current_session_id',
        'session-1'
      );
    });

    test('should save session ID to localStorage when creating new session', async () => {
      const { result } = renderHookDirectly();

      await act(async () => {
        await result.current.createNewSession();
      });

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'current_session_id',
        'session-1'
      );
    });

    test('should remove session ID from localStorage when deleting current session', async () => {
      const { result } = renderHookDirectly();

      await act(async () => {
        await result.current.loadSessions();
        await result.current.switchToSession('session-1');
        await result.current.deleteSession('session-1');
      });

      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(
        'current_session_id'
      );
    });
  });
});
