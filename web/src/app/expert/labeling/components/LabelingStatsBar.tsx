'use client';

import type { LabelingStatsResponse } from '@/types/intentLabeling';
import {
  INTENT_DISPLAY_NAMES,
  INTENT_COLORS,
  type IntentLabel,
} from '@/types/intentLabeling';

interface LabelingStatsBarProps {
  stats: LabelingStatsResponse | null;
  isLoading: boolean;
}

function StatCard({
  label,
  value,
  color = 'text-gray-900',
}: {
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

export function LabelingStatsBar({ stats, isLoading }: LabelingStatsBarProps) {
  if (isLoading) {
    return (
      <div
        className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6"
        data-testid="stats-loading"
      >
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse"
          >
            <div className="h-3 bg-gray-200 rounded w-20 mb-2" />
            <div className="h-7 bg-gray-200 rounded w-16" />
          </div>
        ))}
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-4 mb-6" data-testid="stats-bar">
      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Totale Query" value={stats.total_queries} />
        <StatCard
          label="Etichettate"
          value={stats.labeled_queries}
          color="text-[#2A5D67]"
        />
        <StatCard
          label="In Attesa"
          value={stats.pending_queries}
          color="text-[#D4A574]"
        />
        <StatCard
          label="Completamento"
          value={`${stats.completion_percentage.toFixed(1)}%`}
          color="text-[#2A5D67]"
        />
      </div>

      {/* Progress bar */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-500">Progresso Complessivo</span>
          <span className="text-xs font-medium text-[#2A5D67]">
            {stats.labeled_queries} / {stats.total_queries}
          </span>
        </div>
        <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-[#2A5D67] rounded-full transition-all duration-500"
            style={{ width: `${stats.completion_percentage}%` }}
          />
        </div>

        {/* Labels by intent */}
        {Object.keys(stats.labels_by_intent).length > 0 && (
          <div className="flex flex-wrap gap-3 mt-3">
            {Object.entries(stats.labels_by_intent).map(([intent, count]) => {
              const label =
                INTENT_DISPLAY_NAMES[intent as IntentLabel] || intent;
              const color = INTENT_COLORS[intent as IntentLabel] || '#6B7280';
              return (
                <span
                  key={intent}
                  className="flex items-center gap-1.5 text-xs"
                >
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  {label}: {count}
                </span>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
