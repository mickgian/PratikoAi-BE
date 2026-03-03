/**
 * Shared API helpers for studio_id injection and auth headers.
 */

import { apiClient } from '@/lib/api';

/**
 * Get the current user's studio_id from localStorage.
 */
export function getStudioId(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('studio_id');
}

/**
 * Get the current user's user_id from localStorage.
 */
export function getUserId(): number | null {
  if (typeof window === 'undefined') return null;
  const id = localStorage.getItem('user_id');
  return id ? parseInt(id, 10) : null;
}

/**
 * Get standard auth headers including studio_id.
 */
export function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  const token = apiClient.getAccessToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const studioId = getStudioId();
  if (studioId) {
    headers['X-Studio-Id'] = studioId;
  }

  return headers;
}

/**
 * Build a URL with studio_id and optional extra query params.
 */
export function buildStudioUrl(
  path: string,
  params?: Record<string, string | number | boolean | undefined>
): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const url = new URL(`${baseUrl}${path}`);

  const studioId = getStudioId();
  if (studioId) {
    url.searchParams.set('studio_id', studioId);
  }

  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== '') {
        url.searchParams.set(key, String(value));
      }
    }
  }

  return url.toString();
}
