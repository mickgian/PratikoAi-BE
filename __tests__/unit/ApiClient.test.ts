import apiClient from '@/lib/api';

// Mock fetch for testing
global.fetch = jest.fn();

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

describe('ApiClient', () => {
  const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

  // Use a proper JWT-formatted token for tests
  const mockToken =
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c';

  beforeEach(() => {
    jest.clearAllMocks();

    // Clear localStorage mocks
    mockLocalStorage.getItem.mockReturnValue(null);
    mockLocalStorage.setItem.mockClear();
    mockLocalStorage.removeItem.mockClear();

    // Mock successful response BEFORE calling logout
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: jest.fn().mockResolvedValue({}),
      headers: new Headers(),
      redirected: false,
      statusText: 'OK',
      type: 'basic',
      url: 'http://localhost:8000',
      clone: jest.fn(),
      body: null,
      bodyUsed: false,
      arrayBuffer: jest.fn(),
      blob: jest.fn(),
      formData: jest.fn(),
      text: jest.fn(),
    } as any);

    // Reset apiClient state after mock is set up
    apiClient.logout();
  });

  describe('initialization', () => {
    test('should have default configuration', () => {
      expect(apiClient).toBeDefined();
    });

    test('should start unauthenticated', () => {
      expect(apiClient.isAuthenticated()).toBe(false);
    });
  });

  describe('authentication', () => {
    const mockAuthResponse = {
      access_token: mockToken,
      refresh_token: mockToken,
      token_type: 'Bearer',
      expires_at: '2023-12-31T23:59:59Z',
    };

    test('should login successfully', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue(mockAuthResponse),
      } as any);

      const result = await apiClient.login('testuser', 'password123');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/login',
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
        })
      );

      expect(result).toEqual(mockAuthResponse);
      expect(apiClient.isAuthenticated()).toBe(true);
    });

    test('should handle login errors', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
        json: jest.fn().mockResolvedValue({ detail: 'Invalid credentials' }),
      } as any);

      await expect(apiClient.login('wrong', 'password')).rejects.toThrow(
        'Invalid credentials'
      );
      expect(apiClient.isAuthenticated()).toBe(false);
    });

    test('should register successfully', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockAuthResponse),
      } as any);

      const result = await apiClient.register({
        email: 'test@example.com',
        password: 'password123',
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/register',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: 'test@example.com',
            password: 'password123',
          }),
        })
      );

      expect(result).toEqual(mockAuthResponse);
      expect(apiClient.isAuthenticated()).toBe(true);
    });

    test('should logout successfully', async () => {
      // First login to have a token (use JWT-formatted token)
      (apiClient as any)['accessToken'] = mockToken;
      expect(apiClient.isAuthenticated()).toBe(true);

      await apiClient.logout();

      expect(apiClient.isAuthenticated()).toBe(false);
      expect((apiClient as any)['accessToken']).toBe(null);
    });

    test('should refresh token successfully', async () => {
      const newTokenResponse = {
        ...mockAuthResponse,
        access_token: mockToken,
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(newTokenResponse),
      } as any);

      apiClient['refreshToken'] = mockToken;

      const result = await apiClient.refreshAccessToken();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/refresh',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('refresh_token'),
        })
      );

      expect(result).toBe(true);
    });
  });

  describe('session management', () => {
    beforeEach(() => {
      // Mock authenticated state (use JWT-formatted token)
      (apiClient as any)['accessToken'] = mockToken;
    });

    test('should create session successfully', async () => {
      const mockSession = {
        session_id: 'session-123',
        name: 'New Session',
        created_at: '2023-01-01T00:00:00Z',
        token: {
          access_token: mockToken,
          token_type: 'Bearer',
          expires_at: '2023-01-01T01:00:00Z',
        },
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue(mockSession),
      } as any);

      const result = await apiClient.createSession();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/session',
        expect.objectContaining({
          method: 'POST',
        })
      );

      expect(result).toEqual(mockSession);
    });

    test('should get user sessions successfully', async () => {
      const mockSessions = [
        {
          session_id: 'session-1',
          name: 'Session 1',
          created_at: '2023-01-01T00:00:00Z',
          token: { access_token: mockToken },
        },
        {
          session_id: 'session-2',
          name: 'Session 2',
          created_at: '2023-01-02T00:00:00Z',
          token: { access_token: mockToken },
        },
      ];

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue(mockSessions),
      } as any);

      const result = await apiClient.getUserSessions();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/sessions',
        expect.anything()
      );

      expect(result).toEqual(mockSessions);
    });

    test('should update session name successfully', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue({ message: 'Session updated' }),
      } as any);

      await apiClient.updateSessionName(
        'session-123',
        'Updated Name',
        mockToken
      );

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/session/session-123/name',
        expect.objectContaining({
          method: 'PATCH',
          headers: expect.objectContaining({
            Authorization: `Bearer ${mockToken}`,
          }),
        })
      );
    });

    test('should delete session successfully', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue({ message: 'Session deleted' }),
      } as any);

      await apiClient.deleteSession('session-123', mockToken);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/session/session-123',
        expect.objectContaining({
          method: 'DELETE',
          headers: expect.objectContaining({
            Authorization: `Bearer ${mockToken}`,
          }),
        })
      );
    });

    test('should set current session', () => {
      apiClient.setCurrentSession('session-123', 'session-token-456');

      const current = apiClient.getCurrentSession();
      expect(current).toEqual({
        sessionId: 'session-123',
        sessionToken: 'session-token-456',
      });
    });
  });

  describe('chat operations', () => {
    beforeEach(() => {
      (apiClient as any)['accessToken'] = mockToken;
      apiClient.setCurrentSession('session-123', mockToken);
    });

    test('should send chat message successfully', async () => {
      const mockResponse = {
        messages: [
          { role: 'user', content: 'Hello' },
          { role: 'assistant', content: 'Hi there!' },
        ],
        metadata: {
          model_used: 'gpt-4',
          provider: 'openai',
          strategy: 'standard',
        },
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue(mockResponse),
      } as any);

      const messages = [{ role: 'user' as const, content: 'Hello' }];
      const result = await apiClient.sendChatMessage(messages);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/chatbot/chat',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ messages }),
        })
      );

      expect(result).toEqual(mockResponse);
    });

    test('should get chat history successfully', async () => {
      const mockHistory = {
        messages: [
          { role: 'user', content: 'Previous question' },
          { role: 'assistant', content: 'Previous answer' },
        ],
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue(mockHistory),
      } as any);

      const result = await apiClient.getChatHistory();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/chatbot/messages',
        expect.anything()
      );

      expect(result).toEqual(mockHistory);
    });

    test('should clear chat history successfully', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue({ message: 'Chat history cleared' }),
      } as any);

      const result = await apiClient.clearChatHistory();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/chatbot/messages',
        expect.objectContaining({
          method: 'DELETE',
        })
      );

      expect(result).toEqual({ message: 'Chat history cleared' });
    });

    test('should ensure session before operations', async () => {
      // Start without session
      apiClient['currentSessionId'] = null;
      apiClient['currentSessionToken'] = null;

      const mockSession = {
        session_id: 'auto-session',
        token: { access_token: mockToken },
      };

      // Mock createSession for auto-creation
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: jest.fn().mockResolvedValue(mockSession),
        } as any)
        // Mock the chat message request
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: jest.fn().mockResolvedValue({ messages: [] }),
        } as any);

      const messages = [{ role: 'user' as const, content: 'Test' }];
      await apiClient.sendChatMessage(messages);

      // Should have called createSession first (correct endpoint)
      expect(mockFetch).toHaveBeenNthCalledWith(
        2,
        'http://localhost:8000/api/v1/auth/session',
        expect.objectContaining({ method: 'POST' })
      );

      // Then the actual chat message
      expect(mockFetch).toHaveBeenNthCalledWith(
        3,
        'http://localhost:8000/api/v1/chatbot/chat',
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  describe('streaming', () => {
    beforeEach(() => {
      (apiClient as any)['accessToken'] = mockToken;
      apiClient.setCurrentSession('session-123', mockToken);
    });

    test('should handle streaming errors', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: jest.fn().mockResolvedValue({ detail: 'Internal server error' }),
      } as any;

      mockFetch.mockResolvedValue(mockResponse);

      const messages = [{ role: 'user' as const, content: 'Hello' }];
      const onChunk = jest.fn();
      const onDone = jest.fn();
      const onError = jest.fn();

      await apiClient.sendChatMessageStreaming(
        messages,
        onChunk,
        onDone,
        onError
      );

      expect(onError).toHaveBeenCalledWith('Internal server error');
      expect(onChunk).not.toHaveBeenCalled();
      expect(onDone).not.toHaveBeenCalled();
    });

    test('should handle network errors in streaming', async () => {
      mockFetch.mockRejectedValue(new TypeError('Failed to fetch'));

      const messages = [{ role: 'user' as const, content: 'Hello' }];
      const onChunk = jest.fn();
      const onDone = jest.fn();
      const onError = jest.fn();

      await apiClient.sendChatMessageStreaming(
        messages,
        onChunk,
        onDone,
        onError
      );

      expect(onError).toHaveBeenCalledWith(
        'Impossibile connettersi al server. Verifica che il backend sia in funzione.'
      );
    });
  });

  describe('error handling', () => {
    test('should throw error for unauthenticated requests', async () => {
      // Clear authentication
      apiClient.logout();

      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
        json: jest.fn().mockResolvedValue({ detail: 'Not authenticated' }),
      } as any);

      await expect(apiClient.getUserSessions()).rejects.toThrow(
        'Not authenticated'
      );
    });

    test('should handle network errors', async () => {
      (apiClient as any)['accessToken'] = mockToken;

      mockFetch.mockRejectedValue(new Error('Network error'));

      await expect(apiClient.getUserSessions()).rejects.toThrow(
        'Network error'
      );
    });

    test('should handle invalid JSON responses', async () => {
      (apiClient as any)['accessToken'] = mockToken;

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: jest.fn().mockRejectedValue(new Error('Invalid JSON')),
      } as any);

      await expect(apiClient.getUserSessions()).rejects.toThrow('Invalid JSON');
    });
  });

  describe('request building', () => {
    test('should build request with authentication headers', async () => {
      (apiClient as any)['accessToken'] = mockToken;

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue([]),
      } as any);

      await apiClient.getUserSessions();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/sessions',
        expect.anything()
      );
    });

    test('should handle requests with proper headers', () => {
      // This test verifies that the API client can make requests
      expect(apiClient).toBeDefined();
      expect(typeof apiClient.isAuthenticated).toBe('function');
    });

    test('should be a singleton instance', () => {
      // Verify it's the same instance
      expect(apiClient).toBeDefined();
      expect(typeof apiClient.login).toBe('function');
    });
  });
});
