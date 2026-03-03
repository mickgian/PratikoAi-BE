/**
 * @jest-environment jsdom
 */
import { renderHook, waitFor, act } from '@testing-library/react';

jest.mock('@/lib/api/communications', () => ({
  listCommunications: jest.fn(),
  createCommunication: jest.fn(),
  submitForReview: jest.fn(),
  approveCommunication: jest.fn(),
  rejectCommunication: jest.fn(),
  sendCommunication: jest.fn(),
  deleteCommunication: jest.fn(),
}));

jest.mock('@/lib/api/clients', () => ({
  listClients: jest.fn(),
}));

jest.mock('@/lib/api/helpers', () => ({
  getStudioId: jest.fn().mockReturnValue('studio-123'),
  getUserId: jest.fn().mockReturnValue(42),
  getAuthHeaders: jest.fn().mockReturnValue({}),
  buildStudioUrl: jest.fn(),
}));

jest.mock('@/lib/api/transformers', () => ({
  communicationStatusToItalian: {
    DRAFT: 'bozza',
    PENDING_REVIEW: 'in_revisione',
    APPROVED: 'approvata',
    REJECTED: 'rifiutata',
    SENT: 'inviata',
  },
}));

import {
  listCommunications,
  createCommunication,
  submitForReview,
  approveCommunication,
  rejectCommunication,
  sendCommunication,
  deleteCommunication,
} from '@/lib/api/communications';
import { listClients } from '@/lib/api/clients';
import { getStudioId } from '@/lib/api/helpers';
import {
  useCommunications,
  useCommunicationActions,
} from '../useCommunications';

const mockListCommunications = listCommunications as jest.MockedFunction<
  typeof listCommunications
>;
const mockListClients = listClients as jest.MockedFunction<typeof listClients>;
const mockCreateCommunication = createCommunication as jest.MockedFunction<
  typeof createCommunication
>;
const mockSubmitForReview = submitForReview as jest.MockedFunction<
  typeof submitForReview
>;
const mockApproveCommunication = approveCommunication as jest.MockedFunction<
  typeof approveCommunication
>;
const mockRejectCommunication = rejectCommunication as jest.MockedFunction<
  typeof rejectCommunication
>;
const mockSendCommunication = sendCommunication as jest.MockedFunction<
  typeof sendCommunication
>;
const mockDeleteCommunication = deleteCommunication as jest.MockedFunction<
  typeof deleteCommunication
>;
const mockGetStudioId = getStudioId as jest.MockedFunction<typeof getStudioId>;

const makeCommunication = (
  overrides: Partial<{
    id: string;
    status: string;
    client_id: number | null;
  }> = {}
) => ({
  id: overrides.id ?? 'comm-1',
  studio_id: 'studio-123',
  client_id: overrides.client_id ?? 1,
  subject: 'Oggetto',
  content: 'Contenuto',
  channel: 'EMAIL',
  status: overrides.status ?? 'DRAFT',
  created_by: 42,
  approved_by: null,
  approved_at: null,
  sent_at: null,
  normativa_riferimento: null,
  created_at: '2025-01-01T00:00:00Z',
});

const mockClientListResponse = {
  items: [
    {
      id: 1,
      studio_id: 'studio-123',
      codice_fiscale: 'RSSMRA80A01H501Z',
      nome: 'Mario Rossi',
      tipo_cliente: 'PERSONA_FISICA',
      stato_cliente: 'ATTIVO',
      comune: 'Roma',
      provincia: 'RM',
      partita_iva: null,
      email: null,
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
    },
  ],
  total: 1,
  offset: 0,
  limit: 200,
};

// ---------- useCommunications ----------

