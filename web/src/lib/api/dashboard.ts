/**
 * Dashboard API client.
 *
 * Fetches aggregated dashboard data from GET /api/v1/dashboard.
 */

import { buildStudioUrl, getAuthHeaders } from './helpers';

export interface DashboardResponse {
  clients: { total: number };
  communications: { total: number; pending_review: number };
  procedures: { total: number; active: number };
  matches: { active_rules: number };
  roi: { hours_saved: number; breakdown?: Record<string, unknown> };
  distributions: {
    by_regime: Array<{ regime: string; count: number }>;
    by_ateco: Array<{ ateco: string; count: number }>;
    by_status: Array<{ status: string; count: number }>;
  };
  matching: {
    total_matches: number;
    conversion_rate: number;
    pending_reviews: number;
  };
  period: string;
}

/**
 * Fetch dashboard data for the current studio.
 */
export async function getDashboardData(
  period: 'week' | 'month' | 'year' = 'month'
): Promise<DashboardResponse> {
  const url = buildStudioUrl('/api/v1/dashboard', { period });
  const response = await fetch(url, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error('Errore nel caricamento della dashboard');
  }
  return response.json();
}
