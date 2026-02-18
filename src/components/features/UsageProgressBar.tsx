'use client';

interface UsageProgressBarProps {
  label: string;
  current: number;
  limit: number;
  percentage: number;
}

export function UsageProgressBar({
  label,
  current,
  limit,
  percentage,
}: UsageProgressBarProps) {
  const color =
    percentage >= 90
      ? 'bg-red-500'
      : percentage >= 70
        ? 'bg-amber-500'
        : 'bg-[#2A5D67]';

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium text-[#1E293B]">
          {current.toFixed(2)} / {limit.toFixed(2)} EUR
        </span>
      </div>
      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      <div className="text-xs text-gray-400 text-right">
        {percentage.toFixed(1)}%
      </div>
    </div>
  );
}
