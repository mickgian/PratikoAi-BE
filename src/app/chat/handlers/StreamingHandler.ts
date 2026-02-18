/**
 * StreamingHandler: accumulator with de-duplication (live typing)
 * - Emits only NEW visible content to the reducer (no word-splitting)
 * - Works with both "delta" and "accumulated" servers
 * - Ignores the classic "full message repeated at done"
 * - Adds sliding-window replay guard on FE
 * - Logs FE/BE length mismatch on final frame
 */

import { ChatAction } from '../types/chat';
import { logger } from '@/utils/logger';
import apiClient from '@/lib/api';

type OutboundMessage = {
  role: 'user' | 'assistant' | 'system';
  content: string;
  attachment_ids?: string[];
};

import type { SseFrame } from '@/lib/api';

export interface StreamingConfig {
  apiUrl: string;
  getSessionToken: () => string;
  timeout?: number;
  cancelOnNewMessage?: boolean;
  allowInterruption?: boolean;
}

export interface StreamingOptions {
  timeout?: number;
  allowInterruption?: boolean;
  skipProactivity?: boolean;
}

export class StreamingHandler {
  private dispatch: (action: ChatAction) => void;
  private config: StreamingConfig;

  private currentStreamId: string | null = null;
  private abortController: AbortController | null = null;
  private isActive = false;
  private lastError: Error | null = null;
  private retryCount = 0;
  private readonly maxRetries = 3;
  private lastSeq: number | null = null;

  /** cumulative buffer already "rendered" (post-normalization) */
  private accumulated = '';
  /** prevents double COMPLETE_STREAMING */
  private hasCompleted = false;

  /** Timeout handle for activity-based timeout reset */
  private timeoutHandle: NodeJS.Timeout | null = null;
  /** Reject function for timeout promise */
  private timeoutReject: ((reason?: any) => void) | null = null;

  constructor(opts: {
    dispatch: (action: ChatAction) => void;
    apiUrl: string;
    getSessionToken: () => string;
  }) {
    this.dispatch = opts.dispatch;
    this.config = {
      apiUrl: opts.apiUrl,
      getSessionToken: opts.getSessionToken,
      timeout: 120000, // 120 seconds to handle long RAG queries
      cancelOnNewMessage: false,
      allowInterruption: true,
    };
  }

  // ──────────────────────────────────────────────────────────────────────────────
  // Public API
  // ──────────────────────────────────────────────────────────────────────────────

  /**
   * Starts a stream bound to an existing UI-generated messageId
   * (UI already dispatched START_AI_STREAMING with this id)
   */
  async startStreaming(
    messageId: string,
    messages: OutboundMessage[],
    options: StreamingOptions = {}
  ): Promise<boolean> {
    if (
      this.isActive &&
      !this.config.cancelOnNewMessage &&
      !options.allowInterruption
    ) {
      const e = new Error('Streaming already in progress');
      logger.warn('start_stream_blocked', {
        component: 'StreamingHandler',
        action: 'start_stream',
        metadata: { activeStreamId: this.currentStreamId },
      });
      throw e;
    }

    this.isActive = true;

    try {
      await this.cleanup(); // ensure clean state

      this.currentStreamId = messageId;
      this.retryCount = 0;
      this.abortController = new AbortController();
      this.resetBoundaryState();

      logger.logStreamingStart(this.currentStreamId, messages.length);

      // NOTE: DO NOT dispatch a start action. UI already did START_AI_STREAMING.

      await this.executeStream(messages, options);
      return true;
    } catch (error) {
      logger.logStreamingError(
        this.currentStreamId || 'unknown',
        error as Error
      );
      await this.cleanup(true);
      // Do not dispatch STREAM_ERROR (not in reducer); just keep internal error
      this.lastError = error as Error;
      return false;
    }
  }

  async cancelStreaming(): Promise<boolean> {
    if (!this.isActive || !this.currentStreamId) return false;
    logger.info('cancel_stream', {
      component: 'StreamingHandler',
      action: 'cancel_stream',
      metadata: { streamId: this.currentStreamId },
    });

    if (this.abortController) this.abortController.abort();

    // Reducer has no CANCEL action; just cleanup
    await this.cleanup(true);
    return true;
  }

  canRetry(): boolean {
    return (
      this.lastError !== null &&
      this.retryCount < this.maxRetries &&
      !this.isActive
    );
  }

  async retry(): Promise<boolean> {
    if (!this.canRetry() || !this.lastError) return false;
    this.retryCount++;
    this.lastError = null;
    return false; // caller must re-invoke startStreaming with messages
  }

  isStreaming(): boolean {
    return this.isActive;
  }

  getStatus() {
    return {
      isActive: this.isActive,
      streamId: this.currentStreamId,
      hasError: this.lastError !== null,
      canRetry: this.canRetry(),
    };
  }

  getLastError(): Error | null {
    return this.lastError;
  }

  getCurrentAbortController(): AbortController | null {
    return this.abortController;
  }

  setConfig(config: Partial<StreamingConfig>): void {
    this.config = { ...this.config, ...config };
  }

