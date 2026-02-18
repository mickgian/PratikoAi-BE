'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../types/chat';
import { SourceCitation } from '@/components/ui/source-citation';
import { FeedbackButtons } from './FeedbackButtons';
import { useRouter } from 'next/navigation';
import { GitCompare } from 'lucide-react';
import { useExpertStatus } from '@/hooks/useExpertStatus';
import { createPendingComparison } from '@/lib/api/modelComparison';
import { isCitationUrl } from '@/config/citation-sources';
import { ChatModelSelector } from './ChatModelSelector';
import {
  InteractiveQuestionInline,
  type InteractiveQuestion,
} from './InteractiveQuestionInline';
import { SourcesIndex } from '@/components/chat/SourcesIndex';
import { ReasoningTrace } from '@/components/chat/ReasoningTrace';
import { KBSourceUrls } from '@/components/chat/KBSourceUrls';
import { WebVerification } from '@/components/chat/WebVerification';

interface AIMessageV2Props {
  message: Message;
  isStreaming?: boolean;
  /** typing speed: tokens per second while streaming (optional) */
  speedTps?: number;
  /** Current session ID for feedback submission */
  sessionId?: string;
  /** All messages in the current session for feedback context */
  sessionMessages?: Message[];
  /** Interactive question to display after the message (DEV-166) */
  interactiveQuestion?: InteractiveQuestion;
  /** Callback when a question option is selected (DEV-166) */
  onQuestionAnswer?: (optionId: string, customInput?: string) => void;
  /** Callback when question is skipped via Escape (DEV-166) */
  onQuestionSkip?: () => void;
}

/**
 * AIMessageV2
 * - Tag/entity-aware typewriter
 * - Never restarts the RAF on every chunk (prevents flashing)
 * - Flushes immediately when streaming completes or on revisit
 * - Includes expert feedback buttons for qualified users
 */
