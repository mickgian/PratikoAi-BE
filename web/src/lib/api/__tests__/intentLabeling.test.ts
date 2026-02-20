// src/lib/api/__tests__/intentLabeling.test.ts
import {
  getLabelingQueue,
  submitLabel,
  skipQuery,
  getLabelingStats,
  exportTrainingData,
} from '../intentLabeling';
import type {
  QueueResponse,
  LabeledQueryResponse,
  SkipResponse,
  LabelingStatsResponse,
} from '@/types/intentLabeling';

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  clear: jest.fn(),
  removeItem: jest.fn(),
  length: 0,
  key: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock URL.createObjectURL and revokeObjectURL
global.URL.createObjectURL = jest.fn(() => 'blob:http://localhost/mock');
global.URL.revokeObjectURL = jest.fn();

describe('intentLabeling API', () => {
  const mockToken = 'test-token-123';

  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(mockToken);
  });

  describe('getLabelingQueue', () => {
    const mockQueueResponse: QueueResponse = {
      total_count: 50,
      page: 1,
      page_size: 20,
      items: [
        {
          id: '123e4567-e89b-12d3-a456-426614174000',
          query: "Come si calcola l'imposta sostitutiva?",
          predicted_intent: 'technical_research',
          confidence: 0.45,
          all_scores: {
            technical_research: 0.45,
            theoretical_definition: 0.3,
            calculator: 0.15,
            chitchat: 0.05,
            normative_reference: 0.05,
          },
          expert_intent: null,
          skip_count: 0,
          created_at: '2026-02-03T10:30:00',
        },
      ],
    };

    it('should fetch queue successfully with default params', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockQueueResponse,
      });

      const result = await getLabelingQueue();

      expect(result).toEqual(mockQueueResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/labeling/queue?page=1&page_size=20'),
        expect.objectContaining({ method: 'GET' })
      );
    });

    it('should fetch queue with custom pagination', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockQueueResponse,
      });

      await getLabelingQueue(2, 50);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/labeling/queue?page=2&page_size=50'),
        expect.objectContaining({ method: 'GET' })
      );
    });

    it('should throw error when not authenticated', async () => {
      localStorageMock.getItem.mockReturnValue(null);

      await expect(getLabelingQueue()).rejects.toThrow('Non autenticato');
    });

    it('should handle HTTP error responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({ detail: 'Accesso non autorizzato' }),
      });

      await expect(getLabelingQueue()).rejects.toThrow(
        'Accesso non autorizzato'
      );
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

      await expect(getLabelingQueue()).rejects.toThrow(
        'Impossibile connettersi al server'
      );
    });
  });

  describe('submitLabel', () => {
    const mockLabeledResponse: LabeledQueryResponse = {
      id: '123e4567-e89b-12d3-a456-426614174000',
      query: "Come si calcola l'imposta sostitutiva?",
      predicted_intent: 'technical_research',
      expert_intent: 'calculator',
      labeled_by: 1,
      labeled_at: '2026-02-03T11:45:00',
      labeling_notes: 'Richiesta di calcolo, non ricerca',
    };

    it('should submit label successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockLabeledResponse,
      });

      const result = await submitLabel({
        query_id: '123e4567-e89b-12d3-a456-426614174000',
        expert_intent: 'calculator',
        notes: 'Richiesta di calcolo, non ricerca',
      });

      expect(result).toEqual(mockLabeledResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/labeling/label'),
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('should throw error when query_id is missing', async () => {
      await expect(
        submitLabel({ query_id: '', expert_intent: 'calculator' })
      ).rejects.toThrow('query_id e expert_intent sono richiesti');
    });

    it('should throw error when expert_intent is missing', async () => {
      await expect(
        submitLabel({
          query_id: '123e4567-e89b-12d3-a456-426614174000',
          expert_intent: '',
        })
      ).rejects.toThrow('query_id e expert_intent sono richiesti');
    });

    it('should throw error when not authenticated', async () => {
      localStorageMock.getItem.mockReturnValue(null);

      await expect(
        submitLabel({
          query_id: '123e4567-e89b-12d3-a456-426614174000',
          expert_intent: 'calculator',
        })
      ).rejects.toThrow('Non autenticato');
    });
  });

  describe('skipQuery', () => {
    const mockSkipResponse: SkipResponse = {
      id: '123e4567-e89b-12d3-a456-426614174000',
      skip_count: 2,
      message: 'Query saltata con successo',
    };

    it('should skip query successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockSkipResponse,
      });

      const result = await skipQuery('123e4567-e89b-12d3-a456-426614174000');

      expect(result).toEqual(mockSkipResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(
          '/api/v1/labeling/skip/123e4567-e89b-12d3-a456-426614174000'
        ),
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('should throw error when not authenticated', async () => {
      localStorageMock.getItem.mockReturnValue(null);

      await expect(
        skipQuery('123e4567-e89b-12d3-a456-426614174000')
      ).rejects.toThrow('Non autenticato');
    });
  });

  describe('getLabelingStats', () => {
    const mockStats: LabelingStatsResponse = {
      total_queries: 500,
      labeled_queries: 125,
      pending_queries: 375,
      completion_percentage: 25.0,
      labels_by_intent: {
        chitchat: 30,
        technical_research: 45,
        calculator: 25,
        theoretical_definition: 15,
        normative_reference: 10,
      },
      new_since_export: 50,
    };

    it('should fetch stats successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockStats,
      });

      const result = await getLabelingStats();

      expect(result).toEqual(mockStats);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/labeling/stats'),
        expect.objectContaining({ method: 'GET' })
      );
    });

    it('should throw error when not authenticated', async () => {
      localStorageMock.getItem.mockReturnValue(null);

      await expect(getLabelingStats()).rejects.toThrow('Non autenticato');
    });

    it('should handle server errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Errore interno del server' }),
      });

      await expect(getLabelingStats()).rejects.toThrow(
        'Errore interno del server'
      );
    });
  });

  describe('exportTrainingData', () => {
    it('should trigger file download for jsonl', async () => {
      const mockBlob = new Blob(['{"text":"test","label":"chitchat"}'], {
        type: 'application/jsonl',
      });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        blob: async () => mockBlob,
      });

      const appendChildSpy = jest.spyOn(document.body, 'appendChild');
      const removeChildSpy = jest.spyOn(document.body, 'removeChild');

      await exportTrainingData('jsonl');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/labeling/export?format=jsonl'),
        expect.objectContaining({ method: 'GET' })
      );
      expect(appendChildSpy).toHaveBeenCalled();
      expect(removeChildSpy).toHaveBeenCalled();

      appendChildSpy.mockRestore();
      removeChildSpy.mockRestore();
    });

    it('should throw error when not authenticated', async () => {
      localStorageMock.getItem.mockReturnValue(null);

      await expect(exportTrainingData()).rejects.toThrow('Non autenticato');
    });

    it('should handle export error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({ detail: 'Solo gli admin possono esportare' }),
      });

      await expect(exportTrainingData()).rejects.toThrow(
        'Solo gli admin possono esportare'
      );
    });
  });

  describe('token fallback', () => {
    it('should use current_session_token first', async () => {
      localStorageMock.getItem.mockImplementation((key: string) => {
        if (key === 'current_session_token') return 'session-token';
        if (key === 'access_token') return 'access-token';
        return null;
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          total_count: 0,
          page: 1,
          page_size: 20,
          items: [],
        }),
      });

      await getLabelingQueue();

      const callHeaders = mockFetch.mock.calls[0][1].headers as Headers;
      expect(callHeaders.get('Authorization')).toBe('Bearer session-token');
    });

    it('should fallback to access_token', async () => {
      localStorageMock.getItem.mockImplementation((key: string) => {
        if (key === 'current_session_token') return null;
        if (key === 'access_token') return 'access-token';
        return null;
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          total_count: 0,
          page: 1,
          page_size: 20,
          items: [],
        }),
      });

      await getLabelingQueue();

      const callHeaders = mockFetch.mock.calls[0][1].headers as Headers;
      expect(callHeaders.get('Authorization')).toBe('Bearer access-token');
    });
  });
});
