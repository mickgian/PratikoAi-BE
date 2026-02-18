'use client';

import { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, ArrowUpCircle, CreditCard, Shield } from 'lucide-react';

interface UsageLimitBannerProps {
  resetAt: string | null;
  canBypass: boolean;
  onBypass: () => void;
  onDismiss: () => void;
}

export function UsageLimitBanner({
  resetAt,
  canBypass,
  onBypass,
  onDismiss,
}: UsageLimitBannerProps) {
  const [label, setLabel] = useState('');

  const computeLabel = useCallback(() => {
    if (!resetAt) return '';
    const target = new Date(resetAt);
    if (target.getTime() <= Date.now()) {
      onDismiss();
      return '';
    }
    const hh = String(target.getHours()).padStart(2, '0');
    const mm = String(target.getMinutes()).padStart(2, '0');
    return `${hh}.${mm}`;
  }, [resetAt, onDismiss]);

  useEffect(() => {
    setLabel(computeLabel());
    const id = setInterval(() => setLabel(computeLabel()), 30_000);
    return () => clearInterval(id);
  }, [computeLabel]);

  return (
    <div
      data-testid="usage-limit-banner"
      role="alert"
      className="rounded-lg p-4 relative"
    >
      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-red-600 font-semibold text-sm">
            Limite di utilizzo raggiunto
          </p>
        </div>
      </div>

      {/* Reset time */}
      <div className="rounded-md px-3 py-2 mb-3">
        <p className="text-red-600 text-xs font-medium">
          {label
            ? `Il limite si azzera alle ${label}`
            : 'Il limite si azzera a breve'}
        </p>
      </div>

      {/* Action links */}
      <div className="flex flex-wrap gap-2">
        <a
          href="/account/piano"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-[#C4BDB4] rounded-md text-[#2F3E46] text-xs font-medium hover:bg-gray-50 transition-colors"
          data-testid="usage-limit-upgrade"
        >
          <ArrowUpCircle className="w-3.5 h-3.5" />
          Passa a un piano superiore
        </a>
        <a
          href="/account/crediti"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-[#C4BDB4] rounded-md text-[#2F3E46] text-xs font-medium hover:bg-gray-50 transition-colors"
          data-testid="usage-limit-recharge"
        >
          <CreditCard className="w-3.5 h-3.5" />
          Ricarica crediti
        </a>
        {canBypass && (
          <button
            onClick={onBypass}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-100 border border-amber-300 rounded-md text-amber-800 text-xs font-medium hover:bg-amber-200 transition-colors"
            data-testid="usage-limit-bypass"
          >
            <Shield className="w-3.5 h-3.5" />
            Continua comunque (admin)
          </button>
        )}
      </div>
    </div>
  );
}
