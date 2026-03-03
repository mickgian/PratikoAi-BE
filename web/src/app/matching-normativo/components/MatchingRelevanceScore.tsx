'use client';

interface MatchingRelevanceScoreProps {
  score: number;
}

export function MatchingRelevanceScore({ score }: MatchingRelevanceScoreProps) {
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-16 h-16 flex items-center justify-center">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 64 64">
          <circle
            cx="32"
            cy="32"
            r="28"
            stroke="#E5E7EB"
            strokeWidth="6"
            fill="none"
          />
          <circle
            cx="32"
            cy="32"
            r="28"
            stroke="#2A5D67"
            strokeWidth="6"
            fill="none"
            strokeDasharray={`${score * 1.76} 176`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-bold text-[#2A5D67]">{score}%</span>
        </div>
      </div>
      <span className="text-xs text-[#1E293B] mt-1">Rilevanza</span>
    </div>
  );
}
