/**
 * Release notes API client.
 * Handles version info, release notes listing, and seen tracking.
 */

import { apiClient } from '../api';

export interface VersionInfo {
  version: string;
  environment: string;
}

export interface ReleaseNotePublic {
  version: string;
  released_at: string | null;
  user_notes: string;
}

export interface ReleaseNote extends ReleaseNotePublic {
  technical_notes: string;
}

export interface ReleaseNotesListResponse {
  items: ReleaseNotePublic[];
  total: number;
  page: number;
  page_size: number;
}

export interface ReleaseNotesFullListResponse {
  items: ReleaseNote[];
  total: number;
  page: number;
  page_size: number;
}

export interface MarkSeenResponse {
  success: boolean;
  message_it: string;
}

const API_BASE = '/api/v1/release-notes';

export async function getVersion(): Promise<VersionInfo> {
  const response = await fetch(`${apiClient['baseUrl']}${API_BASE}/version`);
  if (!response.ok) {
    throw new Error('Errore nel recupero della versione');
  }
  return response.json();
}

export async function getReleaseNotes(
  page: number = 1,
  pageSize: number = 10
): Promise<ReleaseNotesListResponse> {
  const response = await fetch(
    `${apiClient['baseUrl']}${API_BASE}?page=${page}&page_size=${pageSize}`
  );
  if (!response.ok) {
    throw new Error('Errore nel recupero delle note di rilascio');
  }
  return response.json();
}

export async function getLatestReleaseNote(): Promise<ReleaseNotePublic | null> {
  const response = await fetch(`${apiClient['baseUrl']}${API_BASE}/latest`);
  if (!response.ok) {
    throw new Error("Errore nel recupero dell'ultima nota di rilascio");
  }
  const data = await response.json();
  return data || null;
}

export async function getUnseenReleaseNote(): Promise<ReleaseNote | null> {
  const token = localStorage.getItem('access_token');
  if (!token) return null;

  const response = await fetch(`${apiClient['baseUrl']}${API_BASE}/unseen`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    if (response.status === 401) return null;
    throw new Error('Errore nel recupero delle novità');
  }
  const data = await response.json();
  return data || null;
}

export async function getReleaseNotesFull(
  page: number = 1,
  pageSize: number = 10
): Promise<ReleaseNotesFullListResponse> {
  const token = localStorage.getItem('access_token');
  if (!token) {
    throw new Error('Non autenticato');
  }

  const response = await fetch(
    `${apiClient['baseUrl']}${API_BASE}/full?page=${page}&page_size=${pageSize}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
  if (!response.ok) {
    throw new Error('Errore nel recupero delle note di rilascio complete');
  }
  return response.json();
}

export async function updateUserNotes(
  version: string,
  userNotes: string
): Promise<MarkSeenResponse> {
  const token = localStorage.getItem('access_token');
  if (!token) {
    throw new Error('Non autenticato');
  }

  const response = await fetch(
    `${apiClient['baseUrl']}${API_BASE}/${version}/user-notes`,
    {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_notes: userNotes }),
    }
  );
  if (!response.ok) {
    throw new Error("Errore nell'aggiornamento delle note utente");
  }
  return response.json();
}

export async function markReleaseNoteSeen(
  version: string
): Promise<MarkSeenResponse> {
  const token = localStorage.getItem('access_token');
  if (!token) {
    throw new Error('Non autenticato');
  }

  const response = await fetch(
    `${apiClient['baseUrl']}${API_BASE}/${version}/seen`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    }
  );
  if (!response.ok) {
    throw new Error('Errore nel segnare come visto');
  }
  return response.json();
}
