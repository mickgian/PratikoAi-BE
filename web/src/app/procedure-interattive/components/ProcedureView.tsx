'use client';

import { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { PlayCircle, RefreshCw, AlertTriangle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ProcedureSidebar } from './ProcedureSidebar';
import { ProcedureMainContent } from './ProcedureMainContent';
import {
  useProcedureList,
  useProcedureProgress,
  useProcedureDetail,
} from '@/lib/hooks/useProcedure';
import { mockClients } from '../data/mock-data';
import type { Procedura, Step, ChecklistItem, Document } from '../types';
import type { ProceduraResponse } from '@/lib/api/procedure';

/**
 * Merge a catalog procedure with its progress record to build
 * the unified Procedura the UI expects.
 */
function mapCatalogToProcedura(
  catalog: ProceduraResponse,
  completedSteps: number[],
  currentStep: number,
  progressStartedAt?: string
): Procedura {
  const totalSteps = catalog.steps.length;
  const completedCount = completedSteps.length;
  const progress =
    totalSteps > 0 ? Math.round((completedCount / totalSteps) * 100) : 0;

  const steps: Step[] = catalog.steps.map((s, idx) => {
    const isCompleted = completedSteps.includes(idx);
    const checklistItems: ChecklistItem[] = (s.checklist ?? []).map(
      (text, ci) => ({
        id: `${catalog.id}_step${idx}_cl${ci}`,
        text,
        completed: isCompleted,
      })
    );
    const documents: Document[] = (s.documents ?? []).map((name, di) => ({
      id: `${catalog.id}_step${idx}_doc${di}`,
      name,
      required: true,
      verified: isCompleted,
    }));

    return {
      id: `${catalog.id}_step_${idx}`,
      number: idx + 1,
      title: s.title,
      description: s.notes ?? '',
      checklist: checklistItems,
      documents,
      notes: [],
      completed: isCompleted,
    };
  });

  return {
    id: catalog.id,
    title: catalog.title,
    description: catalog.description ?? '',
    category: catalog.category,
    totalSteps,
    completedSteps: completedCount,
    progress,
    steps,
    lastUpdated: progressStartedAt,
  };
}

export function ProcedureView() {
  const {
    procedures: catalogList,
    isLoading: catalogLoading,
    error: catalogError,
  } = useProcedureList();

  const {
    progressList,
    isLoading: progressLoading,
    error: progressError,
    refresh: refreshProgress,
    startProgress,
    advanceStep,
  } = useProcedureProgress();

  // --- local UI state ---
  const [selectedProceduraId, setSelectedProceduraId] = useState<string | null>(
    null
  );
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [showNoteEditor, setShowNoteEditor] = useState(false);
  const [newNote, setNewNote] = useState('');
  const [showClientSelector, setShowClientSelector] = useState(false);
  const [selectedClient, setSelectedClient] = useState('');
  const [isClientMode, setIsClientMode] = useState(false);
  const [documentNotes, setDocumentNotes] = useState<Record<string, string>>(
    {}
  );

  // --- merge catalog + progress ---
  const procedures: Procedura[] = useMemo(() => {
    return catalogList.map(cat => {
      const prog = progressList.find(p => p.procedura_id === cat.id);
      if (prog) {
        return mapCatalogToProcedura(
          cat,
          prog.completed_steps,
          prog.current_step,
          prog.started_at
        );
      }
      return mapCatalogToProcedura(cat, [], 0);
    });
  }, [catalogList, progressList]);

  // Auto-select first procedure once data arrives
  const effectiveId = selectedProceduraId ?? procedures[0]?.id ?? null;
  const selectedProcedura =
    procedures.find(p => p.id === effectiveId) ?? procedures[0] ?? null;

  // Find active progress record for the selected procedure
  const activeProgress = useMemo(
    () => progressList.find(p => p.procedura_id === effectiveId) ?? null,
    [progressList, effectiveId]
  );

  const { updateChecklist, updateNotes, updateDocument } = useProcedureDetail(
    activeProgress?.id ?? null
  );

  const activeClientName = mockClients.find(c => c.id === selectedClient)?.name;

  const handleSelectProcedura = (id: string, stepIndex: number) => {
    setSelectedProceduraId(id);
    setCurrentStepIndex(stepIndex);
    setIsClientMode(false);
    setShowNoteEditor(false);
    setNewNote('');
  };

  const handleToggleChecklistItem = useCallback(
    async (itemId: string) => {
      if (!activeProgress || !selectedProcedura) return;

      // Parse itemId to get stepIndex and itemIndex
      const parts = itemId.split('_');
      const stepPart = parts.find(p => p.startsWith('step'));
      const clPart = parts.find(p => p.startsWith('cl'));
      if (!stepPart || !clPart) return;

      const stepIndex = parseInt(stepPart.replace('step', ''), 10);
      const itemIndex = parseInt(clPart.replace('cl', ''), 10);
      const currentItem =
        selectedProcedura.steps[stepIndex]?.checklist[itemIndex];
      if (!currentItem) return;

      try {
        await updateChecklist(stepIndex, itemIndex, !currentItem.completed);
        await refreshProgress();
        toast.success('Checklist aggiornata');
      } catch {
        toast.error("Errore durante l'aggiornamento della checklist");
      }
    },
    [activeProgress, selectedProcedura, updateChecklist, refreshProgress]
  );

  const handleCompleteStep = useCallback(async () => {
    if (!activeProgress || !selectedProcedura) return;

    try {
      await advanceStep(activeProgress.id);
      if (currentStepIndex < selectedProcedura.totalSteps - 1) {
        setCurrentStepIndex(currentStepIndex + 1);
      }
      toast.success('Passo completato');
    } catch {
      toast.error('Errore durante il completamento del passo');
    }
  }, [activeProgress, selectedProcedura, advanceStep, currentStepIndex]);

  const handleSaveNote = useCallback(async () => {
    if (!activeProgress || !newNote.trim()) return;

    try {
      await updateNotes(newNote.trim());
      await refreshProgress();
      setNewNote('');
      setShowNoteEditor(false);
      toast.success('Nota salvata');
    } catch {
      toast.error('Errore durante il salvataggio della nota');
    }
  }, [activeProgress, newNote, updateNotes, refreshProgress]);

  const handleConfirmClient = useCallback(async () => {
    if (!selectedClient || !effectiveId) return;

    try {
      await startProgress(effectiveId, parseInt(selectedClient, 10));
      setIsClientMode(true);
      setShowClientSelector(false);
      toast.success('Procedura avviata per il cliente');
    } catch {
      toast.error("Errore durante l'avvio della procedura");
    }
  }, [selectedClient, effectiveId, startProgress]);

  const handleToggleDocumentVerification = useCallback(
    async (docId: string) => {
      if (!activeProgress || !selectedProcedura) return;

      // Find the document name from the current procedure steps
      for (const step of selectedProcedura.steps) {
        const doc = step.documents.find(d => d.id === docId);
        if (doc) {
          try {
            await updateDocument(doc.name, !doc.verified);
            await refreshProgress();
            toast.success('Verifica documento aggiornata');
          } catch {
            toast.error("Errore durante l'aggiornamento del documento");
          }
          return;
        }
      }
    },
    [activeProgress, selectedProcedura, updateDocument, refreshProgress]
  );

  const handleDocumentNoteChange = useCallback(
    (docId: string, note: string) => {
      setDocumentNotes(prev => ({ ...prev, [docId]: note }));
    },
    []
  );

  // --- loading state ---
  const isLoading = catalogLoading || progressLoading;
  const error = catalogError || progressError;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F8F5F1] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 text-[#2A5D67] animate-spin mx-auto mb-4" />
          <p className="text-[#1E293B] text-lg">Caricamento procedure...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#F8F5F1] flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-10 h-10 text-red-500 mx-auto mb-4" />
          <p className="text-[#1E293B] text-lg mb-2">
            Errore nel caricamento delle procedure
          </p>
          <p className="text-[#1E293B]/60 text-sm mb-4">{error}</p>
          <Button
            onClick={() => window.location.reload()}
            className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Riprova
          </Button>
        </div>
      </div>
    );
  }

  if (!selectedProcedura) {
    return (
      <div className="min-h-screen bg-[#F8F5F1] flex items-center justify-center">
        <p className="text-[#1E293B] text-lg">Nessuna procedura disponibile</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8F5F1] flex">
      <ProcedureSidebar
        procedures={procedures}
        selectedId={effectiveId ?? ''}
        onSelect={handleSelectProcedura}
      />

      <ProcedureMainContent
        procedura={selectedProcedura}
        currentStepIndex={currentStepIndex}
        isClientMode={isClientMode}
        clientName={activeClientName}
        showNoteEditor={showNoteEditor}
        newNote={newNote}
        onStepSelect={setCurrentStepIndex}
        onStartForClient={() => setShowClientSelector(true)}
        onToggleChecklistItem={handleToggleChecklistItem}
        onToggleDocumentVerification={handleToggleDocumentVerification}
        onDocumentNoteChange={handleDocumentNoteChange}
        onNewNoteChange={setNewNote}
        onShowNoteEditor={() => setShowNoteEditor(true)}
        onCancelNoteEditor={() => {
          setShowNoteEditor(false);
          setNewNote('');
        }}
        onSaveNote={handleSaveNote}
        onCompleteStep={handleCompleteStep}
        onPreviousStep={() => setCurrentStepIndex(currentStepIndex - 1)}
        onNextStep={() => setCurrentStepIndex(currentStepIndex + 1)}
      />

      <AnimatePresence>
        {showClientSelector && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
              onClick={() => setShowClientSelector(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg shadow-2xl z-50 w-full max-w-md"
            >
              <div className="p-6">
                <h2 className="text-2xl font-bold text-[#2A5D67] mb-4">
                  Seleziona un cliente
                </h2>
                <p className="text-sm text-[#1E293B] mb-6">
                  Scegli il cliente per cui vuoi avviare questa procedura
                </p>

                <Select
                  value={selectedClient}
                  onValueChange={setSelectedClient}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleziona un cliente" />
                  </SelectTrigger>
                  <SelectContent>
                    {mockClients.map(client => (
                      <SelectItem key={client.id} value={client.id}>
                        {client.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <div className="flex items-center justify-end space-x-3 mt-6">
                  <Button
                    onClick={() => setShowClientSelector(false)}
                    variant="outline"
                  >
                    Annulla
                  </Button>
                  <Button
                    onClick={handleConfirmClient}
                    disabled={!selectedClient}
                    className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                  >
                    <PlayCircle className="w-4 h-4 mr-2" />
                    <span className="font-bold">Avvia procedura</span>
                  </Button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
