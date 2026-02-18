'use client';

import { useState, useCallback } from 'react';
import { submitLabel, skipQuery } from '@/lib/api/intentLabeling';

export function useLabelSubmission() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    async (queryId: string, expertIntent: string, notes?: string) => {
      try {
        setIsSubmitting(true);
        setError(null);
        const result = await submitLabel({
          query_id: queryId,
          expert_intent: expertIntent,
          notes,
        });
        return result;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Errore nell'invio della label";
        setError(message);
        throw err;
      } finally {
        setIsSubmitting(false);
      }
    },
    []
  );

  const handleSkip = useCallback(async (queryId: string) => {
    try {
      setIsSubmitting(true);
      setError(null);
      const result = await skipQuery(queryId);
      return result;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Errore nel saltare la query';
      setError(message);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return { isSubmitting, error, handleSubmit, handleSkip, clearError };
}
