/**
 * SSE Parser Unit Tests
 * Tests the SSE event parsing logic in api.ts
 */
import { apiClient } from '../api';

describe('SSE Parser', () => {
  let mockFetch: jest.Mock;

  beforeEach(() => {
    mockFetch = jest.fn();
    global.fetch = mockFetch;

    // Mock ensureSession to avoid actual API calls
    jest.spyOn(apiClient as any, 'ensureSession').mockResolvedValue(undefined);
    (apiClient as any).currentSessionToken = 'mock-token';
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('should parse keepalive comments and ignore them', async () => {
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(': keepalive\n\n'));
        controller.enqueue(new TextEncoder().encode('data: {"done":true}\n\n'));
        controller.close();
      },
    });

    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
      headers: new Headers({ 'content-type': 'text/event-stream' }),
    });

    const chunks: any[] = [];
    await apiClient.sendChatMessageStreaming(
      [{ role: 'user', content: 'test' }],
      chunk => chunks.push(chunk),
      () => {},
      () => {}
    );

    // Keepalive should be ignored, filter out done chunks - no content chunks forwarded
    const contentChunks = chunks.filter(c => c.content !== undefined);
    expect(contentChunks).toHaveLength(0);
  });

  it('should parse complete SSE data events', async () => {
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode('data: {"content":"hello","done":false}\n\n')
        );
        controller.enqueue(
          new TextEncoder().encode('data: {"content":"world","done":false}\n\n')
        );
        controller.enqueue(new TextEncoder().encode('data: {"done":true}\n\n'));
        controller.close();
      },
    });

    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
      headers: new Headers(),
    });

    const chunks: any[] = [];
    let doneCount = 0;

    await apiClient.sendChatMessageStreaming(
      [{ role: 'user', content: 'test' }],
      chunk => chunks.push(chunk),
      () => doneCount++,
      () => {}
    );

    // Filter out done chunks - only count content chunks
    const contentChunks = chunks.filter(c => c.content !== undefined);
    expect(contentChunks).toHaveLength(2);
    expect(contentChunks[0].content).toBe('hello');
    expect(contentChunks[1].content).toBe('world');
    expect(doneCount).toBe(1);
  });

  it('should handle 30 chunks without dropping any', async () => {
    const stream = new ReadableStream({
      start(controller) {
        // Send 30 data chunks
        for (let i = 0; i < 30; i++) {
          controller.enqueue(
            new TextEncoder().encode(
              `data: {"content":"chunk${i}","done":false}\n\n`
            )
          );
        }
        controller.enqueue(new TextEncoder().encode('data: {"done":true}\n\n'));
        controller.close();
      },
    });

    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
      headers: new Headers(),
    });

    const chunks: any[] = [];
    await apiClient.sendChatMessageStreaming(
      [{ role: 'user', content: 'test' }],
      chunk => chunks.push(chunk),
      () => {},
      () => {}
    );

    // Filter out done chunks - only count content chunks
    const contentChunks = chunks.filter(c => c.content !== undefined);
    expect(contentChunks).toHaveLength(30);
    // Verify all chunks arrived in order
    for (let i = 0; i < 30; i++) {
      expect(contentChunks[i].content).toBe(`chunk${i}`);
    }
  });

  it('should handle incomplete chunks in buffer', async () => {
    const stream = new ReadableStream({
      start(controller) {
        // Simulate incomplete chunk arriving in two parts
        controller.enqueue(new TextEncoder().encode('data: {"conte'));
        controller.enqueue(
          new TextEncoder().encode('nt":"hello","done":false}\n\n')
        );
        controller.enqueue(new TextEncoder().encode('data: {"done":true}\n\n'));
        controller.close();
      },
    });

    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
      headers: new Headers(),
    });

    const chunks: any[] = [];
    await apiClient.sendChatMessageStreaming(
      [{ role: 'user', content: 'test' }],
      chunk => chunks.push(chunk),
      () => {},
      () => {}
    );

    // Filter out done chunks - only count content chunks
    const contentChunks = chunks.filter(c => c.content !== undefined);
    expect(contentChunks).toHaveLength(1);
    expect(contentChunks[0].content).toBe('hello');
  });

  it('should call onDone exactly once when done:true is received', async () => {
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode('data: {"content":"test","done":false}\n\n')
        );
        controller.enqueue(new TextEncoder().encode('data: {"done":true}\n\n'));
        controller.close();
      },
    });

    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
      headers: new Headers(),
    });

    let doneCount = 0;
    await apiClient.sendChatMessageStreaming(
      [{ role: 'user', content: 'test' }],
      () => {},
      () => doneCount++,
      () => {}
    );

    expect(doneCount).toBe(1);
  });

  it('should handle empty content chunks', async () => {
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode('data: {"content":"","done":false}\n\n')
        );
        controller.enqueue(
          new TextEncoder().encode('data: {"content":"real","done":false}\n\n')
        );
        controller.enqueue(new TextEncoder().encode('data: {"done":true}\n\n'));
        controller.close();
      },
    });

    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
      headers: new Headers(),
    });

    const chunks: any[] = [];
    await apiClient.sendChatMessageStreaming(
      [{ role: 'user', content: 'test' }],
      chunk => chunks.push(chunk),
      () => {},
      () => {}
    );

    // Empty chunks should be skipped, filter out done chunks
    const contentChunks = chunks.filter(
      c => c.content !== undefined && c.content !== ''
    );
    expect(contentChunks).toHaveLength(1);
    expect(contentChunks[0].content).toBe('real');
  });

  it('should handle special characters in content', async () => {
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode(
            'data: {"content":"Line1\\nLine2","done":false}\n\n'
          )
        );
        controller.enqueue(
          new TextEncoder().encode(
            'data: {"content":"Quote: \\"test\\"","done":false}\n\n'
          )
        );
        controller.enqueue(
          new TextEncoder().encode(
            'data: {"content":"Unicode: 🚀","done":false}\n\n'
          )
        );
        controller.enqueue(new TextEncoder().encode('data: {"done":true}\n\n'));
        controller.close();
      },
    });

    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
      headers: new Headers(),
    });

    const chunks: any[] = [];
    await apiClient.sendChatMessageStreaming(
      [{ role: 'user', content: 'test' }],
      chunk => chunks.push(chunk),
      () => {},
      () => {}
    );

    // Filter out done chunks - only count content chunks
    const contentChunks = chunks.filter(c => c.content !== undefined);
    expect(contentChunks).toHaveLength(3);
    expect(contentChunks[0].content).toContain('Line1');
    expect(contentChunks[1].content).toContain('Quote');
    expect(contentChunks[2].content).toContain('🚀');
  });

  it('should error on invalid SSE format', async () => {
    const stream = new ReadableStream({
      start(controller) {
        // Send invalid line (not starting with "data:" or ":")
        controller.enqueue(new TextEncoder().encode('invalid line\n\n'));
        controller.close();
      },
    });

    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
      headers: new Headers(),
    });

    let errorReceived = false;
    await apiClient.sendChatMessageStreaming(
      [{ role: 'user', content: 'test' }],
      () => {},
      () => {},
      error => {
        errorReceived = true;
        expect(error).toContain('Invalid SSE format');
      }
    );

    // Should have called onError for invalid format
    expect(errorReceived).toBe(true);
  });

  it('should handle connection errors gracefully', async () => {
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'));

    let errorMessage = '';
    await apiClient.sendChatMessageStreaming(
      [{ role: 'user', content: 'test' }],
      () => {},
      () => {},
      error => {
        errorMessage = error;
      }
    );

    expect(errorMessage).toContain('server');
  });
});