export function AIMessageV2({
  message,
  isStreaming = false,
  speedTps = 90,
  sessionId,
  sessionMessages,
  interactiveQuestion,
  onQuestionAnswer,
  onQuestionSkip,
}: AIMessageV2Props) {
  const [visibleMarkdown, setVisibleMarkdown] = useState<string>('');
  // DEV-257: State for selected models in comparison
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);

  const router = useRouter();

  // Check if user is an expert
  const {
    isExpert,
    isSuperUser,
    isLoading: isLoadingExpertStatus,
  } = useExpertStatus();

  // DEV-256: Debug logging for compare button visibility
  useEffect(() => {
    console.log('🔍 [AIMessageV2] Compare button conditions:', {
      isSuperUser,
      isStreaming,
      isLoadingExpertStatus,
      willShowButton: isSuperUser && !isStreaming && !isLoadingExpertStatus,
    });
  }, [isSuperUser, isStreaming, isLoadingExpertStatus]);

  // Track "which message" we're rendering
  const lastMsgIdRef = useRef<string | null>(null);

  // The full markdown we want to render (updated as chunks arrive)
  const fullMarkdownRef = useRef<string>('');

  // Character stream & progress (we reveal by character index for raw text)
  const charsRef = useRef<string[]>([]);
  const shownCharIdxRef = useRef<number>(0);

  // Track if this is a new streaming message (for immediate typing)
  const isNewStreamingRef = useRef<boolean>(false);
  const lastContentLengthRef = useRef<number>(0);

  // Buffer for gradual content release during new streaming
  const contentBufferRef = useRef<string>('');
  const bufferReleasedRef = useRef<number>(0);

  // RAF control
  const rafRef = useRef<number | null>(null);
  const lastTickRef = useRef<number>(0);

  // Simple character tokenizer for raw markdown display
  const tokenize = (markdown: string): string[] => {
    return markdown.split('');
  };

  // Sanitize content: remove emojis and fix source citations
  const sanitizeContent = useCallback((text: string): string => {
    if (!text) return text;

    let cleaned = text;

    // Remove all emojis (paperclip 📎 and others)
    cleaned = cleaned.replace(
      /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu,
      ''
    );

    // Fix "Fonte" citations - extract actual source name from preceding context
    // Pattern: "Risoluzione n. 62 del 30 ottobre 2025 ... 📎 Fonte"
    // Result: "Risoluzione n.62/30 ott 2025"
    cleaned = cleaned.replace(
      /([A-Z][a-zà-ùè]+(?:\s+[a-zà-ùè]+)*)\s+n\.\s*(\d+)(?:\s+del\s+(\d+)\s+([a-zà-ùè]+)\s+(\d{4}))?\s*[📎\s]*Fonte\s*/gi,
      (_match, type, num, day, month, year) => {
        if (day && month && year) {
          const monthAbbr = month.slice(0, 3);
          return `${type} n.${num}/${day} ${monthAbbr} ${year}`;
        }
        return `${type} n.${num}`;
      }
    );

    // Also handle cases where "Fonte" appears alone after citations
    cleaned = cleaned.replace(/\s*[📎\s]+Fonte\s*$/gi, '');
    cleaned = cleaned.replace(/\s*[📎\s]+Fonte\s+\./gi, '.');

    return cleaned;
  }, []);

  // Restore markdown formatting for streaming content that lost line breaks
  const restoreMarkdownFormatting = useCallback(
    (text: string): string => {
      if (!text) return text;

      // First sanitize the content
      let formatted = sanitizeContent(text);

      // If content already has proper line breaks, return as-is
      if (formatted.includes('\n\n')) return formatted;

      // Pattern fixes for markdown that lost line breaks during streaming

      // Fix headers: ###Header -> \n\n### Header
      formatted = formatted.replace(/(#{1,6})(\s*)([A-Z0-9])/g, '\n\n$1 $3');

      // Fix bullet points: - Item -> \n- Item
      formatted = formatted.replace(
        /([.!?])\s*(-\s+\*{0,2}[A-Z])/g,
        '$1\n\n$2'
      );

      // Fix numbered lists: 1. Item -> \n1. Item
      formatted = formatted.replace(/([.!?])\s*(\d+\.\s+[A-Z])/g, '$1\n\n$2');

      // Add line break before "In sintesi" or similar conclusions
      formatted = formatted.replace(
        /(\.)\s*(In sintesi|In conclusione|Riassumendo)/g,
        '$1\n\n$2'
      );

      // Clean up any triple+ newlines
      formatted = formatted.replace(/\n{3,}/g, '\n\n');

      // Remove leading newlines
      formatted = formatted.replace(/^\n+/, '');

      return formatted;
    },
    [sanitizeContent]
  );

  // ── Message identity change → reset everything ───────────────────────────────
  useEffect(() => {
    const idChanged = lastMsgIdRef.current !== message.id;
    if (idChanged) {
      lastMsgIdRef.current = message.id;
      fullMarkdownRef.current = message.content || '';
      charsRef.current = tokenize(fullMarkdownRef.current);
      lastContentLengthRef.current = fullMarkdownRef.current.length;

      if (!isStreaming) {
        // Completed message - show immediately
        shownCharIdxRef.current = charsRef.current.length;
        setVisibleMarkdown(fullMarkdownRef.current);
        isNewStreamingRef.current = false;
      } else if (fullMarkdownRef.current.length > 0) {
        // CRITICAL FIX: Streaming message with existing content (returning to session)
        // Show accumulated content immediately, but typing will continue for new content
        shownCharIdxRef.current = charsRef.current.length;
        setVisibleMarkdown(fullMarkdownRef.current);
        isNewStreamingRef.current = false;
        contentBufferRef.current = ''; // Clear buffer when returning to session
        bufferReleasedRef.current = 0;
      } else {
        // New streaming message with no content yet - start fresh with typing
        shownCharIdxRef.current = 0;
        setVisibleMarkdown('');
        isNewStreamingRef.current = true; // Mark as new streaming message
        contentBufferRef.current = '';
        bufferReleasedRef.current = 0;
      }
    } else {
      // Same message: ensure we have the latest full content
      fullMarkdownRef.current = message.content || '';
      charsRef.current = tokenize(fullMarkdownRef.current);

      // If not streaming, show all content immediately
      if (!isStreaming) {
        shownCharIdxRef.current = charsRef.current.length;
        setVisibleMarkdown(fullMarkdownRef.current);
        isNewStreamingRef.current = false;
      }
      // For streaming messages, let the animation handle content updates
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message.id]);

  // ── Content growth (chunks) → update refs only (no restart) ─────────────────
  useEffect(() => {
    // Only update underlying buffers; the RAF will consume the delta.
    if (lastMsgIdRef.current === message.id) {
      const previousContent =
        contentBufferRef.current || fullMarkdownRef.current;
      const newContent = message.content || '';

      if (newContent !== previousContent) {
        const hadContent = lastContentLengthRef.current > 0;

        // CRITICAL FIX: For new streaming messages, buffer ALL content
        if (isNewStreamingRef.current || contentBufferRef.current !== '') {
          // Store ALL content in buffer - the animator will release it gradually
          contentBufferRef.current = newContent;

          if (!hadContent && newContent.length > 0) {
            console.log(
              '🎬 [TYPING] First chunk received, buffering ALL content for gradual release'
            );
            isNewStreamingRef.current = false;
          }
        } else {
          // Normal update for session switching or continuing messages
          fullMarkdownRef.current = newContent;
          charsRef.current = tokenize(fullMarkdownRef.current);
        }

        lastContentLengthRef.current = newContent.length;
      }
      // If stream ended but we're still mid-typing, flush.
      if (!isStreaming) {
        fullMarkdownRef.current = message.content || '';
        charsRef.current = tokenize(fullMarkdownRef.current);
        shownCharIdxRef.current = charsRef.current.length;
        setVisibleMarkdown(fullMarkdownRef.current);
        contentBufferRef.current = ''; // Clear buffer when streaming ends
        bufferReleasedRef.current = 0;
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message.content, isStreaming]); // <-- Added isStreaming dependency

  // ── Animator ────────────────────────────────────────────────────────────────
  const cancelAnimation = () => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  };

  const step = useCallback(
    (now: number) => {
      const elapsed = Math.max(0, now - (lastTickRef.current || now));
      lastTickRef.current = now;

      if (!isStreaming) {
        // Flush when not streaming
        shownCharIdxRef.current = charsRef.current.length;
        setVisibleMarkdown(fullMarkdownRef.current);
        rafRef.current = null;
        return;
      }

      // For buffered content (new streaming messages), gradually release from buffer
      if (
        contentBufferRef.current &&
        bufferReleasedRef.current < contentBufferRef.current.length
      ) {
        const cpf = Math.max(1, Math.round((speedTps / 1000) * elapsed));
        const bufferRemaining =
          contentBufferRef.current.length - bufferReleasedRef.current;
        const take = Math.min(cpf, bufferRemaining);

        bufferReleasedRef.current += take;
        const releasedContent = contentBufferRef.current.slice(
          0,
          bufferReleasedRef.current
        );

        // Update charsRef with released content
        charsRef.current = tokenize(releasedContent);
        fullMarkdownRef.current = releasedContent;
        shownCharIdxRef.current = charsRef.current.length;
        // Apply formatting restoration for streaming content
        const formattedContent = isStreaming
          ? restoreMarkdownFormatting(releasedContent)
          : releasedContent;
        setVisibleMarkdown(formattedContent);

        rafRef.current = requestAnimationFrame(step);
        return;
      }

      // Normal typing animation for non-buffered content
      const cpf = Math.max(1, Math.round((speedTps / 1000) * elapsed));
      const remaining = charsRef.current.length - shownCharIdxRef.current;
      if (remaining <= 0) {
        rafRef.current = requestAnimationFrame(step);
        return;
      }

      const take = Math.min(cpf, remaining);
      shownCharIdxRef.current += take;

      const markdown = charsRef.current
        .slice(0, shownCharIdxRef.current)
        .join('');
      // Apply formatting restoration for streaming content
      const formattedMarkdown = isStreaming
        ? restoreMarkdownFormatting(markdown)
        : markdown;
      setVisibleMarkdown(formattedMarkdown);

      rafRef.current = requestAnimationFrame(step);
    },
    [isStreaming, speedTps, restoreMarkdownFormatting]
  );

  // Start/stop animator ONLY when streaming flag or speed changes
  useEffect(() => {
    cancelAnimation();
    if (isStreaming) {
      lastTickRef.current = performance.now();
      rafRef.current = requestAnimationFrame(step);
    } else {
      // Not streaming → ensure full is shown
      shownCharIdxRef.current = charsRef.current.length;
      setVisibleMarkdown(fullMarkdownRef.current);
    }
    return cancelAnimation;
    // ⬇️ important: DO NOT depend on message.content here
  }, [isStreaming, speedTps, step]);

  // ── UI ──────────────────────────────────────────────────────────────────────
  const ariaLabel = isStreaming
    ? 'Risposta di PratikoAI (in elaborazione)'
    : 'Risposta di PratikoAI';

  const borderColor = isStreaming
    ? 'border-l-[#2A5D67]/50'
    : 'border-l-[#2A5D67]';

  // Custom ReactMarkdown components for citation links
  const markdownComponents: Components = {
    // Render links with SourceCitation for citation-style URLs
    a: ({ href, children }) => {
      // Check if this is a citation link from recognized Italian institutional sources
      // Uses centralized domain configuration from @/config/citation-sources
      const isCitation = isCitationUrl(href);

      if (isCitation && typeof children === 'string') {
        return (
          <SourceCitation
            citation={children}
            href={href}
            size="md"
            className="inline-flex mx-0.5"
          />
        );
      }

      // Regular link
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#2A5D67] underline hover:text-[#2A5D67]/80"
        >
          {children}
        </a>
      );
    },
  };

  // DEV-256: Handle compare navigation for SUPER_USERs
  // Uses backend database storage instead of sessionStorage to avoid race conditions
  const handleCompare = useCallback(async () => {
    console.log('🔄 [AIMessageV2] handleCompare called');

    // Find the user's question (previous user message before this AI message)
    let userQuery = '';
    if (sessionMessages) {
      const messageIndex = sessionMessages.findIndex(m => m.id === message.id);
      console.log('🔍 [AIMessageV2] Finding user query:', {
        messageIndex,
        totalMessages: sessionMessages.length,
      });
      if (messageIndex > 0) {
        // Look backwards for the closest user message
        for (let i = messageIndex - 1; i >= 0; i--) {
          if (sessionMessages[i].type === 'user') {
            userQuery = sessionMessages[i].content;
            break;
          }
        }
      }
    }

    // DEV-256: Extract metrics from message metadata
    const metadata = message.metadata || {};
    const latency_ms = metadata.response_time_ms ?? undefined;
    // Convert cost_cents to cost_eur (cents -> euros)
    const cost_eur =
      metadata.cost_cents != null ? metadata.cost_cents / 100 : undefined;
    // Note: Chat only has total tokens, not split into input/output
    const output_tokens = metadata.tokens_used ?? undefined;

    console.log('📤 [AIMessageV2] Creating pending comparison:', {
      queryLength: userQuery.length,
      responseLength: message.content.length,
      model_id: 'openai:gpt-4o',
      hasEnrichedPrompt: !!message.enriched_prompt,
      latency_ms,
      cost_eur,
      output_tokens,
    });

    try {
      // Store in backend database (avoids sessionStorage race conditions)
      // DEV-256: Include enriched_prompt and metrics so comparison shows actual values
      const { pending_id } = await createPendingComparison({
        query: userQuery,
        response: message.content,
        model_id: 'openai:gpt-4o', // Current production model
        enriched_prompt: message.enriched_prompt,
        latency_ms,
        cost_eur,
        output_tokens,
      });

      console.log('✅ [AIMessageV2] Pending comparison created:', pending_id);

      // DEV-257: Navigate with pending_id and selected models in URL
      const modelsParam =
        selectedModelIds.length > 0
          ? `&models=${encodeURIComponent(selectedModelIds.join(','))}`
          : '';
      router.push(
        `/expert/model-comparison?pending=${pending_id}${modelsParam}`
      );
    } catch (error) {
      console.error(
        '❌ [AIMessageV2] Failed to create pending comparison:',
        error
      );
    }
  }, [message, sessionMessages, router, selectedModelIds]);

  return (
    <div
      data-testid="ai-message-v2"
      data-streaming={isStreaming}
      role="region"
      aria-label={ariaLabel}
      className={`
        bg-white mr-auto max-w-[280px] md:max-w-[600px] p-4
        rounded-2xl rounded-bl-md shadow-sm border-l-[3px] ${borderColor}
      `}
    >
      <div
        data-testid="ai-message-content"
        className="prose prose-sm max-w-none text-[#1E293B]"
      >
        <ReactMarkdown
          components={markdownComponents}
          remarkPlugins={[remarkGfm]}
        >
          {visibleMarkdown || ''}
        </ReactMarkdown>
      </div>
      {isStreaming && (
        <div aria-hidden className="mt-1 h-4">
          <span className="inline-block w-2 h-4 align-baseline animate-pulse bg-[#2A5D67]/60" />
        </div>
      )}
      {/* DEV-241: Chain of Thought Reasoning Trace */}
      {!isStreaming && message.reasoning && (
        <ReasoningTrace reasoning={message.reasoning} className="mt-3" />
      )}
      {/* DEV-242: Structured Sources Index */}
      {!isStreaming &&
        message.structured_sources &&
        message.structured_sources.length > 0 && (
          <SourcesIndex sources={message.structured_sources} />
        )}
      {/* DEV-244: KB Source URLs (deterministic, independent of LLM output) */}
      {!isStreaming &&
        message.kb_source_urls &&
        message.kb_source_urls.length > 0 && (
          <KBSourceUrls sources={message.kb_source_urls} />
        )}
      {/* DEV-245: Web Verification Results from Brave Search */}
      {!isStreaming && message.web_verification && (
        <WebVerification data={message.web_verification} />
      )}
      {/* DEV-166: Interactive Question (rendered before SuggestedActions) */}
      {interactiveQuestion && onQuestionAnswer && (
        <InteractiveQuestionInline
          question={interactiveQuestion}
          onAnswer={onQuestionAnswer}
          onSkip={onQuestionSkip}
          disabled={isStreaming}
        />
      )}
      {isExpert && !isStreaming && !isLoadingExpertStatus && sessionId && (
        <FeedbackButtons
          message={message}
          sessionId={sessionId}
          sessionMessages={sessionMessages}
          onFeedbackSubmitted={() => {
            console.log('✅ Feedback submitted for message:', message.id);
          }}
        />
      )}
      {/* DEV-256: Compare button for SUPER_USERs */}
      {/* DEV-257: Added model selector dropdown next to Confronta button */}
      {isSuperUser && !isStreaming && !isLoadingExpertStatus && (
        <div className="mt-2 flex items-center gap-2">
          <ChatModelSelector
            selectedModelIds={selectedModelIds}
            onSelectionChange={setSelectedModelIds}
            disabled={isStreaming}
          />
          <button
            data-testid="compare-button"
            onClick={handleCompare}
            disabled={selectedModelIds.length < 2}
            className={`
              text-sm flex items-center gap-1.5 px-3 py-1.5 rounded-md border
              font-medium transition-all duration-200
              ${
                selectedModelIds.length < 2
                  ? 'text-gray-400 border-gray-200 bg-gray-50 cursor-not-allowed'
                  : 'text-[#2A5D67] border-[#2A5D67]/30 bg-[#2A5D67]/5 hover:bg-[#2A5D67]/10 hover:border-[#2A5D67]/50 cursor-pointer'
              }
            `}
            title={
              selectedModelIds.length < 2
                ? 'Seleziona almeno 2 modelli'
                : 'Confronta questa risposta con altri modelli'
            }
          >
            <GitCompare className="w-4 h-4" />
            <span>Confronta</span>
          </button>
        </div>
      )}
    </div>
  );
}