describe('useCommunications', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetStudioId.mockReturnValue('studio-123');
  });

  it('fetches communications and clients on mount', async () => {
    const comms = [
      makeCommunication({ id: 'c1', status: 'DRAFT' }),
      makeCommunication({ id: 'c2', status: 'SENT' }),
    ];
    mockListCommunications.mockResolvedValueOnce(comms);
    mockListClients.mockResolvedValueOnce(mockClientListResponse);

    const { result } = renderHook(() => useCommunications());

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.communications).toEqual(comms);
    expect(result.current.error).toBeNull();
  });

  it('computes stats from communications', async () => {
    const comms = [
      makeCommunication({ id: 'c1', status: 'DRAFT' }),
      makeCommunication({ id: 'c2', status: 'DRAFT' }),
      makeCommunication({ id: 'c3', status: 'PENDING_REVIEW' }),
      makeCommunication({ id: 'c4', status: 'APPROVED' }),
      makeCommunication({ id: 'c5', status: 'SENT' }),
      makeCommunication({ id: 'c6', status: 'SENT' }),
    ];
    mockListCommunications.mockResolvedValueOnce(comms);
    mockListClients.mockResolvedValueOnce(mockClientListResponse);

    const { result } = renderHook(() => useCommunications());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.stats).toEqual({
      bozze: 2,
      in_revisione: 1,
      approvate: 1,
      inviate: 2,
    });
  });

  it('builds client map for name lookup', async () => {
    mockListCommunications.mockResolvedValueOnce([]);
    mockListClients.mockResolvedValueOnce(mockClientListResponse);

    const { result } = renderHook(() => useCommunications());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.getClientName(1)).toBe('Mario Rossi');
    expect(result.current.getClientName(999)).toBe('Cliente #999');
    expect(result.current.getClientName(null)).toBe('N/A');
  });

  it('exposes clients list for dropdowns', async () => {
    mockListCommunications.mockResolvedValueOnce([]);
    mockListClients.mockResolvedValueOnce(mockClientListResponse);

    const { result } = renderHook(() => useCommunications());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.clients).toEqual([{ id: 1, name: 'Mario Rossi' }]);
  });

  it('translates status to Italian', async () => {
    mockListCommunications.mockResolvedValueOnce([]);
    mockListClients.mockResolvedValueOnce(mockClientListResponse);

    const { result } = renderHook(() => useCommunications());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.getItalianStatus('DRAFT')).toBe('bozza');
    expect(result.current.getItalianStatus('SENT')).toBe('inviata');
    expect(result.current.getItalianStatus('UNKNOWN')).toBe('UNKNOWN');
  });

  it('sets error on API failure', async () => {
    mockListCommunications.mockRejectedValueOnce(
      new Error('Errore nel caricamento delle comunicazioni')
    );
    mockListClients.mockResolvedValueOnce(mockClientListResponse);

    const { result } = renderHook(() => useCommunications());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe(
      'Errore nel caricamento delle comunicazioni'
    );
  });

  it('handles non-Error exceptions with fallback message', async () => {
    mockListCommunications.mockRejectedValueOnce(500);
    mockListClients.mockResolvedValueOnce(mockClientListResponse);

    const { result } = renderHook(() => useCommunications());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe('Errore nel caricamento');
  });

  it('sets error when studio is not configured', async () => {
    mockGetStudioId.mockReturnValue(null);

    const { result } = renderHook(() => useCommunications());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe('Studio non configurato');
    expect(mockListCommunications).not.toHaveBeenCalled();
  });

  it('passes statusFilter to listCommunications', async () => {
    mockListCommunications.mockResolvedValueOnce([]);
    mockListClients.mockResolvedValueOnce(mockClientListResponse);

    renderHook(() => useCommunications('DRAFT'));

    await waitFor(() => {
      expect(mockListCommunications).toHaveBeenCalledWith({
        status: 'DRAFT',
      });
    });
  });

  it('supports refresh', async () => {
    mockListCommunications.mockResolvedValueOnce([]);
    mockListClients.mockResolvedValueOnce(mockClientListResponse);

    const { result } = renderHook(() => useCommunications());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const newComms = [makeCommunication({ id: 'c-new' })];
    mockListCommunications.mockResolvedValueOnce(newComms);
    mockListClients.mockResolvedValueOnce(mockClientListResponse);

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.communications).toEqual(newComms);
  });
});

