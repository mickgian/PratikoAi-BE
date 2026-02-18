'use client';

import { useState, useEffect, useCallback } from 'react';
import type { QueueItem, IntentLabel } from '@/types/intentLabeling';
import { INTENT_DISPLAY_NAMES, INTENT_COLORS } from '@/types/intentLabeling';
import { IntentSelector } from './IntentSelector';
import { ConfidenceBar } from './ConfidenceBar';
import { ScoreDistribution } from './ScoreDistribution';

interface LabelingCardProps {
  item: QueueItem;
  onSubmit: (id: string, intent: string, notes?: string) => Promise<void>;
  onSkip: (id: string) => Promise<void>;
  isSubmitting: boolean;
}

export function LabelingCard({
  item,
  onSubmit,
  onSkip,
  isSubmitting,
}: LabelingCardProps) {
  const [selectedIntent, setSelectedIntent] = useState<IntentLabel | null>(
    null
  );
  const [showNotes, setShowNotes] = useState(false);
  const [notes, setNotes] = useState('');

  const handleSubmit = useCallback(async () => {
    if (!selectedIntent || isSubmitting) return;
    await onSubmit(item.id, selectedIntent, notes || undefined);
    setSelectedIntent(null);
    setNotes('');
    setShowNotes(false);
  }, [selectedIntent, isSubmitting, item.id, notes, onSubmit]);

  const handleSkip = useCallback(async () => {
    if (isSubmitting) return;
    await onSkip(item.id);
  }, [isSubmitting, item.id, onSkip]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;

      switch (e.key) {
        case 'Enter':
          e.preventDefault();
          handleSubmit();
          break;
        case 's':
        case 'S':
          e.preventDefault();
          handleSkip();
          break;
        case 'n':
        case 'N':
          e.preventDefault();
          setShowNotes(prev => !prev);
          break;
        case 'Escape':
          e.preventDefault();
          setSelectedIntent(null);
          setNotes('');
          setShowNotes(false);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSubmit, handleSkip]);

  const predictedLabel =
    INTENT_DISPLAY_NAMES[item.predicted_intent as IntentLabel] ||
    item.predicted_intent;
  const predictedColor =
    INTENT_COLORS[item.predicted_intent as IntentLabel] || '#6B7280';

  return (
    <div
      className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm"
      data-testid="labeling-card"
    >
      {/* Query text */}
      <p className="text-lg font-medium text-gray-900 mb-4 leading-relaxed">
        &ldquo;{item.query}&rdquo;
      </p>

      {/* Predicted intent + confidence */}
      <div className="flex items-center gap-3 mb-3">
        <span className="text-xs text-gray-500">Predizione:</span>
        <span
          className="text-xs font-medium px-2 py-0.5 rounded-full text-white"
          style={{ backgroundColor: predictedColor }}
        >
          {predictedLabel}
        </span>
        <div className="flex-1 max-w-[200px]">
          <ConfidenceBar confidence={item.confidence} />
        </div>
      </div>

      {/* Score distribution */}
      <div className="mb-4">
        <ScoreDistribution scores={item.all_scores} />
      </div>

      {/* Intent selector */}
      <div className="mb-4">
        <p className="text-xs text-gray-500 mb-2">
          Seleziona l&apos;intento corretto (tasti 1-5):
        </p>
        <IntentSelector
          selectedIntent={selectedIntent}
          onSelect={setSelectedIntent}
          disabled={isSubmitting}
        />
      </div>

      {/* Notes toggle */}
      {showNotes && (
        <div className="mb-4">
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Note opzionali..."
            maxLength={500}
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg
                     resize-none focus:outline-none focus:ring-2 focus:ring-[#2A5D67]/30
                     focus:border-[#2A5D67]"
            rows={2}
            data-testid="labeling-notes"
          />
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSubmit}
          disabled={!selectedIntent || isSubmitting}
          className={`
            px-4 py-2 rounded-lg text-sm font-medium transition-all
            ${
              selectedIntent && !isSubmitting
                ? 'bg-[#2A5D67] text-white hover:bg-[#1e4a52] shadow-sm'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }
          `}
          data-testid="submit-btn"
        >
          {isSubmitting ? 'Invio...' : 'Conferma'}{' '}
          <kbd className="text-[10px] font-mono opacity-60 ml-1">Enter</kbd>
        </button>

        <button
          onClick={handleSkip}
          disabled={isSubmitting}
          className="px-4 py-2 rounded-lg text-sm font-medium text-gray-600
                   bg-gray-100 hover:bg-gray-200 transition-all"
          data-testid="skip-btn"
        >
          Salta <kbd className="text-[10px] font-mono opacity-60 ml-1">S</kbd>
        </button>

        <button
          onClick={() => setShowNotes(prev => !prev)}
          className={`
            px-3 py-2 rounded-lg text-sm transition-all
            ${showNotes ? 'text-[#2A5D67] bg-[#2A5D67]/10' : 'text-gray-500 hover:bg-gray-100'}
          `}
          data-testid="notes-toggle"
        >
          Note <kbd className="text-[10px] font-mono opacity-60 ml-1">N</kbd>
        </button>

        {item.skip_count > 0 && (
          <span className="text-xs text-gray-400 ml-auto">
            Saltata {item.skip_count}x
          </span>
        )}
      </div>
    </div>
  );
}
