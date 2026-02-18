'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  getCreditTransactions,
  type CreditTransaction,
} from '@/lib/api/billing';

export function useCreditTransactions() {
  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getCreditTransactions();
      setTransactions(response.transactions);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Errore sconosciuto');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { transactions, loading, error, refetch: fetch };
}
