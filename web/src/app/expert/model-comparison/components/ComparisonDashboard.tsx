'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { useExpertStatus } from '@/hooks/useExpertStatus';
import { useComparison } from '../hooks/useComparison';
import { useLeaderboard } from '../hooks/useLeaderboard';
import { ComparisonGrid } from './ComparisonGrid';
import { Leaderboard } from './Leaderboard';
import { getPendingComparison } from '@/lib/api/modelComparison';

// SSR guard - sessionStorage is only available in browser
const isBrowser = typeof window !== 'undefined';

export function ComparisonDashboard() {
  const searchParams = useSearchParams();
  const { isSuperUser, isLoading: isAuthLoading } = useExpertStatus();
  const {
    comparison,
    stats,
    isRunning,
    isVoting,
    isLoadingStats,
    error,
    voteResult,
    fetchStats,
    runWithExisting,
    vote,
    restoreComparison,
    setError,
  } = useComparison();
  const {
    rankings,
    lastUpdated,
    isLoading: isLeaderboardLoading,
    refetch: refetchLeaderboard,
  } = useLeaderboard();

  const [query, setQuery] = useState('');
  const [selectedWinner, setSelectedWinner] = useState<string | null>(null);
  const [voteComment, setVoteComment] = useState('');
  const [activeTab, setActiveTab] = useState<'compare' | 'leaderboard'>(
    'compare'
  );
  // Track the current model ID from URL params (for badge display)
  const [currentModelId, setCurrentModelId] = useState<string | null>(null);

  // Extract pendingId outside useEffect for stable dependency
  const pendingId = searchParams.get('pending');

  // Load stats on mount
  useEffect(() => {
    if (isSuperUser) {
      fetchStats();
    }
  }, [isSuperUser, fetchStats]);

  // Restore cached comparison results on mount (survives navigation away and back)
  // Uses a stable key so results persist even when URL has no ?pending= param
  useEffect(() => {
    if (!isBrowser) return;

    // If there's a new pending ID that hasn't been processed yet,
    // don't restore stale results - the pending data effect will handle it
    if (pendingId) {
      try {
        if (!sessionStorage.getItem(`processed_${pendingId}`)) {
          return; // New comparison incoming, skip restore
        }
      } catch {
        // sessionStorage may be disabled
      }
    }

    // Try pendingId-specific key first, then fall back to latest results
    const keys = pendingId
      ? [`comparison_results_${pendingId}`, 'latest_comparison_results']
      : ['latest_comparison_results'];

    for (const key of keys) {
      try {
        const cached = sessionStorage.getItem(key);
        if (cached) {
          const data = JSON.parse(cached);
          restoreComparison({
            comparison: data.comparison,
            voteResult: data.voteResult ?? null,
          });
          setCurrentModelId(data.currentModelId);
          setQuery(data.query);
          console.log(
            `🔄 [ComparisonDashboard] Restored cached comparison results from ${key}`
          );
          return;
        }
      } catch {
        // Ignore parse errors, try next key
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingId]);

  // Cache comparison results when they change (for navigation persistence)
  // Stores under both a pendingId-specific key and a stable "latest" key
  useEffect(() => {
    if (!isBrowser || !comparison) return;

    const payload = JSON.stringify({
      comparison,
      currentModelId,
      query,
      voteResult,
    });

    try {
      // Always cache under the stable key (works when navigating back without params)
      sessionStorage.setItem('latest_comparison_results', payload);
      // Also cache under pendingId key if available (for URL-specific restore)
      if (pendingId) {
        sessionStorage.setItem(`comparison_results_${pendingId}`, payload);
      }
    } catch {
      // Ignore sessionStorage errors
    }
  }, [comparison, voteResult, pendingId, currentModelId, query]);

  // DEV-256: Handle incoming response from main chat via backend database
  // Uses backend storage instead of sessionStorage to avoid race conditions with hydration
  // FIX: Added sessionStorage caching to survive page refreshes (backend deletes on first read)
  // FIX: Use sessionStorage for processed flag (survives page refresh, unlike useRef)
  useEffect(() => {
    // SSR guard - skip on server-side rendering
    if (!isBrowser) {
      return;
    }

    console.log('🔍 [ComparisonDashboard] Pending comparison check:', {
      pendingId,
      isSuperUser,
      isAuthLoading,
      isRunning,
    });

    if (!isSuperUser || isAuthLoading || isRunning || !pendingId) {
      console.log('⏸️ [ComparisonDashboard] Skipping - conditions not met');
      return;
    }

    const cacheKey = `pending_comparison_${pendingId}`;
    const processedKey = `processed_${pendingId}`;

    // Check if we've already processed this pendingId (survives page refresh)
    try {
      if (sessionStorage.getItem(processedKey)) {
        console.log(
          '⏭️ [ComparisonDashboard] Already processed this pendingId'
        );
        return;
      }
    } catch {
      // sessionStorage may be disabled in private browsing
    }

    // Helper to process pending data (used for both cached and API response)
    const processPendingData = (
      data: import('@/types/modelComparison').PendingComparisonData
    ) => {
      console.log('✅ [ComparisonDashboard] Processing pending data:', {
        queryLength: data.query?.length,
        responseLength: data.response?.length,
        model_id: data.model_id,
        hasEnrichedPrompt: !!data.enriched_prompt,
        latency_ms: data.latency_ms,
        cost_eur: data.cost_eur,
        output_tokens: data.output_tokens,
      });

      setQuery(data.query);
      setCurrentModelId(data.model_id);

      // DEV-256: Use actual metrics from pending comparison data
      const existingResponse = {
        model_id: data.model_id,
        response_text: data.response,
        latency_ms: data.latency_ms ?? 0,
        cost_eur: data.cost_eur ?? null,
        input_tokens: data.input_tokens ?? null,
        output_tokens: data.output_tokens ?? null,
        trace_id: data.trace_id ?? null,
      };

      // DEV-257: Get model IDs from URL params if user selected models from chat
      const modelsParam = searchParams.get('models');
      const selectedModelIds = modelsParam
        ? decodeURIComponent(modelsParam).split(',')
        : undefined;

      // Run comparison with the existing response
      // DEV-256: Pass enriched_prompt so comparison models get same context
      // DEV-257: Pass model_ids if user selected models from chat
      console.log(
        '🚀 [ComparisonDashboard] Running comparison with existing response',
        {
          hasEnrichedPrompt: !!data.enriched_prompt,
          selectedModelIds,
        }
      );
      runWithExisting(
        data.query,
        existingResponse,
        data.enriched_prompt,
        selectedModelIds
      )
        .then(() => {
          // FIX: Clear cache after comparison runs successfully
          console.log(
            '🧹 [ComparisonDashboard] Clearing cached pending data after successful comparison'
          );
          try {
            sessionStorage.removeItem(cacheKey);
          } catch {
            // Ignore sessionStorage errors
          }
        })
        .catch(() => {
          // Keep cache on error so user can retry
        });
    };

    // Check sessionStorage cache first (survives page refresh)
    // Backend deletes the record on first read, so we cache it client-side
    let cached: string | null = null;
    try {
      cached = sessionStorage.getItem(cacheKey);
    } catch {
      // sessionStorage may be disabled in private browsing
    }

    if (cached) {
      // Use cached data (page was refreshed)
      console.log(
        '📦 [ComparisonDashboard] Using cached pending data (page refresh)'
      );
      try {
        // Mark as processed BEFORE starting async work
        sessionStorage.setItem(processedKey, 'true');
        const data = JSON.parse(
          cached
        ) as import('@/types/modelComparison').PendingComparisonData;
        processPendingData(data);
      } catch (parseErr) {
        console.error(
          '❌ [ComparisonDashboard] Failed to parse cached data:',
          parseErr
        );
        try {
          sessionStorage.removeItem(cacheKey);
          sessionStorage.removeItem(processedKey);
        } catch {
          // Ignore sessionStorage errors
        }
        setError(
          'Dati del confronto corrotti. Torna alla chat e clicca nuovamente su "Confronta Modelli".'
        );
      }
      return;
    }

    // Mark as processed BEFORE starting async work to prevent race conditions
    try {
      sessionStorage.setItem(processedKey, 'true');
    } catch {
      // Ignore sessionStorage errors
    }

    // Fetch from API and cache for page refresh resilience
    console.log(
      '📥 [ComparisonDashboard] Fetching pending comparison from API:',
      pendingId
    );
    getPendingComparison(pendingId)
      .then(data => {
        // Cache for page refresh resilience (backend deletes on first read)
        console.log(
          '💾 [ComparisonDashboard] Caching pending data for page refresh resilience'
        );
        try {
          sessionStorage.setItem(cacheKey, JSON.stringify(data));
        } catch {
          // Ignore sessionStorage errors
        }
        processPendingData(data);
      })
      .catch(err => {
        console.error(
          '❌ [ComparisonDashboard] Failed to fetch pending comparison:',
          err
        );
        // Clear processed flag on error so user can retry
        try {
          sessionStorage.removeItem(processedKey);
        } catch {
          // Ignore sessionStorage errors
        }
        // DEV-256: Provide user-friendly error messages
        const errorMessage = err instanceof Error ? err.message : String(err);
        if (
          errorMessage.includes('non trovato') ||
          errorMessage.includes('not found')
        ) {
          setError(
            'Il confronto richiesto non è più disponibile. Torna alla chat e clicca nuovamente su "Confronta Modelli".'
          );
        } else if (
          errorMessage.includes('scaduto') ||
          errorMessage.includes('expired')
        ) {
          setError(
            'Il confronto è scaduto (validità 1 ora). Torna alla chat e clicca nuovamente su "Confronta Modelli".'
          );
        } else {
          setError(errorMessage || 'Errore nel caricamento del confronto');
        }
      });
  }, [
    isSuperUser,
    isAuthLoading,
    isRunning,
    pendingId, // Use extracted string instead of searchParams object
    searchParams, // Keep for modelsParam access inside processPendingData
    runWithExisting,
    setError,
  ]);

  const handleVote = useCallback(async () => {
    if (!comparison || !selectedWinner) return;
    try {
      await vote(comparison.batch_id, selectedWinner, voteComment || undefined);
      refetchLeaderboard();
    } catch {
      // Error is handled in the hook
    }
  }, [comparison, selectedWinner, voteComment, vote, refetchLeaderboard]);

  // Auth loading
  if (isAuthLoading) {
    return (
      <div className="min-h-screen bg-[#F8F5F1] flex items-center justify-center">
        <div className="text-gray-500">Verifica autorizzazione...</div>
      </div>
    );
  }

  // Access denied
  if (!isSuperUser) {
    return (
      <div
        className="min-h-screen bg-[#F8F5F1] flex items-center justify-center"
        data-testid="access-denied"
      >
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center max-w-md">
          <p className="text-lg font-medium text-gray-900 mb-2">
            Accesso non autorizzato
          </p>
          <p className="text-sm text-gray-500">
            Solo gli esperti e gli amministratori possono accedere al confronto
            modelli.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen bg-[#F8F5F1]"
      data-testid="comparison-dashboard"
    >
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                Confronto Modelli LLM
              </h1>
              <p className="text-sm text-gray-500">
                Confronta le risposte di diversi modelli e vota il migliore
              </p>
            </div>
            {stats && (
              <div className="hidden md:flex gap-4 text-sm">
                <div className="text-center">
                  <div className="font-semibold text-gray-900">
                    {stats.total_comparisons}
                  </div>
                  <div className="text-gray-500 text-xs">Confronti</div>
                </div>
                <div className="text-center">
                  <div className="font-semibold text-gray-900">
                    {stats.total_votes}
                  </div>
                  <div className="text-gray-500 text-xs">Voti</div>
                </div>
                {stats.favorite_model && (
                  <div className="text-center">
                    <div className="font-semibold text-gray-900 truncate max-w-[100px]">
                      {stats.favorite_model.split(':')[1]}
                    </div>
                    <div className="text-gray-500 text-xs">Preferito</div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Tabs */}
          <div className="flex gap-4 mt-4 border-b border-gray-200 -mb-px">
            <button
              onClick={() => setActiveTab('compare')}
              className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'compare'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Confronta
            </button>
            <button
              onClick={() => setActiveTab('leaderboard')}
              className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'leaderboard'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Classifica
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {activeTab === 'compare' ? (
          <div className="space-y-4">
            {/* Info box about pending comparisons */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
              <div className="flex items-start gap-2">
                <svg
                  className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <div>
                  <p className="font-medium mb-1">
                    Come funziona il confronto:
                  </p>
                  <ul className="list-disc list-inside space-y-0.5 text-blue-700">
                    <li>
                      I confronti dalla chat scadono dopo <strong>1 ora</strong>{' '}
                      se non utilizzati
                    </li>
                    <li>
                      Puoi ricaricare la pagina durante il confronto senza
                      perdere i dati
                    </li>
                    <li>
                      I dati vengono eliminati automaticamente dopo aver
                      completato il voto
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Loading indicator when auto-running comparison from chat */}
            {isRunning && !comparison && (
              <div
                className="bg-white rounded-lg border border-gray-200 p-8 text-center"
                data-testid="comparison-loading"
              >
                <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-4" />
                <p className="text-gray-600">Confrontando i modelli...</p>
              </div>
            )}

            {/* Prompt to use chat - show when no comparison is active */}
            {!comparison && !isRunning && (
              <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
                <svg
                  className="w-16 h-16 text-gray-300 mx-auto mb-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Inizia dalla Chat
                </h3>
                <p className="text-gray-600 mb-4 max-w-md mx-auto">
                  Per confrontare i modelli, vai alla{' '}
                  <a
                    href="/chat"
                    className="text-blue-600 hover:text-blue-800 font-medium"
                  >
                    pagina Chat
                  </a>
                  , fai una domanda e clicca sul pulsante{' '}
                  <strong>&quot;Confronta Modelli&quot;</strong> nella risposta.
                </p>
                <a
                  href="/chat"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                    />
                  </svg>
                  Vai alla Chat
                </a>
              </div>
            )}

            {/* Comparison results */}
            {comparison && (
              <div className="space-y-4">
                {/* Query display */}
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <div className="text-sm text-gray-500 mb-1">Domanda:</div>
                  <div className="text-gray-900">{comparison.query}</div>
                </div>

                {/* Response grid */}
                <ComparisonGrid
                  responses={comparison.responses}
                  selectedWinner={selectedWinner}
                  onSelectWinner={setSelectedWinner}
                  isVoting={isVoting}
                  hasVoted={!!voteResult}
                  currentModelId={currentModelId}
                />

                {/* Vote panel */}
                {!voteResult ? (
                  <div className="bg-white rounded-lg border border-gray-200 p-4">
                    <div className="flex flex-col md:flex-row gap-4">
                      <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Commento (opzionale)
                        </label>
                        <input
                          type="text"
                          value={voteComment}
                          onChange={e => setVoteComment(e.target.value)}
                          placeholder="Perché hai scelto questo modello?"
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          maxLength={1000}
                        />
                      </div>
                      <div className="flex items-end gap-2">
                        <button
                          onClick={handleVote}
                          disabled={!selectedWinner || isVoting}
                          className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                          {isVoting && (
                            <svg
                              className="animate-spin w-4 h-4"
                              viewBox="0 0 24 24"
                            >
                              <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                                fill="none"
                              />
                              <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                              />
                            </svg>
                          )}
                          {isVoting ? 'Votando...' : 'Vota vincitore'}
                        </button>
                        <a
                          href="/chat"
                          className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 inline-block"
                        >
                          Torna alla Chat
                        </a>
                      </div>
                    </div>
                    {!selectedWinner && (
                      <p className="text-xs text-gray-500 mt-2">
                        Clicca su una risposta per selezionarla come vincitrice
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="bg-green-50 rounded-lg border border-green-200 p-4">
                    <div className="flex items-center gap-2 text-green-700 mb-2">
                      <svg
                        className="w-5 h-5"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                          clipRule="evenodd"
                        />
                      </svg>
                      <span className="font-medium">Voto registrato!</span>
                    </div>
                    <p className="text-sm text-green-600 mb-3">
                      {voteResult.message}
                    </p>
                    <div className="text-xs text-green-600 mb-3">
                      Variazioni Elo:{' '}
                      {Object.entries(voteResult.elo_changes).map(
                        ([model, change], i) => (
                          <span key={model}>
                            {model.split(':')[1]}: {change > 0 ? '+' : ''}
                            {change.toFixed(1)}
                            {i <
                              Object.keys(voteResult.elo_changes).length - 1 &&
                              ', '}
                          </span>
                        )
                      )}
                    </div>
                    <a
                      href="/chat"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                        />
                      </svg>
                      Torna alla Chat per un nuovo confronto
                    </a>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <Leaderboard
            rankings={rankings}
            isLoading={isLeaderboardLoading}
            lastUpdated={lastUpdated}
            onRefresh={refetchLeaderboard}
          />
        )}
      </div>
    </div>
  );
}
