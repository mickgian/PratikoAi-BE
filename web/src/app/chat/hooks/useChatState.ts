'use client';

import React, {
  createContext,
  useContext,
  useReducer,
  useCallback,
  useMemo,
} from 'react';
import { nanoid } from 'nanoid';
import {
  ChatState,
  ChatAction,
  Message,
  AttachmentInfo,
  UsageLimitInfo,
  createInitialChatState,
  createUserMessage,
} from '../types/chat';
import { useChatStorage } from './useChatStorage';
import { LogPrefix } from '../utils/LogPrefix';

/* ---------------------------- DEDUP HELPERS ---------------------------- */

function normalizeLoose(s: string) {
  return s.replace(/\r/g, '').replace(/\s+/g, ' ').trim();
}
function normalizeAggressive(s: string) {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '')
    .trim();
}

// KMP period collapse: if s = X repeated k≥2 → return X
function collapseByKmp(s: string): string {
  const n = s.length;
  if (n <= 1) return s;
  const pi = new Array<number>(n).fill(0);
  for (let i = 1; i < n; i++) {
    let j = pi[i - 1];
    while (j > 0 && s[i] !== s[j]) j = pi[j - 1];
    if (s[i] === s[j]) j++;
    pi[i] = j;
  }
  const p = n - pi[n - 1];
  if (p < n && n % p === 0) return s.slice(0, p);
  return s;
}

// Near-middle halves equality (loose normalization)
function collapseNearMiddle(s: string): string {
  const n = s.length;
  if (n < 40) return s;
  const mid = Math.floor(n / 2);
  // check exact mid and a small window around it for natural boundaries
  const WINDOW = Math.min(200, Math.floor(n / 4));
  const trySplit = (idx: number) => {
    if (idx <= 0 || idx >= n) return null;
    const left = s.slice(0, idx);
    const right = s.slice(idx);
    if (!left.trim() || !right.trim()) return null;
    const L = normalizeLoose(left);
    const R = normalizeLoose(right);
    if (L === R) return left;
    // super loose check (handles tiny punctuation/space diffs)
    if (normalizeAggressive(left) === normalizeAggressive(right)) return left;
    return null;
  };
  const c0 = trySplit(mid);
  if (c0) return c0;
  for (let off = 1; off <= WINDOW; off++) {
    const cL = trySplit(mid - off);
    if (cL) return cL;
    const cR = trySplit(mid + off);
    if (cR) return cR;
  }
  return s;
}

// Heuristic: look for a reoccurrence of the prefix later; if so, and halves are ~same by loose norm → keep the first
function collapsePrefixReoccurrence(s: string): string {
  const n = s.length;
  if (n < 80) return s;
  const probeLen = Math.min(96, Math.floor(n / 3));
  const head = s.slice(0, probeLen);
  const start = s.indexOf(head, Math.max(40, Math.floor(n / 3)));
  if (start <= 0) return s;
  const left = s.slice(0, start);
  const right = s.slice(start);
  const L = normalizeLoose(left);
  const R = normalizeLoose(right.slice(0, left.length));
  if (L && L === R) return left;
  if (
    normalizeAggressive(left) ===
    normalizeAggressive(right.slice(0, left.length))
  )
    return left;
  return s;
}

// Full pipeline: try strong → looser → heuristic
function collapseDuplicatesAll(raw: string): string {
  if (!raw) return raw;
  const kmp = collapseByKmp(raw);
  if (kmp.length < raw.length) return kmp;
  const mid = collapseNearMiddle(raw);
  if (mid.length < raw.length) return mid;
  return collapsePrefixReoccurrence(raw);
}

/* ---------------------------- STREAM MERGE ---------------------------- */

// Reconcile previous buffer and incoming chunk/snapshot
// Handles: snapshots (incoming supersets prev), older snapshots, overlap glue
function reconcile(prev: string, incoming: string): string {
  if (!prev) return incoming;
  if (!incoming) return prev;
  if (incoming === prev) return prev;
  if (incoming.startsWith(prev)) return incoming;
  if (prev.startsWith(incoming)) return prev;
  // glue by overlap
  const maxOverlap = Math.min(prev.length, incoming.length);
  let k = 0;
  for (let i = 1; i <= maxOverlap; i++) {
    if (prev.slice(-i) === incoming.slice(0, i)) k = i;
  }
  return prev + incoming.slice(k);
}

/* ------------------------------ REDUCER ------------------------------ */

