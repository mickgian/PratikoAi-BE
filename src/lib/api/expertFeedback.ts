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
 * Make authenticated API request
 */
async function makeRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  if (!token) {
    console.error('❌ [Expert Feedback API] No auth token found');
    throw new Error('Non autenticato. Effettua il login per continuare.');
  }

  const url = `${getBaseUrl()}${endpoint}`;
  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${token}`);
  headers.set('Content-Type', 'application/json');

  console.log(`🌐 [Expert Feedback API] ${options.method || 'GET'} ${url}`);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    console.log(
      `📡 [Expert Feedback API] Response: ${response.status} ${response.statusText}`
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText}`,
      }));
      console.error('❌ [Expert Feedback API] Error response:', errorData);
      throw new Error(errorData.detail || 'Errore durante la richiesta API');
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  } catch (error) {
    if (
      error instanceof TypeError &&
      error.message.includes('Failed to fetch')
    ) {
      console.error(
        '❌ [Expert Feedback API] Network error - server unreachable'
      );
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
  console.log('📤 [Expert Feedback] Submitting feedback:', data);

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

  const response = await makeRequest<SubmitFeedbackResponse>(
    '/api/v1/expert-feedback/submit',
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  );

  console.log(
    '✅ [Expert Feedback] Feedback submitted successfully:',
    response
  );
  return response;
}

/**
 * Get feedback history for the current expert
 */
export async function getFeedbackHistory(): Promise<FeedbackHistoryItem[]> {
  console.log('📥 [Expert Feedback] Fetching feedback history');

  const response = await makeRequest<FeedbackHistoryItem[]>(
    '/api/v1/expert-feedback/history',
    {
      method: 'GET',
    }
  );

  console.log(`✅ [Expert Feedback] Fetched ${response.length} feedback items`);
  return response;
}

/**
 * Get specific feedback details by ID
 */
export async function getFeedbackById(
  feedbackId: string
): Promise<SubmitFeedbackResponse> {
  console.log('📥 [Expert Feedback] Fetching feedback:', feedbackId);

  const response = await makeRequest<SubmitFeedbackResponse>(
    `/api/v1/expert-feedback/${feedbackId}`,
    {
      method: 'GET',
    }
  );

  console.log('✅ [Expert Feedback] Fetched feedback details:', response);
  return response;
}

/**
 * Get expert profile (to check role and expert status)
 */
export async function getExpertProfile(): Promise<ExpertProfile> {
  const token = getAuthToken();
  console.log('📥 [Expert Feedback] Fetching expert profile', {
    hasToken: !!token,
    tokenPreview: token ? `${token.slice(0, 20)}...` : 'none',
  });

  const response = await makeRequest<ExpertProfile>(
    '/api/v1/expert-feedback/experts/me/profile',
    {
      method: 'GET',
    }
  );

  console.log('✅ [Expert Feedback] Expert profile:', {
    role: response.role,
    user_id: response.user_id,
  });
  return response;
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
    const canProvideFeedback =
      profile.role === 'super_user' || profile.role === 'admin';
    console.log(
      `🔍 [Expert Feedback] User role: ${profile.role}, can provide feedback: ${canProvideFeedback}`
    );
    return canProvideFeedback;
  } catch (error) {
    console.error('❌ [Expert Feedback] Failed to check user role:', error);
    return false;
  }
}

/**
 * @deprecated Use isUserSuperUser() instead. This function checks trust_score which is no longer used for authorization.
 */
export async function isUserExpert(): Promise<boolean> {
  console.warn(
    '⚠️ [Expert Feedback] isUserExpert() is deprecated. Use isUserSuperUser() instead.'
  );
  return isUserSuperUser();
}
