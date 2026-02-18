/**
 * @file Chat History API Client
 * @description Backend API integration for PostgreSQL chat history storage
 * Implements multi-device sync and migration from IndexedDB
 */

// ============================================================================
// TypeScript Interfaces (matching backend schemas)
// ============================================================================

/**
 * Chat message from backend PostgreSQL database
 * Matches backend ChatHistoryMessageResponse schema
 */
export interface ChatMessage {
  /** Unique message ID (UUID) */
  id: string;
  /** User query text */
  query: string;
  /** AI response text */
  response: string;
  /** ISO 8601 timestamp */
  timestamp: string;
  /** LLM model used (e.g., 'gpt-4', 'claude-3') */
  model_used: string | null;
  /** Total tokens consumed */
  tokens_used: number | null;
  /** Cost in cents */
  cost_cents: number | null;
  /** Whether response was served from cache */
  response_cached: boolean;
  /** Response generation time in milliseconds */
  response_time_ms: number | null;
  /** DEV-244: KB source URLs for Fonti section */
  kb_sources_metadata: Array<{
    title: string;
    url: string;
    type: string;
    date?: string;
  }> | null;
}

/**
 * Message format for importing from IndexedDB to backend
 */
export interface ImportChatMessage {
  /** Session ID */
  session_id: string;
  /** User query */
  query: string;
  /** AI response */
  response: string;
  /** ISO 8601 timestamp */
  timestamp: string;
}

/**
 * Request payload for bulk import
 */
export interface ImportChatHistoryRequest {
  messages: ImportChatMessage[];
}

/**
 * Response from import endpoint
 */
export interface ImportChatHistoryResponse {
  /** Number of messages successfully imported */
  imported_count: number;
  /** Number of messages skipped (duplicates) */
  skipped_count: number;
  /** Import status: 'success', 'partial', or 'failed' */
  status: string;
  /** Human-readable message */
  message?: string;
}

// ============================================================================
// Configuration
// ============================================================================

/**
 * Get backend API base URL from environment
 */
function getApiBaseUrl(): string {
  if (typeof window === 'undefined') {
    // Server-side rendering
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }
  // Client-side
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

/**
 * Get auth token from localStorage
 */
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth_token');
}

/**
 * Build headers for authenticated requests
 */
function buildHeaders(): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return headers;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch chat history for a specific session from backend PostgreSQL
 *
 * @param sessionId - Session UUID
 * @param limit - Maximum number of messages to return (default: 100)
 * @param offset - Number of messages to skip for pagination (default: 0)
 * @returns Array of chat messages ordered by timestamp DESC
 * @throws Error if request fails or user is unauthorized
 *
 * @example
 * ```typescript
 * const messages = await getChatHistory('session-123', 50, 0);
 * console.log(`Loaded ${messages.length} messages`);
 * ```
 */
export async function getChatHistory(
  sessionId: string,
  limit: number = 100,
  offset: number = 0
): Promise<ChatMessage[]> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/chatbot/sessions/${sessionId}/messages?limit=${limit}&offset=${offset}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: buildHeaders(),
  });

  if (!response.ok) {
    throw new Error(
      `Failed to fetch chat history: ${response.status} ${response.statusText}`
    );
  }

  const messages: ChatMessage[] = await response.json();
  return messages;
}

/**
 * Import chat messages from IndexedDB to backend PostgreSQL
 * Enables migration of local chat history to server-side storage
 *
 * @param messages - Array of messages to import
 * @returns Import result with counts and status
 * @throws Error if import fails or user is unauthorized
 *
 * @example
 * ```typescript
 * const result = await importChatHistory([
 *   {
 *     session_id: 'session-local-1',
 *     query: 'What is IVA?',
 *     response: 'IVA is Italian VAT...',
 *     timestamp: '2025-11-28T10:00:00Z',
 *   }
 * ]);
 * console.log(`Imported ${result.imported_count}, skipped ${result.skipped_count}`);
 * ```
 */
export async function importChatHistory(
  messages: ImportChatMessage[]
): Promise<ImportChatHistoryResponse> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/chatbot/import-history`;

  const response = await fetch(url, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify({ messages }),
  });

  if (!response.ok) {
    throw new Error(
      `Failed to import chat history: ${response.status} ${response.statusText}`
    );
  }

  const result: ImportChatHistoryResponse = await response.json();
  return result;
}

/**
 * Check if chat history exists in backend for a session
 * Useful for detecting if migration is needed
 *
 * @param sessionId - Session UUID
 * @returns Number of messages in backend
 */
export async function getChatHistoryCount(sessionId: string): Promise<number> {
  try {
    const _messages = await getChatHistory(sessionId, 1, 0);
    // If we can fetch, count all messages
    const allMessages = await getChatHistory(sessionId, 10000, 0);
    return allMessages.length;
  } catch (_error) {
    // Session doesn't exist in backend
    return 0;
  }
}
