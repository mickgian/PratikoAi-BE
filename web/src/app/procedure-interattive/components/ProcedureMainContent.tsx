'use client';

import { motion } from 'motion/react';
import { Eye, PlayCircle, User } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ProcedureStepper } from './ProcedureStepper';
import { ProcedureStepContent } from './ProcedureStepContent';
import type { Procedura } from '../types';

const getProgressColor = (progress: number): string => {
  if (progress === 100) return 'bg-green-500';
  if (progress >= 50) return 'bg-blue-500';
  if (progress > 0) return 'bg-yellow-500';
  return 'bg-gray-300';
};

interface ProcedureMainContentProps {
  procedura: Procedura;
  currentStepIndex: number;
  isClientMode: boolean;
  clientName?: string;
  showNoteEditor: boolean;
  newNote: string;
  onStepSelect: (index: number) => void;
  onStartForClient: () => void;
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

export function ProcedureMainContent({
  procedura,
  currentStepIndex,
  isClientMode,
  clientName,
  showNoteEditor,
  newNote,
  onStepSelect,
  onStartForClient,
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
}: ProcedureMainContentProps) {
  const currentStep = procedura.steps[currentStepIndex];

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="bg-white border-b border-[#C4BDB4]/20 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-[#2A5D67] mb-1">
              {procedura.title}
            </h1>
            <p className="text-sm text-[#1E293B]">{procedura.description}</p>
          </div>

          <div className="flex items-center space-x-2">
            {!isClientMode ? (
              <>
                <Badge className="bg-gray-100 text-gray-700 border-gray-300 border px-3 py-1">
                  <Eye className="w-3 h-3 mr-1" />
                  Modalità consultazione
                </Badge>
                <Button
                  onClick={onStartForClient}
                  className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                >
                  <PlayCircle className="w-4 h-4 mr-2" />
                  <span className="font-bold">Avvia per un cliente</span>
                </Button>
              </>
            ) : (
              <Badge className="bg-blue-100 text-blue-700 border-blue-300 border px-3 py-1.5">
                <User className="w-4 h-4 mr-1" />
                {clientName}
              </Badge>
            )}
          </div>
        </div>

        {isClientMode && currentStep && (
          <div className="bg-[#F8F5F1] rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-[#2A5D67]">
                Passo {currentStep.number} di {procedura.totalSteps} -{' '}
                {procedura.progress}% completato
              </span>
              <span className="text-xs text-[#1E293B]">
                Ultimo aggiornamento:{' '}
                {new Date(procedura.lastUpdated || '').toLocaleDateString(
                  'it-IT'
                )}
              </span>
            </div>
            <div className="w-full h-3 bg-white rounded-full overflow-hidden border border-[#C4BDB4]/20">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${procedura.progress}%` }}
                className={`h-full ${getProgressColor(procedura.progress)}`}
              />
            </div>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-5xl mx-auto">
          <ProcedureStepper
            steps={procedura.steps}
            currentStepIndex={currentStepIndex}
            onStepClick={onStepSelect}
          />

          {currentStep && (
            <ProcedureStepContent
              step={currentStep}
              currentStepIndex={currentStepIndex}
              totalSteps={procedura.totalSteps}
              isClientMode={isClientMode}
              showNoteEditor={showNoteEditor}
              newNote={newNote}
              onToggleChecklistItem={onToggleChecklistItem}
              onToggleDocumentVerification={onToggleDocumentVerification}
              onDocumentNoteChange={onDocumentNoteChange}
              onNewNoteChange={onNewNoteChange}
              onShowNoteEditor={onShowNoteEditor}
              onCancelNoteEditor={onCancelNoteEditor}
              onSaveNote={onSaveNote}
              onCompleteStep={onCompleteStep}
              onPreviousStep={onPreviousStep}
              onNextStep={onNextStep}
            />
          )}
        </div>
      </div>
    </div>
  );
}