function chatStateReducer(state: ChatState, action: ChatAction): ChatState {
  LogPrefix.log(LogPrefix.STATE_REDUCER, `${action.type} action received`);
  LogPrefix.log(
    LogPrefix.STATE_REDUCER,
    `BEFORE - sessionMessages: ${state.sessionMessages.length}, activeStreaming: ${
      (state as any).activeStreaming?.messageId || 'none'
    }`
  );

  switch (action.type) {
    case 'ADD_USER_MESSAGE': {
      const actionMessage = (action as any).message;
      const newMessage = createUserMessage(
        actionMessage.content,
        actionMessage.attachments
      );
      return {
        ...state,
        sessionMessages: [...state.sessionMessages, newMessage],
        // Clear proactivity state when user sends a new message (DEV-155)
        interactiveQuestion: null,
      };
    }

    case 'START_AI_STREAMING': {
      if ((state as any).activeStreaming !== null) {
        console.warn(
          '⚠️ START_AI_STREAMING: Already streaming; ignoring duplicate'
        );
        return state;
      }
      const messageId = (action as any).messageId;
      const providedSessionId = (action as any).currentSessionId;
      const stateSessionId = (state as any).currentSessionId;

      // Use provided session ID if available, fallback to state session ID
      const originSessionId = providedSessionId || stateSessionId;

      // CRITICAL FIX: Capture the user message that triggered this streaming
      // Find the most recent user message to store with streaming state
      let triggeringUserMessage = null;
      for (let i = state.sessionMessages.length - 1; i >= 0; i--) {
        if (state.sessionMessages[i].type === 'user') {
          triggeringUserMessage = state.sessionMessages[i];
          break;
        }
      }

      LogPrefix.log(
        LogPrefix.STREAM_SESSION,
        `START_AI_STREAMING: ${messageId} in session: ${originSessionId}`,
        {
          providedSessionId,
          stateSessionId,
          usingOriginSessionId: originSessionId,
          capturedUserMessage: triggeringUserMessage?.content
            ? triggeringUserMessage.content.substring(0, 50)
            : 'none',
        }
      );

      return {
        ...state,
        currentSessionId: originSessionId, // Update state session ID if provided
        activeStreaming: {
          messageId,
          content: '',
          visibleLen: 0,
          startedAt: new Date().toISOString(),
          originSessionId: originSessionId,
          triggeringUserMessage: triggeringUserMessage, // Store user message in streaming state
        } as any,
      };
    }

    case 'UPDATE_STREAMING_CONTENT': {
      const { messageId, content } =
        'payload' in action
          ? (action as any).payload
          : {
              messageId: (action as any).messageId,
              content: (action as any).content,
            };

      const s = (state as any).activeStreaming;
      if (!s) {
        LogPrefix.warn(
          LogPrefix.STREAM_CONTENT,
          'No active stream, ignoring chunk'
        );
        return state;
      }
      if (messageId !== s.messageId) {
        LogPrefix.warn(LogPrefix.STREAM_CONTENT, 'Chunk for different stream', {
          chunkFor: messageId,
          active: s.messageId,
        });
        return state;
      }

      // REMOVED: Don't clear streaming when session changes - allow background streaming
      // The streaming will only be VISIBLE in the session where it originated
      // but the process continues in the background

      const prevFull: string = s.content || '';
      const incoming: string = typeof content === 'string' ? content : '';
      if (!incoming) return state;

      // 1) reconcile
      const merged = reconcile(prevFull, incoming);

      // 2) DON'T dedupe during streaming - only reconcile
      // Deduplication blocks legitimate chunks and causes incomplete responses
      // We only dedupe on COMPLETE_STREAMING (final state)
      // const deduped = collapseDuplicatesAll(merged)  // DISABLED DURING STREAMING

      if (merged === prevFull) return state; // no visible change

      // 3) expose all known content (append-only UX)
      const newVisibleLen = Math.max(s.visibleLen ?? 0, merged.length);

      return {
        ...state,
        activeStreaming: {
          ...s,
          content: merged, // Use merged directly, not deduped
          visibleLen: newVisibleLen,
        },
      };
    }

    // DEV-201: Replace streaming content with cleaned version (XML tags stripped)
    case 'REPLACE_STREAMING_CONTENT': {
      const { messageId, content } = (action as any).payload;

      const s = (state as any).activeStreaming;
      if (!s) {
        LogPrefix.warn(
          LogPrefix.STREAM_CONTENT,
          'REPLACE: No active stream, ignoring'
        );
        return state;
      }
      if (messageId !== s.messageId) {
        LogPrefix.warn(LogPrefix.STREAM_CONTENT, 'REPLACE: Wrong stream ID', {
          replaceFor: messageId,
          active: s.messageId,
        });
        return state;
      }

      LogPrefix.log(
        LogPrefix.STREAM_CONTENT,
        'REPLACE: Replacing content with cleaned version',
        {
          originalLen: (s.content || '').length,
          cleanedLen: content.length,
        }
      );

      return {
        ...state,
        activeStreaming: {
          ...s,
          content: content,
          visibleLen: content.length,
        },
      };
    }

    case 'FORCE_STOP_STREAMING': {
      const s = (state as any).activeStreaming;
      if (!s) {
        LogPrefix.log(
          LogPrefix.STREAM_SESSION,
          'FORCE_STOP_STREAMING: No active streaming to stop'
        );
        return state;
      }
      LogPrefix.log(
        LogPrefix.STREAM_SESSION,
        'FORCE_STOP_STREAMING: Forcefully stopping streaming',
        {
          messageId: s.messageId,
          originSession: s.originSessionId,
        }
      );
      return { ...state, activeStreaming: null as any };
    }

    case 'COMPLETE_STREAMING': {
      const s = (state as any).activeStreaming;
      if (!s) {
        console.warn('⚠️ COMPLETE_STREAMING: No active streaming to complete');
        return state;
      }

      // Final belt & suspenders: collapse any duplicates
      const finalContent = collapseDuplicatesAll(s.content || '');

      if (!finalContent.trim()) {
        LogPrefix.log(
          LogPrefix.STREAM_CONTENT,
          'COMPLETE: Empty after collapse; clearing activeStreaming only'
        );
        return { ...state, activeStreaming: null as any };
      }

      const currentSessionId = (state as any).currentSessionId;
      const streamingOriginSession = s.originSessionId;

      LogPrefix.log(
        LogPrefix.STREAM_SESSION,
        'COMPLETE: Completing streaming',
        {
          messageId: s.messageId,
          originSession: streamingOriginSession,
          currentSession: currentSessionId,
          willAddToCurrentSession: streamingOriginSession === currentSessionId,
        }
      );

      // Guard against double-commit (same id or same (loose) content) - only for current session
      if (streamingOriginSession === currentSessionId) {
        const last = state.sessionMessages[state.sessionMessages.length - 1];
        if (
          last &&
          last.type === 'ai' &&
          (last.id === s.messageId ||
            normalizeLoose(last.content ?? '') === normalizeLoose(finalContent))
        ) {
          LogPrefix.log(
            LogPrefix.MSG_DEDUP,
            'COMPLETE_STREAMING: dropping duplicate AI message (same id/content)'
          );
          return { ...state, activeStreaming: null as any };
        }
      }

      // DEV-244 FIX: Apply pending KB sources from activeStreaming
      // DEV-245: Apply pending web verification from activeStreaming
      // DEV-256: Apply pending enriched_prompt and metadata for model comparison
      const aiMessage: Message = {
        id: s.messageId,
        type: 'ai',
        content: finalContent,
        timestamp: new Date().toISOString(),
        ...(s.pendingKbSources && { kb_source_urls: s.pendingKbSources }),
        ...(s.pendingWebVerification && {
          web_verification: s.pendingWebVerification,
        }),
        ...(s.pendingEnrichedPrompt && {
          enriched_prompt: s.pendingEnrichedPrompt,
        }),
        ...(s.pendingMetadata && { metadata: s.pendingMetadata }),
      };

      if (s.pendingKbSources) {
        LogPrefix.log(
          LogPrefix.STATE_REDUCER,
          'COMPLETE_STREAMING: Applying pending KB sources to AI message',
          { messageId: s.messageId, sourcesCount: s.pendingKbSources.length }
        );
      }
      if (s.pendingWebVerification) {
        LogPrefix.log(
          LogPrefix.STATE_REDUCER,
          'COMPLETE_STREAMING: Applying pending web verification to AI message',
          {
            messageId: s.messageId,
            sourcesChecked: s.pendingWebVerification.web_sources_checked,
          }
        );
      }

      const userMessage = s.triggeringUserMessage;

      // CRITICAL FIX: Store completed conversation in local cache to prevent disappearing
      // This ensures messages persist even if there's a delay before backend saves are available
      if (userMessage && streamingOriginSession) {
        const completedConversation = [userMessage, aiMessage];
        LogPrefix.log(
          LogPrefix.STREAM_PERSIST,
          `Caching completed conversation for session: ${streamingOriginSession}`,
          {
            userMessage: userMessage.content.substring(0, 50),
            aiMessage: aiMessage.content.substring(0, 50),
          }
        );

        // Store in global cache that persists across session switches
        if (!(window as any).__completedConversations) {
          (window as any).__completedConversations = new Map();
        }
        (window as any).__completedConversations.set(
          streamingOriginSession,
          completedConversation
        );
      }

      // Always add to sessionMessages if streaming originated from current session
      const newSessionMessages =
        streamingOriginSession === currentSessionId
          ? [...state.sessionMessages, aiMessage]
          : state.sessionMessages;

      // CRITICAL: Always save both user and AI messages to backend for the originating session
      if (streamingOriginSession) {
        setTimeout(() => {
          if (userMessage && userMessage.type === 'user') {
            LogPrefix.log(
              LogPrefix.STREAM_PERSIST,
              `Saving captured user message: ${userMessage.content.substring(0, 50)}`
            );
            (window as any).__pendingMessageSave = {
              messages: [userMessage, aiMessage],
              sessionId: streamingOriginSession,
            };
          } else {
            LogPrefix.log(
              LogPrefix.STREAM_PERSIST,
              `Saving AI message only (no user message captured)`
            );
            (window as any).__pendingMessageSave = {
              message: aiMessage,
              sessionId: streamingOriginSession,
            };
          }
        }, 0);
      }

      return {
        ...state,
        sessionMessages: newSessionMessages,
        activeStreaming: null as any,
      };
    }

    case 'CLEAR_MESSAGES': {
      return { ...state, sessionMessages: [], activeStreaming: null as any };
    }

    case 'LOAD_SESSION': {
      const loadingSessionId = (action as any).sessionId;
      const currentStreamingSessionId = (state as any).currentSessionId;
      const activeStreaming = (state as any).activeStreaming;
      const incomingMessages = (action as any).messages;

      LogPrefix.log(
        LogPrefix.SESSION_LOAD,
        `LOAD_SESSION: ${incomingMessages.length} msgs for session ${loadingSessionId}`
      );

      // CRITICAL FIX: Check for cached completed conversations and active streaming
      let messagesToLoad = incomingMessages;

      // First check for cached completed conversations (prevents disappearing after completion)
      const completedCache = (window as any).__completedConversations;
      if (completedCache && completedCache.has(loadingSessionId)) {
        const cachedConversation = completedCache.get(loadingSessionId);
        LogPrefix.log(
          LogPrefix.SESSION_LOAD,
          'LOAD_SESSION: Found cached completed conversation',
          {
            sessionId: loadingSessionId,
            cachedMessages: cachedConversation.length,
            incomingMessages: incomingMessages.length,
          }
        );

        // Use cached conversation if backend doesn't have the messages yet
        if (
          incomingMessages.length === 0 ||
          !incomingMessages.some(
            (msg: Message) => msg.content === cachedConversation[0].content
          )
        ) {
          LogPrefix.log(
            LogPrefix.SESSION_LOAD,
            'LOAD_SESSION: Using cached conversation (not in backend yet)'
          );
          messagesToLoad = cachedConversation;
        } else {
          LogPrefix.log(
            LogPrefix.SESSION_LOAD,
            'LOAD_SESSION: Backend has messages, removing from cache'
          );
          completedCache.delete(loadingSessionId);
        }
      }

      // Then handle active streaming sessions
      if (
        activeStreaming &&
        activeStreaming.originSessionId === loadingSessionId
      ) {
        // We're loading the session where streaming is active
        const capturedUserMessage = activeStreaming.triggeringUserMessage;

        if (
          capturedUserMessage &&
          !messagesToLoad.some(
            (msg: Message) => msg.content === capturedUserMessage.content
          )
        ) {
          LogPrefix.log(
            LogPrefix.SESSION_LOAD,
            'LOAD_SESSION: Including captured user message for active streaming session',
            {
              capturedMessage: capturedUserMessage.content.substring(0, 50),
              currentMessagesCount: messagesToLoad.length,
            }
          );
          // Add the captured user message to the messages
          messagesToLoad = [...messagesToLoad, capturedUserMessage];
        } else if (capturedUserMessage) {
          LogPrefix.log(
            LogPrefix.SESSION_LOAD,
            'LOAD_SESSION: Captured user message already exists in messages'
          );
        } else {
          LogPrefix.log(
            LogPrefix.SESSION_LOAD,
            'LOAD_SESSION: No captured user message found in streaming state'
          );
        }
      }

      // Handle streaming visibility based on session context
      if (activeStreaming && activeStreaming.originSessionId) {
        const streamingBelongsToLoadedSession =
          activeStreaming.originSessionId === loadingSessionId;
        const streamingBelongsToCurrentSession =
          activeStreaming.originSessionId === currentStreamingSessionId;

        if (streamingBelongsToLoadedSession) {
          LogPrefix.log(
            LogPrefix.STREAM_SESSION,
            'LOAD_SESSION: Returning to session with active streaming - showing streaming UI'
          );
        } else if (streamingBelongsToCurrentSession) {
          LogPrefix.log(
            LogPrefix.STREAM_SESSION,
            'LOAD_SESSION: Leaving session with active streaming - hiding streaming UI but keeping background'
          );
        }
      }

      return {
        ...state,
        sessionMessages: messagesToLoad,
        currentSessionId: loadingSessionId,
        // Keep activeStreaming but it will only be visible if it belongs to current session
        activeStreaming: activeStreaming,
      };
    }

    case 'ADD_MESSAGE_FEEDBACK': {
      return {
        ...state,
        sessionMessages: state.sessionMessages.map(msg =>
          msg.id === (action as any).messageId
            ? { ...msg, feedback: (action as any).feedback }
            : msg
        ),
      };
    }

    // Proactivity actions (DEV-155)
    case 'SET_INTERACTIVE_QUESTION': {
      LogPrefix.log(
        LogPrefix.STATE_REDUCER,
        'SET_INTERACTIVE_QUESTION: Setting question',
        { questionId: (action as any).question?.id }
      );
      return {
        ...state,
        interactiveQuestion: (action as any).question,
      };
    }

    case 'CLEAR_PROACTIVITY': {
      LogPrefix.log(LogPrefix.STATE_REDUCER, 'CLEAR_PROACTIVITY: Clearing all');
      return {
        ...state,
        interactiveQuestion: null,
      };
    }

    // DEV-257: Usage limit inline banner
    case 'SET_USAGE_LIMIT': {
      const payload = (
        action as { type: 'SET_USAGE_LIMIT'; payload: UsageLimitInfo | null }
      ).payload;
      LogPrefix.log(
        LogPrefix.STATE_REDUCER,
        'SET_USAGE_LIMIT: Setting usage limit info',
        { hasPayload: payload !== null }
      );
      return {
        ...state,
        usageLimitInfo: payload,
      };
    }

    // DEV-242: Chain of Thought reasoning
    case 'SET_MESSAGE_REASONING': {
      const { messageId, reasoning } = action as {
        type: 'SET_MESSAGE_REASONING';
        messageId: string;
        reasoning: any;
      };
      LogPrefix.log(
        LogPrefix.STATE_REDUCER,
        'SET_MESSAGE_REASONING: Setting reasoning for message',
        { messageId, hasTema: !!reasoning?.tema_identificato }
      );
      return {
        ...state,
        sessionMessages: state.sessionMessages.map(msg =>
          msg.id === messageId ? { ...msg, reasoning } : msg
        ),
      };
    }

    // DEV-244: KB source URLs (deterministic, independent of LLM output)
    case 'SET_MESSAGE_KB_SOURCES': {
      const { messageId, kb_source_urls } = action as {
        type: 'SET_MESSAGE_KB_SOURCES';
        messageId: string;
        kb_source_urls: Array<{
          title: string;
          url: string;
          type: string;
          date?: string; // Optional - may not be available for all sources
        }>;
      };

      // DEV-244 FIX: If message is currently streaming, store in activeStreaming
      // The kb_source_urls event arrives BEFORE COMPLETE_STREAMING, so we need to
      // store it in activeStreaming and apply it when the message is finalized
      const s = (state as any).activeStreaming;
      if (s && s.messageId === messageId) {
        LogPrefix.log(
          LogPrefix.STATE_REDUCER,
          'SET_MESSAGE_KB_SOURCES: Storing pending KB sources in activeStreaming',
          { messageId, sourcesCount: kb_source_urls?.length }
        );
        return {
          ...state,
          activeStreaming: {
            ...s,
            pendingKbSources: kb_source_urls,
          },
        };
      }

      // Otherwise update sessionMessages (for non-streaming updates)
      LogPrefix.log(
        LogPrefix.STATE_REDUCER,
        'SET_MESSAGE_KB_SOURCES: Setting KB sources for message in sessionMessages',
        { messageId, sourcesCount: kb_source_urls?.length }
      );
      return {
        ...state,
        sessionMessages: state.sessionMessages.map(msg =>
          msg.id === messageId ? { ...msg, kb_source_urls } : msg
        ),
      };
    }

    // DEV-245: Web verification results from Brave Search
    case 'SET_MESSAGE_WEB_VERIFICATION': {
      const { messageId, web_verification } = action as {
        type: 'SET_MESSAGE_WEB_VERIFICATION';
        messageId: string;
        web_verification: {
          caveats?: string[];
          has_caveats?: boolean;
          web_sources_checked?: number;
          verification_performed?: boolean;
          brave_ai_summary?: string;
          synthesized_response?: string;
          has_synthesized_response?: boolean;
        };
      };

      // If message is currently streaming, store in activeStreaming
      const s = (state as any).activeStreaming;
      if (s && s.messageId === messageId) {
        LogPrefix.log(
          LogPrefix.STATE_REDUCER,
          'SET_MESSAGE_WEB_VERIFICATION: Storing pending web verification in activeStreaming',
          { messageId, sourcesChecked: web_verification?.web_sources_checked }
        );
        return {
          ...state,
          activeStreaming: {
            ...s,
            pendingWebVerification: web_verification,
          },
        };
      }

      // Otherwise update sessionMessages (for non-streaming updates)
      LogPrefix.log(
        LogPrefix.STATE_REDUCER,
        'SET_MESSAGE_WEB_VERIFICATION: Setting web verification for message in sessionMessages',
        { messageId, sourcesChecked: web_verification?.web_sources_checked }
      );
      return {
        ...state,
        sessionMessages: state.sessionMessages.map(msg =>
          msg.id === messageId ? { ...msg, web_verification } : msg
        ),
      };
    }

    // DEV-256: Enriched prompt for model comparison feature
    case 'SET_MESSAGE_ENRICHED_PROMPT': {
      const { messageId, enriched_prompt } = action as {
        type: 'SET_MESSAGE_ENRICHED_PROMPT';
        messageId: string;
        enriched_prompt: string;
      };

      // If message is currently streaming, store in activeStreaming
      const s = (state as any).activeStreaming;
      if (s && s.messageId === messageId) {
        LogPrefix.log(
          LogPrefix.STATE_REDUCER,
          'SET_MESSAGE_ENRICHED_PROMPT: Storing pending enriched_prompt in activeStreaming',
          { messageId, promptLength: enriched_prompt?.length }
        );
        return {
          ...state,
          activeStreaming: {
            ...s,
            pendingEnrichedPrompt: enriched_prompt,
          },
        };
      }

      // Otherwise update sessionMessages (for non-streaming updates)
      LogPrefix.log(
        LogPrefix.STATE_REDUCER,
        'SET_MESSAGE_ENRICHED_PROMPT: Setting enriched_prompt for message in sessionMessages',
        { messageId, promptLength: enriched_prompt?.length }
      );
      return {
        ...state,
        sessionMessages: state.sessionMessages.map(msg =>
          msg.id === messageId ? { ...msg, enriched_prompt } : msg
        ),
      };
    }

    // DEV-256: LLM metrics for model comparison feature
    case 'SET_MESSAGE_METADATA': {
      const { messageId, metadata } = action as {
        type: 'SET_MESSAGE_METADATA';
        messageId: string;
        metadata: {
          response_time_ms?: number;
          tokens_used?: number;
          cost_cents?: number;
          model_used?: string;
        };
      };

      // If message is currently streaming, store in activeStreaming
      const s = (state as any).activeStreaming;
      if (s && s.messageId === messageId) {
        LogPrefix.log(
          LogPrefix.STATE_REDUCER,
          'SET_MESSAGE_METADATA: Storing pending metadata in activeStreaming',
          { messageId, metadata }
        );
        return {
          ...state,
          activeStreaming: {
            ...s,
            pendingMetadata: metadata,
          },
        };
      }

      // Otherwise update sessionMessages (for non-streaming updates)
      LogPrefix.log(
        LogPrefix.STATE_REDUCER,
        'SET_MESSAGE_METADATA: Setting metadata for message in sessionMessages',
        { messageId, metadata }
      );
      return {
        ...state,
        sessionMessages: state.sessionMessages.map(msg =>
          msg.id === messageId
            ? { ...msg, metadata: { ...msg.metadata, ...metadata } }
            : msg
        ),
      };
    }

    default:
      return state;
  }
}

