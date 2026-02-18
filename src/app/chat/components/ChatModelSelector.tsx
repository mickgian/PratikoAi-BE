'use client';

/**
 * ChatModelSelector - Compact model selector for the chat page (DEV-257)
 *
 * A simplified dropdown for selecting models to compare, displayed next to
 * the "Confronta" button. Shows selected models as chips with a dropdown
 * for changing selection.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { ChevronDown, Check } from 'lucide-react';
import type { AvailableModel } from '@/types/modelComparison';
import { getAvailableModels } from '@/lib/api/modelComparison';

interface ChatModelSelectorProps {
  selectedModelIds: string[];
  onSelectionChange: (modelIds: string[]) => void;
  disabled?: boolean;
}

const PROVIDER_COLORS: Record<string, string> = {
  openai: 'bg-green-100 text-green-800',
  anthropic: 'bg-amber-100 text-amber-800',
  gemini: 'bg-blue-100 text-blue-800',
  mistral: 'bg-purple-100 text-purple-800',
};

const MAX_MODELS = 6;
const MIN_MODELS = 2;

export function ChatModelSelector({
  selectedModelIds,
  onSelectionChange,
  disabled = false,
}: ChatModelSelectorProps) {
  const [models, setModels] = useState<AvailableModel[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const hasInitialized = useRef(false);

  // Memoize onSelectionChange to avoid dependency issues
  const stableOnSelectionChange = useCallback(onSelectionChange, [
    onSelectionChange,
  ]);

  // Fetch available models on mount
  useEffect(() => {
    if (hasInitialized.current) return;
    hasInitialized.current = true;

    const fetchModels = async () => {
      try {
        setIsLoading(true);
        const response = await getAvailableModels();
        setModels(response.models);

        // Auto-select default models if none selected
        if (selectedModelIds.length === 0) {
          const defaultModels = response.models
            .filter(
              m => m.is_enabled && !m.is_disabled && (m.is_current || m.is_best)
            )
            .slice(0, MAX_MODELS)
            .map(m => m.model_id);
          if (defaultModels.length >= MIN_MODELS) {
            stableOnSelectionChange(defaultModels);
          }
        }
      } catch (error) {
        console.error('Failed to fetch models:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchModels();
  }, [selectedModelIds.length, stableOnSelectionChange]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleModel = (modelId: string) => {
    if (selectedModelIds.includes(modelId)) {
      if (selectedModelIds.length > MIN_MODELS) {
        onSelectionChange(selectedModelIds.filter(id => id !== modelId));
      }
    } else {
      if (selectedModelIds.length < MAX_MODELS) {
        onSelectionChange([...selectedModelIds, modelId]);
      }
    }
  };

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

  if (isLoading) {
    return (
      <div className="flex items-center gap-1 text-xs text-gray-400">
        <div className="w-3 h-3 border border-gray-300 border-t-transparent rounded-full animate-spin" />
        <span>Caricamento...</span>
      </div>
    );
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Toggle button showing selected count */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={`
          flex items-center gap-1 px-2 py-1 text-xs rounded-md border
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-50 cursor-pointer'}
          ${isOpen ? 'border-[#2A5D67] bg-[#2A5D67]/5' : 'border-gray-300'}
        `}
        title="Seleziona modelli da confrontare"
      >
        <span className="text-gray-600">{selectedModelIds.length} modelli</span>
        <ChevronDown
          className={`w-3 h-3 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Dropdown panel */}
      {isOpen && (
        <div className="absolute left-0 bottom-full mb-1 w-64 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
          <div className="p-2 border-b border-gray-100">
            <p className="text-xs text-gray-500">
              {selectedModelIds.length}/{MAX_MODELS} modelli selezionati (min{' '}
              {MIN_MODELS})
            </p>
          </div>

          <div className="max-h-60 overflow-y-auto p-2 space-y-2">
            {Object.entries(modelsByProvider).map(
              ([provider, providerModels]) => (
                <div key={provider}>
                  <h4 className="text-xs font-medium text-gray-500 uppercase mb-1 px-1">
                    {provider}
                  </h4>
                  <div className="space-y-0.5">
                    {providerModels.map(model => {
                      const isSelected = selectedModelIds.includes(
                        model.model_id
                      );
                      const isDisabled =
                        model.is_disabled ||
                        !model.is_enabled ||
                        (!isSelected && selectedModelIds.length >= MAX_MODELS);

                      return (
                        <button
                          key={model.model_id}
                          type="button"
                          onClick={() =>
                            !isDisabled && toggleModel(model.model_id)
                          }
                          disabled={isDisabled}
                          className={`
                          w-full flex items-center justify-between px-2 py-1.5 rounded text-xs
                          ${isSelected ? PROVIDER_COLORS[provider] || 'bg-gray-100' : 'hover:bg-gray-50'}
                          ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                        `}
                        >
                          <span className="flex items-center gap-1">
                            {model.display_name}
                            {model.is_current && (
                              <span
                                className="text-green-600"
                                title="Modello Corrente"
                              >
                                {'\u25CF'}
                              </span>
                            )}
                            {model.is_best && !model.is_current && (
                              <span
                                className="text-yellow-600"
                                title="Migliore"
                              >
                                {'\u2605'}
                              </span>
                            )}
                          </span>
                          {isSelected && <Check className="w-3 h-3" />}
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
