/**
 * @file Simplified Chat Storage Hook Tests
 * @description Simplified test suite focusing on core functionality
 * Following TDD principles with practical mocking
 */

import { describe, expect, it } from '@jest/globals';
import {
  convertBackendToFrontend,
  convertFrontendToBackendImport,
} from '../useChatStorageV2.utils';
import type { ChatMessage } from '@/lib/api/chat-history';
import type { Message } from '../../types/chat';

describe('useChatStorageV2 Utility Functions', () => {
  describe('convertBackendToFrontend', () => {
    it('should convert backend ChatMessage to frontend Message pair', () => {
      // Arrange
      const backendMessage: ChatMessage = {
        id: 'msg-1',
        query: 'What is IVA?',
        response: 'IVA is Italian VAT',
        timestamp: '2025-11-29T10:00:00Z',
        model_used: 'gpt-4',
        tokens_used: 100,
        cost_cents: 5,
        response_cached: false,
        response_time_ms: 500,
        kb_sources_metadata: null,
      };

      // Act
      const result = convertBackendToFrontend(backendMessage);

      // Assert
      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({
        id: 'msg-1-user',
        type: 'user',
        content: 'What is IVA?',
        timestamp: '2025-11-29T10:00:00Z',
      });
      expect(result[1]).toEqual({
        id: 'msg-1-assistant',
        type: 'ai',
        content: 'IVA is Italian VAT',
        timestamp: '2025-11-29T10:00:00Z',
        metadata: {
          model_used: 'gpt-4',
          tokens_used: 100,
          cost_cents: 5,
          response_cached: false,
          response_time_ms: 500,
        },
      });
    });

    it('should handle null metadata fields', () => {
      // Arrange
      const backendMessage: ChatMessage = {
        id: 'msg-2',
        query: 'Test query',
        response: 'Test response',
        timestamp: '2025-11-29T11:00:00Z',
        model_used: null,
        tokens_used: null,
        cost_cents: null,
        response_cached: false,
        response_time_ms: null,
        kb_sources_metadata: null,
      };

      // Act
      const result = convertBackendToFrontend(backendMessage);

      // Assert
      expect(result).toHaveLength(2);
      expect(result[1].metadata).toEqual({
        model_used: null,
        tokens_used: null,
        cost_cents: null,
        response_cached: false,
        response_time_ms: null,
      });
    });
  });

  describe('convertFrontendToBackendImport', () => {
    it('should convert frontend Messages to backend import format', () => {
      // Arrange
      const frontendMessages: Message[] = [
        {
          id: 'msg-1-user',
          type: 'user',
          content: 'Query 1',
          timestamp: '2025-11-29T10:00:00Z',
        },
        {
          id: 'msg-1-ai',
          type: 'ai',
          content: 'Response 1',
          timestamp: '2025-11-29T10:01:00Z',
        },
        {
          id: 'msg-2-user',
          type: 'user',
          content: 'Query 2',
          timestamp: '2025-11-29T10:05:00Z',
        },
        {
          id: 'msg-2-ai',
          type: 'ai',
          content: 'Response 2',
          timestamp: '2025-11-29T10:06:00Z',
        },
      ];

      const sessionId = 'session-123';

      // Act
      const result = convertFrontendToBackendImport(
        frontendMessages,
        sessionId
      );

      // Assert
      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({
        session_id: 'session-123',
        query: 'Query 1',
        response: 'Response 1',
        timestamp: '2025-11-29T10:00:00Z',
      });
      expect(result[1]).toEqual({
        session_id: 'session-123',
        query: 'Query 2',
        response: 'Response 2',
        timestamp: '2025-11-29T10:05:00Z',
      });
    });

    it('should handle empty array', () => {
      // Arrange
      const frontendMessages: Message[] = [];
      const sessionId = 'session-456';

      // Act
      const result = convertFrontendToBackendImport(
        frontendMessages,
        sessionId
      );

      // Assert
      expect(result).toHaveLength(0);
    });

    it('should skip unpaired messages', () => {
      // Arrange - Only user message, no AI response
      const frontendMessages: Message[] = [
        {
          id: 'msg-1-user',
          type: 'user',
          content: 'Orphan query',
          timestamp: '2025-11-29T10:00:00Z',
        },
      ];

      const sessionId = 'session-789';

      // Act
      const result = convertFrontendToBackendImport(
        frontendMessages,
        sessionId
      );

      // Assert
      expect(result).toHaveLength(0);
    });

    it('should handle system messages as user messages', () => {
      // Arrange
      const frontendMessages: Message[] = [
        {
          id: 'msg-1-system',
          type: 'system',
          content: 'System prompt',
          timestamp: '2025-11-29T10:00:00Z',
        },
        {
          id: 'msg-1-ai',
          type: 'ai',
          content: 'AI response',
          timestamp: '2025-11-29T10:01:00Z',
        },
      ];

      const sessionId = 'session-sys';

      // Act
      const result = convertFrontendToBackendImport(
        frontendMessages,
        sessionId
      );

      // Assert
      expect(result).toHaveLength(1);
      expect(result[0].query).toBe('System prompt');
    });
  });
});
