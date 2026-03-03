'use client';

import { AnimatePresence, motion } from 'motion/react';
import { Paperclip, Plus, Check, Calendar, Edit, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import type { Note } from '../types';

interface ProcedureNotesProps {
  notes: Note[];
  isClientMode: boolean;
  showNoteEditor: boolean;
  newNote: string;
  onNewNoteChange: (value: string) => void;
  onShowEditor: () => void;
  onCancelEditor: () => void;
  onSaveNote: () => void;
}

export function ProcedureNotes({
  notes,
  isClientMode,
  showNoteEditor,
  newNote,
  onNewNoteChange,
  onShowEditor,
  onCancelEditor,
  onSaveNote,
}: ProcedureNotesProps) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-[#2A5D67] flex items-center">
          <Paperclip className="w-5 h-5 mr-2" />
          Note
        </h3>
        {isClientMode && (
          <Button
            onClick={onShowEditor}
            size="sm"
            variant="outline"
            className="text-[#2A5D67] border-[#2A5D67]"
          >
            <Plus className="w-4 h-4 mr-1" />
            Aggiungi nota
          </Button>
        )}
      </div>

      {notes.length === 0 && !showNoteEditor && (
        <div className="text-center py-8 bg-[#F8F5F1] rounded-lg border border-[#C4BDB4]/20">
          <Paperclip className="w-8 h-8 text-[#C4BDB4] mx-auto mb-2" />
          <p className="text-sm text-[#C4BDB4]">Nessuna nota aggiunta</p>
        </div>
      )}

      <AnimatePresence>
        {showNoteEditor && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-4 p-4 bg-[#F8F5F1] rounded-lg border border-[#2A5D67]"
          >
            <Textarea
              value={newNote}
              onChange={e => onNewNoteChange(e.target.value)}
              placeholder="Scrivi una nota..."
              className="mb-3 min-h-[100px]"
            />
            <div className="flex items-center justify-end space-x-2">
              <Button onClick={onCancelEditor} size="sm" variant="ghost">
                Annulla
              </Button>
              <Button
                onClick={onSaveNote}
                size="sm"
                className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                disabled={!newNote.trim()}
              >
                <Check className="w-4 h-4 mr-1" />
                Salva nota
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {notes.length > 0 && (
        <div className="space-y-3">
          {notes.map(note => (
            <div
              key={note.id}
              className="p-4 bg-white rounded-lg border border-[#C4BDB4]/20"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center space-x-2 text-xs text-[#1E293B]">
                  <Calendar className="w-4 h-4" />
                  <span>{new Date(note.date).toLocaleString('it-IT')}</span>
                </div>
                {isClientMode && (
                  <div className="flex space-x-1">
                    <Button size="sm" variant="ghost" className="h-6 w-6 p-0">
                      <Edit className="w-3 h-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0 text-red-600"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                )}
              </div>
              <p className="text-[#1E293B]">{note.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
