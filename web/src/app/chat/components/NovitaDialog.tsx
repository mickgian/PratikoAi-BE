'use client';

import { useEffect } from 'react';
import { Sparkles, Calendar, AlertCircle } from 'lucide-react';
import type { ReleaseNotePublic } from '@/lib/api/release-notes';

interface NovitaDialogProps {
  notes: ReleaseNotePublic[];
  error: string | null;
  onClose: () => void;
}

export function NovitaDialog({ notes, error, onClose }: NovitaDialogProps) {
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
      data-testid="novita-dialog"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Novità"
    >
      <div
        data-testid="novita-content"
        className="relative max-w-lg w-full max-h-[80vh] mx-4"
        onClick={e => e.stopPropagation()}
      >
        {error ? (
          <div className="bg-white rounded-xl border border-amber-200 p-5 space-y-3">
            <div className="flex items-start gap-2 text-amber-800">
              <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
            <p className="text-xs text-gray-400 text-center">
              Premi Esc per chiudere
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-[#D4A574]" />
              <h2 className="text-lg font-semibold text-[#2A5D67]">Novità</h2>
            </div>

            <div className="overflow-y-auto max-h-[60vh] p-5 space-y-6">
              {notes.length === 0 ? (
                <p className="text-center text-gray-500 py-4">
                  Nessuna nota di rilascio disponibile.
                </p>
              ) : (
                notes.map(note => (
                  <article key={note.version}>
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-base font-semibold text-[#2A5D67]">
                        v{note.version}
                      </h3>
                      {note.released_at && (
                        <div className="flex items-center space-x-1 text-xs text-gray-400">
                          <Calendar className="w-3 h-3" />
                          <time dateTime={note.released_at}>
                            {new Date(note.released_at).toLocaleDateString(
                              'it-IT',
                              {
                                day: 'numeric',
                                month: 'long',
                                year: 'numeric',
                              }
                            )}
                          </time>
                        </div>
                      )}
                    </div>
                    <div className="space-y-1">
                      {note.user_notes
                        .split('\n')
                        .filter(line => line.trim())
                        .map((line, i) => {
                          if (line.startsWith('- ')) {
                            return (
                              <div
                                key={i}
                                className="flex items-start space-x-2 ml-2"
                              >
                                <span className="text-[#D4A574] mt-0.5">•</span>
                                <span className="text-sm text-gray-700">
                                  {line.slice(2)}
                                </span>
                              </div>
                            );
                          }
                          if (line.endsWith(':')) {
                            return (
                              <h4
                                key={i}
                                className="text-sm font-semibold text-[#2A5D67] pt-1"
                              >
                                {line}
                              </h4>
                            );
                          }
                          return (
                            <p key={i} className="text-sm text-gray-700">
                              {line}
                            </p>
                          );
                        })}
                    </div>
                  </article>
                ))
              )}
            </div>

            <div className="px-5 py-3 border-t border-gray-100">
              <p className="text-xs text-gray-400 text-center">
                Premi Esc per chiudere
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
