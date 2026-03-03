/**
 * @jest-environment jsdom
 */
import { renderHook, waitFor, act } from '@testing-library/react';

jest.mock('@/lib/api/dashboard', () => ({
  getDashboardData: jest.fn(),
}));

jest.mock('@/lib/api/helpers', () => ({
  getStudioId: jest.fn().mockReturnValue('studio-123'),
  getUserId: jest.fn().mockReturnValue(42),
  getAuthHeaders: jest.fn().mockReturnValue({}),
  buildStudioUrl: jest.fn(),
}));

import { getDashboardData } from '@/lib/api/dashboard';
import { getStudioId } from '@/lib/api/helpers';
import { useDashboard } from '../useDashboard';

const mockGetDashboardData = getDashboardData as jest.MockedFunction<
  typeof getDashboardData
>;
const mockGetStudioId = getStudioId as jest.MockedFunction<typeof getStudioId>;

const makeDashboardResponse = (period: string = 'month') => ({
  clients: { total: 100 },
  communications: { total: 50, pending_review: 5 },
  procedures: { total: 10, active: 3 },
  matches: { active_rules: 8 },
  roi: { hours_saved: 120, breakdown: {} },
  distributions: {
    by_regime: [{ regime: 'forfettario', count: 40 }],
    by_ateco: [{ ateco: '62.01', count: 30 }],
    by_status: [{ status: 'ATTIVO', count: 80 }],
  },
  matching: {
    total_matches: 25,
    conversion_rate: 0.6,
    pending_reviews: 5,
  },
  period,
});

describe('useDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetStudioId.mockReturnValue('studio-123');
  });

  it('fetches dashboard data on mount with default period', async () => {
    const response = makeDashboardResponse('month');
    mockGetDashboardData.mockResolvedValueOnce(response);

    const { result } = renderHook(() => useDashboard('month'));

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual(response);
    expect(result.current.error).toBeNull();
    expect(mockGetDashboardData).toHaveBeenCalledWith('month');
  });

  it('fetches with week period', async () => {
    const response = makeDashboardResponse('week');
    mockGetDashboardData.mockResolvedValueOnce(response);

    const { result } = renderHook(() => useDashboard('week'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual(response);
    expect(mockGetDashboardData).toHaveBeenCalledWith('week');
  });

  it('fetches with year period', async () => {
    const response = makeDashboardResponse('year');
    mockGetDashboardData.mockResolvedValueOnce(response);

    const { result } = renderHook(() => useDashboard('year'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual(response);
    expect(mockGetDashboardData).toHaveBeenCalledWith('year');
  });

  it('refetches when period changes', async () => {
    const monthResponse = makeDashboardResponse('month');
    mockGetDashboardData.mockResolvedValueOnce(monthResponse);

    const { result, rerender } = renderHook(
      ({ period }: { period: 'week' | 'month' | 'year' }) =>
        useDashboard(period),
      { initialProps: { period: 'month' as 'week' | 'month' | 'year' } }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data?.period).toBe('month');

    const weekResponse = makeDashboardResponse('week');
    mockGetDashboardData.mockResolvedValueOnce(weekResponse);

    rerender({ period: 'week' });

    await waitFor(() => {
      expect(result.current.data?.period).toBe('week');
    });

    expect(mockGetDashboardData).toHaveBeenCalledTimes(2);
  });

  it('sets error on API failure', async () => {
    mockGetDashboardData.mockRejectedValueOnce(
      new Error('Errore nel caricamento della dashboard')
    );

    const { result } = renderHook(() => useDashboard('month'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe('Errore nel caricamento della dashboard');
  });

  it('handles non-Error exceptions with fallback message', async () => {
    mockGetDashboardData.mockRejectedValueOnce(undefined);

    const { result } = renderHook(() => useDashboard('month'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe('Errore nel caricamento della dashboard');
  });

  it('sets error when studio is not configured', async () => {
    mockGetStudioId.mockReturnValue(null);

    const { result } = renderHook(() => useDashboard('month'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe('Studio non configurato');
    expect(mockGetDashboardData).not.toHaveBeenCalled();
  });

  it('data is null during loading', () => {
    mockGetDashboardData.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useDashboard('month'));

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeNull();
  });

  it('supports refresh', async () => {
    const response = makeDashboardResponse('month');
    mockGetDashboardData.mockResolvedValueOnce(response);

    const { result } = renderHook(() => useDashboard('month'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const updatedResponse = {
      ...makeDashboardResponse('month'),
      clients: { total: 200 },
    };
    mockGetDashboardData.mockResolvedValueOnce(updatedResponse);

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.data?.clients.total).toBe(200);
  });
});
