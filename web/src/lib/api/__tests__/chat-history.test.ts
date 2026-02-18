/**
 * @file Chat History API Client Tests
 * @description Test suite for backend PostgreSQL chat history API integration
 * Following TDD RED-GREEN-REFACTOR cycle
 */

import { describe, expect, it, jest, beforeEach } from '@jest/globals';
import {
  getChatHistory,
  importChatHistory,
  ChatMessage,
  ImportChatHistoryRequest,
  ImportChatHistoryResponse,
} from '../chat-history';

// Mock global fetch
global.fetch = jest.fn() as jest.MockedFunction<typeof fetch>;

describe('Chat History API Client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock localStorage for auth token
    const mockLocalStorage = {
      getItem: jest.fn((key: string) => {
        if (key === 'auth_token') return 'mock-jwt-token';
        return null;
      }),
      setItem: jest.fn(),
      removeItem: jest.fn(),
      clear: jest.fn(),
      length: 0,
      key: jest.fn(),
    };
    Object.defineProperty(window, 'localStorage', {
      value: mockLocalStorage,
      writable: true,
    });
  });

  describe('getChatHistory', () => {
    it('should fetch chat history for a session', async () => {
      // Arrange
      const mockMessages: ChatMessage[] = [
        {
          id: 'msg-1',
          query: 'What is IVA in Italy?',
          response: 'IVA (Imposta sul Valore Aggiunto) is the Italian VAT...',
          timestamp: '2025-11-29T10:00:00Z',
          model_used: 'gpt-4',
          tokens_used: 150,
          cost_cents: 5,
          response_cached: false,
          response_time_ms: 1200,
          kb_sources_metadata: null,
        },
        {
          id: 'msg-2',
          query: 'What is the current IVA rate?',
          response: 'The standard IVA rate in Italy is 22%...',
          timestamp: '2025-11-29T10:05:00Z',
          model_used: 'gpt-4',
          tokens_used: 120,
          cost_cents: 4,
          response_cached: true,
          response_time_ms: 300,
          kb_sources_metadata: null,
        },
      ];

      (global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce(
        {
          ok: true,
          status: 200,
          json: async () => mockMessages,
        } as Response
      );

      // Act
      const result = await getChatHistory('session-123');

      // Assert
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(
          '/api/v1/chatbot/sessions/session-123/messages'
        ),
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            Authorization: 'Bearer mock-jwt-token',
          }),
        })
      );
      expect(result).toEqual(mockMessages);
      expect(result).toHaveLength(2);
    });

    it('should support pagination with limit and offset', async () => {
      // Arrange
      const mockMessages: ChatMessage[] = [
        {
          id: 'msg-3',
          query: 'Test query',
          response: 'Test response',
          timestamp: '2025-11-29T10:10:00Z',
          model_used: null,
          tokens_used: null,
          cost_cents: null,
          response_cached: false,
          response_time_ms: null,
          kb_sources_metadata: null,
        },
      ];

      (global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce(
        {
          ok: true,
          status: 200,
          json: async () => mockMessages,
        } as Response
      );

      // Act
      const result = await getChatHistory('session-456', 10, 20);

      // Assert
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('limit=10&offset=20'),
        expect.any(Object)
      );
      expect(result).toEqual(mockMessages);
    });

    it('should throw error on 401 unauthorized', async () => {
      // Arrange
      (global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce(
        {
          ok: false,
          status: 401,
          statusText: 'Unauthorized',
        } as Response
      );

      // Act & Assert
      await expect(getChatHistory('session-123')).rejects.toThrow(
        'Failed to fetch chat history: 401 Unauthorized'
      );
    });

    it('should throw error on 404 session not found', async () => {
      // Arrange
      (global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce(
        {
          ok: false,
          status: 404,
          statusText: 'Not Found',
        } as Response
      );

      // Act & Assert
      await expect(getChatHistory('nonexistent-session')).rejects.toThrow(
        'Failed to fetch chat history: 404 Not Found'
      );
    });

    it('should throw error on network failure', async () => {
      // Arrange
      (global.fetch as jest.MockedFunction<typeof fetch>).mockRejectedValueOnce(
        new Error('Network error')
      );

      // Act & Assert
      await expect(getChatHistory('session-123')).rejects.toThrow(
        'Network error'
      );
    });
  });

  describe('importChatHistory', () => {
    it('should import chat messages from IndexedDB to backend', async () => {
      // Arrange
      const mockRequest: ImportChatHistoryRequest = {
        messages: [
          {
            session_id: 'session-local-1',
            query: 'Local query 1',
            response: 'Local response 1',
            timestamp: '2025-11-28T15:00:00Z',
          },
          {
            session_id: 'session-local-1',
            query: 'Local query 2',
            response: 'Local response 2',
            timestamp: '2025-11-28T15:05:00Z',
          },
        ],
      };

      const mockResponse: ImportChatHistoryResponse = {
        imported_count: 2,
        skipped_count: 0,
        status: 'success',
        message: 'Successfully imported 2 messages',
      };

      (global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce(
        {
          ok: true,
          status: 200,
          json: async () => mockResponse,
        } as Response
      );

      // Act
      const result = await importChatHistory(mockRequest.messages);

      // Assert
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/chatbot/import-history'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            Authorization: 'Bearer mock-jwt-token',
          }),
          body: JSON.stringify({ messages: mockRequest.messages }),
        })
      );
      expect(result.imported_count).toBe(2);
      expect(result.skipped_count).toBe(0);
      expect(result.status).toBe('success');
    });

    it('should handle partial import (some messages skipped)', async () => {
      // Arrange
      const mockRequest: ImportChatHistoryRequest = {
        messages: [
          {
            session_id: 'session-local-2',
            query: 'Duplicate query',
            response: 'Duplicate response',
            timestamp: '2025-11-28T16:00:00Z',
          },
          {
            session_id: 'session-local-2',
            query: 'New query',
            response: 'New response',
            timestamp: '2025-11-28T16:05:00Z',
          },
        ],
      };

      const mockResponse: ImportChatHistoryResponse = {
        imported_count: 1,
        skipped_count: 1,
        status: 'partial',
        message: 'Imported 1 messages, skipped 1 duplicates',
      };

      (global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce(
        {
          ok: true,
          status: 200,
          json: async () => mockResponse,
        } as Response
      );

      // Act
      const result = await importChatHistory(mockRequest.messages);

      // Assert
      expect(result.imported_count).toBe(1);
      expect(result.skipped_count).toBe(1);
      expect(result.status).toBe('partial');
    });

    it('should throw error when importing with invalid data', async () => {
      // Arrange
      const invalidMessages = [
        {
          session_id: '',
          query: 'Missing session ID',
          response: 'Invalid',
          timestamp: '2025-11-28T17:00:00Z',
        },
      ];

      (global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce(
        {
          ok: false,
          status: 400,
          statusText: 'Bad Request',
        } as Response
      );

      // Act & Assert
      await expect(importChatHistory(invalidMessages)).rejects.toThrow(
        'Failed to import chat history: 400 Bad Request'
      );
    });

    it('should throw error on 401 unauthorized during import', async () => {
      // Arrange
      const mockRequest: ImportChatHistoryRequest = {
        messages: [
          {
            session_id: 'session-test',
            query: 'Test',
            response: 'Test',
            timestamp: '2025-11-28T18:00:00Z',
          },
        ],
      };

      (global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce(
        {
          ok: false,
          status: 401,
          statusText: 'Unauthorized',
        } as Response
      );

      // Act & Assert
      await expect(importChatHistory(mockRequest.messages)).rejects.toThrow(
        'Failed to import chat history: 401 Unauthorized'
      );
    });
  });

  describe('TypeScript Interfaces', () => {
    it('should define ChatMessage interface correctly', () => {
      const message: ChatMessage = {
        id: 'test-id',
        query: 'test query',
        response: 'test response',
        timestamp: '2025-11-29T10:00:00Z',
        model_used: 'gpt-4',
        tokens_used: 100,
        cost_cents: 3,
        response_cached: false,
        response_time_ms: 500,
        kb_sources_metadata: null,
      };

      expect(message.id).toBe('test-id');
      expect(message.query).toBe('test query');
      expect(message.timestamp).toBe('2025-11-29T10:00:00Z');
    });

    it('should allow null values for optional ChatMessage fields', () => {
      const message: ChatMessage = {
        id: 'test-id-2',
        query: 'query',
        response: 'response',
        timestamp: '2025-11-29T10:00:00Z',
        model_used: null,
        tokens_used: null,
        cost_cents: null,
        response_cached: false,
        response_time_ms: null,
        kb_sources_metadata: null,
      };

      expect(message.model_used).toBeNull();
      expect(message.tokens_used).toBeNull();
    });
  });
});
