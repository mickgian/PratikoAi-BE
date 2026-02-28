'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type {
  ModelResponseInfo,
  ModelResponseDetail,
  ExpertEvaluationType,
} from '@/types/modelComparison';
import { submitExpertEvaluation } from '@/lib/api/modelComparison';

/** Union type: responses can come from live comparison or stored session */
type ResponseItem = ModelResponseInfo | ModelResponseDetail;

function isDetailResponse(r: ResponseItem): r is ModelResponseDetail {
  return 'response_id' in r;
}

interface ComparisonGridProps {
  responses: ResponseItem[];
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

/** Expert evaluation buttons for a single model response */
function EvaluationButtons({ response }: { response: ResponseItem }) {
  const detail = isDetailResponse(response) ? response : null;
  const responseId = detail?.response_id;

  const [evaluation, setEvaluation] = useState<ExpertEvaluationType | null>(
    (detail?.expert_evaluation as ExpertEvaluationType) ?? null
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [pendingEval, setPendingEval] = useState<ExpertEvaluationType | null>(
    null
  );
  const [detailsText, setDetailsText] = useState(
    detail?.expert_evaluation_details ?? ''
  );

  if (!responseId) return null;

  const handleEval = async (
    evalType: ExpertEvaluationType,
    details?: string
  ) => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    try {
      await submitExpertEvaluation({
        response_id: responseId,
        evaluation: evalType,
        details,
      });
      setEvaluation(evalType);
      setShowDetailsModal(false);
    } catch (err) {
      console.error('Evaluation failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const onClickEval = (evalType: ExpertEvaluationType) => {
    if (evalType === 'correct') {
      handleEval(evalType);
    } else {
      setPendingEval(evalType);
      setDetailsText('');
      setShowDetailsModal(true);
    }
  };

  const EVAL_CONFIG: Record<
    ExpertEvaluationType,
    { label: string; color: string; activeColor: string }
  > = {
    correct: {
      label: 'Corretta',
      color: 'text-green-600 border-green-300 hover:bg-green-50',
      activeColor: 'bg-green-100 text-green-800 border-green-400',
    },
    incomplete: {
      label: 'Incompleta',
      color: 'text-yellow-600 border-yellow-300 hover:bg-yellow-50',
      activeColor: 'bg-yellow-100 text-yellow-800 border-yellow-400',
    },
    incorrect: {
      label: 'Errata',
      color: 'text-red-600 border-red-300 hover:bg-red-50',
      activeColor: 'bg-red-100 text-red-800 border-red-400',
    },
  };

  return (
    <div className="border-t border-gray-200 px-3 py-2">
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-gray-500 mr-1">Valutazione:</span>
        {(
          Object.entries(EVAL_CONFIG) as [
            ExpertEvaluationType,
            typeof EVAL_CONFIG.correct,
          ][]
        ).map(([type, cfg]) => (
          <button
            key={type}
            onClick={e => {
              e.stopPropagation();
              onClickEval(type);
            }}
            disabled={isSubmitting}
            className={`text-xs px-2 py-0.5 rounded border transition-colors ${
              evaluation === type ? cfg.activeColor : cfg.color
            } ${isSubmitting ? 'opacity-50 cursor-wait' : ''}`}
          >
            {cfg.label}
          </button>
        ))}
      </div>

      {/* Details modal for incomplete/incorrect */}
      {showDetailsModal && pendingEval && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={e => {
            e.stopPropagation();
            setShowDetailsModal(false);
          }}
        >
          <div
            className="bg-white rounded-lg p-4 w-full max-w-md mx-4 shadow-xl"
            onClick={e => e.stopPropagation()}
          >
            <h3 className="font-medium text-gray-900 mb-2">
              {pendingEval === 'incomplete'
                ? 'Dettagli incompletezza'
                : 'Dettagli errore'}
            </h3>
            <textarea
              value={detailsText}
              onChange={e => setDetailsText(e.target.value)}
              placeholder="Descrivi il problema..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm h-24 resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              maxLength={2000}
            />
            <div className="flex justify-end gap-2 mt-3">
              <button
                onClick={() => setShowDetailsModal(false)}
                className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Annulla
              </button>
              <button
                onClick={() =>
                  handleEval(pendingEval, detailsText || undefined)
                }
                disabled={isSubmitting}
                className="px-3 py-1.5 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {isSubmitting ? 'Invio...' : 'Conferma'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
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

              {/* Expert evaluation buttons */}
              <EvaluationButtons response={response} />
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
