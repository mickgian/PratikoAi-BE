// src/lib/api/__tests__/modelComparison.test.ts
import {
  runComparison,
  submitVote,
  getAvailableModels,
  updateModelPreferences,
  getUserStats,
  getLeaderboard,
} from '../modelComparison';
import type {
  ComparisonRequest,
  ComparisonResponse,
  VoteRequest,
  VoteResponse,
  AvailableModelsResponse,
  LeaderboardResponse,
  ComparisonStatsResponse,
  ModelPreferencesRequest,
} from '@/types/modelComparison';

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

// Mock console methods to avoid noise
const consoleSpy = {
  log: jest.spyOn(console, 'log').mockImplementation(),
  error: jest.spyOn(console, 'error').mockImplementation(),
};

describe('modelComparison API', () => {
  const mockToken = 'test-token-123';

  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(mockToken);
  });

  afterAll(() => {
    consoleSpy.log.mockRestore();
    consoleSpy.error.mockRestore();
  });

  describe('runComparison', () => {
    const validRequest: ComparisonRequest = {
      query: 'What is the capital of Italy?',
      model_ids: ['openai:gpt-4o', 'anthropic:claude-3-sonnet'],
    };

    const mockResponse: ComparisonResponse = {
      batch_id: 'batch-123',
      query: 'What is the capital of Italy?',
      responses: [
        {
          model_id: 'openai:gpt-4o',
          provider: 'openai',
          model_name: 'gpt-4o',
          response_text: 'Rome is the capital of Italy.',
          latency_ms: 1200,
          cost_eur: 0.003,
          cost_usd: 0.0033,
          input_tokens: 15,
          output_tokens: 8,
          status: 'success',
          trace_id: 'trace-1',
        },
        {
          model_id: 'anthropic:claude-3-sonnet',
          provider: 'anthropic',
          model_name: 'claude-3-sonnet',
          response_text: 'The capital of Italy is Rome.',
          latency_ms: 1500,
          cost_eur: 0.004,
          cost_usd: 0.0044,
          input_tokens: 15,
          output_tokens: 7,
          status: 'success',
          trace_id: 'trace-2',
        },
      ],
      created_at: '2026-02-06T12:00:00Z',
    };

    it('should run comparison successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await runComparison(validRequest);

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/model-comparison/compare'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(validRequest),
        })
      );
    });

    it('should throw error when not authenticated', async () => {
      localStorageMock.getItem.mockReturnValue(null);

      await expect(runComparison(validRequest)).rejects.toThrow(
        'Non autenticato'
      );
    });

    it('should throw error when query is empty', async () => {
      const invalidRequest: ComparisonRequest = { query: '' };

      await expect(runComparison(invalidRequest)).rejects.toThrow(
        'La domanda non può essere vuota'
      );
    });

    it('should throw error when query is whitespace only', async () => {
      const invalidRequest: ComparisonRequest = { query: '   ' };

      await expect(runComparison(invalidRequest)).rejects.toThrow(
        'La domanda non può essere vuota'
      );
    });

    it('should throw error when query exceeds 2000 characters', async () => {
      const invalidRequest: ComparisonRequest = {
        query: 'a'.repeat(2001),
      };

      await expect(runComparison(invalidRequest)).rejects.toThrow(
        'supera il limite di 2000 caratteri'
      );
    });

    it('should throw error when less than 2 models are selected', async () => {
      const invalidRequest: ComparisonRequest = {
        query: 'Test query',
        model_ids: ['openai:gpt-4o'],
      };

      await expect(runComparison(invalidRequest)).rejects.toThrow(
        'Seleziona almeno 2 modelli'
      );
    });

    it('should throw error when more than 6 models are selected', async () => {
      const invalidRequest: ComparisonRequest = {
        query: 'Test query',
        model_ids: [
          'openai:gpt-4o',
          'anthropic:claude-3-sonnet',
          'gemini:gemini-1.5-pro',
          'mistral:mistral-large',
          'gemini:gemini-2.0-flash',
          'openai:gpt-4o-mini',
          'anthropic:claude-3-haiku',
        ],
      };

      await expect(runComparison(invalidRequest)).rejects.toThrow(
        'Massimo 6 modelli'
      );
    });

    it('should handle HTTP error responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({ detail: 'Accesso non autorizzato' }),
      });

      await expect(runComparison(validRequest)).rejects.toThrow(
        'Accesso non autorizzato'
      );
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

      await expect(runComparison(validRequest)).rejects.toThrow(
        'Impossibile connettersi al server'
      );
    });
  });

  describe('submitVote', () => {
    const validRequest: VoteRequest = {
      batch_id: 'batch-123',
      winner_model_id: 'openai:gpt-4o',
      comment: 'More concise response',
    };

    const mockResponse: VoteResponse = {
      success: true,
      message: 'Voto registrato con successo',
      winner_model_id: 'openai:gpt-4o',
      elo_changes: {
        'openai:gpt-4o': 16.0,
        'anthropic:claude-3-sonnet': -16.0,
      },
    };

    it('should submit vote successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await submitVote(validRequest);

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/model-comparison/vote'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(validRequest),
        })
      );
    });

    it('should throw error when batch_id is missing', async () => {
      const invalidRequest: VoteRequest = {
        batch_id: '',
        winner_model_id: 'openai:gpt-4o',
      };

      await expect(submitVote(invalidRequest)).rejects.toThrow(
        'batch_id è obbligatorio'
      );
    });

    it('should throw error when winner_model_id is missing', async () => {
      const invalidRequest: VoteRequest = {
        batch_id: 'batch-123',
        winner_model_id: '',
      };

      await expect(submitVote(invalidRequest)).rejects.toThrow(
        'Seleziona il modello vincitore'
      );
    });

    it('should handle 404 error for non-existent session', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Sessione di confronto non trovata' }),
      });

      await expect(submitVote(validRequest)).rejects.toThrow(
        'Sessione di confronto non trovata'
      );
    });

    it('should handle 409 error for duplicate vote', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => ({
          detail: 'Voto già registrato per questa sessione',
        }),
      });

      await expect(submitVote(validRequest)).rejects.toThrow(
        'Voto già registrato'
      );
    });
  });

  describe('getAvailableModels', () => {
    const mockResponse: AvailableModelsResponse = {
      models: [
        {
          model_id: 'openai:gpt-4o',
          provider: 'openai',
          model_name: 'gpt-4o',
          display_name: 'GPT-4o',
          is_enabled: true,
          is_best: false,
          is_current: true,
          is_disabled: false,
          elo_rating: 1550.0,
          total_comparisons: 100,
          wins: 60,
        },
        {
          model_id: 'anthropic:claude-3-sonnet',
          provider: 'anthropic',
          model_name: 'claude-3-sonnet',
          display_name: 'Claude 3 Sonnet',
          is_enabled: true,
          is_best: true,
          is_current: false,
          is_disabled: false,
          elo_rating: 1520.0,
          total_comparisons: 100,
          wins: 45,
        },
      ],
    };

    it('should fetch available models successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await getAvailableModels();

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/model-comparison/models'),
        expect.objectContaining({ method: 'GET' })
      );
    });

    it('should throw error when not authenticated', async () => {
      localStorageMock.getItem.mockReturnValue(null);

      await expect(getAvailableModels()).rejects.toThrow('Non autenticato');
    });
  });

  describe('updateModelPreferences', () => {
    const validRequest: ModelPreferencesRequest = {
      enabled_model_ids: ['openai:gpt-4o', 'anthropic:claude-3-sonnet'],
    };

    it('should update preferences successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ message: 'Preferenze aggiornate con successo' }),
      });

      const result = await updateModelPreferences(validRequest);

      expect(result.message).toBe('Preferenze aggiornate con successo');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/model-comparison/models/preferences'),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(validRequest),
        })
      );
    });

    it('should throw error when less than 2 models are selected', async () => {
      const invalidRequest: ModelPreferencesRequest = {
        enabled_model_ids: ['openai:gpt-4o'],
      };

      await expect(updateModelPreferences(invalidRequest)).rejects.toThrow(
        'Seleziona almeno 2 modelli'
      );
    });

    it('should throw error when enabled_model_ids is empty', async () => {
      const invalidRequest: ModelPreferencesRequest = {
        enabled_model_ids: [],
      };

      await expect(updateModelPreferences(invalidRequest)).rejects.toThrow(
        'Seleziona almeno 2 modelli'
      );
    });
  });

  describe('getUserStats', () => {
    const mockResponse: ComparisonStatsResponse = {
      stats: {
        total_comparisons: 50,
        total_votes: 45,
        comparisons_this_week: 10,
        votes_this_week: 8,
        favorite_model: 'openai:gpt-4o',
        favorite_model_vote_count: 20,
      },
    };

    it('should fetch user stats successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await getUserStats();

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/model-comparison/stats'),
        expect.objectContaining({ method: 'GET' })
      );
    });
  });

  describe('getLeaderboard', () => {
    const mockResponse: LeaderboardResponse = {
      rankings: [
        {
          rank: 1,
          model_id: 'openai:gpt-4o',
          provider: 'openai',
          model_name: 'gpt-4o',
          display_name: 'GPT-4o',
          elo_rating: 1600.0,
          total_comparisons: 200,
          wins: 130,
          win_rate: 0.65,
        },
        {
          rank: 2,
          model_id: 'anthropic:claude-3-sonnet',
          provider: 'anthropic',
          model_name: 'claude-3-sonnet',
          display_name: 'Claude 3 Sonnet',
          elo_rating: 1550.0,
          total_comparisons: 200,
          wins: 100,
          win_rate: 0.5,
        },
      ],
      last_updated: '2026-02-06T12:00:00Z',
    };

    it('should fetch leaderboard successfully (no auth required)', async () => {
      localStorageMock.getItem.mockReturnValue(null); // No token

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await getLeaderboard();

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/model-comparison/leaderboard'),
        expect.not.objectContaining({
          headers: expect.objectContaining({
            Authorization: expect.any(String),
          }),
        })
      );
    });

    it('should respect limit parameter', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      await getLeaderboard(50);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('limit=50'),
        expect.any(Object)
      );
    });

    it('should cap limit at 100', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      await getLeaderboard(200);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('limit=100'),
        expect.any(Object)
      );
    });
  });

  describe('makeRequest 204 handling', () => {
    it('should handle 204 No Content response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      // updateModelPreferences returns {} on success, so 204 handling is tested properly
      const result = await updateModelPreferences({
        enabled_model_ids: ['openai:gpt-4o', 'anthropic:claude-3-sonnet'],
      });

      expect(result).toEqual({});
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
        json: async () => ({ models: [] }),
      });

      await getAvailableModels();

      const callHeaders = mockFetch.mock.calls[0][1].headers as Headers;
      expect(callHeaders.get('Authorization')).toBe('Bearer session-token');
    });

    it('should fallback to access_token when session token not available', async () => {
      localStorageMock.getItem.mockImplementation((key: string) => {
        if (key === 'current_session_token') return null;
        if (key === 'access_token') return 'access-token';
        return null;
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ models: [] }),
      });

      await getAvailableModels();

      const callHeaders = mockFetch.mock.calls[0][1].headers as Headers;
      expect(callHeaders.get('Authorization')).toBe('Bearer access-token');
    });
  });
});
