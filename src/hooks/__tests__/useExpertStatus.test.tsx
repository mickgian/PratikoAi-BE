// src/hooks/__tests__/useExpertStatus.test.tsx
import { renderHook, waitFor } from '@testing-library/react';
import { useExpertStatus } from '../useExpertStatus';
import * as expertFeedbackApi from '@/lib/api/expertFeedback';

// Mock the expertFeedback API module
jest.mock('@/lib/api/expertFeedback');

const mockedIsUserSuperUser = expertFeedbackApi.isUserSuperUser as jest.Mock;

describe('useExpertStatus', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should return loading state initially', () => {
    mockedIsUserSuperUser.mockResolvedValue(true);

    const { result } = renderHook(() => useExpertStatus());

    expect(result.current.isLoading).toBe(true);
    expect(result.current.isSuperUser).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should return isSuperUser=true when user is a super user', async () => {
    mockedIsUserSuperUser.mockResolvedValue(true);

    const { result } = renderHook(() => useExpertStatus());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isSuperUser).toBe(true);
    expect(result.current.isExpert).toBe(true); // Backward compatibility
    expect(result.current.error).toBeNull();
  });

  it('should return isSuperUser=false when user is not a super user', async () => {
    mockedIsUserSuperUser.mockResolvedValue(false);

    const { result } = renderHook(() => useExpertStatus());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isSuperUser).toBe(false);
    expect(result.current.isExpert).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should set error when API call fails', async () => {
    const errorMessage = 'Network error';
    mockedIsUserSuperUser.mockRejectedValue(new Error(errorMessage));

    const { result } = renderHook(() => useExpertStatus());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isSuperUser).toBe(false);
    expect(result.current.error).toBe(errorMessage);
  });

  it('should set generic error message for non-Error exceptions', async () => {
    mockedIsUserSuperUser.mockRejectedValue('Some string error');

    const { result } = renderHook(() => useExpertStatus());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isSuperUser).toBe(false);
    expect(result.current.error).toBe('Failed to check user role');
  });

  it('should clean up on unmount (not update state after unmount)', async () => {
    // Use a promise that we can control
    let resolvePromise: (value: boolean) => void;
    const promise = new Promise<boolean>(resolve => {
      resolvePromise = resolve;
    });
    mockedIsUserSuperUser.mockReturnValue(promise);

    const { result, unmount } = renderHook(() => useExpertStatus());

    // Unmount before promise resolves
    unmount();

    // Resolve the promise after unmount
    resolvePromise!(true);

    // Wait a bit to ensure no state updates happen
    await new Promise(r => setTimeout(r, 50));

    // The hook should have cleaned up properly (no error thrown)
    expect(result.current.isLoading).toBe(true);
  });
});
