'use client';

import { useState } from 'react';
import type { ModelRanking } from '@/types/modelComparison';

interface LeaderboardProps {
  rankings: ModelRanking[];
  isLoading: boolean;
  lastUpdated: string | null;
  onRefresh: () => void;
}

const PROVIDER_ICONS: Record<string, string> = {
  openai: '🤖',
  anthropic: '🧠',
  gemini: '💎',
  mistral: '🌬️',
};

const RANK_COLORS: Record<number, string> = {
  1: 'text-yellow-500',
  2: 'text-gray-400',
  3: 'text-amber-600',
};

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('it-IT', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function Leaderboard({
  rankings,
  isLoading,
  lastUpdated,
  onRefresh,
}: LeaderboardProps) {
  const [showEloInfo, setShowEloInfo] = useState(false);

  if (isLoading && rankings.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="h-12 bg-gray-100 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-900">Classifica Modelli</h3>
          {lastUpdated && (
            <p className="text-xs text-gray-500">
              Aggiornato: {formatDate(lastUpdated)}
            </p>
          )}
        </div>
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
          title="Aggiorna classifica"
        >
          <svg
            className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </button>
      </div>

      {/* Rankings */}
      {rankings.length === 0 ? (
        <div className="p-6 text-center text-gray-500">
          Nessun modello nella classifica.
          <br />
          Inizia a votare per vedere i risultati!
        </div>
      ) : (
        <div className="divide-y divide-gray-100">
          {rankings.map(model => {
            const providerIcon = PROVIDER_ICONS[model.provider] || '🔮';
            const rankColor = RANK_COLORS[model.rank] || 'text-gray-500';

            return (
              <div
                key={model.model_id}
                className="p-3 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {/* Rank */}
                  <div
                    className={`w-8 h-8 flex items-center justify-center font-bold text-lg ${rankColor}`}
                  >
                    {model.rank <= 3 ? (
                      <span className="text-xl">
                        {model.rank === 1
                          ? '🥇'
                          : model.rank === 2
                            ? '🥈'
                            : '🥉'}
                      </span>
                    ) : (
                      <span className="text-gray-400">{model.rank}</span>
                    )}
                  </div>

                  {/* Model info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span>{providerIcon}</span>
                      <span className="font-medium text-gray-900 truncate">
                        {model.display_name}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500">
                      {model.wins}/{model.total_comparisons} vittorie (
                      {(model.win_rate * 100).toFixed(0)}%)
                    </div>
                  </div>

                  {/* Elo rating */}
                  <div className="text-right">
                    <div className="font-semibold text-gray-900">
                      {model.elo_rating?.toFixed(0) ?? 'N/A'}
                    </div>
                    <div className="text-xs text-gray-500">Elo</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Elo Rating Explanation */}
      <div className="border-t border-gray-200">
        <button
          onClick={() => setShowEloInfo(!showEloInfo)}
          className="w-full p-3 flex items-center justify-between text-sm text-gray-600 hover:bg-gray-50 transition-colors"
        >
          <span className="flex items-center gap-2">
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
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            Cos&apos;è il punteggio Elo?
          </span>
          <svg
            className={`w-4 h-4 transition-transform ${showEloInfo ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>

        {showEloInfo && (
          <div className="px-4 pb-4 text-sm text-gray-600 space-y-3">
            <p>
              <strong>Elo</strong> è un sistema di classificazione
              originariamente progettato per gli scacchi. Ecco come funziona:
            </p>

            <div>
              <p className="font-medium text-gray-700 mb-1">
                Come viene calcolato:
              </p>
              <ul className="list-disc list-inside space-y-1 text-gray-600">
                <li>
                  Ogni modello parte da <strong>1500</strong> (Elo predefinito)
                </li>
                <li>
                  Quando voti per un vincitore:
                  <ul className="list-disc list-inside ml-4 mt-1">
                    <li>Il vincitore guadagna punti (+16 a +32)</li>
                    <li>I perdenti perdono punti (-16 a -32)</li>
                  </ul>
                </li>
                <li>Il fattore K è 32 (variazione massima per confronto)</li>
              </ul>
            </div>

            <div>
              <p className="font-medium text-gray-700 mb-1">La formula:</p>
              <ul className="list-disc list-inside space-y-1 text-gray-600">
                <li>
                  Se un modello con punteggio alto batte uno con punteggio basso
                  → <span className="text-green-600">guadagno piccolo</span>{' '}
                  (risultato atteso)
                </li>
                <li>
                  Se un modello con punteggio basso batte uno con punteggio alto
                  → <span className="text-blue-600">guadagno grande</span>{' '}
                  (sorpresa!)
                </li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
