/**
 * Model Comparison API Client (DEV-256)
 *
 * API client for the multi-model LLM comparison feature that allows SUPER_USER
 * role users to compare responses from multiple LLM models.
 */

import {
  ComparisonRequest,
  ComparisonResponse,
  ComparisonWithExistingRequest,
  VoteRequest,
  VoteResponse,
  AvailableModelsResponse,
  LeaderboardResponse,
  ComparisonStatsResponse,
  ModelPreferencesRequest,
  CreatePendingComparisonRequest,
  PendingComparisonResponse,
  PendingComparisonData,
} from '@/types/modelComparison';

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
 * Make public API request (no auth required)
 */
async function makePublicRequest<T>(endpoint: string): Promise<T> {
  const url = `${getBaseUrl()}${endpoint}`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText}`,
      }));
      throw new Error(errorData.detail || 'Errore durante la richiesta API');
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
 * Run a multi-model comparison
 *
 * Sends the same query to multiple LLM models in parallel and returns all responses.
 * Requires SUPER_USER or ADMIN role.
 *
 * @param data - Comparison request with query and optional model_ids
 * @returns ComparisonResponse with all model responses
 */
export async function runComparison(
  data: ComparisonRequest
): Promise<ComparisonResponse> {
  console.log('📤 [Model Comparison] Running comparison:', data.query);

  if (!data.query?.trim()) {
    throw new Error('La domanda non può essere vuota');
  }

  if (data.query.length > 2000) {
    throw new Error('La domanda supera il limite di 2000 caratteri');
  }

  if (data.model_ids && data.model_ids.length < 2) {
    throw new Error('Seleziona almeno 2 modelli per il confronto');
  }

  if (data.model_ids && data.model_ids.length > 6) {
    throw new Error('Massimo 6 modelli per confronto');
  }

  const response = await makeRequest<ComparisonResponse>(
    '/api/v1/model-comparison/compare',
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  );

  console.log(
    `✅ [Model Comparison] Comparison completed with ${response.responses.length} responses`
  );
  return response;
}

/**
 * Run a comparison with an existing response from main chat
 *
 * Reuses the current model's response from the main chat and only calls
 * the other best models, saving cost on the current model.
 * Requires SUPER_USER or ADMIN role.
 *
 * @param data - Request with query and existing response from main chat
 * @returns ComparisonResponse with all model responses (existing + new)
 */
export async function runComparisonWithExisting(
  data: ComparisonWithExistingRequest
): Promise<ComparisonResponse> {
  console.log(
    '📤 [Model Comparison] Running comparison with existing response:',
    data.query
  );

  if (!data.query?.trim()) {
    throw new Error('La domanda non può essere vuota');
  }

  if (data.query.length > 2000) {
    throw new Error('La domanda supera il limite di 2000 caratteri');
  }

  if (!data.existing_response?.response_text) {
    throw new Error('La risposta esistente non può essere vuota');
  }

  const response = await makeRequest<ComparisonResponse>(
    '/api/v1/model-comparison/compare-with-existing',
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  );

  console.log(
    `✅ [Model Comparison] Comparison with existing completed with ${response.responses.length} responses`
  );
  return response;
}

/**
 * Submit a vote for the best model in a comparison
 *
 * Updates Elo ratings based on the vote.
 * Requires SUPER_USER or ADMIN role.
 *
 * @param data - Vote request with batch_id and winner_model_id
 * @returns VoteResponse with success status and Elo changes
 */
export async function submitVote(data: VoteRequest): Promise<VoteResponse> {
  console.log('📤 [Model Comparison] Submitting vote:', data);

  if (!data.batch_id) {
    throw new Error('batch_id è obbligatorio');
  }

  if (!data.winner_model_id) {
    throw new Error('Seleziona il modello vincitore');
  }

  const response = await makeRequest<VoteResponse>(
    '/api/v1/model-comparison/vote',
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  );

  console.log('✅ [Model Comparison] Vote submitted successfully:', response);
  return response;
}

/**
 * Get available models with user preferences
 *
 * Returns the list of all configured models with their Elo ratings
 * and whether they are enabled for the current user.
 * Requires SUPER_USER or ADMIN role.
 *
 * @returns AvailableModelsResponse with list of models
 */
export async function getAvailableModels(): Promise<AvailableModelsResponse> {
  console.log('📥 [Model Comparison] Fetching available models');

  const response = await makeRequest<AvailableModelsResponse>(
    '/api/v1/model-comparison/models',
    {
      method: 'GET',
    }
  );

  console.log(`✅ [Model Comparison] Fetched ${response.models.length} models`);
  return response;
}

/**
 * Update user model preferences
 *
 * Sets which models are enabled for the user's comparisons.
 * Requires SUPER_USER or ADMIN role.
 *
 * @param data - Preferences request with enabled_model_ids
 * @returns Success message
 */
export async function updateModelPreferences(
  data: ModelPreferencesRequest
): Promise<{ message: string }> {
  console.log('📤 [Model Comparison] Updating preferences:', data);

  if (!data.enabled_model_ids || data.enabled_model_ids.length < 2) {
    throw new Error('Seleziona almeno 2 modelli');
  }

  const response = await makeRequest<{ message: string }>(
    '/api/v1/model-comparison/models/preferences',
    {
      method: 'PUT',
      body: JSON.stringify(data),
    }
  );

  console.log('✅ [Model Comparison] Preferences updated:', response);
  return response;
}

/**
 * Get user comparison statistics
 *
 * Returns stats about the user's comparison activity.
 * Requires SUPER_USER or ADMIN role.
 *
 * @returns ComparisonStatsResponse with user statistics
 */
export async function getUserStats(): Promise<ComparisonStatsResponse> {
  console.log('📥 [Model Comparison] Fetching user stats');

  const response = await makeRequest<ComparisonStatsResponse>(
    '/api/v1/model-comparison/stats',
    {
      method: 'GET',
    }
  );

  console.log('✅ [Model Comparison] User stats:', response.stats);
  return response;
}

/**
 * Get the model leaderboard
 *
 * Returns models ranked by Elo rating. This endpoint is public
 * (no authentication required).
 *
 * @param limit - Maximum number of results (default 20, max 100)
 * @returns LeaderboardResponse with ranked models
 */
export async function getLeaderboard(limit = 20): Promise<LeaderboardResponse> {
  console.log('📥 [Model Comparison] Fetching leaderboard');

  const response = await makePublicRequest<LeaderboardResponse>(
    `/api/v1/model-comparison/leaderboard?limit=${Math.min(limit, 100)}`
  );

  console.log(
    `✅ [Model Comparison] Fetched leaderboard with ${response.rankings.length} models`
  );
  return response;
}

/**
 * Create a pending comparison from main chat
 *
 * Stores the query and response from main chat so the comparison page
 * can retrieve it. Records expire after 1 hour.
 * Requires SUPER_USER or ADMIN role.
 *
 * @param data - Request with query, response, and model_id
 * @returns PendingComparisonResponse with pending_id UUID
 */
export async function createPendingComparison(
  data: CreatePendingComparisonRequest
): Promise<PendingComparisonResponse> {
  console.log('📤 [Model Comparison] Creating pending comparison');

  if (!data.query?.trim()) {
    throw new Error('La domanda non può essere vuota');
  }

  if (!data.response?.trim()) {
    throw new Error('La risposta non può essere vuota');
  }

  if (!data.model_id) {
    throw new Error('model_id è obbligatorio');
  }

  const response = await makeRequest<PendingComparisonResponse>(
    '/api/v1/model-comparison/pending',
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  );

  console.log(
    '✅ [Model Comparison] Pending comparison created:',
    response.pending_id
  );
  return response;
}

/**
 * Get pending comparison data
 *
 * Retrieves the pending comparison data and deletes it (one-time use).
 * Requires SUPER_USER or ADMIN role.
 *
 * @param pendingId - UUID of the pending comparison
 * @returns PendingComparisonData with query, response, and model_id
 */
export async function getPendingComparison(
  pendingId: string
): Promise<PendingComparisonData> {
  console.log('📥 [Model Comparison] Fetching pending comparison:', pendingId);

  const response = await makeRequest<PendingComparisonData>(
    `/api/v1/model-comparison/pending/${pendingId}`,
    {
      method: 'GET',
    }
  );

  console.log('✅ [Model Comparison] Pending comparison retrieved');
  return response;
}
