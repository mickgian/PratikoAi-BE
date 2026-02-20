'use client';

import { useState } from 'react';
import { exportTrainingData } from '@/lib/api/intentLabeling';

interface ExportButtonProps {
  newSinceExport?: number;
  onExportComplete?: () => void;
}

export function ExportButton({
  newSinceExport = 0,
  onExportComplete,
}: ExportButtonProps) {
  const [isExporting, setIsExporting] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async (format: 'jsonl' | 'csv') => {
    try {
      setIsExporting(true);
      setError(null);
      setShowMenu(false);
      await exportTrainingData(format);
      onExportComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore nell'esportazione");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setShowMenu(prev => !prev)}
        disabled={isExporting}
        className="px-3 py-1.5 rounded-lg text-sm font-medium text-[#2A5D67]
                 border border-[#2A5D67] hover:bg-[#2A5D67]/10 transition-all
                 disabled:opacity-50 disabled:cursor-not-allowed relative"
        data-testid="export-btn"
      >
        {isExporting ? 'Esportazione...' : 'Esporta Dati'}
        {newSinceExport > 0 && !isExporting && (
          <span
            className="absolute -top-2 -right-2 inline-flex items-center justify-center
                     min-w-[20px] h-5 px-1 rounded-full bg-[#06ac2e] text-white
                     text-[10px] font-bold"
            data-testid="export-badge"
          >
            {newSinceExport}
          </span>
        )}
      </button>

      {showMenu && (
        <div
          className="absolute right-0 mt-1 bg-white border border-gray-200
                   rounded-lg shadow-lg z-10 py-1 min-w-[140px]"
          data-testid="export-menu"
        >
          <button
            onClick={() => handleExport('jsonl')}
            className="w-full text-left px-3 py-2 text-sm text-gray-700
                     hover:bg-gray-50 transition-colors"
          >
            JSONL (Training)
          </button>
          <button
            onClick={() => handleExport('csv')}
            className="w-full text-left px-3 py-2 text-sm text-gray-700
                     hover:bg-gray-50 transition-colors"
          >
            CSV (Analisi)
          </button>
        </div>
      )}

      {error && (
        <p className="text-xs text-red-500 mt-1 absolute right-0">{error}</p>
      )}
    </div>
  );
}
