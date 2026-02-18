// src/app/chat/types/chat.ts

import type { InteractiveQuestion } from '@/lib/api';
import type { StructuredSource } from '@/components/chat/SourcesIndex';
import type { ReasoningData } from '@/components/chat/ReasoningTrace';
import type { UsageStatus } from '@/lib/api/billing';

// ───────────────────────────────────────────────────────────────────────────────
// Roles & outbound messages (to backend)
// ───────────────────────────────────────────────────────────────────────────────
export type Role = 'user' | 'assistant' | 'system';

// Re-export proactivity types for convenience
export type { InteractiveQuestion } from '@/lib/api';

/** Message shape sent to the backend */
export interface OutboundMessage {
  role: Role;
  content: string;
}

// ───────────────────────────────────────────────────────────────────────────────
// Attachment info for displaying attached files with user messages
// ───────────────────────────────────────────────────────────────────────────────
export interface AttachmentInfo {
  /** Document ID from backend */
  id: string;
  /** Original filename */
  filename: string;
  /** File size in bytes */
  size?: number;
  /** MIME type */
  type?: string;
}

// ───────────────────────────────────────────────────────────────────────────────
// In-app message model (stored in session history)
// ───────────────────────────────────────────────────────────────────────────────
export interface Message {
  id: string;
  type: 'user' | 'ai' | 'system';
  content: string;
  timestamp: string;
  sources?: any;
  metadata?: any;
  feedback?: {
    rating?: 'up' | 'down';
    comment?: string;
  };
  /** Attachments included with this message (user messages only) */
  attachments?: AttachmentInfo[];
  /** DEV-242: Structured source citations extracted from INDICE DELLE FONTI */
  structured_sources?: StructuredSource[];
  /** DEV-244: KB source URLs (deterministic, independent of LLM output) */
  kb_source_urls?: Array<{
    title: string;
    url: string;
    type: string;
    date?: string; // Optional - may not be available for all sources
  }>;
  /** DEV-245: Web verification results from Brave Search */
  web_verification?: {
    caveats?: string[];
    has_caveats?: boolean;
    web_sources_checked?: number;
    verification_performed?: boolean;
    brave_ai_summary?: string;
    synthesized_response?: string;
    has_synthesized_response?: boolean;
  };
  /** DEV-241: Chain of Thought reasoning trace (AI messages only) */
  reasoning?: ReasoningData;
  /** DEV-256: Full prompt sent to LLM for model comparison feature */
  enriched_prompt?: string;
}

// ───────────────────────────────────────────────────────────────────────────────
// Active streaming (separate from history)
// ───────────────────────────────────────────────────────────────────────────────
export interface ActiveStream {
  messageId: string;
  content: string;
  startedAt: string;
}

// ───────────────────────────────────────────────────────────────────────────────
// Chat state used by chat/hooks/useChatState
// ───────────────────────────────────────────────────────────────────────────────
export interface UsageLimitInfo {
  usageData: UsageStatus;
  canBypass: boolean;
}

export interface ChatState {
  sessionMessages: Message[];
  activeStreaming: ActiveStream | null;
  currentSessionId?: string | null;
  // Proactivity state (DEV-155)
  interactiveQuestion: InteractiveQuestion | null;
  // DEV-257: Usage limit inline banner state
  usageLimitInfo: UsageLimitInfo | null;
}

// ───────────────────────────────────────────────────────────────────────────────
// Action union (aligned with chat/hooks/useChatState reducer)
// NOTE: UPDATE_STREAMING_CONTENT supports both the new "payload" shape and the
// legacy flat shape to avoid breaking existing dispatch sites.
// ───────────────────────────────────────────────────────────────────────────────
export type ChatAction =
  | {
      type: 'ADD_USER_MESSAGE';
      message: {
        type: 'user';
        content: string;
        attachments?: AttachmentInfo[];
      };
    }
  | { type: 'START_AI_STREAMING'; messageId: string }
  | {
      type: 'UPDATE_STREAMING_CONTENT';
      payload: {
        messageId: string;
        content: string;
        done?: boolean;
      };
    }
  // DEV-201: Replace content with cleaned version (XML tags stripped)
  | {
      type: 'REPLACE_STREAMING_CONTENT';
      payload: {
        messageId: string;
        content: string;
      };
    }
  | { type: 'COMPLETE_STREAMING' }
  | { type: 'FORCE_STOP_STREAMING' }
  | { type: 'SAVE_COMPLETED_MESSAGE'; message: Message; sessionId: string }
  | { type: 'CLEAR_MESSAGES' }
  | { type: 'LOAD_SESSION'; sessionId: string; messages: Message[] }
  | {
      type: 'ADD_MESSAGE_FEEDBACK';
      messageId: string;
      feedback: Message['feedback'];
    }
  // Proactivity actions (DEV-155)
  | { type: 'SET_INTERACTIVE_QUESTION'; question: InteractiveQuestion }
  | { type: 'CLEAR_PROACTIVITY' }
  // DEV-242: Chain of Thought reasoning
  | {
      type: 'SET_MESSAGE_REASONING';
      messageId: string;
      reasoning: ReasoningData;
    }
  // DEV-244: KB source URLs (deterministic, independent of LLM)
  | {
      type: 'SET_MESSAGE_KB_SOURCES';
      messageId: string;
      kb_source_urls: Array<{
        title: string;
        url: string;
        type: string;
        date?: string; // Optional - may not be available for all sources
      }>;
    }
  // DEV-245: Web verification results from Brave Search
  | {
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
    }
  // DEV-256: Enriched prompt for model comparison feature
  | {
      type: 'SET_MESSAGE_ENRICHED_PROMPT';
      messageId: string;
      enriched_prompt: string;
    }
  // DEV-256: LLM metrics for model comparison feature
  | {
      type: 'SET_MESSAGE_METADATA';
      messageId: string;
      metadata: {
        response_time_ms?: number;
        input_tokens?: number;
        output_tokens?: number;
        cost_cents?: number;
        model_used?: string;
      };
    }
  // DEV-257: Usage limit inline banner
  | { type: 'SET_USAGE_LIMIT'; payload: UsageLimitInfo | null };

// ───────────────────────────────────────────────────────────────────────────────
// Simple helpers (no external deps)
// ───────────────────────────────────────────────────────────────────────────────
const genId = () =>
  'm_' + Math.random().toString(36).slice(2) + Date.now().toString(36);

export function createInitialChatState(): ChatState {
  return {
    sessionMessages: [],
    activeStreaming: null,
    currentSessionId: null,
    interactiveQuestion: null,
    usageLimitInfo: null,
  };
}

export function createUserMessage(
  content: string,
  attachments?: AttachmentInfo[]
): Message {
  const message: Message = {
    id: genId(),
    type: 'user',
    content,
    timestamp: new Date().toISOString(),
  };
  if (attachments && attachments.length > 0) {
    message.attachments = attachments;
  }
  return message;
}

export function createAIMessage(content: string): Message {
  return {
    id: genId(),
    type: 'ai',
    content,
    timestamp: new Date().toISOString(),
  };
}
