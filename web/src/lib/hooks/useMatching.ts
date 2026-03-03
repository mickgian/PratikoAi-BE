/**
 * Hook for normative matching suggestions.
 */

'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  SuggestionResponse,
  dismissSuggestion,
  listSuggestions,
  markAsRead,
} from '@/lib/api/matching';
import { getStudioId } from '@/lib/api/helpers';

export function useMatching() {
  const [suggestions, setSuggestions] = useState<SuggestionResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!getStudioId()) {
      setError('Studio non configurato');
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const result = await listSuggestions();
      setSuggestions(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore nel caricamento');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const handleMarkAsRead = useCallback(async (ids: string[]) => {
    for (const id of ids) {
      await markAsRead(id);
    }
    setSuggestions(prev =>
      prev.map(s => (ids.includes(s.id) ? { ...s, is_read: true } : s))
    );
  }, []);

  const handleDismiss = useCallback(async (ids: string[]) => {
    for (const id of ids) {
      await dismissSuggestion(id);
    }
    setSuggestions(prev =>
      prev.map(s => (ids.includes(s.id) ? { ...s, is_dismissed: true } : s))
    );
  }, []);

  return {
    suggestions,
    isLoading,
    error,
    refresh: fetch,
    markAsRead: handleMarkAsRead,
    dismiss: handleDismiss,
  };
}
