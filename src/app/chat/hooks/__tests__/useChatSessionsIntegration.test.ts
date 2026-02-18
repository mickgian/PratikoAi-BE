/**
 * @file useChatSessionsV2 Integration Tests
 * @description Tests for integrating backend API calls with hybrid storage via useChatSessionsV2
 * TDD Phase: GREEN - Implementation tests
 */

import { renderHook, waitFor } from '@testing-library/react';
import { useChatSessionsV2 } from '../useChatSessionsV2';
import { useChatSessions } from '../useChatSessions';
import { useChatStorageV2 } from '../useChatStorageV2';

// Mock dependencies
jest.mock('../useChatSessions');
jest.mock('../useChatStorageV2');

describe('useChatSessionsV2 Integration', () => {
  const mockSessionsReturn = {
    sessions: [],
    isLoadingSessions: false,
    sessionsError: null,
    currentSession: {
      id: 'session-1',
      name: 'Test',
      created_at: '2025-11-29',
      isActive: true,
    },
    isLoadingHistory: false,
    historyError: null,
    loadSessions: jest.fn(),
    createNewSession: jest.fn(),
    switchToSession: jest.fn(),
    loadSessionHistory: jest.fn(),
    updateSessionName: jest.fn(),
    deleteSession: jest.fn(),
    initializeSession: jest.fn(),
    isSessionEmpty: jest.fn(),
    hasCompleteQAPair: jest.fn(),
    markSessionAsUsed: jest.fn(),
    cleanupEmptySessions: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useChatSessions as jest.Mock).mockReturnValue(mockSessionsReturn);
  });

  it('should expose migration status from useChatStorageV2', async () => {
    (useChatStorageV2 as jest.Mock).mockReturnValue({
      messages: [],
      isLoading: false,
      error: null,
      migrationNeeded: true,
      migrateToBackend: jest.fn(),
      reload: jest.fn(),
    });

    const { result } = renderHook(() => useChatSessionsV2());

    expect(result.current.migrationNeeded).toBe(true);
  });

  it('should call storage hook with current session ID', async () => {
    (useChatStorageV2 as jest.Mock).mockReturnValue({
      messages: [],
      isLoading: false,
      error: null,
      migrationNeeded: false,
      migrateToBackend: jest.fn(),
      reload: jest.fn(),
    });

    renderHook(() => useChatSessionsV2());

    expect(useChatStorageV2).toHaveBeenCalledWith('session-1');
  });

  it('should expose storage errors', async () => {
    (useChatStorageV2 as jest.Mock).mockReturnValue({
      messages: [],
      isLoading: false,
      error: 'Backend unavailable',
      migrationNeeded: true,
      migrateToBackend: jest.fn(),
      reload: jest.fn(),
    });

    const { result } = renderHook(() => useChatSessionsV2());

    expect(result.current.storageError).toBe('Backend unavailable');
  });

  it('should provide migrateToBackend function from storage hook', async () => {
    const mockMigrate = jest.fn().mockResolvedValue(undefined);
    (useChatStorageV2 as jest.Mock).mockReturnValue({
      messages: [],
      isLoading: false,
      error: null,
      migrationNeeded: true,
      migrateToBackend: mockMigrate,
      reload: jest.fn(),
    });

    const { result } = renderHook(() => useChatSessionsV2());

    await result.current.migrateToBackend();

    expect(mockMigrate).toHaveBeenCalled();
  });
});
