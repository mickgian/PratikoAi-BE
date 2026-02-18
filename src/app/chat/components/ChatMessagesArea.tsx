'use client';

import React, {
  useEffect,
  useMemo,
  useCallback,
  useState,
  useRef,
} from 'react';
import { MessageSquare, Clock, ChevronUp, ChevronDown } from 'lucide-react';
import { useSharedChatState } from '../hooks/useChatState';
import { useSharedChatSessions } from '../hooks/useChatSessions';
import { useSmartScroll } from '../hooks/useSmartScroll';
import { Message } from './Message';
import { TypingIndicator } from './TypingIndicator';
import {
  InteractiveQuestionInline,
  type InteractiveQuestion as InlineQuestionType,
} from './InteractiveQuestionInline';
import { UsageLimitBanner } from './UsageLimitBanner';
import { apiClient } from '@/lib/api';
import { StreamingHandler } from '../handlers/StreamingHandler';

export function ChatMessagesArea() {
  const {
    state,
    messages,
    isCurrentlyStreaming,
    interactiveQuestion,
    clearProactivity,
    setInteractiveQuestion,
    addUserMessage,
    startAIStreaming,
    dispatch,
    usageLimitInfo,
    setUsageLimitInfo,
    clearUsageLimit,
  } = useSharedChatState();
  const handlerRef = useRef<StreamingHandler | null>(null);
  const { currentSession, isLoadingHistory, historyError } =
    useSharedChatSessions();
  const [isAnswering, setIsAnswering] = useState(false);

  const {
    scrollRef,
    bottomRef,
    scrollToBottom,
    scrollToTop,
    setAutoScroll,
    showScrollToTop,
    showScrollToBottom,
  } = useSmartScroll({
    autoScroll: true,
    bottomThreshold: 50,
    smooth: true,
  });

  // ✅ Compute once; keeps the array reference stable across frames
  const visibleMessages = useMemo(() => {
    if (isLoadingHistory || historyError) return [];
    return messages.filter(message => {
      // DEV-007: Never display system messages to users (security)
      if (message.type === 'system') {
        return false;
      }
      // Hide empty AI placeholder only until first content arrives
      const isEmptyStreamingMessage =
        message.type === 'ai' &&
        !message.content &&
        isCurrentlyStreaming &&
        message.id === state.activeStreaming?.messageId;
      return !isEmptyStreamingMessage;
    });
  }, [
    messages,
    isCurrentlyStreaming,
    state.activeStreaming,
    isLoadingHistory,
    historyError,
  ]);

  // Show typing indicator when the placeholder is hidden
  const showTypingIndicator = Boolean(
    isCurrentlyStreaming &&
      state.activeStreaming &&
      !state.activeStreaming.content
  );

  // Handle interactive question answer (DEV-155)
  const handleQuestionAnswer = useCallback(
    async (optionId: string, customInput?: string) => {
      if (!interactiveQuestion || !currentSession?.id) return;
      if (isAnswering) return; // Prevent double-clicks

      setIsAnswering(true);

      console.log('❓ [ChatMessagesArea] Answering question:', {
        questionId: interactiveQuestion.id,
        optionId,
        customInput,
        sessionId: currentSession.id,
      });

      try {
        // Call the /questions/answer endpoint
        const response = await apiClient.answerQuestion({
          question_id: interactiveQuestion.id,
          selected_option: optionId,
          custom_input: customInput,
          session_id: currentSession.id,
        });

        console.log('✅ [ChatMessagesArea] Answer response:', response);

        if (response.next_question) {
          // Multi-step flow: show the next question
          console.log(
            '➡️ [ChatMessagesArea] Multi-step: showing next question:',
            response.next_question.id
          );
          setInteractiveQuestion(response.next_question);
        } else {
          // Terminal question: clear and optionally handle answer
          console.log('✔️ [ChatMessagesArea] Terminal question: clearing');
          clearProactivity();

          // If we have an answer text, send it as a new chat message
          // The backend returns a constructed prompt for dynamic questions
          if (response.answer && currentSession?.id && currentSession?.token) {
            // Use the answer from backend (which is a properly constructed prompt)
            // This triggers a new chat flow with the specific question
            addUserMessage(response.answer);

            // Also trigger the streaming to get AI response
            const messageId = startAIStreaming(currentSession.id);
            if (messageId) {
              // Create streaming handler if needed (with token getter)
              const sessionToken = currentSession.token;
              if (!handlerRef.current) {
                handlerRef.current = new StreamingHandler({
                  dispatch,
                  apiUrl:
                    process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
                  getSessionToken: () => sessionToken,
                });
              } else {
                // Update token getter for current session
                handlerRef.current.setConfig({
                  getSessionToken: () => sessionToken,
                });
              }

              // Build message for streaming
              const outboundMessages: Array<{
                role: 'user' | 'assistant' | 'system';
                content: string;
              }> = [{ role: 'user', content: response.answer }];

              // Start the streaming with skip_proactivity flag
              // This ensures follow-up queries go directly to LLM without triggering proactivity again
              try {
                await handlerRef.current.startStreaming(
                  messageId,
                  outboundMessages,
                  {
                    allowInterruption: false,
                    skipProactivity: true,
                  }
                );
              } catch (streamError) {
                console.error(
                  '❌ [ChatMessagesArea] Streaming failed:',
                  streamError
                );
              }
            }
          }
        }
      } catch (error) {
        console.error(
          '❌ [ChatMessagesArea] Failed to answer question:',
          error
        );
        // Fallback: just clear the question
        clearProactivity();
      } finally {
        setIsAnswering(false);
      }
    },
    [
      interactiveQuestion,
      currentSession,
      isAnswering,
      clearProactivity,
      setInteractiveQuestion,
      addUserMessage,
      startAIStreaming,
      dispatch,
    ]
  );

  // Handle skipping the question (DEV-155)
  const handleQuestionSkip = useCallback(() => {
    console.log('⏭️ [ChatMessagesArea] Question skipped');
    clearProactivity();
  }, [clearProactivity]);

  // Handle multi-field question answer (PRE-RESPONSE PROACTIVITY)
  const handleMultiFieldAnswer = useCallback(
    async (fieldValues: Record<string, string>) => {
      if (!interactiveQuestion || !currentSession?.id) return;
      if (isAnswering) return; // Prevent double-clicks

      setIsAnswering(true);

      console.log('📝 [ChatMessagesArea] Answering multi-field question:', {
        questionId: interactiveQuestion.id,
        fieldValues,
        sessionId: currentSession.id,
      });

      try {
        // Call the /questions/answer endpoint with field_values
        const response = await apiClient.answerQuestion({
          question_id: interactiveQuestion.id,
          field_values: fieldValues,
          session_id: currentSession.id,
        });

        console.log(
          '✅ [ChatMessagesArea] Multi-field answer response:',
          response
        );

        // Clear the question
        clearProactivity();

        // Create user message from field values
        const fieldSummary = Object.entries(fieldValues)
          .map(([key, value]) => `${key}: ${value}`)
          .join(', ');
        addUserMessage(`Calcola con: ${fieldSummary}`);
      } catch (error) {
        console.error(
          '❌ [ChatMessagesArea] Failed to answer multi-field question:',
          error
        );
        // Fallback: just clear the question
        clearProactivity();
      } finally {
        setIsAnswering(false);
      }
    },
    [
      interactiveQuestion,
      currentSession,
      isAnswering,
      clearProactivity,
      addUserMessage,
    ]
  );

  // Convert backend question format to component format
  const mappedQuestion: InlineQuestionType | null = interactiveQuestion
    ? {
        id: interactiveQuestion.id,
        text: interactiveQuestion.text,
        question_type: interactiveQuestion.question_type,
        options: (interactiveQuestion.options || []).map((opt: any) => ({
          id: opt.id,
          label: opt.label,
          icon: opt.icon,
        })),
        fields: interactiveQuestion.fields?.map((field: any) => ({
          id: field.id,
          label: field.label,
          placeholder: field.placeholder,
          input_type: field.input_type,
          required: field.required,
          validation: field.validation,
        })),
        allow_custom_input: interactiveQuestion.allow_custom_input,
        custom_input_placeholder: interactiveQuestion.custom_input_placeholder,
      }
    : null;

  // Auto-scroll behaviors (unchanged)
  useEffect(() => {
    scrollToBottom();
  }, [visibleMessages.length, scrollToBottom]);

  useEffect(() => {
    if (isCurrentlyStreaming) scrollToBottom();
  }, [isCurrentlyStreaming, scrollToBottom]);

  useEffect(() => {
    if (isCurrentlyStreaming && state.activeStreaming?.content) {
      const t = setTimeout(() => scrollToBottom(), 100);
      return () => clearTimeout(t);
    }
  }, [isCurrentlyStreaming, state.activeStreaming?.content, scrollToBottom]);

  // Auto-scroll when interactive question appears (DEV-155)
  useEffect(() => {
    if (interactiveQuestion) {
      const t = setTimeout(() => scrollToBottom(), 150);
      return () => clearTimeout(t);
    }
  }, [interactiveQuestion, scrollToBottom]);

  // Force scroll to bottom when switching sessions
  useEffect(() => {
    if (currentSession?.id) {
      const t = setTimeout(() => setAutoScroll(true), 150);
      return () => clearTimeout(t);
    }
  }, [currentSession?.id, setAutoScroll]);

  // DEV-257: Restore persisted usage limit from localStorage on mount
  useEffect(() => {
    if (usageLimitInfo) return; // already in state
    try {
      const raw = localStorage.getItem('pratiko_usage_limit');
      if (!raw) return;
      const { reset_at, canBypass } = JSON.parse(raw);
      if (!reset_at || new Date(reset_at).getTime() <= Date.now()) {
        localStorage.removeItem('pratiko_usage_limit');
        return;
      }
      // Build minimal UsageLimitInfo to show banner
      setUsageLimitInfo({
        usageData: {
          plan_slug: '',
          plan_name: '',
          window_5h: {
            window_type: '5h',
            current_cost_eur: 0,
            limit_cost_eur: 0,
            usage_percentage: 100,
            reset_at,
            reset_in_minutes: null,
          },
          window_7d: {
            window_type: '7d',
            current_cost_eur: 0,
            limit_cost_eur: 0,
            usage_percentage: 0,
            reset_at: null,
            reset_in_minutes: null,
          },
          credits: { balance_eur: 0, extra_usage_enabled: false },
          message_it: '',
          is_admin: false,
        },
        canBypass: canBypass === true,
      });
    } catch {
      /* ignore */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-scroll when usage limit banner appears (DEV-257)
  useEffect(() => {
    if (usageLimitInfo) {
      const t = setTimeout(() => scrollToBottom(), 150);
      return () => clearTimeout(t);
    }
  }, [usageLimitInfo, scrollToBottom]);

  return (
    <div className="relative flex-1 min-h-0">
      <div
        ref={scrollRef}
        data-testid="chat-messages-area"
        role="log"
        aria-live="polite"
        aria-label="Area messaggi della chat"
        className="h-full overflow-y-auto p-6 bg-[#F8F5F1] scroll-smooth"
      >
        <div
          data-testid="messages-container"
          className="max-w-4xl mx-auto space-y-6"
        >
          {/* Loading / error */}
          {isLoadingHistory && (
            <div
              data-testid="messages-loading-history"
              className="flex items-center justify-center py-12 text-[#C4BDB4]"
            >
              <Clock className="w-6 h-6 mr-2 animate-spin" />
              <span>Caricamento conversazione...</span>
            </div>
          )}

          {historyError && (
            <div
              data-testid="messages-history-error"
              className="bg-red-50 border border-red-200 rounded-lg p-4 text-center"
            >
              <p className="text-red-600 text-sm">
                Errore nel caricamento della conversazione
              </p>
              <p className="text-red-500 text-xs mt-1">{historyError}</p>
            </div>
          )}

          {/* Empty state placeholder - shown when no session and no messages */}
          {!isLoadingHistory &&
            !historyError &&
            !currentSession &&
            visibleMessages.length === 0 && (
              <div
                data-testid="messages-empty-state"
                className="flex flex-col items-center justify-center h-full text-center p-8"
              >
                <MessageSquare className="w-16 h-16 text-gray-400 mb-4" />
                <p className="text-lg text-gray-600">
                  Inizia una nuova conversazione
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  Invia un messaggio per creare una nuova sessione
                </p>
              </div>
            )}

          {/* Messages */}
          {!isLoadingHistory &&
            !historyError &&
            (currentSession || visibleMessages.length > 0) && (
              <>
                <div data-testid="messages-list" className="space-y-4">
                  {visibleMessages.map(message => (
                    <Message
                      key={message.id}
                      message={message}
                      isStreaming={
                        isCurrentlyStreaming &&
                        message.id === state.activeStreaming?.messageId
                      }
                      sessionMessages={messages}
                    />
                  ))}
                </div>

                {/* Interactive Question (DEV-155) */}
                {mappedQuestion && !isCurrentlyStreaming && (
                  <InteractiveQuestionInline
                    question={mappedQuestion}
                    onAnswer={handleQuestionAnswer}
                    onMultiFieldAnswer={handleMultiFieldAnswer}
                    onSkip={handleQuestionSkip}
                    disabled={isCurrentlyStreaming || isAnswering}
                  />
                )}

                {/* DEV-257: Usage limit inline banner */}
                {usageLimitInfo && (
                  <UsageLimitBanner
                    resetAt={
                      usageLimitInfo.usageData.window_5h.reset_at ||
                      usageLimitInfo.usageData.window_7d.reset_at
                    }
                    canBypass={usageLimitInfo.canBypass}
                    onBypass={() => {
                      sessionStorage.setItem('cost_limit_bypass', 'true');
                      localStorage.removeItem('pratiko_usage_limit');
                      clearUsageLimit();
                    }}
                    onDismiss={() => {
                      localStorage.removeItem('pratiko_usage_limit');
                      clearUsageLimit();
                    }}
                  />
                )}

                <TypingIndicator show={showTypingIndicator} />
                <div ref={bottomRef} className="h-1" />
              </>
            )}
        </div>
      </div>

      {showScrollToTop && (
        <button
          onClick={scrollToTop}
          className="absolute top-6 right-6 z-10 w-10 h-10 rounded-full bg-white/90 backdrop-blur-sm text-[#2F3E46] border border-[#C4BDB4]/30 shadow-md hover:shadow-lg transition-all duration-200 hover:scale-105 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#9A8F86] flex items-center justify-center"
          aria-label="Vai all'inizio"
        >
          <ChevronUp className="w-5 h-5" />
        </button>
      )}

      {showScrollToBottom && (
        <button
          onClick={() => scrollToBottom(true)}
          className="absolute bottom-6 right-6 z-10 w-10 h-10 rounded-full bg-white/90 backdrop-blur-sm text-[#2F3E46] border border-[#C4BDB4]/30 shadow-md hover:shadow-lg transition-all duration-200 hover:scale-105 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#9A8F86] flex items-center justify-center"
          aria-label="Vai al fondo"
        >
          <ChevronDown className="w-5 h-5" />
        </button>
      )}
    </div>
  );
}
