/**
 * @jest-environment jsdom
 */
import { renderHook, waitFor, act } from '@testing-library/react';

jest.mock('@/lib/api/clients', () => ({
  listClients: jest.fn(),
  getClient: jest.fn(),
  createClient: jest.fn(),
  updateClient: jest.fn(),
  deleteClient: jest.fn(),
}));

jest.mock('@/lib/api/helpers', () => ({
  getStudioId: jest.fn().mockReturnValue('studio-123'),
  getUserId: jest.fn().mockReturnValue(42),
  getAuthHeaders: jest.fn().mockReturnValue({}),
  buildStudioUrl: jest.fn(),
}));

import {
  listClients,
  getClient,
  createClient,
  updateClient,
  deleteClient,
} from '@/lib/api/clients';
import { getStudioId } from '@/lib/api/helpers';
import { useClients, useClient } from '../useClients';

const mockListClients = listClients as jest.MockedFunction<typeof listClients>;
const mockGetClient = getClient as jest.MockedFunction<typeof getClient>;
const mockCreateClient = createClient as jest.MockedFunction<
  typeof createClient
>;
const mockUpdateClient = updateClient as jest.MockedFunction<
  typeof updateClient
>;
const mockDeleteClient = deleteClient as jest.MockedFunction<
  typeof deleteClient
>;
const mockGetStudioId = getStudioId as jest.MockedFunction<typeof getStudioId>;

const mockClient = {
  id: 1,
  studio_id: 'studio-123',
  codice_fiscale: 'RSSMRA80A01H501Z',
  nome: 'Mario Rossi',
  tipo_cliente: 'PERSONA_FISICA',
  stato_cliente: 'ATTIVO',
  comune: 'Roma',
  provincia: 'RM',
  partita_iva: null,
  email: 'mario@example.com',
  phone: null,
  indirizzo: null,
  cap: null,
  note_studio: null,
  inps_matricola: null,
  inps_status: null,
  inps_ultimo_pagamento: null,
  inail_pat: null,
  inail_status: null,
  created_at: '2025-01-01T00:00:00Z',
};

const mockListResponse = {
  items: [mockClient],
  total: 1,
  offset: 0,
  limit: 50,
};

// ---------- useClients ----------

describe('useClients', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetStudioId.mockReturnValue('studio-123');
  });

  it('fetches client list on mount', async () => {
    mockListClients.mockResolvedValueOnce(mockListResponse);

    const { result } = renderHook(() => useClients());

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.clients).toEqual([mockClient]);
    expect(result.current.total).toBe(1);
    expect(result.current.error).toBeNull();
  });

  it('sets error on API failure', async () => {
    mockListClients.mockRejectedValueOnce(
      new Error('Errore nel caricamento dei clienti')
    );

    const { result } = renderHook(() => useClients());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.clients).toEqual([]);
    expect(result.current.total).toBe(0);
    expect(result.current.error).toBe('Errore nel caricamento dei clienti');
  });

  it('handles non-Error exceptions with fallback message', async () => {
    mockListClients.mockRejectedValueOnce('unexpected');

    const { result } = renderHook(() => useClients());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe('Errore nel caricamento');
  });

  it('sets error when studio is not configured', async () => {
    mockGetStudioId.mockReturnValue(null);

    const { result } = renderHook(() => useClients());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe('Studio non configurato');
    expect(mockListClients).not.toHaveBeenCalled();
  });

  it('passes params to listClients', async () => {
    mockListClients.mockResolvedValueOnce(mockListResponse);

    const params = { offset: 10, limit: 25, stato: 'ATTIVO', search: 'Mario' };
    renderHook(() => useClients(params));

    await waitFor(() => {
      expect(mockListClients).toHaveBeenCalledWith(params);
    });
  });

  it('supports refresh', async () => {
    mockListClients.mockResolvedValueOnce(mockListResponse);

    const { result } = renderHook(() => useClients());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const updatedResponse = { ...mockListResponse, total: 5 };
    mockListClients.mockResolvedValueOnce(updatedResponse);

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.total).toBe(5);
  });

  it('returns empty clients array when data is null', async () => {
    mockListClients.mockRejectedValueOnce(new Error('fail'));

    const { result } = renderHook(() => useClients());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.clients).toEqual([]);
    expect(result.current.total).toBe(0);
  });
});

