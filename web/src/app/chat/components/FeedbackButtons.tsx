'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Check, AlertCircle, X } from 'lucide-react';
import type { Message } from '../types/chat';
import { submitFeedback } from '@/lib/api/expertFeedback';
import type { FeedbackType, FeedbackTypeUI } from '@/types/expertFeedback';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface FeedbackButtonsProps {
  message: Message;
  sessionId: string;
  sessionMessages?: Message[];
  onFeedbackSubmitted?: () => void;
}

// Feedback type mapping: Italian UI → English backend
const FEEDBACK_TYPE_MAP: Record<FeedbackTypeUI, FeedbackType> = {
  corretta: 'correct',
  incompleta: 'incomplete',
  errata: 'incorrect',
} as const;

/**
 * Generate a simple UUID for query_id
 */
function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
/**
 * Extract the user query that prompted this AI message.
 * Searches backwards through chat history to find the last user message before this AI response.
 *
 * @param aiMessageId - The ID of the AI message
 * @param messages - The complete chat history
 * @returns The user query text, or empty string if not found
 */
function extractUserQuery(aiMessageId: string, messages: Message[]): string {
  const aiIndex = messages.findIndex(m => m.id === aiMessageId);
  if (aiIndex === -1) {
    console.warn('[Feedback] AI message not found in history:', aiMessageId);
    return '';
  }

  // Search backwards for last user message
  for (let i = aiIndex - 1; i >= 0; i--) {
    if (messages[i].type === 'user') {
      const query = messages[i].content;
      console.log('[Feedback] Extracted user query:', query);
      return query;
    }
  }

  console.warn('[Feedback] No user message found before AI response');
  return '';
}

/**
 * Expert Feedback Buttons Component (Figma-matched design + Backend API compatible)
 *
 * Displays feedback buttons for expert users to rate AI responses:
 * - Corretta (✓) - Answer is correct (submits immediately)
 * - Incompleta (!) - Answer is incomplete (opens modal for details)
 * - Errata (✗) - Answer is wrong (opens modal for details)
 *
 * Uses modal dialog for collecting additional details on incorrect/incomplete answers.
 * Submits feedback to backend which auto-creates tasks for improvement.
 */
