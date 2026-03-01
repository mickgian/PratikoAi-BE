/**
 * Consigli API client (ADR-038).
 *
 * Fetches on-demand insight report from /api/v1/consigli/report.
 */

import { apiClient } from '@/lib/api';

export interface ConsigliReport {
  status: 'success' | 'insufficient_data' | 'generating' | 'error';
  message_it: string;
  html_report: string | null;
  stats_summary: {
    total_queries: number;
    active_days: number;
    session_count: number;
  } | null;
}

const BASE = '/api/v1/consigli';

export async function getConsigliReport(): Promise<ConsigliReport> {
  const response = await fetch(`${apiClient['baseUrl']}${BASE}/report`, {
    headers: { Authorization: `Bearer ${apiClient['accessToken']}` },
  });
  if (!response.ok) {
    if (response.status === 429) {
      throw new Error(
        'Hai già generato il massimo numero di report oggi. Riprova domani.'
      );
    }
    throw new Error(
      'Errore nella generazione del report. Riprova tra qualche istante.'
    );
  }
  return response.json();
}
