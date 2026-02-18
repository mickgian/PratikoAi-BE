'use client';

import {
  INTENT_DISPLAY_NAMES,
  INTENT_COLORS,
  type IntentLabel,
} from '@/types/intentLabeling';

interface ScoreDistributionProps {
  scores: Record<string, number>;
}

export function ScoreDistribution({ scores }: ScoreDistributionProps) {
  const sortedEntries = Object.entries(scores).sort(([, a], [, b]) => b - a);
  const maxScore = sortedEntries.length > 0 ? sortedEntries[0][1] : 0;

  return (
    <div className="space-y-1.5">
      {sortedEntries.map(([intent, score]) => {
        const label = INTENT_DISPLAY_NAMES[intent as IntentLabel] || intent;
        const color = INTENT_COLORS[intent as IntentLabel] || '#6B7280';
        const width = maxScore > 0 ? (score / maxScore) * 100 : 0;
        const percentage = Math.round(score * 100);

        return (
          <div key={intent} className="flex items-center gap-2">
            <span className="text-xs text-gray-600 w-28 truncate" title={label}>
              {label}
            </span>
            <div className="flex-1 h-3 bg-gray-100 rounded overflow-hidden">
              <div
                className="h-full rounded transition-all"
                style={{ width: `${width}%`, backgroundColor: color }}
              />
            </div>
            <span className="text-xs text-gray-500 font-mono w-10 text-right">
              {percentage}%
            </span>
          </div>
        );
      })}
    </div>
  );
}
