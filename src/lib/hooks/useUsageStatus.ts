'use client';

import { useState, useEffect, useCallback } from 'react';
import { getUsageStatus, type UsageStatus } from '@/lib/api/billing';

export function useUsageStatus() {
  const [data, setData] = useState<UsageStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const status = await getUsageStatus();
      setData(status);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Errore sconosciuto');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, loading, error, refetch: fetch };
}
