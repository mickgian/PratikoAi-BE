/**
 * Procedure API client.
 *
 * Functions for procedure catalog and progress tracking.
 */

import { buildStudioUrl, getAuthHeaders, getUserId } from './helpers';

// --- Response types ---

export interface ProceduraStep {
  title: string;
  checklist?: string[];
  documents?: string[];
  notes?: string;
}

export interface ProceduraResponse {
  id: string;
  code: string;
  title: string;
  description: string | null;
  category: string;
  steps: ProceduraStep[];
  estimated_time_minutes: number;
  version: number;
  is_active: boolean;
}

export interface ProceduraProgressResponse {
  id: string;
  user_id: number;
  studio_id: string;
  procedura_id: string;
  client_id: number | null;
  current_step: number;
  completed_steps: number[];
  notes: string | null;
  started_at: string;
  completed_at: string | null;
}

// --- Catalog endpoints (no studio_id needed) ---

/**
 * List active procedures, optionally filtered by category.
 */
export async function listProcedure(
  category?: string
): Promise<ProceduraResponse[]> {
  const params = category ? `?category=${encodeURIComponent(category)}` : '';
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const response = await fetch(`${baseUrl}/api/v1/procedure${params}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('Errore nel recupero delle procedure');
  return response.json();
}

/**
 * Get a single procedure by code.
 */
export async function getProceduraByCode(
  code: string
): Promise<ProceduraResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const response = await fetch(
    `${baseUrl}/api/v1/procedure/${encodeURIComponent(code)}`,
    { headers: getAuthHeaders() }
  );
  if (!response.ok) throw new Error('Procedura non trovata');
  return response.json();
}

// --- Progress endpoints (require studio_id + user_id) ---

/**
 * Start progress on a procedure for a client.
 */
export async function startProgress(
  proceduraId: string,
  clientId?: number
): Promise<ProceduraProgressResponse> {
  const userId = getUserId();
  const url = buildStudioUrl('/api/v1/procedure/progress', {
    user_id: userId ?? undefined,
  });
  const response = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      procedura_id: proceduraId,
      client_id: clientId ?? null,
    }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Errore nell'avvio della procedura");
  }
  return response.json();
}

/**
 * Advance to the next step.
 */
export async function advanceStep(
  progressId: string
): Promise<ProceduraProgressResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const response = await fetch(
    `${baseUrl}/api/v1/procedure/progress/${progressId}/advance`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
    }
  );
  if (!response.ok) throw new Error("Errore nell'avanzamento del passo");
  return response.json();
}

/**
 * List user's progress records.
 */
export async function listProgress(): Promise<ProceduraProgressResponse[]> {
  const userId = getUserId();
  const url = buildStudioUrl('/api/v1/procedure/progress/list', {
    user_id: userId ?? undefined,
  });
  const response = await fetch(url, { headers: getAuthHeaders() });
  if (!response.ok) throw new Error('Errore nel caricamento dei progressi');
  return response.json();
}

/**
 * Update a checklist item.
 */
export async function updateChecklist(
  progressId: string,
  stepIndex: number,
  itemIndex: number,
  completed: boolean
): Promise<ProceduraProgressResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const response = await fetch(
    `${baseUrl}/api/v1/procedure/progress/${progressId}/checklist`,
    {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        step_index: stepIndex,
        item_index: itemIndex,
        completed,
      }),
    }
  );
  if (!response.ok)
    throw new Error("Errore nell'aggiornamento della checklist");
  return response.json();
}

/**
 * Update notes for a progress record.
 */
export async function updateNotes(
  progressId: string,
  notes: string
): Promise<ProceduraProgressResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const response = await fetch(
    `${baseUrl}/api/v1/procedure/progress/${progressId}/notes`,
    {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify({ notes }),
    }
  );
  if (!response.ok) throw new Error("Errore nell'aggiornamento delle note");
  return response.json();
}

/**
 * Update document verification status.
 */
export async function updateDocument(
  progressId: string,
  documentName: string,
  verified: boolean
): Promise<ProceduraProgressResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const response = await fetch(
    `${baseUrl}/api/v1/procedure/progress/${progressId}/document`,
    {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify({ document_name: documentName, verified }),
    }
  );
  if (!response.ok) throw new Error("Errore nell'aggiornamento del documento");
  return response.json();
}
