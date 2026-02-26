/**
 * @jest-environment jsdom
 */
import { renderHook, waitFor } from '@testing-library/react';
import { useVersionInfo } from '../useReleaseNotes';

jest.mock('@/lib/api/release-notes', () => ({
  getVersion: jest.fn(),
}));

import { getVersion } from '@/lib/api/release-notes';

const mockGetVersion = getVersion as jest.MockedFunction<typeof getVersion>;

describe('useVersionInfo', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns version info on success', async () => {
    const versionData = { version: '1.2.0', environment: 'production' };
    mockGetVersion.mockResolvedValueOnce(versionData);

    const { result } = renderHook(() => useVersionInfo());

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.version).toEqual(versionData);
  });

  it('returns null version on error', async () => {
    mockGetVersion.mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useVersionInfo());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.version).toBeNull();
  });

  it('starts with loading true and version null', () => {
    mockGetVersion.mockReturnValue(new Promise(() => {})); // never resolves

    const { result } = renderHook(() => useVersionInfo());

    expect(result.current.loading).toBe(true);
    expect(result.current.version).toBeNull();
  });
});