  // ──────────────────────────────────────────────────────────────────────────────
  // Internals
  // ──────────────────────────────────────────────────────────────────────────────

  /**
   * Resets the activity-based timeout
   * Called on each chunk received to keep connection alive during streaming
   */
  private resetTimeout(timeoutMs: number): void {
    // Clear existing timeout
    if (this.timeoutHandle) {
      clearTimeout(this.timeoutHandle);
    }

    // Set new timeout
    this.timeoutHandle = setTimeout(() => {
      this.handleTimeout();
    }, timeoutMs);
  }

  /**
   * Handles timeout expiration
   */
  private handleTimeout(): void {
    logger.warn('stream_timeout', {
      component: 'StreamingHandler',
      action: 'timeout',
      metadata: { streamId: this.currentStreamId },
    });

    const error = new Error('Connection timeout');
    this.lastError = error;

    // Reject the timeout promise to propagate the error
    if (this.timeoutReject) {
      this.timeoutReject(error);
    }

    this.cleanup(true);
  }

  /**
   * Clears the timeout without triggering it
   */
  private clearTimeoutHandle(): void {
    if (this.timeoutHandle) {
      clearTimeout(this.timeoutHandle);
      this.timeoutHandle = null;
    }
    this.timeoutReject = null;
  }

  private async executeStream(
    messages: OutboundMessage[],
    options: StreamingOptions
  ): Promise<void> {
    if (!this.currentStreamId || !this.abortController) {
      throw new Error('Stream not properly initialized');
    }
    const timeout = options.timeout ?? this.config.timeout ?? 120000;

    // Create a timeout promise that can be rejected when timeout fires
    const timeoutPromise = new Promise<never>((_, reject) => {
      this.timeoutReject = reject;
      this.resetTimeout(timeout);
    });

    try {
      // Race between stream request and timeout
      await Promise.race([
        this.performStreamRequest(messages, timeout, options),
        timeoutPromise,
      ]);
    } catch (err) {
      logger.error('stream_execution_failed', err as Error, {
        component: 'StreamingHandler',
        action: 'stream_execution_failed',
        metadata: { streamId: this.currentStreamId },
      });
      await this.cleanup(true);
      throw err;
    } finally {
      this.clearTimeoutHandle();
    }
  }

