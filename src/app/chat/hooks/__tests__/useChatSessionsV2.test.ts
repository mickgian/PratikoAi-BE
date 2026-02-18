/**
 * @file useChatSessionsV2 Tests
 * @description Unit tests for hybrid storage integration hook
 */

import { renderHook } from '@testing-library/react';
import { useChatSessionsV2 } from '../useChatSessionsV2';
import { useChatSessions } from '../useChatSessions';
import { useChatStorageV2 } from '../useChatStorageV2';

// Mock dependencies
jest.mock('../useChatSessions');
jest.mock('../useChatStorageV2');

describe('useChatSessionsV2', () => {
  const mockSessionsHook = {
    sessions: [
      {
        id: 'session-1',
        name: 'Test Session',
        created_at: '2025-11-29',
        isActive: true,
      },
    ],
    isLoadingSessions: false,
    sessionsError: null,
    currentSession: {
      id: 'session-1',
      name: 'Test Session',
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

  const mockStorageHook = {
    messages: [],
    isLoading: false,
    error: null,
    migrationNeeded: false,
    migrateToBackend: jest.fn(),
    reload: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useChatSessions as jest.Mock).mockReturnValue(mockSessionsHook);
    (useChatStorageV2 as jest.Mock).mockReturnValue(mockStorageHook);
  });

  it('should combine session management with storage hook', () => {
    const { result } = renderHook(() => useChatSessionsV2());

    expect(result.current.sessions).toEqual(mockSessionsHook.sessions);
    expect(result.current.currentSession).toEqual(
      mockSessionsHook.currentSession
    );
    expect(result.current.migrationNeeded).toBe(false);
    expect(result.current.migrateToBackend).toBeDefined();
    expect(result.current.storageError).toBeNull();
  });

  it('should expose migration status from storage hook', () => {
    (useChatStorageV2 as jest.Mock).mockReturnValue({
      ...mockStorageHook,
      migrationNeeded: true,
    });

    const { result } = renderHook(() => useChatSessionsV2());

    expect(result.current.migrationNeeded).toBe(true);
  });

  it('should expose storage errors', () => {
    (useChatStorageV2 as jest.Mock).mockReturnValue({
      ...mockStorageHook,
      error: 'Backend unavailable',
    });

    const { result } = renderHook(() => useChatSessionsV2());

    expect(result.current.storageError).toBe('Backend unavailable');
  });

  it('should call storage hook with current session ID', () => {
    renderHook(() => useChatSessionsV2());

    expect(useChatStorageV2).toHaveBeenCalledWith('session-1');
  });

  it('should handle no current session', () => {
    (useChatSessions as jest.Mock).mockReturnValue({
      ...mockSessionsHook,
      currentSession: null,
    });

    renderHook(() => useChatSessionsV2());

    expect(useChatStorageV2).toHaveBeenCalledWith('');
  });

  it('should provide migrateToBackend function', async () => {
    const mockMigrate = jest.fn().mockResolvedValue(undefined);
    (useChatStorageV2 as jest.Mock).mockReturnValue({
      ...mockStorageHook,
      migrateToBackend: mockMigrate,
    });

    const { result } = renderHook(() => useChatSessionsV2());

    await result.current.migrateToBackend();

    expect(mockMigrate).toHaveBeenCalled();
  });

  it('should preserve all original session hook functionality', () => {
    const { result } = renderHook(() => useChatSessionsV2());

    expect(result.current.loadSessions).toBe(mockSessionsHook.loadSessions);
    expect(result.current.createNewSession).toBe(
      mockSessionsHook.createNewSession
    );
    expect(result.current.switchToSession).toBe(
      mockSessionsHook.switchToSession
    );
    expect(result.current.loadSessionHistory).toBe(
      mockSessionsHook.loadSessionHistory
    );
    expect(result.current.updateSessionName).toBe(
      mockSessionsHook.updateSessionName
    );
    expect(result.current.deleteSession).toBe(mockSessionsHook.deleteSession);
  });
});
