'use client';

import { motion } from 'motion/react';
import { ArrowLeft, CheckCircle, ChevronRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ProcedureChecklist } from './ProcedureChecklist';
import { ProcedureDocumentVerification } from './ProcedureDocumentVerification';
import { ProcedureNotes } from './ProcedureNotes';
import type { Step } from '../types';

interface ProcedureStepContentProps {
  step: Step;
  currentStepIndex: number;
  totalSteps: number;
  isClientMode: boolean;
  showNoteEditor: boolean;
  newNote: string;
  onToggleChecklistItem: (itemId: string) => void;
  onToggleDocumentVerification: (docId: string) => void;
  onDocumentNoteChange: (docId: string, note: string) => void;
  onNewNoteChange: (value: string) => void;
  onShowNoteEditor: () => void;
  onCancelNoteEditor: () => void;
  onSaveNote: () => void;
  onCompleteStep: () => void;
  onPreviousStep: () => void;
  onNextStep: () => void;
}

export function ProcedureStepContent({
  step,
  currentStepIndex,
  totalSteps,
  isClientMode,
  showNoteEditor,
  newNote,
  onToggleChecklistItem,
  onToggleDocumentVerification,
  onDocumentNoteChange,
  onNewNoteChange,
  onShowNoteEditor,
  onCancelNoteEditor,
  onSaveNote,
  onCompleteStep,
  onPreviousStep,
  onNextStep,
}: ProcedureStepContentProps) {
  return (
    <motion.div
      key={step.id}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-lg shadow-lg border border-[#C4BDB4]/20 overflow-hidden"
    >
      <div className="bg-[#2A5D67] text-white p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center space-x-2 mb-2">
              <Badge className="bg-white/20 text-white border-white/30 border">
                Passo {step.number}
              </Badge>
              {step.completed && (
                <Badge className="bg-green-500 text-white border-green-400 border">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Completato
                </Badge>
              )}
            </div>
            <h2 className="text-2xl font-bold mb-2">{step.title}</h2>
            <p className="text-white/90">{step.description}</p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        <ProcedureChecklist
          items={step.checklist}
          isClientMode={isClientMode}
          onToggle={onToggleChecklistItem}
        />

        {step.documents.length > 0 && (
          <ProcedureDocumentVerification
            documents={step.documents}
            isClientMode={isClientMode}
            onToggleVerification={onToggleDocumentVerification}
            onNoteChange={onDocumentNoteChange}
          />
        )}

        <ProcedureNotes
          notes={step.notes}
          isClientMode={isClientMode}
          showNoteEditor={showNoteEditor}
          newNote={newNote}
          onNewNoteChange={onNewNoteChange}
          onShowEditor={onShowNoteEditor}
          onCancelEditor={onCancelNoteEditor}
          onSaveNote={onSaveNote}
        />
      </div>

      {isClientMode && (
        <div className="bg-[#F8F5F1] px-6 py-4 border-t border-[#C4BDB4]/20 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {currentStepIndex > 0 && (
              <Button
                onClick={onPreviousStep}
                variant="outline"
                className="text-[#2A5D67] border-[#2A5D67]"
              >
                <ArrowLeft className="w-4 h-4 mr-1" />
                Passo precedente
              </Button>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {!step.completed ? (
              <Button
                onClick={onCompleteStep}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                <CheckCircle className="w-4 h-4 mr-2" />
                <span className="font-bold">Segna come completato</span>
              </Button>
            ) : (
              currentStepIndex < totalSteps - 1 && (
                <Button
                  onClick={onNextStep}
                  className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                >
                  <span className="font-bold">Passo successivo</span>
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              )
            )}
          </div>
        </div>
      )}
    </motion.div>
  );
}
