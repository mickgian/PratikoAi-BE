/**
 * @jest-environment jsdom
 */
import {
  listCommunications,
  getCommunication,
  createCommunication,
  submitForReview,
  approveCommunication,
  rejectCommunication,
  sendCommunication,
  deleteCommunication,
  bulkCreateDrafts,
} from '../communications';

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock helpers
jest.mock('@/lib/api/helpers', () => ({
  getStudioId: jest.fn().mockReturnValue('studio-123'),
  getUserId: jest.fn().mockReturnValue(42),
  getAuthHeaders: jest.fn().mockReturnValue({
    Authorization: 'Bearer test-token',
    'X-Studio-Id': 'studio-123',
    'Content-Type': 'application/json',
  }),
  buildStudioUrl: jest.fn().mockImplementation((path, params) => {
    const url = new URL(`http://localhost:8000${path}`);
    url.searchParams.set('studio_id', 'studio-123');
    if (params)
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined) url.searchParams.set(k, String(v));
      });
    return url.toString();
  }),
}));

// --- Fixtures ---

const mockCommunication = {
  id: 'comm-abc-123',
  studio_id: 'studio-123',
  client_id: 1,
  subject: 'Aggiornamento normativo',
  content: 'Gentile cliente, la informiamo...',
  channel: 'email',
  status: 'draft',
  created_by: 42,
  approved_by: null,
  approved_at: null,
  sent_at: null,
  normativa_riferimento: 'DL 123/2024',
  created_at: '2024-06-01T10:00:00Z',
};

