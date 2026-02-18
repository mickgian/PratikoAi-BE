/**
 * @file Chat Storage Utility Functions
 * @description Conversion functions for backend/frontend message formats
 */

import type { ChatMessage } from '@/lib/api/chat-history';
import type { Message } from '../types/chat';

/**
 * Convert backend ChatMessage to frontend Message format
 * Backend stores query/response pairs as single records
 * Frontend displays them as separate user/assistant messages
 */
export function convertBackendToFrontend(chatMessage: ChatMessage): Message[] {
  return [
    {
      id: `${chatMessage.id}-user`,
      type: 'user' as const,
      content: chatMessage.query,
      timestamp: chatMessage.timestamp,
    },
    {
      id: `${chatMessage.id}-assistant`,
      type: 'ai' as const,
      content: chatMessage.response,
      timestamp: chatMessage.timestamp,
      metadata: {
        model_used: chatMessage.model_used,
        tokens_used: chatMessage.tokens_used,
        cost_cents: chatMessage.cost_cents,
        response_cached: chatMessage.response_cached,
        response_time_ms: chatMessage.response_time_ms,
      },
      // DEV-244: Include KB source URLs for Fonti section persistence on page refresh
      ...(chatMessage.kb_sources_metadata &&
        chatMessage.kb_sources_metadata.length > 0 && {
          kb_source_urls: chatMessage.kb_sources_metadata,
        }),
    },
  ];
}

/**
 * Convert frontend Messages to backend import format
 * Groups user/assistant pairs into query/response records
 */
export function convertFrontendToBackendImport(
  messages: Message[],
  sessionId: string
): Array<{
  session_id: string;
  query: string;
  response: string;
  timestamp: string;
}> {
  const importMessages: Array<{
    session_id: string;
    query: string;
    response: string;
    timestamp: string;
  }> = [];

  // Group consecutive user + assistant messages
  for (let i = 0; i < messages.length - 1; i++) {
    const userMsg = messages[i];
    const assistantMsg = messages[i + 1];

    if (
      (userMsg.type === 'user' || userMsg.type === 'system') &&
      assistantMsg.type === 'ai'
    ) {
      importMessages.push({
        session_id: sessionId,
        query: userMsg.content,
        response: assistantMsg.content,
        timestamp: userMsg.timestamp,
      });
      i++; // Skip next message as we've already processed it
    }
  }

  return importMessages;
}