// ---------- useCommunicationActions ----------

describe('useCommunicationActions', () => {
  const mockOnRefresh = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('create calls createCommunication and refreshes', async () => {
    const comm = makeCommunication();
    mockCreateCommunication.mockResolvedValueOnce(comm);

    const { result } = renderHook(() => useCommunicationActions(mockOnRefresh));

    const createData = {
      subject: 'Oggetto',
      content: 'Contenuto',
      channel: 'EMAIL',
    };

    let created: unknown;
    await act(async () => {
      created = await result.current.create(createData);
    });

    expect(mockCreateCommunication).toHaveBeenCalledWith(createData);
    expect(created).toEqual(comm);
    expect(mockOnRefresh).toHaveBeenCalledTimes(1);
  });

  it('submit calls submitForReview and refreshes', async () => {
    const comm = makeCommunication({ status: 'PENDING_REVIEW' });
    mockSubmitForReview.mockResolvedValueOnce(comm);

    const { result } = renderHook(() => useCommunicationActions(mockOnRefresh));

    let submitted: unknown;
    await act(async () => {
      submitted = await result.current.submit('comm-1');
    });

    expect(mockSubmitForReview).toHaveBeenCalledWith('comm-1');
    expect(submitted).toEqual(comm);
    expect(mockOnRefresh).toHaveBeenCalledTimes(1);
  });

  it('approve calls approveCommunication and refreshes', async () => {
    const comm = makeCommunication({ status: 'APPROVED' });
    mockApproveCommunication.mockResolvedValueOnce(comm);

    const { result } = renderHook(() => useCommunicationActions(mockOnRefresh));

    let approved: unknown;
    await act(async () => {
      approved = await result.current.approve('comm-1');
    });

    expect(mockApproveCommunication).toHaveBeenCalledWith('comm-1');
    expect(approved).toEqual(comm);
    expect(mockOnRefresh).toHaveBeenCalledTimes(1);
  });

  it('reject calls rejectCommunication and refreshes', async () => {
    const comm = makeCommunication({ status: 'REJECTED' });
    mockRejectCommunication.mockResolvedValueOnce(comm);

    const { result } = renderHook(() => useCommunicationActions(mockOnRefresh));

    let rejected: unknown;
    await act(async () => {
      rejected = await result.current.reject('comm-1');
    });

    expect(mockRejectCommunication).toHaveBeenCalledWith('comm-1');
    expect(rejected).toEqual(comm);
    expect(mockOnRefresh).toHaveBeenCalledTimes(1);
  });

  it('send calls sendCommunication and refreshes', async () => {
    const comm = makeCommunication({ status: 'SENT' });
    mockSendCommunication.mockResolvedValueOnce(comm);

    const { result } = renderHook(() => useCommunicationActions(mockOnRefresh));

    let sent: unknown;
    await act(async () => {
      sent = await result.current.send('comm-1');
    });

    expect(mockSendCommunication).toHaveBeenCalledWith('comm-1');
    expect(sent).toEqual(comm);
    expect(mockOnRefresh).toHaveBeenCalledTimes(1);
  });

  it('remove calls deleteCommunication and refreshes', async () => {
    mockDeleteCommunication.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useCommunicationActions(mockOnRefresh));

    await act(async () => {
      await result.current.remove('comm-1');
    });

    expect(mockDeleteCommunication).toHaveBeenCalledWith('comm-1');
    expect(mockOnRefresh).toHaveBeenCalledTimes(1);
  });

  it('does not call onRefresh when action fails', async () => {
    mockCreateCommunication.mockRejectedValueOnce(new Error('fail'));

    const { result } = renderHook(() => useCommunicationActions(mockOnRefresh));

    await expect(
      act(async () => {
        await result.current.create({
          subject: 'X',
          content: 'Y',
          channel: 'EMAIL',
        });
      })
    ).rejects.toThrow('fail');

    expect(mockOnRefresh).not.toHaveBeenCalled();
  });
});
