'use client';

import { useState, useEffect, useCallback } from 'react';
import { getBillingPlans, type BillingPlan } from '@/lib/api/billing';

export function useBillingPlans() {
  const [plans, setPlans] = useState<BillingPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getBillingPlans();
      setPlans(response.plans);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Errore sconosciuto');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { plans, loading, error, refetch: fetch };
}