export function FeedbackButtons({
  message,
  sessionId,
  sessionMessages,
  onFeedbackSubmitted,
}: FeedbackButtonsProps) {
  const [uiState, setUiState] = useState<{
    isSubmitting: boolean;
    showDetailsInput: boolean;
    selectedType: FeedbackTypeUI | null;
    error: string | null;
    success: boolean;
  }>({
    isSubmitting: false,
    showDetailsInput: false,
    selectedType: null,
    error: null,
    success: false,
  });

  const [additionalDetails, setAdditionalDetails] = useState<string>('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalType, setModalType] = useState<'incompleta' | 'errata' | null>(
    null
  );

  // Track mount time for time_spent_seconds calculation
  const mountTimeRef = useRef<number>(Date.now());

  // Check if message already has feedback
  const hasFeedback = message.feedback?.rating !== undefined;

  /**
   * Calculate time spent reviewing (in seconds)
   */
  const calculateTimeSpent = (): number => {
    return Math.max(1, Math.floor((Date.now() - mountTimeRef.current) / 1000));
  };

  /**
   * Handle Corretta button click - submits immediately
   */
  const handleCorrettaClick = () => {
    console.log('🔘 [Feedback] Corretta clicked');

    if (uiState.success || hasFeedback) {
      console.log('⏭️ [Feedback] Already submitted, ignoring');
      return;
    }

    setUiState(prev => ({ ...prev, selectedType: 'corretta', error: null }));
    handleSubmit('corretta');
  };

  /**
   * Handle Incompleta button click - opens modal
   */
  const handleIncompletaClick = () => {
    console.log('🔘 [Feedback] Incompleta clicked - opening modal');

    if (uiState.success || hasFeedback) {
      console.log('⏭️ [Feedback] Already submitted, ignoring');
      return;
    }

    setUiState(prev => ({ ...prev, selectedType: 'incompleta', error: null }));
    setModalType('incompleta');
    setIsModalOpen(true);
  };

  /**
   * Handle Errata button click - opens modal
   */
  const handleErrataClick = () => {
    console.log('🔘 [Feedback] Errata clicked - opening modal');

    if (uiState.success || hasFeedback) {
      console.log('⏭️ [Feedback] Already submitted, ignoring');
      return;
    }

    setUiState(prev => ({ ...prev, selectedType: 'errata', error: null }));
    setModalType('errata');
    setIsModalOpen(true);
  };

  /**
   * Handle feedback submission
   */
  const handleSubmit = async (type?: FeedbackTypeUI) => {
    const feedbackTypeUI = type || uiState.selectedType;
    if (!feedbackTypeUI) {
      console.error('❌ [Feedback] No feedback type selected');
      return;
    }

    // Map Italian UI type to English backend type
    const feedbackType = FEEDBACK_TYPE_MAP[feedbackTypeUI];

    console.log('📤 [Feedback] Submitting feedback:', {
      feedbackTypeUI,
      feedbackType,
      additionalDetails,
    });

    // Validate additional details for incomplete/incorrect
    if (
      (feedbackTypeUI === 'incompleta' || feedbackTypeUI === 'errata') &&
      !additionalDetails.trim()
    ) {
      setUiState(prev => ({
        ...prev,
        error: 'I dettagli aggiuntivi sono obbligatori per questa valutazione',
      }));
      return;
    }

    setUiState(prev => ({ ...prev, isSubmitting: true, error: null }));

    try {
      // Calculate time spent
      const timeSpent = calculateTimeSpent();

      // Extract query text from chat history
      const queryText = extractUserQuery(message.id, sessionMessages || []);

      // Validate we got a real query, not a placeholder
      if (!queryText || queryText.trim().length === 0) {
        setUiState(prev => ({
          ...prev,
          isSubmitting: false,
          error:
            "Impossibile estrarre la domanda dell'utente. Riprova più tardi.",
        }));
        return;
      }

      // Build complete request payload matching backend schema
      const payload = {
        // Required fields
        query_id: message.metadata?.query_id || generateUUID(), // Use stored or generate new UUID
        feedback_type: feedbackType,
        query_text: queryText, // ✅ Now extracts actual user query from chat history
        original_answer: message.content,
        confidence_score: 0.8, // Default confidence score - TODO: Add UI for this
        time_spent_seconds: timeSpent,

        // Optional fields
        additional_details:
          feedbackTypeUI !== 'corretta' ? additionalDetails : undefined,
      };

      console.log('📦 [Feedback] Payload:', payload);

      await submitFeedback(payload);

      console.log('✅ [Feedback] Feedback submitted successfully');

      setUiState({
        isSubmitting: false,
        showDetailsInput: false,
        selectedType: feedbackTypeUI,
        error: null,
        success: true,
      });

      // Clear textarea and close modal
      setAdditionalDetails('');
      setIsModalOpen(false);
      setModalType(null);

      // Notify parent component
      onFeedbackSubmitted?.();
    } catch (error) {
      console.error('❌ [Feedback] Submission failed:', error);
      setUiState(prev => ({
        ...prev,
        isSubmitting: false,
        error:
          error instanceof Error
            ? error.message
            : "Errore durante l'invio del feedback",
      }));
    }
  };

  /**
   * Handle modal cancel
   */
  const handleModalCancel = () => {
    console.log('🚫 [Feedback] Modal cancelled');
    setIsModalOpen(false);
    setModalType(null);
    setAdditionalDetails('');
    setUiState(prev => ({
      ...prev,
      selectedType: null,
      error: null,
    }));
  };

  // If already has feedback, show readonly state
  if (hasFeedback) {
    const feedbackIcon =
      message.feedback?.rating === 'up' ? (
        <Check className="w-4 h-4 text-green-600" />
      ) : (
        <X className="w-4 h-4 text-red-600" />
      );

    return (
      <div className="mt-3 pt-3 border-t border-gray-200">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          {feedbackIcon}
          <span>Feedback inviato</span>
        </div>
      </div>
    );
  }

  // If feedback submitted successfully in this session, show success message
  if (uiState.success) {
    return (
      <div className="mt-3 pt-3 border-t border-gray-200">
        <div className="flex items-center gap-2 text-sm text-[#2A5D67] bg-[#A9C1B7]/20 p-3 rounded-lg font-medium">
          <Check className="w-4 h-4" />
          <span>
            Grazie per il tuo feedback! Il tuo contributo aiuta a migliorare
            PratikoAI.
          </span>
        </div>
        {(uiState.selectedType === 'incompleta' ||
          uiState.selectedType === 'errata') && (
          <p className="mt-2 text-xs text-gray-600">
            È stato creato automaticamente un task per analizzare il problema e
            verrà inviata una notifica all&apos;amministratore.
          </p>
        )}
      </div>
    );
  }

  return (
    <>
      <div className="mt-3 pt-3 border-t border-gray-200">
        {/* Error Message (for immediate submissions like "Corretta") */}
        {uiState.error && !isModalOpen && (
          <div
            className="mb-3 p-3 bg-red-50 border-2 border-red-200 rounded-lg text-sm text-red-700 font-medium"
            role="alert"
          >
            {uiState.error}
          </div>
        )}

        {/* Feedback Buttons */}
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-[#1E293B] mr-2">
            Valuta questa risposta:
          </span>

          {/* Corretta Button */}
          <button
            type="button"
            onClick={handleCorrettaClick}
            disabled={uiState.isSubmitting}
            className={`
              inline-flex items-center gap-1.5 px-4 py-2 rounded-full
              text-sm font-semibold transition-all duration-300
              ${
                uiState.selectedType === 'corretta'
                  ? 'bg-[#2A5D67] text-white ring-2 ring-[#2A5D67] shadow-lg scale-105'
                  : 'bg-[#F8F5F1] text-[#2A5D67] hover:bg-[#A9C1B7]/20 hover:scale-105 hover:shadow-md'
              }
              ${uiState.isSubmitting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[#2A5D67]/50
              active:scale-95
            `}
            aria-label="Risposta corretta"
          >
            <Check className="w-4 h-4" />
            <span>Corretta</span>
          </button>

          {/* Incompleta Button */}
          <button
            type="button"
            onClick={handleIncompletaClick}
            disabled={uiState.isSubmitting}
            className={`
              inline-flex items-center gap-1.5 px-4 py-2 rounded-full
              text-sm font-semibold transition-all duration-300
              ${
                uiState.selectedType === 'incompleta'
                  ? 'bg-[#D4A574] text-white ring-2 ring-[#D4A574] shadow-lg scale-105'
                  : 'bg-[#F8F5F1] text-[#D4A574] hover:bg-[#D4A574]/20 hover:scale-105 hover:shadow-md'
              }
              ${uiState.isSubmitting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[#D4A574]/50
              active:scale-95
            `}
            aria-label="Risposta incompleta"
          >
            <AlertCircle className="w-4 h-4" />
            <span>Incompleta</span>
          </button>

          {/* Errata Button */}
          <button
            type="button"
            onClick={handleErrataClick}
            disabled={uiState.isSubmitting}
            className={`
              inline-flex items-center gap-1.5 px-4 py-2 rounded-full
              text-sm font-semibold transition-all duration-300
              ${
                uiState.selectedType === 'errata'
                  ? 'bg-[#d4183d] text-white ring-2 ring-[#d4183d] shadow-lg scale-105'
                  : 'bg-[#F8F5F1] text-[#d4183d] hover:bg-red-50 hover:scale-105 hover:shadow-md'
              }
              ${uiState.isSubmitting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[#d4183d]/50
              active:scale-95
            `}
            aria-label="Risposta errata"
          >
            <X className="w-4 h-4" />
            <span>Errata</span>
          </button>
        </div>
      </div>

      {/* Modal Dialog for Incompleta/Errata */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold text-[#1E293B]">
              {modalType === 'incompleta'
                ? 'Feedback Incompleto'
                : 'Feedback Errore'}
            </DialogTitle>
            <DialogDescription className="text-sm text-gray-600">
              {modalType === 'incompleta'
                ? 'Descrivi cosa manca nella risposta per renderla completa.'
                : 'Spiega perché la risposta è errata e fornisci la correzione.'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4" data-testid="feedback-details-input">
            <div className="space-y-2">
              <label
                htmlFor="feedback-details-textarea"
                className="text-sm font-semibold text-[#1E293B]"
              >
                Dettagli aggiuntivi{' '}
                <span className="text-red-500" aria-label="obbligatorio">
                  *
                </span>
              </label>
              <textarea
                id="feedback-details-textarea"
                value={additionalDetails}
                onChange={e => setAdditionalDetails(e.target.value)}
                placeholder={
                  modalType === 'incompleta'
                    ? 'Descrivi cosa manca nella risposta...'
                    : 'Spiega perché la risposta è errata e fornisci la correzione...'
                }
                className="w-full px-3 py-2 border-2 border-[#C4BDB4] rounded-lg text-sm
                         focus:ring-[3px] focus:ring-[#2A5D67]/20 focus:border-[#2A5D67]
                         resize-y min-h-[150px] transition-all duration-200
                         placeholder:text-[#C4BDB4]"
                disabled={uiState.isSubmitting}
                aria-required="true"
              />
            </div>

            {/* Error Message */}
            {uiState.error && (
              <div
                className="p-3 bg-red-50 border-2 border-red-200 rounded-lg text-sm text-red-700 font-medium"
                role="alert"
              >
                {uiState.error}
              </div>
            )}
          </div>

          <DialogFooter className="gap-2 sm:gap-2">
            <button
              type="button"
              onClick={handleModalCancel}
              disabled={uiState.isSubmitting}
              className="px-6 py-2.5 bg-[#F8F5F1] text-[#1E293B] text-sm font-semibold rounded-lg
                       hover:bg-[#C4BDB4]/30 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all duration-300 border-2 border-[#C4BDB4]
                       hover:scale-105 active:scale-95
                       focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[#C4BDB4]/50"
            >
              Annulla
            </button>
            <button
              type="button"
              onClick={() => handleSubmit()}
              disabled={uiState.isSubmitting || !additionalDetails.trim()}
              className="px-6 py-2.5 bg-[#2A5D67] text-white text-sm font-semibold rounded-lg
                       hover:bg-[#2A5D67]/90 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all duration-300 shadow-lg hover:shadow-xl
                       hover:scale-105 active:scale-95
                       focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[#2A5D67]/50"
            >
              {uiState.isSubmitting ? 'Invio in corso...' : 'Invia Feedback'}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
