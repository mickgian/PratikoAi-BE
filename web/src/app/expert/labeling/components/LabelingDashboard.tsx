'use client';

import { useCallback } from 'react';
import { useExpertStatus } from '@/hooks/useExpertStatus';
import { useLabelingQueue } from '../hooks/useLabelingQueue';
import { useLabelingStats } from '../hooks/useLabelingStats';
import { useLabelSubmission } from '../hooks/useLabelSubmission';
import { LabelingStatsBar } from './LabelingStatsBar';
import { LabelingQueue } from './LabelingQueue';
import { ExportButton } from './ExportButton';
import { LabelingInstructions } from './LabelingInstructions';

export function LabelingDashboard() {
  const { isSuperUser, isLoading: isAuthLoading } = useExpertStatus();
  const queue = useLabelingQueue();
  const {
    stats,
    isLoading: isStatsLoading,
    refetch: refetchStats,
  } = useLabelingStats();
  const {
    isSubmitting,
    error: submitError,
    handleSubmit,
    handleSkip,
  } = useLabelSubmission();

  const onSubmit = useCallback(
    async (id: string, intent: string, notes?: string) => {
      await handleSubmit(id, intent, notes);
      queue.removeItem(id);
      refetchStats();
    },
    [handleSubmit, queue, refetchStats]
  );

  const onSkip = useCallback(
    async (id: string) => {
      await handleSkip(id);
      queue.removeItem(id);
    },
    [handleSkip, queue]
  );

  // Auth loading
  if (isAuthLoading) {
    return (
      <div className="min-h-screen bg-[#F8F5F1] flex items-center justify-center">
        <div className="text-gray-500">Verifica autorizzazione...</div>
      </div>
    );
  }

  // Access denied
  if (!isSuperUser) {
    return (
      <div
        className="min-h-screen bg-[#F8F5F1] flex items-center justify-center"
        data-testid="access-denied"
      >
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center max-w-md">
          <p className="text-lg font-medium text-gray-900 mb-2">
            Accesso non autorizzato
          </p>
          <p className="text-sm text-gray-500">
            Solo gli esperti e gli amministratori possono accedere al sistema di
            etichettatura.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8F5F1]" data-testid="labeling-dashboard">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              Etichettatura Intenti
            </h1>
            <p className="text-sm text-gray-500">
              Etichetta le query a bassa confidenza per migliorare il
              classificatore
            </p>
          </div>
          <ExportButton
            newSinceExport={stats?.new_since_export ?? 0}
            onExportComplete={refetchStats}
          />
        </div>
      </div>

      {/* Content */}
      <div className="max-w-5xl mx-auto px-4 py-6">
        <LabelingInstructions />
        <LabelingStatsBar stats={stats} isLoading={isStatsLoading} />

        {submitError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
            {submitError}
          </div>
        )}

        <LabelingQueue
          items={queue.items}
          page={queue.page}
          totalPages={queue.totalPages}
          totalCount={queue.totalCount}
          isLoading={queue.isLoading}
          error={queue.error}
          isSubmitting={isSubmitting}
          onSubmit={onSubmit}
          onSkip={onSkip}
          onPageChange={queue.goToPage}
        />
      </div>
    </div>
  );
}
