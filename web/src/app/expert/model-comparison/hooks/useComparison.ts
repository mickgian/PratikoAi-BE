'use client';

import { useState, useCallback } from 'react';
import {
  runComparison,
  runComparisonWithExisting,
  submitVote,
  getAvailableModels,
  updateModelPreferences,
  getUserStats,
} from '@/lib/api/modelComparison';
import type {
  ComparisonResponse,
  AvailableModel,
  VoteResponse,
  ComparisonStats,
  ExistingModelResponse,
} from '@/types/modelComparison';

export interface UseComparisonState {
  comparison: ComparisonResponse | null;
  models: AvailableModel[];
  stats: ComparisonStats | null;
  isRunning: boolean;
  isVoting: boolean;
  isLoadingModels: boolean;
  isLoadingStats: boolean;
  error: string | null;
  voteResult: VoteResponse | null;
}

export function useComparison() {
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [models, setModels] = useState<AvailableModel[]>([]);
  const [stats, setStats] = useState<ComparisonStats | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isVoting, setIsVoting] = useState(false);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [isLoadingStats, setIsLoadingStats] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [voteResult, setVoteResult] = useState<VoteResponse | null>(null);

  const fetchModels = useCallback(async () => {
    try {
      setIsLoadingModels(true);
      setError(null);
      const response = await getAvailableModels();
      setModels(response.models);
    } catch (err) {
      console.error('Failed to fetch models:', err);
      setError(
        err instanceof Error
          ? err.message
          : 'Errore nel caricamento dei modelli'
      );
    } finally {
      setIsLoadingModels(false);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      setIsLoadingStats(true);
      const response = await getUserStats();
      setStats(response.stats);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    } finally {
      setIsLoadingStats(false);
    }
  }, []);

  const run = useCallback(async (query: string, modelIds?: string[]) => {
    try {
      setIsRunning(true);
      setError(null);
      setComparison(null);
      setVoteResult(null);

      const result = await runComparison({ query, model_ids: modelIds });
      setComparison(result);
      return result;
    } catch (err) {
      console.error('Comparison failed:', err);
      const message =
        err instanceof Error ? err.message : 'Errore durante il confronto';
      setError(message);
      throw err;
    } finally {
      setIsRunning(false);
    }
  }, []);

  const runWithExisting = useCallback(
    async (
      query: string,
      existingResponse: ExistingModelResponse,
      enrichedPrompt?: string,
      modelIds?: string[]
    ) => {
      try {
        setIsRunning(true);
        setError(null);
        setComparison(null);
        setVoteResult(null);

        // DEV-256: Pass enriched_prompt so comparison models get same context as production
        // DEV-257: Pass model_ids if user selected models from chat
        const result = await runComparisonWithExisting({
          query,
          existing_response: existingResponse,
          enriched_prompt: enrichedPrompt,
          model_ids: modelIds,
        });
        setComparison(result);
        return result;
      } catch (err) {
        console.error('Comparison with existing failed:', err);
        const message =
          err instanceof Error ? err.message : 'Errore durante il confronto';
        setError(message);
        throw err;
      } finally {
        setIsRunning(false);
      }
    },
    []
  );

  const vote = useCallback(
    async (batchId: string, winnerModelId: string, comment?: string) => {
      try {
        setIsVoting(true);
        setError(null);

        const result = await submitVote({
          batch_id: batchId,
          winner_model_id: winnerModelId,
          comment,
        });
        setVoteResult(result);

        // Refresh stats after voting
        fetchStats();

        return result;
      } catch (err) {
        console.error('Vote failed:', err);
        const message =
          err instanceof Error ? err.message : 'Errore durante il voto';
        setError(message);
        throw err;
      } finally {
        setIsVoting(false);
      }
    },
    [fetchStats]
  );

  const savePreferences = useCallback(
    async (enabledModelIds: string[]) => {
      try {
        setError(null);
        await updateModelPreferences({ enabled_model_ids: enabledModelIds });
        // Refresh models after saving preferences
        await fetchModels();
      } catch (err) {
        console.error('Failed to save preferences:', err);
        const message =
          err instanceof Error
            ? err.message
            : 'Errore nel salvataggio delle preferenze';
        setError(message);
        throw err;
      }
    },
    [fetchModels]
  );

  const clearComparison = useCallback(() => {
    setComparison(null);
    setVoteResult(null);
    setError(null);
  }, []);

  const restoreComparison = useCallback(
    (data: {
      comparison: ComparisonResponse;
      voteResult?: VoteResponse | null;
    }) => {
      setComparison(data.comparison);
      if (data.voteResult !== undefined) {
        setVoteResult(data.voteResult);
      }
    },
    []
  );

  return {
    comparison,
    models,
    stats,
    isRunning,
    isVoting,
    isLoadingModels,
    isLoadingStats,
    error,
    voteResult,
    fetchModels,
    fetchStats,
    run,
    runWithExisting,
    vote,
    savePreferences,
    clearComparison,
    restoreComparison,
    setError,
  };
}
