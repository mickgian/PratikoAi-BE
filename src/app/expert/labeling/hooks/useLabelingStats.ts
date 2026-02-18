'use client';

import { useState, useEffect, useCallback } from 'react';
import { getLabelingStats } from '@/lib/api/intentLabeling';
import type { LabelingStatsResponse } from '@/types/intentLabeling';

export function useLabelingStats() {
  const [stats, setStats] = useState<LabelingStatsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await getLabelingStats();
      setStats(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Errore nel caricamento delle statistiche'
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return { stats, isLoading, error, refetch: fetchStats };
}