/* ---------------------------------- HOOK ---------------------------------- */

export function useChatState() {
  const [state, dispatch] = useReducer(
    chatStateReducer,
    createInitialChatState()
  );
  const { saveMessage } = useChatStorage();

  // Handle pending message saves triggered by COMPLETE_STREAMING
  React.useEffect(() => {
    const checkPendingSaves = async () => {
      const pending = (window as any).__pendingMessageSave;
      if (pending) {
        try {
          if (pending.messages) {
            // Save multiple messages (user + AI)
            LogPrefix.log(
              LogPrefix.STREAM_PERSIST,
              `Processing pending messages save: ${pending.messages.length} messages for session: ${pending.sessionId}`
            );
            for (const message of pending.messages) {
              LogPrefix.log(
                LogPrefix.STREAM_PERSIST,
                `Saving ${message.type} message: ${message.content.substring(0, 50)}`
              );
              await saveMessage(message, pending.sessionId);
            }
          } else if (pending.message) {
            // Save single message (backward compatibility)
            LogPrefix.log(
              LogPrefix.STREAM_PERSIST,
              `Processing pending message save: ${pending.message.id} for session: ${pending.sessionId}`
            );
            await saveMessage(pending.message, pending.sessionId);
          }
        } catch (error) {
          console.error(
            'Failed to save completed streaming message(s):',
            error
          );
        }
        delete (window as any).__pendingMessageSave;
      }
    };

    const interval = setInterval(checkPendingSaves, 100);
    return () => clearInterval(interval);
  }, [saveMessage]);

  // Extract complex expressions for React Hooks dependency arrays
  const sessionMessages = state.sessionMessages;
  const activeStreaming = (state as any).activeStreaming;
  const currentSessionId = (state as any).currentSessionId;

  React.useEffect(() => {
    console.log(
      '📊 useChatState: State changed - sessionMessages:',
      sessionMessages.length,
      'activeStreaming:',
      activeStreaming?.messageId || 'none'
    );
    if (sessionMessages.length > 0) {
      console.log(
        '📊 useChatState: Session Message IDs:',
        sessionMessages.map((m: Message) => m.id)
      );
    }
  }, [sessionMessages, activeStreaming]);

  const messages = useMemo(() => {
    const result = [...sessionMessages];
    const s = activeStreaming as {
      messageId: string;
      content: string;
      visibleLen?: number;
      startedAt: string;
      originSessionId?: string;
    } | null;

    // Only show streaming message if it belongs to the current session
    const shouldShowStreaming = s && s.originSessionId === currentSessionId;

    if (shouldShowStreaming) {
      const full = s.content || '';
      const len = s.visibleLen ?? full.length;
      const streamingMessage: Message = {
        id: s.messageId,
        type: 'ai',
        content: full.slice(0, len),
        timestamp: s.startedAt,
      };
      result.push(streamingMessage);
      LogPrefix.log(
        LogPrefix.STREAM_SESSION,
        `Messages: Showing streaming message for current session: ${currentSessionId}`
      );
    } else if (s) {
      LogPrefix.log(
        LogPrefix.STREAM_SESSION,
        `Messages: Hiding streaming message (belongs to different session): ${s.originSessionId} ≠ ${currentSessionId}`
      );
    }

    return result;
  }, [sessionMessages, activeStreaming, currentSessionId]);

  const isCurrentlyStreaming = useMemo(() => {
    // Only consider it "currently streaming" if streaming belongs to current session
    return (
      activeStreaming !== null &&
      activeStreaming?.originSessionId === currentSessionId
    );
  }, [activeStreaming, currentSessionId]);

  const hasMessages = useMemo(() => {
    const result = messages.length > 0;
    console.log(
      '🧮 hasMessages computed:',
      result,
      'for',
      messages.length,
      'total messages in session',
      currentSessionId
    );
    return result;
  }, [messages.length, currentSessionId]);

  const canSendMessage = useMemo(
    () => !isCurrentlyStreaming,
    [isCurrentlyStreaming]
  );

  const lastMessage = useMemo(
    () => (messages.length > 0 ? messages[messages.length - 1] : null),
    [messages]
  );

  // Actions
  const addUserMessage = useCallback(
    (content: string, attachments?: AttachmentInfo[]) => {
      dispatch({
        type: 'ADD_USER_MESSAGE',
        message: {
          type: 'user',
          content,
          attachments,
        },
      } as any);
    },
    []
  );

  const startAIStreaming = useCallback(
    (sessionIdParam?: string) => {
      LogPrefix.log(
        LogPrefix.STREAM_SESSION,
        `startAIStreaming called with sessionId: ${sessionIdParam || 'none'}`
      );
      console.log(
        '🚀 startAIStreaming: activeStreaming:',
        activeStreaming?.messageId || 'none'
      );
      if (activeStreaming !== null) {
        console.warn('⚠️ Already streaming');
        return activeStreaming.messageId as string;
      }
      const messageId = nanoid();
      LogPrefix.log(
        LogPrefix.STREAM_SESSION,
        `Dispatching START_AI_STREAMING with messageId: ${messageId} and sessionId: ${sessionIdParam}`
      );
      dispatch({
        type: 'START_AI_STREAMING',
        messageId,
        currentSessionId: sessionIdParam,
      } as any);
      return messageId;
    },
    [activeStreaming]
  );

  const updateStreamingContent = useCallback(
    (messageId: string, content: string) => {
      console.log('🔄 updateStreamingContent:', {
        messageId,
        contentLength: content.length,
      });
      dispatch({
        type: 'UPDATE_STREAMING_CONTENT',
        payload: { messageId, content },
      } as any);
    },
    []
  );

  const completeStreaming = useCallback(() => {
    console.log('🏁 completeStreaming');
    dispatch({ type: 'COMPLETE_STREAMING' } as any);
  }, []);

  const forceStopStreaming = useCallback(() => {
    console.log('🛑 forceStopStreaming');
    dispatch({ type: 'FORCE_STOP_STREAMING' } as any);
  }, []);

  const clearMessages = useCallback(() => {
    dispatch({ type: 'CLEAR_MESSAGES' } as any);
  }, []);

  const loadSession = useCallback((sessionId: string, messages: Message[]) => {
    LogPrefix.log(LogPrefix.SESSION_LOAD, 'loadSession', {
      sessionId,
      messagesCount: messages.length,
    });

    // Simply load the session - streaming should continue in background
    // The LOAD_SESSION reducer will handle session isolation properly
    dispatch({ type: 'LOAD_SESSION', sessionId, messages } as any);
  }, []);

  const addMessageFeedback = useCallback(
    (messageId: string, feedback: Message['feedback']) => {
      if (feedback)
        dispatch({ type: 'ADD_MESSAGE_FEEDBACK', messageId, feedback } as any);
    },
    []
  );

  // Utilities
  const getMessageById = useCallback(
    (messageId: string) => messages.find(msg => msg.id === messageId) || null,
    [messages]
  );

  const getStreamingMessage = useCallback(() => {
    if (!activeStreaming) return null;
    return {
      id: activeStreaming.messageId,
      type: 'ai' as const,
      content: activeStreaming.content,
      timestamp: activeStreaming.startedAt,
    };
  }, [activeStreaming]);

  // Proactivity state (DEV-155)
  const interactiveQuestion = (state as any).interactiveQuestion ?? null;

  const clearProactivity = useCallback(() => {
    dispatch({ type: 'CLEAR_PROACTIVITY' } as any);
  }, []);

  const setInteractiveQuestion = useCallback((question: any) => {
    dispatch({ type: 'SET_INTERACTIVE_QUESTION', question } as any);
  }, []);

  // DEV-257: Usage limit inline banner state
  const usageLimitInfo: UsageLimitInfo | null = state.usageLimitInfo ?? null;

  const setUsageLimitInfo = useCallback((info: UsageLimitInfo | null) => {
    dispatch({ type: 'SET_USAGE_LIMIT', payload: info });
  }, []);

  const clearUsageLimit = useCallback(() => {
    dispatch({ type: 'SET_USAGE_LIMIT', payload: null });
  }, []);

  return {
    // State
    state,

    // Derived
    messages,
    isCurrentlyStreaming,
    hasMessages,
    canSendMessage,
    lastMessage,

    // Proactivity state (DEV-155)
    interactiveQuestion,

    // Actions
    dispatch,
    addUserMessage,
    startAIStreaming,
    updateStreamingContent,
    completeStreaming,
    forceStopStreaming,
    clearMessages,
    loadSession,
    addMessageFeedback,

    // Proactivity actions (DEV-155)
    clearProactivity,
    setInteractiveQuestion,

    // DEV-257: Usage limit inline banner
    usageLimitInfo,
    setUsageLimitInfo,
    clearUsageLimit,

    // Utilities
    getMessageById,
    getStreamingMessage,
  };
}

/* ------------------------------- CONTEXT ------------------------------- */

type ChatContextType = ReturnType<typeof useChatState>;
const ChatContext = createContext<ChatContextType | null>(null);

export function ChatStateProvider({ children }: { children: React.ReactNode }) {
  const chatStateValue = useChatState();
  const id = React.useRef(Math.random().toString(36).slice(2));
  React.useEffect(() => {
    const currentId = id.current;
    console.log('[ChatStateProvider] mounted', currentId);
    return () => console.log('[ChatStateProvider] unmounted', currentId);
  }, []);
  return React.createElement(
    ChatContext.Provider,
    { value: chatStateValue },
    children
  );
}

export function useSharedChatState(): ChatContextType {
  const context = useContext(ChatContext);
  if (!context)
    throw new Error(
      'useSharedChatState must be used within a ChatStateProvider'
    );
  return context;
}
