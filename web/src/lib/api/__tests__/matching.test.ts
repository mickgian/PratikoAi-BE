/**
 * @jest-environment jsdom
 */
import {
  listSuggestions,
  markAsRead,
  dismissSuggestion,
  triggerMatching,
} from '../matching';

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

const mockSuggestion = {
  id: 'sugg-abc-123',
  studio_id: 'studio-123',
  knowledge_item_id: 10,
  matched_client_ids: [1, 2, 3],
  match_score: 0.85,
  suggestion_text: 'Nuova normativa rilevante per i clienti selezionati',
  is_read: false,
  is_dismissed: false,
  created_at: '2024-06-01T10:00:00Z',
};

const mockTriggerResponse = {
  status: 'started',
  studio_id: 'studio-123',
  knowledge_item_id: null,
  trigger: 'manual',
  message: 'Matching avviato con successo',
};

describe('matching API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ---------------------------------------------------------------
  // listSuggestions
  // ---------------------------------------------------------------
  describe('listSuggestions', () => {
    it('should fetch suggestions with no params', async () => {
      const mockList = [mockSuggestion];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockList,
      });

      const result = await listSuggestions();

      expect(result).toEqual(mockList);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/matching/suggestions'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      );
    });

    it('should pass filter params to buildStudioUrl', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      await listSuggestions({ unread_only: true, offset: 5, limit: 20 });

      const { buildStudioUrl } = require('@/lib/api/helpers');
      expect(buildStudioUrl).toHaveBeenCalledWith(
        '/api/v1/matching/suggestions',
        {
          unread_only: true,
          offset: 5,
          limit: 20,
        }
      );
    });

    it('should pass undefined params when not provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      await listSuggestions();

      const { buildStudioUrl } = require('@/lib/api/helpers');
      expect(buildStudioUrl).toHaveBeenCalledWith(
        '/api/v1/matching/suggestions',
        {
          unread_only: undefined,
          offset: undefined,
          limit: undefined,
        }
      );
    });

    it('should throw on error response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

      await expect(listSuggestions()).rejects.toThrow(
        'Errore nel caricamento dei suggerimenti'
      );
    });
  });

  // ---------------------------------------------------------------
  // markAsRead
  // ---------------------------------------------------------------
  describe('markAsRead', () => {
    it('should mark suggestion as read with PUT', async () => {
      const readSuggestion = { ...mockSuggestion, is_read: true };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => readSuggestion,
      });

      const result = await markAsRead('sugg-abc-123');

      expect(result.is_read).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(
          '/api/v1/matching/suggestions/sugg-abc-123/read'
        ),
        expect.objectContaining({ method: 'PUT' })
      );
    });

    it('should use correct URL via buildStudioUrl', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuggestion,
      });

      await markAsRead('sugg-xyz-789');

      const { buildStudioUrl } = require('@/lib/api/helpers');
      expect(buildStudioUrl).toHaveBeenCalledWith(
        '/api/v1/matching/suggestions/sugg-xyz-789/read'
      );
    });

    it('should throw on error response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });

      await expect(markAsRead('not-found')).rejects.toThrow(
        'Errore nel segnare come letto'
      );
    });
  });

  // ---------------------------------------------------------------
  // dismissSuggestion
  // ---------------------------------------------------------------
  describe('dismissSuggestion', () => {
    it('should dismiss suggestion with PUT', async () => {
      const dismissed = { ...mockSuggestion, is_dismissed: true };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => dismissed,
      });

      const result = await dismissSuggestion('sugg-abc-123');

      expect(result.is_dismissed).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(
          '/api/v1/matching/suggestions/sugg-abc-123/dismiss'
        ),
        expect.objectContaining({ method: 'PUT' })
      );
    });

    it('should use correct URL via buildStudioUrl', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuggestion,
      });

      await dismissSuggestion('sugg-xyz-789');

      const { buildStudioUrl } = require('@/lib/api/helpers');
      expect(buildStudioUrl).toHaveBeenCalledWith(
        '/api/v1/matching/suggestions/sugg-xyz-789/dismiss'
      );
    });

    it('should throw on error response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

      await expect(dismissSuggestion('sugg-abc-123')).rejects.toThrow(
        'Errore nel rifiuto del suggerimento'
      );
    });
  });

  // ---------------------------------------------------------------
  // triggerMatching
  // ---------------------------------------------------------------
  describe('triggerMatching', () => {
    it('should trigger matching with POST and no knowledge item', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTriggerResponse,
      });

      const result = await triggerMatching();

      expect(result).toEqual(mockTriggerResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/matching/trigger'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            knowledge_item_id: null,
            trigger: 'manual',
          }),
        })
      );
    });

    it('should include knowledge_item_id when provided', async () => {
      const responseWithItem = {
        ...mockTriggerResponse,
        knowledge_item_id: 42,
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => responseWithItem,
      });

      const result = await triggerMatching(42);

      expect(result.knowledge_item_id).toBe(42);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/matching/trigger'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            knowledge_item_id: 42,
            trigger: 'manual',
          }),
        })
      );
    });

    it('should use correct auth headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTriggerResponse,
      });

      await triggerMatching();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
            'Content-Type': 'application/json',
          }),
        })
      );
    });

    it('should throw on error response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

      await expect(triggerMatching()).rejects.toThrow(
        "Errore nell'avvio del matching"
      );
    });

    it('should throw on error response with knowledge item', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 400 });

      await expect(triggerMatching(999)).rejects.toThrow(
        "Errore nell'avvio del matching"
      );
    });
  });
});
