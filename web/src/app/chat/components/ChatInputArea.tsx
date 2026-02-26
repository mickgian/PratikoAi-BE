'use client';

import React, { useCallback, useRef, useEffect, useState } from 'react';
import { useSharedChatState } from '../hooks/useChatState';
import { useSharedChatSessions } from '../hooks/useChatSessions';
import { useFileUpload } from '../hooks/useFileUpload';
import { ChatInput } from './ChatInput';
import { FileAttachment } from './FileAttachment';
import { AttachmentPreview } from './AttachmentPreview';
import { DragDropZone } from './DragDropZone';
import { StreamingHandler } from '../handlers/StreamingHandler';
import type { AttachmentInfo } from '../types/chat';
import { getUsageStatus, type UsageStatus } from '@/lib/api/billing';
import {
  getReleaseNotes,
  getReleaseNotesFull,
  getVersion,
  updateUserNotes,
} from '@/lib/api/release-notes';
import type { ReleaseNotePublic, ReleaseNote } from '@/lib/api/release-notes';
import { UsageDialog } from './UsageDialog';
import { NovitaDialog } from './NovitaDialog';

/**
 * DEV-257: Parse a usage limit error from StreamingHandler's lastError.
 * Returns structured data if the error is a USAGE_LIMIT_EXCEEDED 429, null otherwise.
 */
function parseUsageLimitError(error: unknown): {
  usageData: UsageStatus;
  canBypass: boolean;
} | null {
  try {
    const msg = error instanceof Error ? error.message : String(error ?? '');
    const data = JSON.parse(msg);
    if (data?.type !== 'USAGE_LIMIT_EXCEEDED') return null;
    const info = data.limit_info || {};
    return {
      usageData: {
        plan_slug: '',
        plan_name: '',
        window_5h: {
          window_type: '5h',
          current_cost_eur: info.cost_consumed_eur ?? 0,
          limit_cost_eur: info.cost_limit_eur ?? 0,
          usage_percentage:
            info.cost_limit_eur > 0
              ? Math.round((info.cost_consumed_eur / info.cost_limit_eur) * 100)
              : 100,
          reset_at: info.reset_at ?? null,
          reset_in_minutes: info.reset_in_minutes ?? null,
        },
        window_7d: {
          window_type: '7d',
          current_cost_eur: 0,
          limit_cost_eur: 0,
          usage_percentage: 0,
          reset_at: null,
          reset_in_minutes: null,
        },
        credits: {
          balance_eur: data.options?.use_credits?.balance_eur ?? 0,
          extra_usage_enabled: false,
        },
        message_it: data.message_it,
        is_admin: false,
      },
      canBypass: data.can_bypass === true,
    };
  } catch {
    return null;
  }
}

/**
 * DEV-257: Compute a fallback reset_at when the backend doesn't provide one.
 * Uses the window duration (5h or 7d) from now.
 */
function computeFallbackResetAt(windowType: string): string {
  const hours = windowType === '7d' ? 168 : 5;
  return new Date(Date.now() + hours * 3600_000).toISOString();
}

/**
 * Chat input area component (StreamingHandler version)
 * - Single-fire send (sendLockRef) to avoid double sends
 * - Delegates streaming + de-dup to StreamingHandler (no local accumulator)
 * - One streaming instance at a time; cleaned up on complete/error/unmount
 * - Supports file attachments via upload-first pattern
 */

type OutboundMessage = {
  role: 'user' | 'assistant' | 'system';
  content: string;
  attachment_ids?: string[];
};

