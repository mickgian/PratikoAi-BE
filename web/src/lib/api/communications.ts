/**
 * Communications API client.
 *
 * Full CRUD + workflow operations for communication management.
 */

import { buildStudioUrl, getAuthHeaders, getUserId } from './helpers';

// --- Backend response types ---

export interface CommunicationResponse {
  id: string;
  studio_id: string;
  client_id: number | null;
  subject: string;
  content: string;
  channel: string;
  status: string;
  created_by: number;
  approved_by: number | null;
  approved_at: string | null;
  sent_at: string | null;
  normativa_riferimento: string | null;
  created_at: string;
}

export interface CommunicationCreateRequest {
  subject: string;
  content: string;
  channel: string;
  client_id?: number;
  normativa_riferimento?: string;
}

export interface BulkCommunicationCreateRequest {
  client_ids: number[];
  subject: string;
  content: string;
  channel: string;
  normativa_riferimento?: string;
}

export interface CommunicationListParams {
  status?: string;
  offset?: number;
  limit?: number;
}

/**
 * List communications with optional status filter.
 */
export async function listCommunications(
  params?: CommunicationListParams
): Promise<CommunicationResponse[]> {
  const url = buildStudioUrl('/api/v1/communications', {
    status: params?.status,
    offset: params?.offset ?? 0,
    limit: params?.limit ?? 100,
  });
  const response = await fetch(url, { headers: getAuthHeaders() });
  if (!response.ok)
    throw new Error('Errore nel caricamento delle comunicazioni');
  return response.json();
}

/**
 * Get a single communication by ID.
 */
export async function getCommunication(
  communicationId: string
): Promise<CommunicationResponse> {
  const url = buildStudioUrl(`/api/v1/communications/${communicationId}`);
  const response = await fetch(url, { headers: getAuthHeaders() });
  if (!response.ok) throw new Error('Comunicazione non trovata');
  return response.json();
}

/**
 * Create a new communication draft.
 */
export async function createCommunication(
  data: CommunicationCreateRequest
): Promise<CommunicationResponse> {
  const userId = getUserId();
  const url = buildStudioUrl('/api/v1/communications', {
    created_by: userId ?? undefined,
  });
  const response = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Errore nella creazione della comunicazione');
  }
  return response.json();
}

/**
 * Submit a draft for review (DRAFT → PENDING_REVIEW).
 */
export async function submitForReview(
  communicationId: string
): Promise<CommunicationResponse> {
  const url = buildStudioUrl(
    `/api/v1/communications/${communicationId}/submit`
  );
  const response = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Errore nell'invio per revisione");
  return response.json();
}

/**
 * Approve a communication (PENDING_REVIEW → APPROVED).
 */
export async function approveCommunication(
  communicationId: string
): Promise<CommunicationResponse> {
  const userId = getUserId();
  const url = buildStudioUrl(
    `/api/v1/communications/${communicationId}/approve`,
    { approved_by: userId ?? undefined }
  );
  const response = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Errore nell'approvazione");
  return response.json();
}

/**
 * Reject a communication (PENDING_REVIEW → REJECTED).
 */
export async function rejectCommunication(
  communicationId: string
): Promise<CommunicationResponse> {
  const url = buildStudioUrl(
    `/api/v1/communications/${communicationId}/reject`
  );
  const response = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('Errore nel rifiuto');
  return response.json();
}

/**
 * Send an approved communication (APPROVED → SENT).
 */
export async function sendCommunication(
  communicationId: string
): Promise<CommunicationResponse> {
  const url = buildStudioUrl(`/api/v1/communications/${communicationId}/send`);
  const response = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Errore nell'invio");
  return response.json();
}

/**
 * Delete a communication.
 */
export async function deleteCommunication(
  communicationId: string
): Promise<void> {
  const url = buildStudioUrl(`/api/v1/communications/${communicationId}`);
  const response = await fetch(url, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!response.ok)
    throw new Error("Errore nell'eliminazione della comunicazione");
}

/**
 * Bulk create communication drafts for multiple clients.
 */
export async function bulkCreateDrafts(
  data: BulkCommunicationCreateRequest
): Promise<CommunicationResponse[]> {
  const userId = getUserId();
  const url = buildStudioUrl('/api/v1/communications/bulk', {
    created_by: userId ?? undefined,
  });
  const response = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Errore nella creazione bulk');
  }
  return response.json();
}
