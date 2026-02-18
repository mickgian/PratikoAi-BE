/**
 * @jest-environment jsdom
 */

import { render, screen, waitFor } from '@testing-library/react';
import { useSearchParams } from 'next/navigation';
import { ComparisonDashboard } from '../ComparisonDashboard';
import { getPendingComparison } from '@/lib/api/modelComparison';
import { useExpertStatus } from '@/hooks/useExpertStatus';
import { useComparison } from '../../hooks/useComparison';
import { useLeaderboard } from '../../hooks/useLeaderboard';

// Mock all dependencies
jest.mock('next/navigation', () => ({
  useSearchParams: jest.fn(),
}));

jest.mock('@/lib/api/modelComparison', () => ({
  getPendingComparison: jest.fn(),
}));

jest.mock('@/hooks/useExpertStatus', () => ({
  useExpertStatus: jest.fn(),
}));

jest.mock('../../hooks/useComparison', () => ({
  useComparison: jest.fn(),
}));

jest.mock('../../hooks/useLeaderboard', () => ({
  useLeaderboard: jest.fn(),
}));

// Default mock implementations
const mockFetchModels = jest.fn();
const mockFetchStats = jest.fn();
const mockRun = jest.fn();
const mockRunWithExisting = jest.fn().mockResolvedValue(undefined);
const mockVote = jest.fn();
const mockClearComparison = jest.fn();
const mockSetError = jest.fn();

const createComparisonHook = (overrides = {}) => ({
  comparison: null,
  models: [],
  stats: null,
  isRunning: false,
  isVoting: false,
  isLoadingModels: false,
  isLoadingStats: false,
  error: null,
  voteResult: null,
  fetchModels: mockFetchModels,
  fetchStats: mockFetchStats,
  run: mockRun,
  runWithExisting: mockRunWithExisting,
  vote: mockVote,
  clearComparison: mockClearComparison,
  setError: mockSetError,
  ...overrides,
});

const defaultLeaderboardHook = {
  rankings: [],
  lastUpdated: null,
  isLoading: false,
  refetch: jest.fn(),
};

