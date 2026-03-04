// src/lib/api/expertFeedback.ts

import {
  SubmitFeedbackRequest,
  SubmitFeedbackResponse,
  FeedbackHistoryItem,
  ExpertProfile,
} from '@/types/expertFeedback';

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
  // Use session token for expert feedback (since it's chat-related)
  return (
    localStorage.getItem('current_session_token') ||
    localStorage.getItem('access_token')
  );
};

/**
 * Custom error for authentication failures (401/403).
 * These are expected when the user is not logged in or lacks permissions,
 * and should be handled silently — not logged as console errors.
 */
class AuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'AuthError';
  }
}

async function makeRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  if (!token) {
    throw new AuthError('Non autenticato. Effettua il login per continuare.');
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

      // 401/403 are expected auth failures — throw AuthError (handled silently)
      if (response.status === 401 || response.status === 403) {
        throw new AuthError(errorData.detail || 'Credenziali non valide');
      }

      console.error('❌ [Expert Feedback API] Error response:', errorData);
      throw new Error(errorData.detail || 'Errore durante la richiesta API');
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  } catch (error) {
    // Re-throw AuthError without wrapping
    if (error instanceof AuthError) {
      throw error;
    }
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
 * Submit expert feedback for an AI response
 */
export async function submitFeedback(
  data: SubmitFeedbackRequest
): Promise<SubmitFeedbackResponse> {
  // Validate required fields (matching backend FeedbackSubmission schema)
  if (!data.query_id || !data.feedback_type) {
    throw new Error(
      'Campi obbligatori mancanti: query_id e feedback_type sono richiesti'
    );
  }

  if (!data.query_text || !data.original_answer) {
    throw new Error(
      'Campi obbligatori mancanti: query_text e original_answer sono richiesti'
    );
  }

  if (
    typeof data.confidence_score !== 'number' ||
    data.confidence_score < 0 ||
    data.confidence_score > 1
  ) {
    throw new Error('confidence_score deve essere un numero tra 0 e 1');
  }

  if (!data.time_spent_seconds || data.time_spent_seconds <= 0) {
    throw new Error('time_spent_seconds deve essere maggiore di 0');
  }

  // Validate additional_details for incomplete/incorrect
  if (
    (data.feedback_type === 'incomplete' ||
      data.feedback_type === 'incorrect') &&
    !data.additional_details?.trim()
  ) {
    throw new Error(
      'I dettagli aggiuntivi sono obbligatori per risposte incomplete o errate'
    );
  }

  return makeRequest<SubmitFeedbackResponse>('/api/v1/expert-feedback/submit', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Get feedback history for the current expert
 */
export async function getFeedbackHistory(): Promise<FeedbackHistoryItem[]> {
  return makeRequest<FeedbackHistoryItem[]>('/api/v1/expert-feedback/history', {
    method: 'GET',
  });
}

/**
 * Get specific feedback details by ID
 */
export async function getFeedbackById(
  feedbackId: string
): Promise<SubmitFeedbackResponse> {
  return makeRequest<SubmitFeedbackResponse>(
    `/api/v1/expert-feedback/${feedbackId}`,
    { method: 'GET' }
  );
}

/**
 * Get expert profile (to check role and expert status)
 */
export async function getExpertProfile(): Promise<ExpertProfile> {
  return makeRequest<ExpertProfile>(
    '/api/v1/expert-feedback/experts/me/profile',
    { method: 'GET' }
  );
}

/**
 * Check if current user is a SUPER_USER or ADMIN (can give feedback)
 *
 * This replaces the old trust_score check with role-based authorization.
 * Both 'super_user' and 'admin' roles can provide expert feedback.
 */
export async function isUserSuperUser(): Promise<boolean> {
  try {
    const profile = await getExpertProfile();
    return profile.role === 'super_user' || profile.role === 'admin';
  } catch (error) {
    // Auth failures are expected (user not logged in, token expired) — return false silently
    if (error instanceof AuthError) {
      return false;
    }
    console.error('❌ [Expert Feedback] Failed to check user role:', error);
    return false;
  }
}

/**
 * @deprecated Use isUserSuperUser() instead. This function checks trust_score which is no longer used for authorization.
 */
export async function isUserExpert(): Promise<boolean> {
  return isUserSuperUser();
}
