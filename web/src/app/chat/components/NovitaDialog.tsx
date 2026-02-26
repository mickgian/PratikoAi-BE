'use client';

import { useEffect, useState } from 'react';
import { Sparkles, Calendar, AlertCircle, Save, Code } from 'lucide-react';
import type { ReleaseNotePublic, ReleaseNote } from '@/lib/api/release-notes';

interface NovitaDialogProps {
  notes: ReleaseNotePublic[] | ReleaseNote[];
  error: string | null;
  onClose: () => void;
  environment?: string;
  onSaveUserNotes?: (version: string, userNotes: string) => void;
}

function isFullNote(
  note: ReleaseNotePublic | ReleaseNote
): note is ReleaseNote {
  return 'technical_notes' in note;
}

function UserNotesDisplay({ userNotes }: { userNotes: string }) {
  return (
    <div className="space-y-1">
      {userNotes
        .split('\n')
        .filter(line => line.trim())
        .map((line, i) => {
          if (line.startsWith('- ')) {
            return (
              <div key={i} className="flex items-start space-x-2 ml-2">
                <span className="text-[#D4A574] mt-0.5">•</span>
                <span className="text-sm text-gray-700">{line.slice(2)}</span>
              </div>
            );
          }
          if (line.endsWith(':')) {
            return (
              <h4 key={i} className="text-sm font-semibold text-[#2A5D67] pt-1">
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
  );
}

function QaNoteArticle({
  note,
  editedNotes,
  onChangeNotes,
  onSave,
}: {
  note: ReleaseNote;
  editedNotes: string;
  onChangeNotes: (value: string) => void;
  onSave: () => void;
}) {
  return (
    <article key={note.version}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-base font-semibold text-[#2A5D67]">
          v{note.version}
        </h3>
        {note.released_at && (
          <div className="flex items-center space-x-1 text-xs text-gray-400">
            <Calendar className="w-3 h-3" />
            <time dateTime={note.released_at}>
              {new Date(note.released_at).toLocaleDateString('it-IT', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
              })}
            </time>
          </div>
        )}
      </div>

      {/* Technical notes for QA */}
      <div
        data-testid="technical-notes-section"
        className="mb-3 bg-gray-50 rounded-lg p-3 border border-gray-200"
      >
        <div className="flex items-center space-x-1 mb-2">
          <Code className="w-3.5 h-3.5 text-gray-500" />
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Note tecniche (QA)
          </span>
        </div>
        <div className="space-y-0.5">
          {note.technical_notes
            .split('\n')
            .filter(line => line.trim())
            .map((line, i) => (
              <p key={i} className="text-xs text-gray-600 font-mono">
                {line}
              </p>
            ))}
        </div>
      </div>

      {/* Editable user notes preview for production */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-[#2A5D67] uppercase tracking-wide">
          Anteprima note utente (Produzione)
        </label>
        <textarea
          data-testid="user-notes-textarea"
          className="w-full text-sm text-gray-700 border border-gray-200 rounded-lg p-2.5 resize-y min-h-[80px] focus:border-[#D4A574] focus:ring-1 focus:ring-[#D4A574] outline-none"
          value={editedNotes}
          onChange={e => onChangeNotes(e.target.value)}
        />
        <button
          data-testid="save-user-notes-btn"
          className="flex items-center space-x-1.5 px-3 py-1.5 bg-[#2A5D67] text-white text-xs font-medium rounded-lg hover:bg-[#1e4a52] transition-colors"
          onClick={onSave}
        >
          <Save className="w-3.5 h-3.5" />
          <span>Salva note utente</span>
        </button>
      </div>
    </article>
  );
}

export function NovitaDialog({
  notes,
  error,
  onClose,
  environment,
  onSaveUserNotes,
}: NovitaDialogProps) {
  const isQa = environment === 'qa';

  // Track edited user_notes per version for QA editing
  const [editedNotesMap, setEditedNotesMap] = useState<Record<string, string>>(
    {}
  );

  // Initialize edited notes from props
  useEffect(() => {
    const initial: Record<string, string> = {};
    for (const note of notes) {
      initial[note.version] = note.user_notes;
    }
    setEditedNotesMap(initial);
  }, [notes]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const handleSave = (version: string) => {
    const editedText = editedNotesMap[version] ?? '';
    onSaveUserNotes?.(version, editedText);
  };

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
        className={`relative w-full max-h-[80vh] mx-4 ${isQa ? 'max-w-2xl' : 'max-w-lg'}`}
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
              {isQa && (
                <span className="ml-auto text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">
                  QA
                </span>
              )}
            </div>

            <div className="overflow-y-auto max-h-[60vh] p-5 space-y-6">
              {notes.length === 0 ? (
                <p className="text-center text-gray-500 py-4">
                  Nessuna nota di rilascio disponibile.
                </p>
              ) : isQa ? (
                notes.map(note =>
                  isFullNote(note) ? (
                    <QaNoteArticle
                      key={note.version}
                      note={note}
                      editedNotes={
                        editedNotesMap[note.version] ?? note.user_notes
                      }
                      onChangeNotes={value =>
                        setEditedNotesMap(prev => ({
                          ...prev,
                          [note.version]: value,
                        }))
                      }
                      onSave={() => handleSave(note.version)}
                    />
                  ) : null
                )
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
                    <UserNotesDisplay userNotes={note.user_notes} />
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
