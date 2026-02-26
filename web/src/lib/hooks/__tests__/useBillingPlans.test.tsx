/**
 * @jest-environment jsdom
 */
import { renderHook, waitFor, act } from '@testing-library/react';
import { useBillingPlans } from '../useBillingPlans';

jest.mock('@/lib/api/billing', () => ({
  getBillingPlans: jest.fn(),
}));

import { getBillingPlans } from '@/lib/api/billing';

const mockGetBillingPlans = getBillingPlans as jest.MockedFunction<
  typeof getBillingPlans
>;

const mockPlans = [
  {
    slug: 'free',
    name: 'Free',
    price_eur_monthly: 0,
    monthly_cost_limit_eur: 5,
    window_5h_cost_limit_eur: 1,
    window_7d_cost_limit_eur: 3,
    credit_markup_factor: 1.6,
    markup_percentage: 60,
  },
];

describe('useBillingPlans', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('fetches billing plans on mount', async () => {
    mockGetBillingPlans.mockResolvedValueOnce({ plans: mockPlans });

    const { result } = renderHook(() => useBillingPlans());

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.plans).toEqual(mockPlans);
    expect(result.current.error).toBeNull();
  });

  it('sets error on failure', async () => {
    mockGetBillingPlans.mockRejectedValueOnce(new Error('Errore rete'));

    const { result } = renderHook(() => useBillingPlans());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.plans).toEqual([]);
    expect(result.current.error).toBe('Errore rete');
  });

  it('handles non-Error exceptions', async () => {
    mockGetBillingPlans.mockRejectedValueOnce(42);

    const { result } = renderHook(() => useBillingPlans());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('Errore sconosciuto');
  });

  it('supports refetch', async () => {
    mockGetBillingPlans.mockResolvedValueOnce({ plans: mockPlans });

    const { result } = renderHook(() => useBillingPlans());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const updatedPlans = [{ ...mockPlans[0], name: 'Premium' }];
    mockGetBillingPlans.mockResolvedValueOnce({ plans: updatedPlans });

    await act(async () => {
      await result.current.refetch();
    });

    expect(result.current.plans).toEqual(updatedPlans);
  });
});
