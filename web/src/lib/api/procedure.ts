/**
 * Procedure API client.
 *
 * Functions for listing and searching guided procedures.
 */

import { apiClient } from '@/lib/api';

const BASE = '/api/v1/procedure';

export interface ProceduraStep {
  title: string;
  checklist?: string[];
  documents?: string[];
  notes?: string;
}

export interface Procedura {
  id: string;
  code: string;
  title: string;
  description: string | null;
  category: string;
  steps: ProceduraStep[];
  estimated_time_minutes: number;
  version: number;
  is_active: boolean;
  last_updated: string;
}

/**
 * List active procedures, optionally filtered by category.
 */
export async function listProcedure(category?: string): Promise<Procedura[]> {
  const params = category ? `?category=${encodeURIComponent(category)}` : '';
  const response = await fetch(`${apiClient['baseUrl']}${BASE}${params}`, {
    headers: { Authorization: `Bearer ${apiClient['accessToken']}` },
  });
  if (!response.ok) throw new Error('Errore nel recupero delle procedure');
  return response.json();
}

/**
 * Get a single procedure by code.
 */
export async function getProceduraByCode(code: string): Promise<Procedura> {
  const response = await fetch(
    `${apiClient['baseUrl']}${BASE}/${encodeURIComponent(code)}`,
    {
      headers: { Authorization: `Bearer ${apiClient['accessToken']}` },
    }
  );
  if (!response.ok) throw new Error('Procedura non trovata');
  return response.json();
}