export function ChatInputArea() {
  const {
    state,
    addUserMessage,
    isCurrentlyStreaming,
    startAIStreaming,
    completeStreaming,
    dispatch,
  } = useSharedChatState();

  const {
    currentSession,
    isLoadingHistory,
    isLoadingSessions,
    createNewSession,
    updateSessionName,
    markSessionAsUsed,
  } = useSharedChatSessions();

  // File upload state management
  const {
    files,
    uploading: _uploading, // Used for logging only
    uploadFile,
    removeFile,
    clearFiles,
    getAttachmentIds,
    hasUploading,
    hasFiles,
    isAtLimit,
  } = useFileUpload();

  // Usage dialog state (DEV-257: modal overlay instead of chat message)
  const [usageDialog, setUsageDialog] = useState<{
    data: UsageStatus | null;
    error: string | null;
    canBypass?: boolean;
  } | null>(null);

  // Novità dialog state (release notes)
  const [novitaDialog, setNovitaDialog] = useState<{
    notes: ReleaseNotePublic[] | ReleaseNote[];
    error: string | null;
    environment?: string;
  } | null>(null);

  // one active streaming handler at a time
  const handlerRef = useRef<StreamingHandler | null>(null);

  // blocks re-entrant "send" (Enter + button, double-press, etc.)
  const sendLockRef = useRef(false);

  // Track previous session to detect deletion (DEV-007 fix)
  const prevSessionIdRef = useRef<string | null>(currentSession?.id ?? null);
  // Key to force ChatInput remount on deletion (clears local state)
  const [inputResetKey, setInputResetKey] = useState(0);

  useEffect(() => {
    return () => {
      // best-effort cancel on unmount
      handlerRef.current?.cancelStreaming().catch(() => {});
      handlerRef.current = null;
    };
  }, []);

  // Allow streaming to continue in background when session changes
  useEffect(() => {
    const sessionId = currentSession?.id;
    console.log('🔍 [CIA] Session changed:', {
      sessionId,
      isCurrentlyStreaming,
    });

    // Don't cancel streaming on session changes - let it continue in background
    if (isCurrentlyStreaming) {
      console.log(
        '🔄 [CIA] Session changed while streaming - allowing background streaming to continue'
      );
    }
  }, [currentSession?.id, isCurrentlyStreaming]);

  // DEV-007: Clear attachments and input when chat is deleted
  // Detects when session goes from a valid ID to null (deletion)
  useEffect(() => {
    const currentId = currentSession?.id ?? null;
    const prevId = prevSessionIdRef.current;

    // If we had a session before and now it's null, the chat was deleted
    if (prevId !== null && currentId === null) {
      console.log('🗑️ [CIA] Chat deleted - clearing attachments and input');
      clearFiles();
      setInputResetKey(prev => prev + 1); // Force ChatInput remount
    }

    // Update the ref for next comparison
    prevSessionIdRef.current = currentId;
  }, [currentSession?.id, clearFiles]);

  // Handle file selection from button or drag-drop
  const handleFilesSelected = useCallback(
    async (selectedFiles: File[]) => {
      for (const file of selectedFiles) {
        await uploadFile(file);
      }
    },
    [uploadFile]
  );

  // DEV-257: Slash commands bypass the message-send pipeline entirely (no session creation)
  const handleSlashCommand = useCallback(async (content: string) => {
    const cmd = content.trim().toLowerCase();

    if (cmd === '/utilizzo') {
      try {
        const usageData = await getUsageStatus();
        setUsageDialog({ data: usageData, error: null });
      } catch {
        setUsageDialog({
          data: null,
          error:
            'Errore nel recupero dei dati di utilizzo. Riprova tra qualche istante.',
        });
      }
      return;
    }

    if (cmd === '/novita') {
      try {
        const versionInfo = await getVersion();
        if (versionInfo.environment === 'qa') {
          const data = await getReleaseNotesFull(1, 50);
          setNovitaDialog({
            notes: data.items,
            error: null,
            environment: 'qa',
          });
        } else {
          const data = await getReleaseNotes(1, 50);
          setNovitaDialog({
            notes: data.items,
            error: null,
            environment: versionInfo.environment,
          });
        }
      } catch {
        setNovitaDialog({
          notes: [],
          error:
            'Errore nel recupero delle novità. Riprova tra qualche istante.',
        });
      }
      return;
    }

    // Unknown slash command — silently ignore (no session, no message)
  }, []);

  const handleSendMessage = useCallback(
    async (content: string) => {
      const attachmentIds = getAttachmentIds();
      console.log('[CIA] handleSendMessage start', {
        contentPreview: content.slice(0, 60),
        attachmentCount: attachmentIds.length,
      });

      // —— hard guard against duplicate triggers ——
      if (sendLockRef.current) {
        console.warn('[CIA] blocked by sendLock (re-entrant)');
        return;
      }
      sendLockRef.current = true;

      try {
        // Require text content (cannot send just attachments)
        if (!content.trim()) {
          console.warn('[CIA] empty message, bail');
          sendLockRef.current = false;
          return;
        }
        if (isCurrentlyStreaming) {
          console.warn('[CIA] already streaming, bail');
          sendLockRef.current = false;
          return;
        }
        // Block send if uploads are in progress
        if (hasUploading) {
          console.warn('[CIA] uploads in progress, bail');
          sendLockRef.current = false;
          return;
        }

        // ensure session
        let sessionToUse = currentSession;
        if (!sessionToUse || !sessionToUse.token) {
          sessionToUse = await createNewSession();
          if (!sessionToUse || !sessionToUse.token) {
            console.error('[CIA] cannot create a valid session');
            sendLockRef.current = false;
            return;
          }
        }

        const isFirstMessage = state.sessionMessages.length === 0;
        if (isFirstMessage && sessionToUse) {
          const newTitle =
            content.length > 50 ? content.slice(0, 47) + '...' : content;
          // fire & forget title update
          updateSessionName(sessionToUse.id, newTitle).catch(console.error);
        }

        // Create attachment info from successfully uploaded files for display in message history
        const attachmentInfo: AttachmentInfo[] = files
          .filter(
            f =>
              f.status === 'success' &&
              !f.id.startsWith('error-') &&
              !f.id.startsWith('uploading-')
          )
          .map(f => ({
            id: f.id,
            filename: f.name,
            size: f.size,
            type: f.type,
          }));

        // add user message immediately with attachment info for display
        addUserMessage(
          content,
          attachmentInfo.length > 0 ? attachmentInfo : undefined
        );

        // 1) UI dispatches START_AI_STREAMING, gets messageId back
        const messageId = startAIStreaming(sessionToUse.id);
        if (!messageId) {
          console.error('[CIA] startAIStreaming did not return messageId');
          sendLockRef.current = false;
          return;
        }

        // lazily create the handler bound to current session token
        if (!handlerRef.current) {
          handlerRef.current = new StreamingHandler({
            dispatch,
            apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
            // assert non-null: we already guaranteed a valid session+token above
            getSessionToken: () => sessionToUse!.token as string,
          });
        } else {
          // refresh token getter in case session changed
          handlerRef.current.setConfig({
            getSessionToken: () => sessionToUse!.token as string,
          });
        }

        // Build conversation (history -> OutboundMessage[])
        // Safety: only include user/ai messages (filter out system/command if any remain)
        const history: OutboundMessage[] = state.sessionMessages
          .filter(m => m.type === 'user' || m.type === 'ai')
          .map(m => ({
            role: m.type === 'ai' ? 'assistant' : 'user',
            content: m.content || '',
          }));

        // Add this new user message with attachment IDs if present
        const newMessage: OutboundMessage = { role: 'user', content };
        if (attachmentIds.length > 0) {
          newMessage.attachment_ids = attachmentIds;
        }

        const outbound: OutboundMessage[] = [...history, newMessage];

        // 2) Start the handler with that same id
        try {
          const success = await handlerRef.current.startStreaming(
            messageId,
            outbound,
            { allowInterruption: false }
          );

          if (!success) {
            // DEV-257: Check if failure was a usage limit error → show inline banner
            const lastError = handlerRef.current.getLastError();
            const limitError = parseUsageLimitError(lastError);
            if (limitError) {
              dispatch({ type: 'SET_USAGE_LIMIT', payload: limitError });
              dispatch({ type: 'FORCE_STOP_STREAMING' });
              // Persist to localStorage so banner survives refresh
              const w = limitError.usageData.window_5h;
              const effectiveResetAt =
                w.reset_at || computeFallbackResetAt(w.window_type);
              try {
                localStorage.setItem(
                  'pratiko_usage_limit',
                  JSON.stringify({
                    reset_at: effectiveResetAt,
                    canBypass: limitError.canBypass,
                  })
                );
              } catch {
                /* ignore */
              }
            } else {
              console.error(
                '[CIA] streaming failed to start or aborted:',
                lastError?.message
              );
            }
          } else {
            // when the promise resolves, the handler has already dispatched COMPLETE_STREAMING

            // Backend now automatically saves all conversations via LangGraph checkpoints
            console.log(
              '[STREAM_PERSIST] ✅ Streaming completed - backend should have saved conversation via LangGraph'
            );

            // Clear attachments after successful send
            if (attachmentIds.length > 0) {
              clearFiles();
            }

            if (isFirstMessage && sessionToUse) {
              markSessionAsUsed(sessionToUse.id);
            }
          }
        } catch (e) {
          // DEV-257: Also handle thrown errors (e.g. "Streaming already in progress")
          const limitError = parseUsageLimitError(e);
          if (limitError) {
            dispatch({ type: 'SET_USAGE_LIMIT', payload: limitError });
            dispatch({ type: 'FORCE_STOP_STREAMING' });
            // Persist to localStorage so banner survives refresh
            const w = limitError.usageData.window_5h;
            const effectiveResetAt =
              w.reset_at || computeFallbackResetAt(w.window_type);
            try {
              localStorage.setItem(
                'pratiko_usage_limit',
                JSON.stringify({
                  reset_at: effectiveResetAt,
                  canBypass: limitError.canBypass,
                })
              );
            } catch {
              /* ignore */
            }
          } else {
            console.error('[CIA] streaming failed to start or aborted:', e);
          }
        } finally {
          // always release the lock
          sendLockRef.current = false;
        }
      } catch (err) {
        console.error('[CIA] handleSendMessage fatal:', err);
        // make sure we never leave the lock engaged
        sendLockRef.current = false;
      }
    },
    [
      isCurrentlyStreaming,
      currentSession,
      createNewSession,
      addUserMessage,
      startAIStreaming,
      state.sessionMessages,
      updateSessionName,
      markSessionAsUsed,
      dispatch,
      getAttachmentIds,
      hasUploading,
      clearFiles,
      files,
    ]
  );

  const isInputDisabled =
    isCurrentlyStreaming || isLoadingHistory || isLoadingSessions;
  const isSendDisabled = isInputDisabled || hasUploading;

  // Show warning if files attached but no text
  const showAttachmentWarning = hasFiles && !hasUploading;

  return (
    <>
      {usageDialog && (
        <UsageDialog
          data={usageDialog.data}
          error={usageDialog.error}
          canBypass={usageDialog.canBypass}
          onBypass={() => {
            sessionStorage.setItem('cost_limit_bypass', 'true');
            setUsageDialog(null);
          }}
          onClose={() => setUsageDialog(null)}
        />
      )}
      {novitaDialog && (
        <NovitaDialog
          notes={novitaDialog.notes}
          error={novitaDialog.error}
          environment={novitaDialog.environment}
          onClose={() => setNovitaDialog(null)}
          onSaveUserNotes={async (version, userNotes) => {
            try {
              await updateUserNotes(version, userNotes);
            } catch {
              console.error('Errore nel salvataggio delle note utente');
            }
          }}
        />
      )}
      <DragDropZone
        onFilesDropped={handleFilesSelected}
        disabled={isInputDisabled}
      >
        <div
          data-testid="chat-input-area"
          role="region"
          aria-label="Area di input per i messaggi"
          className="bg-[#F8F5F1] border-t border-[#C4BDB4]/20 p-6"
        >
          <div className="max-w-4xl mx-auto">
            {/* Attachment preview chips */}
            <AttachmentPreview
              files={files}
              onRemove={removeFile}
              disabled={isSendDisabled}
            />

            {/* Warning message for attachments without text */}
            {showAttachmentWarning && (
              <div
                className="text-sm text-amber-600 mb-2"
                role="alert"
                data-testid="attachment-warning"
              >
                Aggiungi una domanda per inviare
              </div>
            )}

            {/* Input form with attachment button */}
            <div className="flex items-end gap-2">
              <FileAttachment
                onFilesSelected={handleFilesSelected}
                disabled={isInputDisabled}
                isAtLimit={isAtLimit}
              />
              <div className="flex-1">
                <ChatInput
                  key={inputResetKey}
                  onSendMessage={handleSendMessage}
                  onSlashCommand={handleSlashCommand}
                  disabled={isSendDisabled}
                  placeholder={
                    isLoadingSessions
                      ? 'Caricamento sessioni...'
                      : isLoadingHistory
                        ? 'Caricamento conversazione...'
                        : isCurrentlyStreaming
                          ? 'Invio in corso...'
                          : hasUploading
                            ? 'Caricamento in corso...'
                            : 'Fai una domanda fiscale o richiedi assistenza...'
                  }
                />
              </div>
            </div>
          </div>
        </div>
      </DragDropZone>
    </>
  );
}
