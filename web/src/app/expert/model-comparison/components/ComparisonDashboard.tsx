'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { useExpertStatus } from '@/hooks/useExpertStatus';
import { useComparison } from '../hooks/useComparison';
import { useLeaderboard } from '../hooks/useLeaderboard';
import { ComparisonGrid } from './ComparisonGrid';
import { Leaderboard } from './Leaderboard';
import {
  getPendingComparison,
  markPendingUsed,
  getComparisonSession,
  getUnevaluatedSessions,
} from '@/lib/api/modelComparison';
import type { ComparisonSessionDetail } from '@/types/modelComparison';

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

  const [selectedWinner, setSelectedWinner] = useState<string | null>(null);
  const [voteComment, setVoteComment] = useState('');
  const [activeTab, setActiveTab] = useState<'compare' | 'leaderboard'>(
    'compare'
  );
  const [currentModelId, setCurrentModelId] = useState<string | null>(null);
  const [isLoadingSession, setIsLoadingSession] = useState(false);

  // Unevaluated sessions list
  const [unevaluatedSessions, setUnevaluatedSessions] = useState<
    ComparisonSessionDetail[]
  >([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] =
    useState<ComparisonSessionDetail | null>(null);
  const [isLoadingUnevaluated, setIsLoadingUnevaluated] = useState(false);

  const pendingId = searchParams.get('pending');

  // Fetch all unevaluated sessions from backend
  const fetchUnevaluated = useCallback(async () => {
    try {
      setIsLoadingUnevaluated(true);
      const response = await getUnevaluatedSessions();
      setUnevaluatedSessions(response.sessions);
    } catch (err) {
      console.error('Failed to fetch unevaluated sessions:', err);
    } finally {
      setIsLoadingUnevaluated(false);
    }
  }, []);

  // Load stats and unevaluated sessions on mount
  useEffect(() => {
    if (isSuperUser) {
      fetchStats();
      fetchUnevaluated();
    }
  }, [isSuperUser, fetchStats, fetchUnevaluated]);

  // When a session is selected from the list, load its details into comparison state
  useEffect(() => {
    if (!selectedBatchId) {
      setSelectedSession(null);
      return;
    }
    const session = unevaluatedSessions.find(
      s => s.batch_id === selectedBatchId
    );
    if (!session) return;

    setSelectedSession(session);
    setSelectedWinner(null);
    setVoteComment('');
    restoreComparison({
      comparison: {
        batch_id: session.batch_id,
        query: session.query,
        responses: session.responses.map(r => ({
          model_id: r.model_id,
          provider:
            r.provider as import('@/types/modelComparison').ModelProvider,
          model_name: r.model_name,
          response_text: r.response_text,
          latency_ms: r.latency_ms,
          cost_eur: r.cost_eur,
          cost_usd: r.cost_usd,
          input_tokens: r.input_tokens,
          output_tokens: r.output_tokens,
          status: r.status,
          error_message: r.error_message,
          trace_id: r.trace_id,
        })),
        created_at: session.created_at,
      },
      voteResult: null,
    });
  }, [selectedBatchId, unevaluatedSessions, restoreComparison]);

  // Handle incoming pending comparison from chat
  useEffect(() => {
    if (!isBrowser) return;

    if (!isSuperUser || isAuthLoading || isRunning || !pendingId) return;

    const cacheKey = `pending_comparison_${pendingId}`;
    const processedKey = `processed_${pendingId}`;

    try {
      if (sessionStorage.getItem(processedKey)) return;
    } catch {
      // sessionStorage may be disabled
    }

    const processPendingData = (
      data: import('@/types/modelComparison').PendingComparisonData
    ) => {
      setCurrentModelId(data.model_id);

      // If comparison was already used, just refresh the list
      if (data.comparison_used && data.batch_id) {
        setIsLoadingSession(true);
        fetchUnevaluated()
          .then(() => setSelectedBatchId(data.batch_id!))
          .finally(() => setIsLoadingSession(false));
        return;
      }

      const existingResponse = {
        model_id: data.model_id,
        response_text: data.response,
        latency_ms: data.latency_ms ?? 0,
        cost_eur: data.cost_eur ?? null,
        input_tokens: data.input_tokens ?? null,
        output_tokens: data.output_tokens ?? null,
        trace_id: data.trace_id ?? null,
      };

      const modelsParam = searchParams.get('models');
      const selectedModelIds = modelsParam
        ? decodeURIComponent(modelsParam).split(',')
        : undefined;

      runWithExisting(
        data.query,
        existingResponse,
        data.enriched_prompt,
        selectedModelIds
      )
        .then(result => {
          if (result?.batch_id && pendingId) {
            markPendingUsed(pendingId, result.batch_id).catch(err =>
              console.warn('Failed to mark pending as used:', err)
            );
            // Refresh unevaluated list and select the new session
            fetchUnevaluated().then(() => setSelectedBatchId(result.batch_id));
          }
          try {
            sessionStorage.removeItem(cacheKey);
          } catch {
            // Ignore
          }
        })
        .catch(() => {
          // Keep cache on error
        });
    };

    let cached: string | null = null;
    try {
      cached = sessionStorage.getItem(cacheKey);
    } catch {
      // sessionStorage may be disabled
    }

    if (cached) {
      try {
        sessionStorage.setItem(processedKey, 'true');
        const data = JSON.parse(
          cached
        ) as import('@/types/modelComparison').PendingComparisonData;
        processPendingData(data);
      } catch {
        try {
          sessionStorage.removeItem(cacheKey);
          sessionStorage.removeItem(processedKey);
        } catch {
          // Ignore
        }
        setError(
          'Dati del confronto corrotti. Torna alla chat e clicca nuovamente su "Confronta Modelli".'
        );
      }
      return;
    }

    try {
      sessionStorage.setItem(processedKey, 'true');
    } catch {
      // Ignore
    }

    getPendingComparison(pendingId)
      .then(data => {
        try {
          sessionStorage.setItem(cacheKey, JSON.stringify(data));
        } catch {
          // Ignore
        }
        processPendingData(data);
      })
      .catch(err => {
        try {
          sessionStorage.removeItem(processedKey);
        } catch {
          // Ignore
        }
        const errorMessage = err instanceof Error ? err.message : String(err);
        if (
          errorMessage.includes('non trovato') ||
          errorMessage.includes('not found')
        ) {
          setError(
            'Il confronto richiesto non è stato trovato. Torna alla chat e clicca nuovamente su "Confronta Modelli".'
          );
        } else {
          setError(errorMessage || 'Errore nel caricamento del confronto');
        }
      });
  }, [
    isSuperUser,
    isAuthLoading,
    isRunning,
    pendingId,
    searchParams,
    runWithExisting,
    setError,
    fetchUnevaluated,
  ]);

  const handleVote = useCallback(async () => {
    if (!comparison || !selectedWinner) return;
    try {
      await vote(comparison.batch_id, selectedWinner, voteComment || undefined);
      refetchLeaderboard();
      // After voting, refresh the unevaluated list and clear selection
      await fetchUnevaluated();
      setSelectedBatchId(null);
      setSelectedWinner(null);
      setVoteComment('');
    } catch {
      // Error is handled in the hook
    }
  }, [
    comparison,
    selectedWinner,
    voteComment,
    vote,
    refetchLeaderboard,
    fetchUnevaluated,
  ]);

  // Select a session from the list
  const handleSelectSession = useCallback(
    (batchId: string) => {
      if (selectedBatchId === batchId) {
        setSelectedBatchId(null);
      } else {
        setSelectedBatchId(batchId);
      }
    },
    [selectedBatchId]
  );

  if (isAuthLoading) {
    return (
      <div className="min-h-screen bg-[#F8F5F1] flex items-center justify-center">
        <div className="text-gray-500">Verifica autorizzazione...</div>
      </div>
    );
  }

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

  const unevaluatedCount = unevaluatedSessions.length;

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
                {unevaluatedCount > 0 && (
                  <div className="text-center">
                    <div className="font-semibold text-amber-600">
                      {unevaluatedCount}
                    </div>
                    <div className="text-gray-500 text-xs">Da valutare</div>
                  </div>
                )}
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
              {unevaluatedCount > 0 && (
                <span className="ml-1.5 inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-medium bg-amber-100 text-amber-700 rounded-full">
                  {unevaluatedCount}
                </span>
              )}
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
            {/* Info box */}
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
                  <ul className="space-y-0.5 text-blue-700">
                    <li>
                      I confronti sono <strong>permanenti</strong>: puoi tornare
                      quando vuoi
                    </li>
                    <li>
                      Valuta ogni risposta come <strong>Corretta</strong>,{' '}
                      <strong>Incompleta</strong> o <strong>Errata</strong>
                    </li>
                    <li>
                      Vota il modello migliore per aggiornare la classifica Elo
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Loading indicator when processing a new comparison from chat */}
            {(isRunning || isLoadingSession) && !comparison && (
              <div
                className="bg-white rounded-lg border border-gray-200 p-8 text-center"
                data-testid="comparison-loading"
              >
                <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-4" />
                <p className="text-gray-600">
                  {isLoadingSession
                    ? 'Caricamento sessione salvata...'
                    : 'Confrontando i modelli...'}
                </p>
              </div>
            )}

            {/* Unevaluated sessions list */}
            {!isLoadingUnevaluated &&
              unevaluatedSessions.length > 0 &&
              !isRunning && (
                <div data-testid="unevaluated-sessions-list">
                  <h2 className="text-sm font-semibold text-gray-700 mb-2">
                    Confronti da valutare ({unevaluatedSessions.length})
                  </h2>
                  <div className="grid gap-2">
                    {unevaluatedSessions.map(session => (
                      <button
                        key={session.batch_id}
                        onClick={() => handleSelectSession(session.batch_id)}
                        className={`w-full text-left bg-white rounded-lg border p-3 transition-colors hover:border-blue-300 ${
                          selectedBatchId === session.batch_id
                            ? 'border-blue-500 ring-1 ring-blue-500'
                            : 'border-gray-200'
                        }`}
                        data-testid={`session-card-${session.batch_id}`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-gray-900 truncate">
                              {session.query}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              <span className="text-xs text-gray-500">
                                {session.responses.length} modelli
                              </span>
                              <span className="text-xs text-gray-400">
                                {new Date(
                                  session.created_at
                                ).toLocaleDateString('it-IT', {
                                  day: '2-digit',
                                  month: 'short',
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })}
                              </span>
                            </div>
                          </div>
                          <div className="flex-shrink-0">
                            {selectedBatchId === session.batch_id ? (
                              <svg
                                className="w-5 h-5 text-blue-500"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                                  clipRule="evenodd"
                                />
                              </svg>
                            ) : (
                              <svg
                                className="w-5 h-5 text-gray-400"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                                  clipRule="evenodd"
                                />
                              </svg>
                            )}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

            {/* Loading unevaluated sessions */}
            {isLoadingUnevaluated && !isRunning && (
              <div className="bg-white rounded-lg border border-gray-200 p-6 text-center">
                <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2" />
                <p className="text-sm text-gray-600">
                  Caricamento confronti...
                </p>
              </div>
            )}

            {/* Empty state - no sessions at all */}
            {!isLoadingUnevaluated &&
              unevaluatedSessions.length === 0 &&
              !comparison &&
              !isRunning &&
              !isLoadingSession && (
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
                    {stats && stats.total_comparisons > 0
                      ? 'Tutti i confronti sono stati valutati!'
                      : 'Inizia dalla Chat'}
                  </h3>
                  <p className="text-gray-600 mb-4 max-w-md mx-auto">
                    {stats && stats.total_comparisons > 0
                      ? 'Hai votato tutti i confronti. Torna alla chat per crearne di nuovi.'
                      : 'Per confrontare i modelli, vai alla pagina Chat, fai una domanda e clicca sul pulsante "Confronta Modelli" nella risposta.'}
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

            {/* Selected session detail */}
            {comparison && selectedBatchId && (
              <div className="space-y-4">
                {/* Query display */}
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <div className="text-sm text-gray-500 mb-1">Domanda:</div>
                  <div className="text-gray-900">{comparison.query}</div>
                </div>

                {/* Response grid */}
                <ComparisonGrid
                  responses={selectedSession?.responses ?? comparison.responses}
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
                    {unevaluatedSessions.length > 0 ? (
                      <p className="text-sm text-green-700">
                        Hai ancora {unevaluatedSessions.length} confronti da
                        valutare. Selezionane uno dalla lista.
                      </p>
                    ) : (
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
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Active comparison from pending (not yet in unevaluated list) */}
            {comparison && !selectedBatchId && !isRunning && (
              <div className="space-y-4">
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <div className="text-sm text-gray-500 mb-1">Domanda:</div>
                  <div className="text-gray-900">{comparison.query}</div>
                </div>

                <ComparisonGrid
                  responses={comparison.responses}
                  selectedWinner={selectedWinner}
                  onSelectWinner={setSelectedWinner}
                  isVoting={isVoting}
                  hasVoted={!!voteResult}
                  currentModelId={currentModelId}
                />

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
                    <a
                      href="/chat"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700"
                    >
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
