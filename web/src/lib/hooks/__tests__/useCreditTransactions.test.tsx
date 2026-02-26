/**
 * @jest-environment jsdom
 */
import { renderHook, waitFor, act } from '@testing-library/react';
import { useCreditTransactions } from '../useCreditTransactions';

jest.mock('@/lib/api/billing', () => ({
  getCreditTransactions: jest.fn(),
}));

import { getCreditTransactions } from '@/lib/api/billing';

const mockGetTransactions = getCreditTransactions as jest.MockedFunction<
  typeof getCreditTransactions
>;

const mockTransactions = [
  {
    id: 1,
    transaction_type: 'credit',
    amount_eur: 10.0,
    balance_after_eur: 10.0,
    description: 'Initial credit',
    created_at: '2026-01-01T00:00:00Z',
  },
];

describe('useCreditTransactions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('fetches transactions on mount', async () => {
    mockGetTransactions.mockResolvedValueOnce({
      transactions: mockTransactions,
      total: 1,
    });

    const { result } = renderHook(() => useCreditTransactions());

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.transactions).toEqual(mockTransactions);
    expect(result.current.error).toBeNull();
  });

  it('sets error on failure', async () => {
    mockGetTransactions.mockRejectedValueOnce(new Error('Errore rete'));

    const { result } = renderHook(() => useCreditTransactions());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.transactions).toEqual([]);
    expect(result.current.error).toBe('Errore rete');
  });

  it('handles non-Error exceptions', async () => {
    mockGetTransactions.mockRejectedValueOnce(undefined);

    const { result } = renderHook(() => useCreditTransactions());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('Errore sconosciuto');
  });

  it('supports refetch', async () => {
    mockGetTransactions.mockResolvedValueOnce({
      transactions: mockTransactions,
      total: 1,
    });

    const { result } = renderHook(() => useCreditTransactions());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const updated = [{ ...mockTransactions[0], amount_eur: 20.0 }];
    mockGetTransactions.mockResolvedValueOnce({
      transactions: updated,
      total: 1,
    });

    await act(async () => {
      await result.current.refetch();
    });

    expect(result.current.transactions).toEqual(updated);
  });
});
