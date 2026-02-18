'use client';

import type { UsageStatus } from '@/lib/api/billing';

interface UsageCardMessageProps {
  data: UsageStatus;
}

function formatResetTime(minutes: number | null): string {
  if (minutes === null || minutes <= 0) return '--';
  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  const mins = Math.round(minutes % 60);
  if (days > 0) return `${days}g ${hours}h`;
  if (hours > 0) return `${hours}h ${mins}min`;
  return `${mins}min`;
}

function barColor(pct: number): string {
  if (pct >= 90) return 'bg-red-500';
  if (pct >= 70) return 'bg-amber-500';
  return 'bg-[#2A5D67]';
}

function WindowRow({
  label,
  percentage,
  resetMinutes,
}: {
  label: string;
  percentage: number;
  resetMinutes: number | null;
}) {
  const clamped = Math.min(percentage, 100);
  return (
    <div className="space-y-1" data-testid={`window-row-${label}`}>
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium text-[#1E293B]">
          {percentage.toFixed(1)}%
        </span>
      </div>
      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${barColor(percentage)}`}
          style={{ width: `${clamped}%` }}
          data-testid="progress-bar-fill"
        />
      </div>
      <div className="text-xs text-gray-400 text-right">
        Reset: {formatResetTime(resetMinutes)}
      </div>
    </div>
  );
}

export function UsageCardMessage({ data }: UsageCardMessageProps) {
  return (
    <div
      data-testid="usage-card"
      className="max-w-md bg-white rounded-xl border border-[#C4BDB4] p-5 space-y-4"
    >
      <div>
        <h3 className="text-sm font-semibold text-[#2A5D67]">Stato utilizzo</h3>
        <p className="text-xs text-gray-500 mt-0.5">
          Piano{' '}
          <span className="font-medium" data-testid="plan-name">
            {data.plan_name}
          </span>
        </p>
      </div>

      <WindowRow
        label="Sessione corrente"
        percentage={data.window_5h.usage_percentage}
        resetMinutes={data.window_5h.reset_in_minutes}
      />

      <WindowRow
        label="Settimana corrente"
        percentage={data.window_7d.usage_percentage}
        resetMinutes={data.window_7d.reset_in_minutes}
      />

      <div className="flex items-baseline gap-2">
        <span
          className="text-lg font-bold text-[#2A5D67]"
          data-testid="credit-balance"
        >
          {data.credits.balance_eur.toFixed(2)} EUR
        </span>
        <span
          data-testid="extra-usage-badge"
          className={`text-xs px-2 py-0.5 rounded-full ${
            data.credits.extra_usage_enabled
              ? 'bg-green-100 text-green-700'
              : 'bg-gray-100 text-gray-500'
          }`}
        >
          {data.credits.extra_usage_enabled
            ? 'Consumo automatico attivo'
            : 'Consumo automatico disattivato'}
        </span>
      </div>

      {data.message_it && (
        <p
          className="text-xs text-gray-500 italic"
          data-testid="status-message"
        >
          {data.message_it}
        </p>
      )}
    </div>
  );
}