describe('communications API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ---------------------------------------------------------------
  // listCommunications
  // ---------------------------------------------------------------
  describe('listCommunications', () => {
    it('should fetch communications with default params', async () => {
      const mockList = [mockCommunication];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockList,
      });

      const result = await listCommunications();

      expect(result).toEqual(mockList);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/communications'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      );
    });

    it('should pass status filter param', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      await listCommunications({ status: 'draft', offset: 0, limit: 50 });

      const { buildStudioUrl } = require('@/lib/api/helpers');
      expect(buildStudioUrl).toHaveBeenCalledWith('/api/v1/communications', {
        status: 'draft',
        offset: 0,
        limit: 50,
      });
    });

    it('should throw on error response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

      await expect(listCommunications()).rejects.toThrow(
        'Errore nel caricamento delle comunicazioni'
      );
    });
  });

  // ---------------------------------------------------------------
  // getCommunication
  // ---------------------------------------------------------------
  describe('getCommunication', () => {
    it('should fetch a single communication by ID', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockCommunication,
      });

      const result = await getCommunication('comm-abc-123');

      expect(result).toEqual(mockCommunication);
      const { buildStudioUrl } = require('@/lib/api/helpers');
      expect(buildStudioUrl).toHaveBeenCalledWith(
        '/api/v1/communications/comm-abc-123'
      );
    });

    it('should throw when communication not found', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });

      await expect(getCommunication('not-found')).rejects.toThrow(
        'Comunicazione non trovata'
      );
    });
  });

  // ---------------------------------------------------------------
  // createCommunication
  // ---------------------------------------------------------------
  describe('createCommunication', () => {
    const createData = {
      subject: 'Nuova comunicazione',
      content: 'Contenuto della comunicazione',
      channel: 'email',
      client_id: 1,
    };

    it('should create a communication with POST', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockCommunication,
      });

      const result = await createCommunication(createData);

      expect(result).toEqual(mockCommunication);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/communications'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(createData),
        })
      );
    });

    it('should include created_by param in URL', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockCommunication,
      });

      await createCommunication(createData);

      const { buildStudioUrl } = require('@/lib/api/helpers');
      expect(buildStudioUrl).toHaveBeenCalledWith('/api/v1/communications', {
        created_by: 42,
      });
    });

    it('should throw with detail from error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Subject obbligatorio' }),
      });

      await expect(createCommunication(createData)).rejects.toThrow(
        'Subject obbligatorio'
      );
    });

    it('should throw default message when error has no detail', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('parse error');
        },
      });

      await expect(createCommunication(createData)).rejects.toThrow(
        'Errore nella creazione della comunicazione'
      );
    });
  });

  // ---------------------------------------------------------------
  // submitForReview
  // ---------------------------------------------------------------
  describe('submitForReview', () => {
    it('should submit communication for review with POST', async () => {
      const submitted = { ...mockCommunication, status: 'pending_review' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => submitted,
      });

      const result = await submitForReview('comm-abc-123');

      expect(result.status).toBe('pending_review');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/communications/comm-abc-123/submit'),
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('should throw on error response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 400 });

      await expect(submitForReview('comm-abc-123')).rejects.toThrow(
        "Errore nell'invio per revisione"
      );
    });
  });

  // ---------------------------------------------------------------
  // approveCommunication
  // ---------------------------------------------------------------
  describe('approveCommunication', () => {
    it('should approve communication with POST', async () => {
      const approved = {
        ...mockCommunication,
        status: 'approved',
        approved_by: 42,
        approved_at: '2024-06-02T10:00:00Z',
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => approved,
      });

      const result = await approveCommunication('comm-abc-123');

      expect(result.status).toBe('approved');
      const { buildStudioUrl } = require('@/lib/api/helpers');
      expect(buildStudioUrl).toHaveBeenCalledWith(
        '/api/v1/communications/comm-abc-123/approve',
        { approved_by: 42 }
      );
    });

    it('should throw on error response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 403 });

      await expect(approveCommunication('comm-abc-123')).rejects.toThrow(
        "Errore nell'approvazione"
      );
    });
  });

  // ---------------------------------------------------------------
  // rejectCommunication
  // ---------------------------------------------------------------
  describe('rejectCommunication', () => {
    it('should reject communication with POST', async () => {
      const rejected = { ...mockCommunication, status: 'rejected' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => rejected,
      });

      const result = await rejectCommunication('comm-abc-123');

      expect(result.status).toBe('rejected');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/communications/comm-abc-123/reject'),
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('should throw on error response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 400 });

      await expect(rejectCommunication('comm-abc-123')).rejects.toThrow(
        'Errore nel rifiuto'
      );
    });
  });

  // ---------------------------------------------------------------
  // sendCommunication
  // ---------------------------------------------------------------
  describe('sendCommunication', () => {
    it('should send communication with POST', async () => {
      const sent = {
        ...mockCommunication,
        status: 'sent',
        sent_at: '2024-06-03T10:00:00Z',
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => sent,
      });

      const result = await sendCommunication('comm-abc-123');

      expect(result.status).toBe('sent');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/communications/comm-abc-123/send'),
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('should throw on error response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

      await expect(sendCommunication('comm-abc-123')).rejects.toThrow(
        "Errore nell'invio"
      );
    });
  });

  // ---------------------------------------------------------------
  // deleteCommunication
  // ---------------------------------------------------------------
  describe('deleteCommunication', () => {
    it('should delete communication with DELETE method', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

      await deleteCommunication('comm-abc-123');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/communications/comm-abc-123'),
        expect.objectContaining({ method: 'DELETE' })
      );
    });

    it('should throw on error response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

      await expect(deleteCommunication('comm-abc-123')).rejects.toThrow(
        "Errore nell'eliminazione della comunicazione"
      );
    });
  });

  // ---------------------------------------------------------------
  // bulkCreateDrafts
  // ---------------------------------------------------------------
  describe('bulkCreateDrafts', () => {
    const bulkData = {
      client_ids: [1, 2, 3],
      subject: 'Aggiornamento per tutti',
      content: 'Testo della comunicazione',
      channel: 'email',
    };

    it('should create bulk drafts with POST', async () => {
      const mockBulkResult = [
        { ...mockCommunication, client_id: 1 },
        { ...mockCommunication, id: 'comm-def-456', client_id: 2 },
        { ...mockCommunication, id: 'comm-ghi-789', client_id: 3 },
      ];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockBulkResult,
      });

      const result = await bulkCreateDrafts(bulkData);

      expect(result).toHaveLength(3);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/communications/bulk'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(bulkData),
        })
      );
    });

    it('should include created_by param in URL', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      await bulkCreateDrafts(bulkData);

      const { buildStudioUrl } = require('@/lib/api/helpers');
      expect(buildStudioUrl).toHaveBeenCalledWith(
        '/api/v1/communications/bulk',
        { created_by: 42 }
      );
    });

    it('should throw with detail from error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Client IDs non validi' }),
      });

      await expect(bulkCreateDrafts(bulkData)).rejects.toThrow(
        'Client IDs non validi'
      );
    });

    it('should throw default message when error has no detail', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('parse error');
        },
      });

      await expect(bulkCreateDrafts(bulkData)).rejects.toThrow(
        'Errore nella creazione bulk'
      );
    });
  });
});
