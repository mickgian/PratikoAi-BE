'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ModelResponseInfo } from '@/types/modelComparison';

interface ComparisonGridProps {
  responses: ModelResponseInfo[];
  selectedWinner: string | null;
  onSelectWinner: (modelId: string) => void;
  isVoting: boolean;
  hasVoted: boolean;
  /** Model ID of the current production model (for badge display) */
  currentModelId?: string | null;
}

const PROVIDER_COLORS: Record<string, string> = {
  openai: 'border-green-500 bg-green-50',
  anthropic: 'border-amber-500 bg-amber-50',
  gemini: 'border-blue-500 bg-blue-50',
  mistral: 'border-purple-500 bg-purple-50',
};

const PROVIDER_ICONS: Record<string, string> = {
  openai: '🤖',
  anthropic: '🧠',
  gemini: '💎',
  mistral: '🌬️',
};

function formatLatency(ms: number): string {
  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(1)}s`;
  }
  return `${ms}ms`;
}

function formatCost(eur: number | null): string {
  if (eur === null) return '—';
  if (eur < 0.001) return '<€0.001';
  return `€${eur.toFixed(3)}`;
}

function formatCostUsd(usd: number | null): string {
  if (usd === null) return '—';
  if (usd < 0.001) return '<$0.001';
  return `$${usd.toFixed(3)}`;
}

function formatTokens(input: number | null, output: number | null): string {
  if (input === null && output === null) return '—';
  const inStr = input !== null ? input.toString() : '?';
  const outStr = output !== null ? output.toString() : '?';
  return `${inStr}→${outStr}`;
}

export function ComparisonGrid({
  responses,
  selectedWinner,
  onSelectWinner,
  isVoting,
  hasVoted,
  currentModelId,
}: ComparisonGridProps) {
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());

  const toggleExpand = (modelId: string) => {
    setExpandedCards(prev => {
      const next = new Set(prev);
      if (next.has(modelId)) {
        next.delete(modelId);
      } else {
        next.add(modelId);
      }
      return next;
    });
  };

  const successResponses = responses.filter(r => r.status === 'success');
  const failedResponses = responses.filter(r => r.status !== 'success');

  const gridCols =
    successResponses.length <= 2
      ? 'md:grid-cols-2'
      : successResponses.length <= 3
        ? 'md:grid-cols-3'
        : 'md:grid-cols-2 lg:grid-cols-3';

  return (
    <div className="space-y-4">
      {/* Success responses grid */}
      <div className={`grid grid-cols-1 ${gridCols} gap-4`}>
        {successResponses.map(response => {
          const isSelected = selectedWinner === response.model_id;
          const isExpanded = expandedCards.has(response.model_id);
          const providerColor =
            PROVIDER_COLORS[response.provider] || 'border-gray-300 bg-gray-50';
          const providerIcon = PROVIDER_ICONS[response.provider] || '🔮';

          return (
            <div
              key={response.model_id}
              className={`
                relative rounded-lg border-2 transition-all duration-200
                ${providerColor}
                ${isSelected ? 'ring-2 ring-blue-500 ring-offset-2' : ''}
                ${!hasVoted && !isVoting ? 'hover:shadow-lg cursor-pointer' : ''}
              `}
              onClick={() =>
                !hasVoted && !isVoting && onSelectWinner(response.model_id)
              }
            >
              {/* Header */}
              <div className="p-3 border-b border-gray-200 bg-white bg-opacity-80">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{providerIcon}</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900 text-sm">
                          {response.model_name}
                        </span>
                        {currentModelId === response.model_id && (
                          <span className="bg-green-100 text-green-800 text-xs px-2 py-0.5 rounded">
                            Modello Corrente
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 capitalize">
                        {response.provider}
                      </div>
                    </div>
                  </div>

                  {/* Selection indicator */}
                  {!hasVoted && (
                    <div
                      className={`
                        w-5 h-5 rounded-full border-2 flex items-center justify-center
                        ${isSelected ? 'border-blue-500 bg-blue-500' : 'border-gray-300'}
                      `}
                    >
                      {isSelected && (
                        <svg
                          className="w-3 h-3 text-white"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                      )}
                    </div>
                  )}

                  {hasVoted && isSelected && (
                    <span className="text-xs font-medium text-blue-600 bg-blue-100 px-2 py-1 rounded">
                      Vincitore
                    </span>
                  )}
                </div>

                {/* Metrics */}
                <div className="flex gap-3 mt-2 text-xs text-gray-500">
                  <span title="Latenza">
                    {formatLatency(response.latency_ms)}
                  </span>
                  <span title="Costo">
                    {formatCost(response.cost_eur)}
                    <br />
                    <span className="text-muted-foreground">
                      {formatCostUsd(response.cost_usd)}
                    </span>
                  </span>
                  <span title="Token (input→output)">
                    {formatTokens(
                      response.input_tokens,
                      response.output_tokens
                    )}
                  </span>
                </div>
              </div>

              {/* Response content */}
              <div className="p-3">
                <div
                  className={`
                    prose prose-sm max-w-none text-sm text-gray-700
                    ${!isExpanded ? 'line-clamp-6' : ''}
                  `}
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {response.response_text}
                  </ReactMarkdown>
                </div>

                {response.response_text.length > 300 && (
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      toggleExpand(response.model_id);
                    }}
                    className="mt-2 text-xs text-blue-600 hover:text-blue-800"
                  >
                    {isExpanded ? 'Mostra meno' : 'Mostra tutto'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Failed responses */}
      {failedResponses.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-gray-500 mb-2">
            Risposte fallite ({failedResponses.length})
          </h4>
          <div className="space-y-2">
            {failedResponses.map(response => (
              <div
                key={response.model_id}
                className="bg-red-50 border border-red-200 rounded-lg p-3"
              >
                <div className="flex items-center gap-2">
                  <span className="text-red-500">⚠️</span>
                  <span className="font-medium text-red-700 text-sm">
                    {response.model_name}
                  </span>
                  <span className="text-xs text-red-500 capitalize">
                    ({response.status})
                  </span>
                </div>
                {response.error_message && (
                  <p className="text-xs text-red-600 mt-1">
                    {response.error_message}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
