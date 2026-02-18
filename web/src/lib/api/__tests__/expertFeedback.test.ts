// src/lib/api/__tests__/expertFeedback.test.ts
import {
  submitFeedback,
  getFeedbackHistory,
  getFeedbackById,
  getExpertProfile,
  isUserSuperUser,
  isUserExpert,
} from '../expertFeedback';
import type {
  SubmitFeedbackRequest,
  SubmitFeedbackResponse,
  FeedbackHistoryItem,
  ExpertProfile,
} from '@/types/expertFeedback';

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
  warn: jest.spyOn(console, 'warn').mockImplementation(),
};

describe('expertFeedback API', () => {
  const mockToken = 'test-token-123';

  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(mockToken);
  });

  afterAll(() => {
    consoleSpy.log.mockRestore();
    consoleSpy.error.mockRestore();
    consoleSpy.warn.mockRestore();
  });

  describe('submitFeedback', () => {
    const validRequest: SubmitFeedbackRequest = {
      query_id: 'query-123',
      feedback_type: 'correct',
      query_text: 'Test question',
      original_answer: 'Test answer',
      confidence_score: 0.9,
      time_spent_seconds: 120,
    };

    const mockResponse: SubmitFeedbackResponse = {
      id: 1,
      message: 'Feedback submitted successfully',
      feedback_type: 'correct',
    };

    it('should submit feedback successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockResponse,
      });

      const result = await submitFeedback(validRequest);

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/expert-feedback/submit'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(validRequest),
        })
      );
    });

    it('should throw error when not authenticated', async () => {
      localStorageMock.getItem.mockReturnValue(null);

      await expect(submitFeedback(validRequest)).rejects.toThrow(
        'Non autenticato'
      );
    });

    it('should throw error when query_id is missing', async () => {
      const invalidRequest = { ...validRequest, query_id: '' };

      await expect(submitFeedback(invalidRequest)).rejects.toThrow(
        'query_id e feedback_type sono richiesti'
      );
    });

    it('should throw error when feedback_type is missing', async () => {
      const invalidRequest = {
        ...validRequest,
        feedback_type: '' as 'correct',
      };

      await expect(submitFeedback(invalidRequest)).rejects.toThrow(
        'query_id e feedback_type sono richiesti'
      );
    });

    it('should throw error when query_text is missing', async () => {
      const invalidRequest = { ...validRequest, query_text: '' };

      await expect(submitFeedback(invalidRequest)).rejects.toThrow(
        'query_text e original_answer sono richiesti'
      );
    });

    it('should throw error when original_answer is missing', async () => {
      const invalidRequest = { ...validRequest, original_answer: '' };

      await expect(submitFeedback(invalidRequest)).rejects.toThrow(
        'query_text e original_answer sono richiesti'
      );
    });

    it('should throw error when confidence_score is out of range', async () => {
      const invalidRequest = { ...validRequest, confidence_score: 1.5 };

      await expect(submitFeedback(invalidRequest)).rejects.toThrow(
        'confidence_score deve essere un numero tra 0 e 1'
      );
    });

    it('should throw error when confidence_score is negative', async () => {
      const invalidRequest = { ...validRequest, confidence_score: -0.5 };

      await expect(submitFeedback(invalidRequest)).rejects.toThrow(
        'confidence_score deve essere un numero tra 0 e 1'
      );
    });

    it('should throw error when time_spent_seconds is zero or negative', async () => {
      const invalidRequest = { ...validRequest, time_spent_seconds: 0 };

      await expect(submitFeedback(invalidRequest)).rejects.toThrow(
        'time_spent_seconds deve essere maggiore di 0'
      );
    });

    it('should throw error when incomplete feedback lacks additional_details', async () => {
      const invalidRequest: SubmitFeedbackRequest = {
        ...validRequest,
        feedback_type: 'incomplete',
        additional_details: '',
      };

      await expect(submitFeedback(invalidRequest)).rejects.toThrow(
        'dettagli aggiuntivi sono obbligatori'
      );
    });

    it('should throw error when incorrect feedback lacks additional_details', async () => {
      const invalidRequest: SubmitFeedbackRequest = {
        ...validRequest,
        feedback_type: 'incorrect',
        additional_details: '   ', // whitespace only
      };

      await expect(submitFeedback(invalidRequest)).rejects.toThrow(
        'dettagli aggiuntivi sono obbligatori'
      );
    });

    it('should handle HTTP error responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ detail: 'Invalid feedback data' }),
      });

      await expect(submitFeedback(validRequest)).rejects.toThrow(
        'Invalid feedback data'
      );
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

      await expect(submitFeedback(validRequest)).rejects.toThrow(
        'Impossibile connettersi al server'
      );
    });
  });

  describe('getFeedbackHistory', () => {
    const mockHistory: FeedbackHistoryItem[] = [
      {
        id: 1,
        query_id: 'query-1',
        feedback_type: 'correct',
        query_text: 'Question 1',
        original_answer: 'Answer 1',
        confidence_score: 0.9,
        created_at: '2025-01-01T00:00:00Z',
        status: 'accepted',
      },
      {
        id: 2,
        query_id: 'query-2',
        feedback_type: 'incomplete',
        query_text: 'Question 2',
        original_answer: 'Answer 2',
        confidence_score: 0.7,
        created_at: '2025-01-02T00:00:00Z',
        status: 'pending',
      },
    ];

    it('should fetch feedback history successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockHistory,
      });

      const result = await getFeedbackHistory();

      expect(result).toEqual(mockHistory);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/expert-feedback/history'),
        expect.objectContaining({ method: 'GET' })
      );
    });

    it('should throw error when not authenticated', async () => {
      localStorageMock.getItem.mockReturnValue(null);

      await expect(getFeedbackHistory()).rejects.toThrow('Non autenticato');
    });
  });

  describe('getFeedbackById', () => {
    const mockFeedback: SubmitFeedbackResponse = {
      id: 1,
      message: 'Feedback details',
      feedback_type: 'correct',
    };

    it('should fetch feedback by ID successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockFeedback,
      });

      const result = await getFeedbackById('feedback-123');

      expect(result).toEqual(mockFeedback);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/expert-feedback/feedback-123'),
        expect.objectContaining({ method: 'GET' })
      );
    });
  });

  describe('getExpertProfile', () => {
    const mockProfile: ExpertProfile = {
      user_id: 1,
      email: 'expert@test.com',
      role: 'super_user',
      total_feedbacks: 50,
      accepted_feedbacks: 45,
      trust_score: 0.9,
    };

    it('should fetch expert profile successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockProfile,
      });

      const result = await getExpertProfile();

      expect(result).toEqual(mockProfile);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/expert-feedback/experts/me/profile'),
        expect.objectContaining({ method: 'GET' })
      );
    });
  });

  describe('isUserSuperUser', () => {
    it('should return true for super_user role', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ role: 'super_user' }),
      });

      const result = await isUserSuperUser();

      expect(result).toBe(true);
    });

    it('should return true for admin role', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ role: 'admin' }),
      });

      const result = await isUserSuperUser();

      expect(result).toBe(true);
    });

    it('should return false for regular_user role', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ role: 'regular_user' }),
      });

      const result = await isUserSuperUser();

      expect(result).toBe(false);
    });

    it('should return false on API error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await isUserSuperUser();

      expect(result).toBe(false);
    });
  });

  describe('isUserExpert (deprecated)', () => {
    it('should call isUserSuperUser and show deprecation warning', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ role: 'super_user' }),
      });

      const result = await isUserExpert();

      expect(result).toBe(true);
      expect(consoleSpy.warn).toHaveBeenCalledWith(
        expect.stringContaining('deprecated')
      );
    });
  });

  describe('makeRequest 204 handling', () => {
    it('should handle 204 No Content response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      // Call any function that uses makeRequest
      const result = await getFeedbackHistory();

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
        json: async () => ({ role: 'super_user' }),
      });

      await isUserSuperUser();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );

      // Check that the correct token was used (session token)
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
        json: async () => ({ role: 'super_user' }),
      });

      await isUserSuperUser();

      const callHeaders = mockFetch.mock.calls[0][1].headers as Headers;
      expect(callHeaders.get('Authorization')).toBe('Bearer access-token');
    });
  });
});
