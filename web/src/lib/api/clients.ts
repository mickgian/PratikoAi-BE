/**
 * Clients API client.
 *
 * CRUD operations for client management.
 */

import { apiClient } from '@/lib/api';
import {
  buildStudioUrl,
  getAuthHeaders,
  getStudioId,
  getUserId,
} from './helpers';

// --- Backend response types (snake_case) ---

export interface ClientResponse {
  id: number;
  studio_id: string;
  codice_fiscale: string;
  nome: string;
  tipo_cliente: string;
  stato_cliente: string;
  comune: string;
  provincia: string;
  partita_iva: string | null;
  email: string | null;
  phone: string | null;
  indirizzo: string | null;
  cap: string | null;
  note_studio: string | null;
  inps_matricola: string | null;
  inps_status: string | null;
  inps_ultimo_pagamento: string | null;
  inail_pat: string | null;
  inail_status: string | null;
  created_at: string;
}

export interface ClientListResponse {
  items: ClientResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface ClientCreateRequest {
  codice_fiscale: string;
  nome: string;
  tipo_cliente: string;
  comune: string;
  provincia: string;
  partita_iva?: string;
  email?: string;
  phone?: string;
  indirizzo?: string;
  cap?: string;
  stato_cliente?: string;
  note_studio?: string;
}

export interface ClientUpdateRequest {
  codice_fiscale?: string;
  nome?: string;
  tipo_cliente?: string;
  comune?: string;
  provincia?: string;
  partita_iva?: string;
  email?: string;
  phone?: string;
  indirizzo?: string;
  cap?: string;
  stato_cliente?: string;
  note_studio?: string;
  inps_matricola?: string;
  inps_status?: string;
  inps_ultimo_pagamento?: string;
  inail_pat?: string;
  inail_status?: string;
}

export interface ClientListParams {
  offset?: number;
  limit?: number;
  stato?: string;
  search?: string;
}

/**
 * List clients with optional filters.
 */
export async function listClients(
  params?: ClientListParams
): Promise<ClientListResponse> {
  const url = buildStudioUrl('/api/v1/clients', {
    offset: params?.offset ?? 0,
    limit: params?.limit ?? 50,
    stato: params?.stato,
  });
  const response = await fetch(url, { headers: getAuthHeaders() });
  if (!response.ok) throw new Error('Errore nel caricamento dei clienti');
  return response.json();
}

/**
 * Get a single client by ID.
 */
export async function getClient(clientId: number): Promise<ClientResponse> {
  const url = buildStudioUrl(`/api/v1/clients/${clientId}`);
  const response = await fetch(url, { headers: getAuthHeaders() });
  if (!response.ok) throw new Error('Cliente non trovato');
  return response.json();
}

/**
 * Create a new client.
 */
export async function createClient(
  data: ClientCreateRequest
): Promise<ClientResponse> {
  const url = buildStudioUrl('/api/v1/clients');
  const response = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Errore nella creazione del cliente');
  }
  return response.json();
}

/**
 * Update an existing client.
 */
export async function updateClient(
  clientId: number,
  data: ClientUpdateRequest
): Promise<ClientResponse> {
  const url = buildStudioUrl(`/api/v1/clients/${clientId}`);
  const response = await fetch(url, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Errore nell'aggiornamento del cliente");
  }
  return response.json();
}

/**
 * Soft-delete a client.
 */
export async function deleteClient(clientId: number): Promise<void> {
  const url = buildStudioUrl(`/api/v1/clients/${clientId}`);
  const response = await fetch(url, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Errore nell'eliminazione del cliente");
}

// --- Preview types ---

export interface ImportPreviewRow {
  row_number: number;
  data: Record<string, string | null>;
  is_valid: boolean;
  errors: string[];
}

export interface SuggestedMapping {
  file_column: string;
  confidence: number; // 0.0–1.0
  match_method: 'exact_alias' | 'fuzzy' | 'data_pattern';
}

export interface ImportPreviewResponse {
  detected_columns: string[];
  suggested_mappings: Record<string, SuggestedMapping>;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  rows: ImportPreviewRow[];
}

// --- Import types ---

export interface ClientImportError {
  row_number: number;
  field: string | null;
  message: string;
}

export interface ClientMissingFieldWarning {
  client_id: number;
  client_nome: string;
  field: string;
  priority: string;
  reason: string;
}

export interface ClientImportWarningsSummary {
  clients_without_profile: number;
  clients_missing_partita_iva: number;
  missing_fields: ClientMissingFieldWarning[];
}

export interface ClientImportResult {
  total: number;
  success_count: number;
  error_count: number;
  errors: ClientImportError[];
  warnings: ClientImportWarningsSummary | null;
}

/**
 * Preview an import file — parse and validate without writing to DB.
 */
export async function previewImport(
  file: File
): Promise<ImportPreviewResponse> {
  const url = buildStudioUrl('/api/v1/clients/import/preview');

  const headers: Record<string, string> = {};
  const token = apiClient.getAccessToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const studioId = getStudioId();
  if (studioId) headers['X-Studio-Id'] = studioId;

  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Errore durante l'anteprima del file");
  }

  return response.json();
}

/**
 * Import clients from an Excel, CSV, or PDF file.
 *
 * Uses FormData — must NOT set Content-Type header (browser adds
 * multipart boundary automatically).
 */
export async function importClients(
  file: File,
  columnMapping?: Record<string, string>
): Promise<ClientImportResult> {
  const url = buildStudioUrl('/api/v1/clients/import');

  const headers: Record<string, string> = {};
  const token = apiClient.getAccessToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const studioId = getStudioId();
  if (studioId) headers['X-Studio-Id'] = studioId;
  const userId = getUserId();
  if (userId) headers['X-User-Id'] = String(userId);

  const formData = new FormData();
  formData.append('file', file);
  if (columnMapping) {
    formData.append('column_mapping', JSON.stringify(columnMapping));
  }

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Errore durante l'importazione dei clienti");
  }

  return response.json();
}
