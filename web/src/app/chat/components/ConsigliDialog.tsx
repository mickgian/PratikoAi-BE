'use client';

import { useEffect, useRef } from 'react';
import { AlertCircle, Download, Loader2, X } from 'lucide-react';
import type { ConsigliReport } from '@/lib/api/consigli';

interface ConsigliDialogProps {
  data: ConsigliReport | null;
  error: string | null;
  loading: boolean;
  onClose: () => void;
}

export function ConsigliDialog({
  data,
  error,
  loading,
  onClose,
}: ConsigliDialogProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Write HTML into iframe when available
  useEffect(() => {
    if (data?.html_report && iframeRef.current) {
      const doc = iframeRef.current.contentDocument;
      if (doc) {
        doc.open();
        doc.write(data.html_report);
        doc.close();
      }
    }
  }, [data?.html_report]);

  const handleDownload = () => {
    if (!data?.html_report) return;
    const blob = new Blob([data.html_report], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `consigli-pratikoai-${new Date().toISOString().slice(0, 10)}.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      data-testid="consigli-dialog"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Report consigli personalizzati"
    >
      <div
        className="relative bg-white rounded-xl border border-[#E8E2DB] shadow-xl w-[90vw] max-w-4xl h-[85vh] flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-[#E8E2DB]">
          <h2 className="text-[#8B7355] font-semibold text-lg">
            Consigli Personalizzati
          </h2>
          <div className="flex items-center gap-2">
            {data?.html_report && (
              <button
                onClick={handleDownload}
                className="p-2 rounded-lg hover:bg-[#F8F5F1] text-[#6B6560] transition"
                title="Scarica report"
                data-testid="download-report"
              >
                <Download className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-[#F8F5F1] text-[#6B6560] transition"
              data-testid="close-consigli"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {loading && (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-[#8B7355]" />
              <p className="text-[#6B6560] text-sm">
                Generazione report in corso...
              </p>
              <p className="text-[#A09890] text-xs">
                L&apos;analisi potrebbe richiedere fino a un minuto
              </p>
            </div>
          )}

          {error && (
            <div className="flex items-start gap-3 p-5">
              <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-amber-800">{error}</p>
            </div>
          )}

          {!loading && !error && data?.status === 'error' && (
            <div className="flex items-start gap-3 p-5">
              <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-amber-800">{data.message_it}</p>
            </div>
          )}

          {!loading && data?.status === 'insufficient_data' && (
            <div className="flex flex-col items-center justify-center h-full gap-3 px-8 text-center">
              <p className="text-[#6B6560]">{data.message_it}</p>
            </div>
          )}

          {!loading && data?.status === 'generating' && (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-[#8B7355]" />
              <p className="text-[#6B6560] text-sm">{data.message_it}</p>
            </div>
          )}

          {!loading && data?.html_report && (
            <iframe
              ref={iframeRef}
              title="Report consigli"
              className="w-full h-full border-0"
              sandbox="allow-same-origin"
              data-testid="consigli-iframe"
            />
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-2 border-t border-[#E8E2DB] text-center">
          <p className="text-xs text-[#A09890]">Premi Esc per chiudere</p>
        </div>
      </div>
    </div>
  );
}
