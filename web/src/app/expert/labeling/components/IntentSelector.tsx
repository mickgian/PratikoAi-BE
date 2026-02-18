'use client';

import { useEffect, useCallback } from 'react';
import {
  INTENT_LABELS,
  INTENT_DISPLAY_NAMES,
  INTENT_COLORS,
  type IntentLabel,
} from '@/types/intentLabeling';

interface IntentSelectorProps {
  selectedIntent: IntentLabel | null;
  onSelect: (intent: IntentLabel) => void;
  disabled?: boolean;
}

export function IntentSelector({
  selectedIntent,
  onSelect,
  disabled = false,
}: IntentSelectorProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (disabled) return;
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;

      const keyIndex = parseInt(e.key) - 1;
      if (keyIndex >= 0 && keyIndex < INTENT_LABELS.length) {
        e.preventDefault();
        onSelect(INTENT_LABELS[keyIndex]);
      }
    },
    [disabled, onSelect]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div className="flex flex-wrap gap-2" data-testid="intent-selector">
      {INTENT_LABELS.map((intent, index) => {
        const isSelected = selectedIntent === intent;
        const color = INTENT_COLORS[intent];
        const label = INTENT_DISPLAY_NAMES[intent];

        return (
          <button
            key={intent}
            onClick={() => onSelect(intent)}
            disabled={disabled}
            data-testid={`intent-btn-${intent}`}
            className={`
              inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full
              text-sm font-medium transition-all duration-200
              ${
                isSelected
                  ? 'text-white ring-2 shadow-md scale-105'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }
              ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
            style={
              isSelected
                ? ({
                    backgroundColor: color,
                    '--tw-ring-color': color,
                  } as React.CSSProperties)
                : undefined
            }
          >
            <kbd className="text-[10px] font-mono opacity-60 bg-white/20 px-1 rounded">
              {index + 1}
            </kbd>
            {label}
          </button>
        );
      })}
    </div>
  );
}