describe('ComparisonDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Clear sessionStorage to prevent stale data from affecting tests
    sessionStorage.clear();

    // Reset mockRunWithExisting to return a resolved promise
    mockRunWithExisting.mockResolvedValue(undefined);

    // Default: user is super_user
    (useExpertStatus as jest.Mock).mockReturnValue({
      isSuperUser: true,
      isLoading: false,
    });

    // Default: no URL params
    (useSearchParams as jest.Mock).mockReturnValue({
      get: jest.fn().mockReturnValue(null),
    });

    // Default hooks
    (useComparison as jest.Mock).mockReturnValue(createComparisonHook());
    (useLeaderboard as jest.Mock).mockReturnValue(defaultLeaderboardHook);
  });

  describe('access control', () => {
    it('should show loading state when auth is loading', () => {
      (useExpertStatus as jest.Mock).mockReturnValue({
        isSuperUser: false,
        isLoading: true,
      });

      render(<ComparisonDashboard />);

      expect(
        screen.getByText('Verifica autorizzazione...')
      ).toBeInTheDocument();
    });

    it('should show access denied for non-super users', () => {
      (useExpertStatus as jest.Mock).mockReturnValue({
        isSuperUser: false,
        isLoading: false,
      });

      render(<ComparisonDashboard />);

      expect(screen.getByTestId('access-denied')).toBeInTheDocument();
      expect(screen.getByText('Accesso non autorizzato')).toBeInTheDocument();
    });

    it('should show dashboard for super users', () => {
      render(<ComparisonDashboard />);

      expect(screen.getByTestId('comparison-dashboard')).toBeInTheDocument();
      expect(screen.getByText('Confronto Modelli LLM')).toBeInTheDocument();
    });
  });

  describe('pending comparison error handling', () => {
    it('should call setError when pending comparison fetch fails with 404', async () => {
      // Setup: URL has pending param
      (useSearchParams as jest.Mock).mockReturnValue({
        get: jest.fn().mockImplementation((key: string) => {
          if (key === 'pending') return 'invalid-uuid-that-does-not-exist';
          return null;
        }),
      });

      // Setup: getPendingComparison rejects with 404-like error
      (getPendingComparison as jest.Mock).mockRejectedValueOnce(
        new Error('Pending comparison not found')
      );

      render(<ComparisonDashboard />);

      // Component maps "not found" errors to Italian user-friendly message
      await waitFor(() => {
        expect(mockSetError).toHaveBeenCalledWith(
          'Il confronto richiesto non è più disponibile. Torna alla chat e clicca nuovamente su "Confronta Modelli".'
        );
      });
    });

    it('should call setError when pending comparison is expired', async () => {
      // Setup: URL has pending param
      (useSearchParams as jest.Mock).mockReturnValue({
        get: jest.fn().mockImplementation((key: string) => {
          if (key === 'pending') return 'expired-uuid';
          return null;
        }),
      });

      // Setup: getPendingComparison rejects with expiry error
      (getPendingComparison as jest.Mock).mockRejectedValueOnce(
        new Error('Pending comparison expired')
      );

      render(<ComparisonDashboard />);

      // Component maps "expired" errors to Italian user-friendly message
      await waitFor(() => {
        expect(mockSetError).toHaveBeenCalledWith(
          'Il confronto è scaduto (validità 1 ora). Torna alla chat e clicca nuovamente su "Confronta Modelli".'
        );
      });
    });

    it('should call setError when network fails during pending comparison fetch', async () => {
      // Setup: URL has pending param
      (useSearchParams as jest.Mock).mockReturnValue({
        get: jest.fn().mockImplementation((key: string) => {
          if (key === 'pending') return 'valid-uuid';
          return null;
        }),
      });

      // Setup: getPendingComparison rejects with network error
      (getPendingComparison as jest.Mock).mockRejectedValueOnce(
        new Error('Impossibile connettersi al server')
      );

      render(<ComparisonDashboard />);

      // Wait for setError to be called
      await waitFor(() => {
        expect(mockSetError).toHaveBeenCalledWith(
          'Impossibile connettersi al server'
        );
      });
    });

    it('should handle non-Error exceptions by converting to string', async () => {
      // Setup: URL has pending param
      (useSearchParams as jest.Mock).mockReturnValue({
        get: jest.fn().mockImplementation((key: string) => {
          if (key === 'pending') return 'valid-uuid';
          return null;
        }),
      });

      // Setup: getPendingComparison rejects with non-Error
      (getPendingComparison as jest.Mock).mockRejectedValueOnce(
        'String error instead of Error object'
      );

      render(<ComparisonDashboard />);

      // Component uses String(err) for non-Error exceptions
      await waitFor(() => {
        expect(mockSetError).toHaveBeenCalledWith(
          'String error instead of Error object'
        );
      });
    });

    it('should display error in UI when error state is set', () => {
      // Setup: hook returns with an error
      (useComparison as jest.Mock).mockReturnValue(
        createComparisonHook({ error: 'Test error message' })
      );

      render(<ComparisonDashboard />);

      // Error should be displayed in the error banner
      expect(screen.getByText('Test error message')).toBeInTheDocument();
    });
  });

  describe('successful pending comparison', () => {
    it('should call runWithExisting when pending comparison is fetched', async () => {
      const pendingData = {
        query: 'Test query',
        response: 'Test response',
        model_id: 'openai:gpt-4o',
        latency_ms: 1500,
        cost_eur: 0.002,
        input_tokens: 100,
        output_tokens: 50,
      };

      // Setup: URL has pending param
      (useSearchParams as jest.Mock).mockReturnValue({
        get: jest.fn().mockImplementation((key: string) => {
          if (key === 'pending') return 'valid-pending-id';
          return null;
        }),
      });

      // Setup: getPendingComparison resolves with data
      (getPendingComparison as jest.Mock).mockResolvedValueOnce(pendingData);

      render(<ComparisonDashboard />);

      await waitFor(() => {
        expect(getPendingComparison).toHaveBeenCalledWith('valid-pending-id');
      });

      await waitFor(() => {
        expect(mockRunWithExisting).toHaveBeenCalledWith(
          pendingData.query,
          expect.objectContaining({
            model_id: pendingData.model_id,
            response_text: pendingData.response,
          }),
          undefined, // enriched_prompt (not in test data)
          undefined // selectedModelIds (not in URL)
        );
      });
    });

    it('should not call setError on success', async () => {
      const pendingData = {
        query: 'Test query',
        response: 'Test response',
        model_id: 'openai:gpt-4o',
        latency_ms: 1500,
        cost_eur: 0.002,
        input_tokens: 100,
        output_tokens: 50,
      };

      (useSearchParams as jest.Mock).mockReturnValue({
        get: jest.fn().mockImplementation((key: string) => {
          if (key === 'pending') return 'valid-pending-id';
          return null;
        }),
      });

      (getPendingComparison as jest.Mock).mockResolvedValueOnce(pendingData);

      render(<ComparisonDashboard />);

      await waitFor(() => {
        expect(mockRunWithExisting).toHaveBeenCalled();
      });

      // setError should not have been called
      expect(mockSetError).not.toHaveBeenCalled();
    });
  });
});
