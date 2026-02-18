'use client';

import { useState, useEffect } from 'react';
import type { AvailableModel } from '@/types/modelComparison';

interface ModelSelectorProps {
  models: AvailableModel[];
  selectedModelIds: string[];
  onSelectionChange: (modelIds: string[]) => void;
  isLoading: boolean;
  maxModels?: number;
  minModels?: number;
}

const PROVIDER_COLORS: Record<string, string> = {
  openai: 'bg-green-100 text-green-800 border-green-300',
  anthropic: 'bg-amber-100 text-amber-800 border-amber-300',
  gemini: 'bg-blue-100 text-blue-800 border-blue-300',
  mistral: 'bg-purple-100 text-purple-800 border-purple-300',
};

export function ModelSelector({
  models,
  selectedModelIds,
  onSelectionChange,
  isLoading,
  maxModels = 6,
  minModels = 2,
}: ModelSelectorProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Group models by provider
  const modelsByProvider = models.reduce(
    (acc, model) => {
      if (!acc[model.provider]) {
        acc[model.provider] = [];
      }
      acc[model.provider].push(model);
      return acc;
    },
    {} as Record<string, AvailableModel[]>
  );

  const toggleModel = (modelId: string) => {
    if (selectedModelIds.includes(modelId)) {
      if (selectedModelIds.length > minModels) {
        onSelectionChange(selectedModelIds.filter(id => id !== modelId));
      }
    } else {
      if (selectedModelIds.length < maxModels) {
        onSelectionChange([...selectedModelIds, modelId]);
      }
    }
  };

  const selectAll = () => {
    const allEnabledIds = models
      .filter(m => m.is_enabled)
      .slice(0, maxModels)
      .map(m => m.model_id);
    onSelectionChange(allEnabledIds);
  };

  const selectDefaults = () => {
    // Select current model + best from each provider
    const defaultIds = models
      .filter(m => (m.is_current || m.is_best) && m.is_enabled)
      .slice(0, maxModels)
      .map(m => m.model_id);

    // Fallback: if no best/current flags, select first enabled from each provider
    if (defaultIds.length < minModels) {
      Object.values(modelsByProvider).forEach(providerModels => {
        const firstEnabled = providerModels.find(m => m.is_enabled);
        if (
          firstEnabled &&
          !defaultIds.includes(firstEnabled.model_id) &&
          defaultIds.length < maxModels
        ) {
          defaultIds.push(firstEnabled.model_id);
        }
      });
    }
    onSelectionChange(defaultIds);
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="animate-pulse flex space-x-4">
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            <div className="h-8 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Header */}
      <div
        className="p-3 flex items-center justify-between cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div>
          <h3 className="font-medium text-gray-900 text-sm">
            Modelli selezionati
          </h3>
          <p className="text-xs text-gray-500">
            {selectedModelIds.length} di {maxModels} modelli (min {minModels})
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Selected model chips */}
          <div className="hidden md:flex gap-1 flex-wrap">
            {selectedModelIds.slice(0, 3).map(modelId => {
              const model = models.find(m => m.model_id === modelId);
              if (!model) return null;
              return (
                <span
                  key={modelId}
                  className={`
                    text-xs px-2 py-0.5 rounded-full border
                    ${PROVIDER_COLORS[model.provider] || 'bg-gray-100 text-gray-700'}
                  `}
                >
                  {model.model_name}
                </span>
              );
            })}
            {selectedModelIds.length > 3 && (
              <span className="text-xs text-gray-500">
                +{selectedModelIds.length - 3}
              </span>
            )}
          </div>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
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
        </div>
      </div>

      {/* Expanded selection panel */}
      {isExpanded && (
        <div className="border-t border-gray-200 p-3">
          {/* Quick actions */}
          <div className="flex gap-2 mb-3">
            <button
              onClick={e => {
                e.stopPropagation();
                selectDefaults();
              }}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              Consigliati
            </button>
            <span className="text-gray-300">|</span>
            <button
              onClick={e => {
                e.stopPropagation();
                selectAll();
              }}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              Tutti (max {maxModels})
            </button>
          </div>

          {/* Models by provider */}
          <div className="space-y-3">
            {Object.entries(modelsByProvider).map(
              ([provider, providerModels]) => (
                <div key={provider}>
                  <h4 className="text-xs font-medium text-gray-500 uppercase mb-1">
                    {provider}
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {providerModels.map(model => {
                      const isSelected = selectedModelIds.includes(
                        model.model_id
                      );
                      const isDisabled =
                        !model.is_enabled ||
                        (!isSelected && selectedModelIds.length >= maxModels);

                      return (
                        <button
                          key={model.model_id}
                          onClick={e => {
                            e.stopPropagation();
                            if (!isDisabled) toggleModel(model.model_id);
                          }}
                          disabled={isDisabled}
                          className={`
                          text-xs px-3 py-1.5 rounded-lg border transition-colors
                          ${
                            isSelected
                              ? PROVIDER_COLORS[provider] ||
                                'bg-blue-100 text-blue-800 border-blue-300'
                              : 'bg-white text-gray-700 border-gray-300 hover:border-gray-400'
                          }
                          ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                        `}
                          title={`Elo: ${model.elo_rating?.toFixed(0) ?? 'N/A'} | ${model.wins}/${model.total_comparisons} vittorie`}
                        >
                          <span className="flex items-center gap-1">
                            {model.display_name}
                            {model.is_current && (
                              <span
                                className="text-green-600"
                                title="Modello Corrente"
                              >
                                ●
                              </span>
                            )}
                            {model.is_best && !model.is_current && (
                              <span
                                className="text-yellow-600"
                                title="Migliore"
                              >
                                ★
                              </span>
                            )}
                            {isSelected && (
                              <svg
                                className="w-3 h-3"
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
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )
            )}
          </div>
        </div>
      )}
    </div>
  );
}