  private async performStreamRequest(
    messages: OutboundMessage[],
    timeout: number,
    options: StreamingOptions = {}
  ): Promise<void> {
    if (!this.abortController || !this.currentStreamId) {
      throw new Error('Stream not initialized');
    }

    const token = this.config.getSessionToken();
    if (!token) throw new Error('No session token available');

    const perf = logger.startPerformanceTimer('streaming_request', {
      component: 'StreamingHandler',
      metadata: { messageCount: messages.length },
    });

    try {
      console.log(
        '🚀 [StreamingHandler] Starting stream request with messages:',
        messages
      );

      await apiClient.sendChatMessageStreaming(
        messages as any,
        // onChunk — pass full frame object
        (frame: SseFrame) => {
          console.log('📦 [StreamingHandler] Received chunk frame:', frame);

          // Reset timeout on ANY activity (content OR keepalive comments)
          this.resetTimeout(timeout);

          // Process frame directly without re-serialization
          if (typeof frame.content === 'string' && frame.content.length > 0) {
            // DEV-201: Check for content_cleaned event type (XML tags stripped)
            if (frame.event_type === 'content_cleaned') {
              console.log(
                '🧹 [StreamingHandler] Received content_cleaned event, replacing content'
              );
              this.dispatch({
                type: 'REPLACE_STREAMING_CONTENT',
                payload: {
                  messageId: this.currentStreamId!,
                  content: frame.content,
                },
              });
            } else {
              // Regular content update (append)
              this.dispatch({
                type: 'UPDATE_STREAMING_CONTENT',
                payload: {
                  messageId: this.currentStreamId!,
                  content: frame.content,
                },
              });
            }
          }

          // Handle proactivity frames (DEV-155)
          if (frame.interactive_question) {
            console.log(
              '❓ [StreamingHandler] Received interactive question:',
              frame.interactive_question.id
            );
            this.dispatch({
              type: 'SET_INTERACTIVE_QUESTION',
              question: frame.interactive_question,
            });
          }

          // DEV-242: Handle reasoning trace for Chain of Thought display
          if (frame.event_type === 'reasoning' && frame.reasoning) {
            console.log(
              '🧠 [StreamingHandler] Received reasoning trace:',
              frame.reasoning.tema_identificato?.substring(0, 50)
            );
            // Ensure required fields are present before dispatching
            if (frame.reasoning.tema_identificato) {
              this.dispatch({
                type: 'SET_MESSAGE_REASONING',
                messageId: this.currentStreamId!,
                reasoning:
                  frame.reasoning as import('@/components/chat/ReasoningTrace').ReasoningData,
              });
            }
          }

          // DEV-244: Handle KB source URLs (deterministic, independent of LLM output)
          if (
            frame.event_type === 'kb_source_urls' &&
            frame.kb_source_urls &&
            frame.kb_source_urls.length > 0
          ) {
            console.log(
              '📚 [StreamingHandler] Received KB source URLs:',
              frame.kb_source_urls.length
            );
            this.dispatch({
              type: 'SET_MESSAGE_KB_SOURCES',
              messageId: this.currentStreamId!,
              kb_source_urls: frame.kb_source_urls,
            });
          }

          // DEV-245: Handle web verification results from Brave Search
          if (
            frame.event_type === 'web_verification' &&
            frame.web_verification &&
            frame.web_verification.verification_performed
          ) {
            console.log(
              '🌐 [StreamingHandler] Received web verification:',
              frame.web_verification.web_sources_checked,
              'sources checked'
            );
            this.dispatch({
              type: 'SET_MESSAGE_WEB_VERIFICATION',
              messageId: this.currentStreamId!,
              web_verification: frame.web_verification,
            });
          }

          // DEV-256: Handle enriched_prompt for model comparison feature
          // This arrives in the done frame and needs to be stored on the message
          if (frame.enriched_prompt && this.currentStreamId) {
            console.log(
              '📝 [StreamingHandler] Received enriched_prompt:',
              frame.enriched_prompt.length,
              'chars'
            );
            this.dispatch({
              type: 'SET_MESSAGE_ENRICHED_PROMPT',
              messageId: this.currentStreamId,
              enriched_prompt: frame.enriched_prompt,
            });
          }

          // DEV-256: Handle LLM metrics for model comparison feature
          // These arrive in the done frame and need to be stored on the message
          if (
            this.currentStreamId &&
            (frame.tokens_used ||
              frame.cost_cents ||
              frame.model_used ||
              frame.response_time_ms)
          ) {
            console.log('📊 [StreamingHandler] Received metrics:', {
              tokens_used: frame.tokens_used,
              cost_cents: frame.cost_cents,
              model_used: frame.model_used,
              response_time_ms: frame.response_time_ms,
            });
            this.dispatch({
              type: 'SET_MESSAGE_METADATA',
              messageId: this.currentStreamId,
              metadata: {
                // DEV-256: Keep separate input/output tokens instead of summing
                input_tokens: frame.tokens_used?.input,
                output_tokens: frame.tokens_used?.output,
                cost_cents: frame.cost_cents,
                model_used: frame.model_used,
                response_time_ms: frame.response_time_ms,
              },
            });
          }

          // Handle done frame
          if (frame.done === true && !this.hasCompleted) {
            this.hasCompleted = true;
            this.dispatch({ type: 'COMPLETE_STREAMING' });
            this.isActive = false;
          }
        },
        // onDone — optional final frame already sent by BE; finalize UI if not done
        (finalFrame?: SseFrame) => {
          console.log(
            '🏁 [StreamingHandler] Stream done, final frame:',
            finalFrame
          );
          // (We rely primarily on done=true frames; this is a safety net.)
          if (this.isActive && this.currentStreamId && !this.hasCompleted) {
            this.hasCompleted = true;
            this.dispatch({ type: 'COMPLETE_STREAMING' });
            this.isActive = false;
          }
          logger.endPerformanceTimer(perf, {
            metadata: { status: 'completed_naturally' },
          });
        },
        // onError
        (err: string) => {
          let isUsageLimit = false;
          try {
            const parsed = JSON.parse(err);
            if (parsed?.type === 'USAGE_LIMIT_EXCEEDED') isUsageLimit = true;
          } catch {
            /* not JSON */
          }

          if (isUsageLimit) {
            console.warn('⚠️ [StreamingHandler] Usage limit exceeded');
          } else {
            console.error('❌ [StreamingHandler] Stream error:', err);
          }
          logger.error('http_error', new Error(err), {
            component: 'StreamingHandler',
            action: 'http_error',
          });
          throw new Error(err);
        },
        // options - pass skip_proactivity for follow-up queries
        options.skipProactivity ? { skip_proactivity: true } : undefined
      );
    } catch (error) {
      // Ensure consistent state on failure/abort
      if (this.isActive) {
        await this.cleanup(true);
      }
      throw error;
    }
  }
  // ──────────────────────────────────────────────────────────────────────────────
  // Helpers
  // ──────────────────────────────────────────────────────────────────────────────

  private async cleanup(resetActiveState = false): Promise<void> {
    try {
      logger.debug('cleanup', {
        component: 'StreamingHandler',
        action: 'cleanup',
        metadata: { streamId: this.currentStreamId },
      });

      // Clear timeout to prevent it from firing after cleanup
      this.clearTimeoutHandle();

      if (this.abortController) {
        this.abortController.abort();
        this.abortController = null;
      }
      this.currentStreamId = null;
      this.resetBoundaryState();
      if (resetActiveState) this.isActive = false;
      await new Promise(r => setTimeout(r, 10));
    } catch (error) {
      logger.error('cleanup_error', error as Error, {
        component: 'StreamingHandler',
        action: 'cleanup_error',
      });
    }
  }

  /** Reset per-stream boundary state */
  private resetBoundaryState() {
    this.accumulated = '';
    this.hasCompleted = false;
    this.lastSeq = null;
  }
}
