/**
 * StreamingHandler Tests
 * Tests public API, state management, and stream lifecycle
 */
import { StreamingHandler } from '../StreamingHandler';
import apiClient from '@/lib/api';

// Mock the logger
jest.mock('@/utils/logger', () => ({
  logger: {
    logStreamingStart: jest.fn(),
    logStreamingError: jest.fn(),
    startPerformanceTimer: jest.fn(() => 'perf-id'),
    endPerformanceTimer: jest.fn(),
    warn: jest.fn(),
    info: jest.fn(),
    debug: jest.fn(),
    error: jest.fn(),
  },
}));

// Mock apiClient
jest.mock('@/lib/api', () => ({
  __esModule: true,
  default: {
    sendChatMessageStreaming: jest.fn(),
  },
}));

describe('StreamingHandler', () => {
  let handler: StreamingHandler;
  let dispatchMock: jest.Mock;
  const mockApiUrl = 'http://localhost:8000';
  const mockToken = 'test-token-123';

  beforeEach(() => {
    dispatchMock = jest.fn();
    handler = new StreamingHandler({
      dispatch: dispatchMock,
      apiUrl: mockApiUrl,
      getSessionToken: () => mockToken,
    });

    // Reset mocks
    jest.clearAllMocks();
  });

  afterEach(async () => {
    await handler.cancelStreaming();
  });

  describe('State Management', () => {
    it('should start inactive', () => {
      expect(handler.isStreaming()).toBe(false);
      const status = handler.getStatus();
      expect(status.isActive).toBe(false);
      expect(status.streamId).toBeNull();
    });

    it('should become active when streaming starts', async () => {
      const mockSendChatMessageStreaming =
        apiClient.sendChatMessageStreaming as jest.Mock;

      // Mock a successful streaming response
      mockSendChatMessageStreaming.mockImplementation(
        async (messages: any, onChunk: any, onDone: any) => {
          // Simulate immediate completion
          setTimeout(() => onDone(), 10);
        }
      );

      const messageId = 'test-msg-123';
      const messages = [{ role: 'user' as const, content: 'test' }];

      const promise = handler.startStreaming(messageId, messages);

      // Should be active during streaming
      expect(handler.isStreaming()).toBe(true);

      await promise;
    });

    it('should track current stream ID', async () => {
      const mockSendChatMessageStreaming =
        apiClient.sendChatMessageStreaming as jest.Mock;

      mockSendChatMessageStreaming.mockImplementation(
        async (messages: any, onChunk: any, onDone: any) => {
          setTimeout(() => onDone(), 10);
        }
      );

      const messageId = 'test-msg-456';
      const messages = [{ role: 'user' as const, content: 'test' }];

      await handler.startStreaming(messageId, messages);

      const status = handler.getStatus();
      expect(status.streamId).toBe(messageId);
    });
  });

  describe('Chunk Processing', () => {
    it('should dispatch UPDATE_STREAMING_CONTENT for each chunk', async () => {
      const mockSendChatMessageStreaming =
        apiClient.sendChatMessageStreaming as jest.Mock;

      mockSendChatMessageStreaming.mockImplementation(
        async (messages: any, onChunk: any, onDone: any) => {
          // Simulate 3 chunks
          onChunk({ content: 'chunk1', done: false });
          onChunk({ content: 'chunk2', done: false });
          onChunk({ content: 'chunk3', done: false });
          setTimeout(() => onDone({ done: true }), 10);
        }
      );

      const messageId = 'test-msg-123';
      const messages = [{ role: 'user' as const, content: 'test' }];

      await handler.startStreaming(messageId, messages);

      // Should have dispatched UPDATE_STREAMING_CONTENT for each chunk
      const updates = dispatchMock.mock.calls.filter(
        call => call[0]?.type === 'UPDATE_STREAMING_CONTENT'
      );
      expect(updates.length).toBe(3);
      expect(updates[0][0].payload.content).toBe('chunk1');
      expect(updates[1][0].payload.content).toBe('chunk2');
      expect(updates[2][0].payload.content).toBe('chunk3');
    });

    it('should handle 30 chunks sequentially', async () => {
      const mockSendChatMessageStreaming =
        apiClient.sendChatMessageStreaming as jest.Mock;

      mockSendChatMessageStreaming.mockImplementation(
        async (messages: any, onChunk: any, onDone: any) => {
          // Simulate 30 chunks
          for (let i = 0; i < 30; i++) {
            onChunk({ content: `chunk${i}`, done: false });
          }
          setTimeout(() => onDone({ done: true }), 10);
        }
      );

      const messageId = 'test-msg-123';
      const messages = [{ role: 'user' as const, content: 'test' }];

      await handler.startStreaming(messageId, messages);

      const updates = dispatchMock.mock.calls.filter(
        call => call[0]?.type === 'UPDATE_STREAMING_CONTENT'
      );
      expect(updates.length).toBe(30);
    });

    it('should ignore empty content chunks', async () => {
      const mockSendChatMessageStreaming =
        apiClient.sendChatMessageStreaming as jest.Mock;

      mockSendChatMessageStreaming.mockImplementation(
        async (messages: any, onChunk: any, onDone: any) => {
          onChunk({ content: '', done: false });
          onChunk({ content: 'real content', done: false });
          onChunk({ content: '', done: false });
          setTimeout(() => onDone({ done: true }), 10);
        }
      );

      const messageId = 'test-msg-123';
      const messages = [{ role: 'user' as const, content: 'test' }];

      await handler.startStreaming(messageId, messages);

      const updates = dispatchMock.mock.calls.filter(
        call => call[0]?.type === 'UPDATE_STREAMING_CONTENT'
      );
      // Should only have 1 update for the real content
      expect(updates.length).toBe(1);
      expect(updates[0][0].payload.content).toBe('real content');
    });
  });

  describe('Stream Completion', () => {
    it('should dispatch COMPLETE_STREAMING on done frame', async () => {
      const mockSendChatMessageStreaming =
        apiClient.sendChatMessageStreaming as jest.Mock;

      mockSendChatMessageStreaming.mockImplementation(
        async (messages: any, onChunk: any, onDone: any) => {
          onChunk({ content: 'test', done: false });
          onChunk({ done: true });
          setTimeout(() => onDone(), 10);
        }
      );

      const messageId = 'test-msg-123';
      const messages = [{ role: 'user' as const, content: 'test' }];

      await handler.startStreaming(messageId, messages);

      const completes = dispatchMock.mock.calls.filter(
        call => call[0]?.type === 'COMPLETE_STREAMING'
      );
      expect(completes.length).toBeGreaterThanOrEqual(1);
    });

    it('should complete only once even with multiple done frames', async () => {
      const mockSendChatMessageStreaming =
        apiClient.sendChatMessageStreaming as jest.Mock;

      mockSendChatMessageStreaming.mockImplementation(
        async (messages: any, onChunk: any, onDone: any) => {
          onChunk({ done: true });
          onChunk({ done: true }); // Duplicate done
          setTimeout(() => onDone({ done: true }), 10);
        }
      );

      const messageId = 'test-msg-123';
      const messages = [{ role: 'user' as const, content: 'test' }];

      await handler.startStreaming(messageId, messages);

      const completes = dispatchMock.mock.calls.filter(
        call => call[0]?.type === 'COMPLETE_STREAMING'
      );
      // Should only complete once despite multiple done frames
      expect(completes.length).toBe(1);
    });

    it('should become inactive after completion', async () => {
      const mockSendChatMessageStreaming =
        apiClient.sendChatMessageStreaming as jest.Mock;

      mockSendChatMessageStreaming.mockImplementation(
        async (messages: any, onChunk: any, onDone: any) => {
          onChunk({ done: true });
          setTimeout(() => onDone(), 10);
        }
      );

      const messageId = 'test-msg-123';
      const messages = [{ role: 'user' as const, content: 'test' }];

      await handler.startStreaming(messageId, messages);

      // Wait a bit for async cleanup
      await new Promise(resolve => setTimeout(resolve, 50));

      expect(handler.isStreaming()).toBe(false);
    });
  });

  describe('Cancellation', () => {
    it('should cleanup on cancel', async () => {
      const mockSendChatMessageStreaming =
        apiClient.sendChatMessageStreaming as jest.Mock;

      mockSendChatMessageStreaming.mockImplementation(
        async (messages: any, onChunk: any, _onDone: any) => {
          // Simulate a long-running stream
          onChunk({ content: 'test', done: false });
          // Keep stream open
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      );

      const messageId = 'test-msg-123';
      const messages = [{ role: 'user' as const, content: 'test' }];

      const streamPromise = handler.startStreaming(messageId, messages);

      // Wait for stream to actually start
      await new Promise(resolve => setTimeout(resolve, 50));

      // Cancel while active
      expect(handler.isStreaming()).toBe(true);
      await handler.cancelStreaming();

      // Wait for cleanup to complete
      await new Promise(resolve => setTimeout(resolve, 50));

      expect(handler.isStreaming()).toBe(false);

      // Wait for any pending promises to settle
      await Promise.race([
        streamPromise,
        new Promise(resolve => setTimeout(resolve, 200)),
      ]);
    });
  });

  describe('Error Handling', () => {
    it('should handle stream errors gracefully', async () => {
      const mockSendChatMessageStreaming =
        apiClient.sendChatMessageStreaming as jest.Mock;

      mockSendChatMessageStreaming.mockRejectedValue(
        new Error('Network error')
      );

      const messageId = 'test-msg-123';
      const messages = [{ role: 'user' as const, content: 'test' }];

      const result = await handler.startStreaming(messageId, messages);

      expect(result).toBe(false);
      expect(handler.isStreaming()).toBe(false);

      const status = handler.getStatus();
      expect(status.hasError).toBe(true);
    });
  });
});
