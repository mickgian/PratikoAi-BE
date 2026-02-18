'use client';

import type { QueueItem } from '@/types/intentLabeling';
import { LabelingCard } from './LabelingCard';

interface LabelingQueueProps {
  items: QueueItem[];
  page: number;
  totalPages: number;
  totalCount: number;
  isLoading: boolean;
  error: string | null;
  isSubmitting: boolean;
  onSubmit: (id: string, intent: string, notes?: string) => Promise<void>;
  onSkip: (id: string) => Promise<void>;
  onPageChange: (page: number) => void;
}

export function LabelingQueue({
  items,
  page,
  totalPages,
  totalCount,
  isLoading,
  error,
  isSubmitting,
  onSubmit,
  onSkip,
  onPageChange,
}: LabelingQueueProps) {
  if (isLoading) {
    return (
      <div className="space-y-4" data-testid="queue-loading">
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className="bg-white rounded-lg border border-gray-200 p-5 animate-pulse"
          >
            <div className="h-5 bg-gray-200 rounded w-3/4 mb-4" />
            <div className="h-3 bg-gray-200 rounded w-1/2 mb-3" />
            <div className="space-y-1.5 mb-4">
              {[...Array(5)].map((_, j) => (
                <div key={j} className="h-3 bg-gray-100 rounded" />
              ))}
            </div>
            <div className="flex gap-2">
              {[...Array(5)].map((_, j) => (
                <div key={j} className="h-8 bg-gray-200 rounded-full w-28" />
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm"
        data-testid="queue-error"
      >
        {error}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div
        className="bg-white rounded-lg border border-gray-200 p-8 text-center"
        data-testid="queue-empty"
      >
        <p className="text-gray-500 text-lg mb-2">Nessuna query in coda</p>
        <p className="text-gray-400 text-sm">
          Tutte le query a bassa confidenza sono state etichettate.
        </p>
      </div>
    );
  }

  return (
    <div data-testid="labeling-queue">
      {/* Queue info */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">
          {totalCount} query in attesa di etichettatura
        </p>
        <div className="text-xs text-gray-400">
          Pagina {page} di {totalPages}
        </div>
      </div>

      {/* Cards */}
      <div className="space-y-4">
        {items.map(item => (
          <LabelingCard
            key={item.id}
            item={item}
            onSubmit={onSubmit}
            onSkip={onSkip}
            isSubmitting={isSubmitting}
          />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="px-3 py-1.5 rounded text-sm text-gray-600 bg-gray-100
                     hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Precedente
          </button>
          {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
            const pageNum = i + 1;
            return (
              <button
                key={pageNum}
                onClick={() => onPageChange(pageNum)}
                className={`
                  px-3 py-1.5 rounded text-sm transition-all
                  ${
                    page === pageNum
                      ? 'bg-[#2A5D67] text-white'
                      : 'text-gray-600 bg-gray-100 hover:bg-gray-200'
                  }
                `}
              >
                {pageNum}
              </button>
            );
          })}
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="px-3 py-1.5 rounded text-sm text-gray-600 bg-gray-100
                     hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Successiva
          </button>
        </div>
      )}
    </div>
  );
}
