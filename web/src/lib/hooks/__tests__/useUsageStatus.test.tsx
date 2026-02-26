/**
 * @jest-environment jsdom
 */
import { renderHook, waitFor, act } from '@testing-library/react';
import { useUsageStatus } from '../useUsageStatus';

jest.mock('@/lib/api/billing', () => ({
  getUsageStatus: jest.fn(),
}));

import { getUsageStatus } from '@/lib/api/billing';

const mockGetUsageStatus = getUsageStatus as jest.MockedFunction<
  typeof getUsageStatus
>;

const mockUsageStatus = {
  plan_slug: 'free',
  plan_name: 'Free',
  window_5h: {
    window_type: '5h',
    current_cost_eur: 0,
    limit_cost_eur: 1,
    usage_percentage: 0,
    reset_at: null,
    reset_in_minutes: null,
  },
  window_7d: {
    window_type: '7d',
    current_cost_eur: 0,
    limit_cost_eur: 5,
    usage_percentage: 0,
    reset_at: null,
    reset_in_minutes: null,
  },
  credits: { balance_eur: 10, extra_usage_enabled: false },
  is_admin: false,
  message_it: 'Tutto ok',
};

describe('useUsageStatus', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('fetches usage status on mount', async () => {
    mockGetUsageStatus.mockResolvedValueOnce(mockUsageStatus);

    const { result } = renderHook(() => useUsageStatus());

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockUsageStatus);
    expect(result.current.error).toBeNull();
  });

  it('sets error on failure', async () => {
    mockGetUsageStatus.mockRejectedValueOnce(new Error('Errore rete'));

    const { result } = renderHook(() => useUsageStatus());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe('Errore rete');
  });

  it('handles non-Error exceptions', async () => {
    mockGetUsageStatus.mockRejectedValueOnce('string error');

    const { result } = renderHook(() => useUsageStatus());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('Errore sconosciuto');
  });

  it('supports refetch', async () => {
    mockGetUsageStatus.mockResolvedValueOnce(mockUsageStatus);

    const { result } = renderHook(() => useUsageStatus());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const updated = { ...mockUsageStatus, plan_name: 'Premium' };
    mockGetUsageStatus.mockResolvedValueOnce(updated);

    await act(async () => {
      await result.current.refetch();
    });

    expect(result.current.data).toEqual(updated);
  });
});
