'use client';

import { useRouter } from 'next/navigation';
import { AlertTriangle } from 'lucide-react';

interface UsageLimitBannerProps {
  windowType: string;
  resetInMinutes: number | null;
  messageIt: string;
}

export function UsageLimitBanner({
  windowType,
  resetInMinutes,
  messageIt,
}: UsageLimitBannerProps) {
  const router = useRouter();

  const resetLabel =
    resetInMinutes != null
      ? resetInMinutes >= 60
        ? `${Math.floor(resetInMinutes / 60)}h ${resetInMinutes % 60}m`
        : `${resetInMinutes}m`
      : null;

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 flex items-start gap-3">
      <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-amber-800">{messageIt}</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {resetLabel && (
            <span className="text-xs text-amber-600">
              Reset tra {resetLabel}
            </span>
          )}
          <button
            onClick={() => router.push('/account/piano')}
            className="text-xs font-medium text-[#2A5D67] hover:underline"
          >
            Cambia piano
          </button>
          <button
            onClick={() => router.push('/account/crediti')}
            className="text-xs font-medium text-[#2A5D67] hover:underline"
          >
            Ricarica crediti
          </button>
        </div>
      </div>
    </div>
  );
}
