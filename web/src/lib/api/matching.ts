/**
 * Matching API client.
 *
 * Operations for normative matching suggestions.
 */

import { buildStudioUrl, getAuthHeaders } from './helpers';

// --- Backend response types ---

export interface SuggestionResponse {
  id: string;
  studio_id: string;
  knowledge_item_id: number;
  matched_client_ids: number[];
  match_score: number;
  suggestion_text: string;
  is_read: boolean;
  is_dismissed: boolean;
  created_at: string;
}

export interface TriggerMatchingResponse {
  status: string;
  studio_id: string;
  knowledge_item_id: number | null;
  trigger: string;
  message: string;
}

export interface MatchingListParams {
  unread_only?: boolean;
  offset?: number;
  limit?: number;
}

/**
 * List matching suggestions. Uses X-Studio-Id header.
 */
export async function listSuggestions(
  params?: MatchingListParams
): Promise<SuggestionResponse[]> {
  const url = buildStudioUrl('/api/v1/matching/suggestions', {
    unread_only: params?.unread_only,
    offset: params?.offset,
    limit: params?.limit,
  });
  const response = await fetch(url, { headers: getAuthHeaders() });
  if (!response.ok) throw new Error('Errore nel caricamento dei suggerimenti');
  return response.json();
}

/**
 * Mark a suggestion as read.
 */
export async function markAsRead(
  suggestionId: string
): Promise<SuggestionResponse> {
  const url = buildStudioUrl(
    `/api/v1/matching/suggestions/${suggestionId}/read`
  );
  const response = await fetch(url, {
    method: 'PUT',
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('Errore nel segnare come letto');
  return response.json();
}

/**
 * Dismiss a suggestion.
 */
export async function dismissSuggestion(
  suggestionId: string
): Promise<SuggestionResponse> {
  const url = buildStudioUrl(
    `/api/v1/matching/suggestions/${suggestionId}/dismiss`
  );
  const response = await fetch(url, {
    method: 'PUT',
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('Errore nel rifiuto del suggerimento');
  return response.json();
}

/**
 * Trigger a matching job.
 */
export async function triggerMatching(
  knowledgeItemId?: number
): Promise<TriggerMatchingResponse> {
  const url = buildStudioUrl('/api/v1/matching/trigger');
  const response = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      knowledge_item_id: knowledgeItemId ?? null,
      trigger: 'manual',
    }),
  });
  if (!response.ok) throw new Error("Errore nell'avvio del matching");
  return response.json();
}