// ---------- useClient ----------

describe('useClient', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetStudioId.mockReturnValue('studio-123');
  });

  it('loads client by numeric ID', async () => {
    mockGetClient.mockResolvedValueOnce(mockClient);

    const { result } = renderHook(() => useClient(1));

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.client).toEqual(mockClient);
    expect(result.current.error).toBeNull();
    expect(mockGetClient).toHaveBeenCalledWith(1);
  });

  it('loads client by string ID', async () => {
    mockGetClient.mockResolvedValueOnce(mockClient);

    const { result } = renderHook(() => useClient('1'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.client).toEqual(mockClient);
    expect(mockGetClient).toHaveBeenCalledWith(1);
  });

  it('does not fetch when clientId is null', async () => {
    const { result } = renderHook(() => useClient(null));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.client).toBeNull();
    expect(mockGetClient).not.toHaveBeenCalled();
  });

  it('does not fetch when clientId is "new"', async () => {
    const { result } = renderHook(() => useClient('new'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.client).toBeNull();
    expect(mockGetClient).not.toHaveBeenCalled();
  });

  it('does not fetch when clientId is NaN string', async () => {
    const { result } = renderHook(() => useClient('abc'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.client).toBeNull();
    expect(mockGetClient).not.toHaveBeenCalled();
  });

  it('sets error on load failure', async () => {
    mockGetClient.mockRejectedValueOnce(new Error('Cliente non trovato'));

    const { result } = renderHook(() => useClient(999));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe('Cliente non trovato');
  });

  it('save calls updateClient for existing client', async () => {
    mockGetClient.mockResolvedValueOnce(mockClient);
    const updatedClient = { ...mockClient, nome: 'Mario Bianchi' };
    mockUpdateClient.mockResolvedValueOnce(updatedClient);

    const { result } = renderHook(() => useClient(1));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let saved: unknown;
    await act(async () => {
      saved = await result.current.save({ nome: 'Mario Bianchi' });
    });

    expect(mockUpdateClient).toHaveBeenCalledWith(1, {
      nome: 'Mario Bianchi',
    });
    expect(saved).toEqual(updatedClient);
    expect(result.current.client).toEqual(updatedClient);
  });

  it('save calls createClient for new client', async () => {
    const newClient = { ...mockClient, id: 2 };
    mockCreateClient.mockResolvedValueOnce(newClient);

    const { result } = renderHook(() => useClient('new'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const createData = {
      codice_fiscale: 'BNCMRA80A01H501Z',
      nome: 'Marco Bianchi',
      tipo_cliente: 'PERSONA_FISICA',
      comune: 'Milano',
      provincia: 'MI',
    };

    let saved: unknown;
    await act(async () => {
      saved = await result.current.save(createData);
    });

    expect(mockCreateClient).toHaveBeenCalledWith(createData);
    expect(saved).toEqual(newClient);
  });

  it('save calls createClient when clientId is null', async () => {
    const newClient = { ...mockClient, id: 3 };
    mockCreateClient.mockResolvedValueOnce(newClient);

    const { result } = renderHook(() => useClient(null));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const createData = {
      codice_fiscale: 'BNCMRA80A01H501Z',
      nome: 'Marco Bianchi',
      tipo_cliente: 'PERSONA_FISICA',
      comune: 'Milano',
      provincia: 'MI',
    };

    await act(async () => {
      await result.current.save(createData);
    });

    expect(mockCreateClient).toHaveBeenCalledWith(createData);
  });

  it('remove calls deleteClient', async () => {
    mockGetClient.mockResolvedValueOnce(mockClient);
    mockDeleteClient.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useClient(1));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.remove();
    });

    expect(mockDeleteClient).toHaveBeenCalledWith(1);
  });

  it('remove does nothing for new client', async () => {
    const { result } = renderHook(() => useClient('new'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.remove();
    });

    expect(mockDeleteClient).not.toHaveBeenCalled();
  });

  it('remove does nothing when clientId is null', async () => {
    const { result } = renderHook(() => useClient(null));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.remove();
    });

    expect(mockDeleteClient).not.toHaveBeenCalled();
  });
});
