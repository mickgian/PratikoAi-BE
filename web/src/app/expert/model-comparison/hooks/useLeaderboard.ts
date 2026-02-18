'use client';

import { useState, useCallback, useEffect } from 'react';
import { getLeaderboard } from '@/lib/api/modelComparison';
import type { ModelRanking } from '@/types/modelComparison';

export function useLeaderboard(initialLimit = 20) {
  const [rankings, setRankings] = useState<ModelRanking[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLeaderboard = useCallback(
    async (limit: number = initialLimit) => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await getLeaderboard(limit);
        setRankings(response.rankings);
        setLastUpdated(response.last_updated);
      } catch (err) {
        console.error('Failed to fetch leaderboard:', err);
        setError(
          err instanceof Error
            ? err.message
            : 'Errore nel caricamento della classifica'
        );
      } finally {
        setIsLoading(false);
      }
    },
    [initialLimit]
  );

  useEffect(() => {
    fetchLeaderboard();
  }, [fetchLeaderboard]);

  return {
    rankings,
    lastUpdated,
    isLoading,
    error,
    refetch: fetchLeaderboard,
  };
}
