'use client';

import { useEffect, useState } from 'react';
import { UsageCardMessage } from './UsageCardMessage';
import { UsageSimulatorPanel } from './UsageSimulatorPanel';
import { AlertCircle } from 'lucide-react';
import type { UsageStatus } from '@/lib/api/billing';

interface UsageDialogProps {
  data: UsageStatus | null;
  error?: string | null;
  canBypass?: boolean;
  onBypass?: () => void;
  onClose: () => void;
}

export function UsageDialog({
  data,
  error,
  canBypass,
  onBypass,
  onClose,
}: UsageDialogProps) {
  const [currentData, setCurrentData] = useState<UsageStatus | null>(data);

  useEffect(() => {
    setCurrentData(data);
  }, [data]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div
      data-testid="usage-dialog"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Stato utilizzo"
    >
      <div className="relative" onClick={e => e.stopPropagation()}>
        {error ? (
          <div className="max-w-md bg-white rounded-xl border border-amber-200 p-5 space-y-3">
            <div className="flex items-start gap-2 text-amber-800">
              <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
            <p className="text-xs text-gray-400 text-center">
              Premi Esc per chiudere
            </p>
          </div>
        ) : currentData ? (
          <div className="space-y-2">
            <UsageCardMessage data={currentData} />
            {canBypass && onBypass && (
              <button
                onClick={onBypass}
                className="w-full mt-1 py-2 px-4 bg-amber-100 border border-amber-300 rounded-lg text-amber-800 text-sm font-medium hover:bg-amber-200 transition"
                data-testid="bypass-button"
              >
                Continua comunque (privilegi admin)
              </button>
            )}
            {currentData.is_admin && (
              <UsageSimulatorPanel onUsageUpdated={setCurrentData} />
            )}
            <p className="text-xs text-gray-400 text-center">
              Premi Esc per chiudere
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
