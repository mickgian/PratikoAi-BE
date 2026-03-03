/**
 * Hooks for procedure catalog and progress tracking.
 */

'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  ProceduraResponse,
  ProceduraProgressResponse,
  advanceStep,
  listProcedure,
  listProgress,
  startProgress,
  updateChecklist,
  updateDocument,
  updateNotes,
} from '@/lib/api/procedure';
import { getStudioId } from '@/lib/api/helpers';

export function useProcedureList(category?: string) {
  const [procedures, setProcedures] = useState<ProceduraResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    listProcedure(category)
      .then(setProcedures)
      .catch(err => setError(err instanceof Error ? err.message : 'Errore'))
      .finally(() => setIsLoading(false));
  }, [category]);

  return { procedures, isLoading, error };
}

export function useProcedureProgress() {
  const [progressList, setProgressList] = useState<ProceduraProgressResponse[]>(
    []
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!getStudioId()) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    try {
      const result = await listProgress();
      setProgressList(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const handleStartProgress = useCallback(
    async (proceduraId: string, clientId?: number) => {
      const result = await startProgress(proceduraId, clientId);
      setProgressList(prev => [...prev, result]);
      return result;
    },
    []
  );

  const handleAdvanceStep = useCallback(async (progressId: string) => {
    const result = await advanceStep(progressId);
    setProgressList(prev => prev.map(p => (p.id === progressId ? result : p)));
    return result;
  }, []);

  return {
    progressList,
    isLoading,
    error,
    refresh: fetch,
    startProgress: handleStartProgress,
    advanceStep: handleAdvanceStep,
  };
}

export function useProcedureDetail(progressId: string | null) {
  const handleUpdateChecklist = useCallback(
    async (stepIndex: number, itemIndex: number, completed: boolean) => {
      if (!progressId) return;
      return updateChecklist(progressId, stepIndex, itemIndex, completed);
    },
    [progressId]
  );

  const handleUpdateNotes = useCallback(
    async (notes: string) => {
      if (!progressId) return;
      return updateNotes(progressId, notes);
    },
    [progressId]
  );

  const handleUpdateDocument = useCallback(
    async (documentName: string, verified: boolean) => {
      if (!progressId) return;
      return updateDocument(progressId, documentName, verified);
    },
    [progressId]
  );

  return {
    updateChecklist: handleUpdateChecklist,
    updateNotes: handleUpdateNotes,
    updateDocument: handleUpdateDocument,
  };
}
