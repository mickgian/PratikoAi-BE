/**
 * Hook for fetching dashboard data.
 */

'use client';

import { useCallback, useEffect, useState } from 'react';
import { DashboardResponse, getDashboardData } from '@/lib/api/dashboard';
import { getStudioId } from '@/lib/api/helpers';
import { Period } from '@/app/dashboard-analitica/types';

export function useDashboard(period: Period) {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    const studioId = getStudioId();
    if (!studioId) {
      setError('Studio non configurato');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const result = await getDashboardData(period);
      setData(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Errore nel caricamento della dashboard'
      );
    } finally {
      setIsLoading(false);
    }
  }, [period]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, isLoading, error, refresh: fetch };
}
