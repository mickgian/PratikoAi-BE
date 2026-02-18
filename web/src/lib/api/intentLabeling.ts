// src/lib/api/intentLabeling.ts

import type {
  QueueResponse,
  LabelSubmission,
  LabeledQueryResponse,
  SkipResponse,
  LabelingStatsResponse,
} from '@/types/intentLabeling';

/**
 * Base API URL from environment or default
 */
const getBaseUrl = (): string => {
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
};

/**
 * Get authorization token from localStorage
 */
const getAuthToken = (): string | null => {
  if (typeof window === 'undefined') {
    return null;
  }
  return (
    localStorage.getItem('current_session_token') ||
    localStorage.getItem('access_token')
  );
};

/**
 * Make authenticated API request
 */
async function makeRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Non autenticato. Effettua il login per continuare.');
  }

  const url = `${getBaseUrl()}${endpoint}`;
  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${token}`);
  headers.set('Content-Type', 'application/json');

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText}`,
      }));
      throw new Error(errorData.detail || 'Errore durante la richiesta API');
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  } catch (error) {
    if (
      error instanceof TypeError &&
      error.message.includes('Failed to fetch')
    ) {
      throw new Error(
        'Impossibile connettersi al server. Verifica la tua connessione.'
      );
    }
    throw error;
  }
}

/**
 * Get the labeling queue with paginated unlabeled queries
 */
export async function getLabelingQueue(
  page: number = 1,
  pageSize: number = 20
): Promise<QueueResponse> {
  return makeRequest<QueueResponse>(
    `/api/v1/labeling/queue?page=${page}&page_size=${pageSize}`,
    { method: 'GET' }
  );
}

/**
 * Submit an expert label for a query
 */
export async function submitLabel(
  data: LabelSubmission
): Promise<LabeledQueryResponse> {
  if (!data.query_id || !data.expert_intent) {
    throw new Error(
      'Campi obbligatori mancanti: query_id e expert_intent sono richiesti'
    );
  }

  return makeRequest<LabeledQueryResponse>('/api/v1/labeling/label', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Skip a query in the labeling queue
 */
export async function skipQuery(queryId: string): Promise<SkipResponse> {
  return makeRequest<SkipResponse>(`/api/v1/labeling/skip/${queryId}`, {
    method: 'POST',
  });
}

/**
 * Get labeling progress statistics
 */
export async function getLabelingStats(): Promise<LabelingStatsResponse> {
  return makeRequest<LabelingStatsResponse>('/api/v1/labeling/stats', {
    method: 'GET',
  });
}

/**
 * Export training data as file download
 */
export async function exportTrainingData(
  format: 'jsonl' | 'csv' = 'jsonl'
): Promise<void> {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Non autenticato. Effettua il login per continuare.');
  }

  const url = `${getBaseUrl()}/api/v1/labeling/export?format=${format}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({
      detail: `HTTP ${response.status}: ${response.statusText}`,
    }));
    throw new Error(errorData.detail || "Errore durante l'esportazione");
  }

  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = `intent_training_data.${format}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(downloadUrl);
}
