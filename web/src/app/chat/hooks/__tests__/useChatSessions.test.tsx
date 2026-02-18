/**
 * @jest-environment jsdom
 */
import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { useChatSessions } from '../useChatSessions';
import { ChatStateProvider } from '../useChatState';

// Mock the API client
jest.mock('@/lib/api', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
    isAuthenticated: jest.fn(() => true),
  },
}));

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Wrapper component to provide ChatStateProvider
const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(ChatStateProvider, null, children);

describe('useChatSessions - Initialize without auto-creating session', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.clear();
  });

  it('should NOT auto-create session when initialized with no saved session', async () => {
    const { apiClient } = require('@/lib/api');

    // Mock: No saved session in localStorage
    // Mock: API returns empty sessions list
    apiClient.get.mockResolvedValue({
      data: {
        sessions: [],
      },
    });

    const { result } = renderHook(() => useChatSessions(), { wrapper });

    await waitFor(() => {
      // This test SHOULD FAIL initially - we expect NO session to be auto-created
      expect(result.current.currentSession).toBeNull();
      expect(result.current.sessions).toEqual([]);
      // Verify createNewSession was NOT called during initialization
      expect(apiClient.post).not.toHaveBeenCalled();
    });
  });

  it('should NOT auto-select session even if localStorage has saved session', async () => {
    const { apiClient } = require('@/lib/api');

    const savedSession = {
      session_id: 'saved-session-123',
      title: 'Saved Chat',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    // Mock: Saved session in localStorage (from previous session)
    localStorageMock.setItem('currentSession', JSON.stringify(savedSession));

    // Mock: API returns the session in the list
    apiClient.get.mockResolvedValue({
      data: {
        sessions: [savedSession],
      },
    });

    const { result } = renderHook(() => useChatSessions(), { wrapper });

    await waitFor(
      () => {
        // CRITICAL: With lazy session creation, currentSession should remain null
        // even if there's a saved session in localStorage
        // User must explicitly select a session or send a message to activate one
        expect(result.current.currentSession).toBeNull();
        // Should NOT create a new session
        expect(apiClient.post).not.toHaveBeenCalled();
      },
      { timeout: 3000 }
    );
  });

  it('should show empty state when no session exists', async () => {
    const { apiClient } = require('@/lib/api');

    apiClient.get.mockResolvedValue({
      data: {
        sessions: [],
      },
    });

    const { result } = renderHook(() => useChatSessions(), { wrapper });

    await waitFor(() => {
      // This test SHOULD FAIL initially - current behavior auto-creates session
      expect(result.current.currentSession).toBeNull();
      expect(result.current.sessions).toEqual([]);
      expect(result.current.isLoadingSessions).toBe(false);
    });
  });

  it('should handle initialization with authentication token', async () => {
    const { apiClient } = require('@/lib/api');

    // Mock: User authenticated but no sessions yet
    apiClient.get.mockResolvedValue({
      data: {
        sessions: [],
      },
    });

    const { result } = renderHook(() => useChatSessions(), { wrapper });

    await waitFor(() => {
      // Should NOT auto-create session even with auth token
      expect(result.current.currentSession).toBeNull();
      expect(apiClient.post).not.toHaveBeenCalled();
    });
  });
});
