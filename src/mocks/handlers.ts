import { http, HttpResponse } from 'msw';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const handlers = [
  // Auth endpoints
  http.post(`${API_BASE_URL}/api/v1/auth/login`, () => {
    return HttpResponse.json({
      access_token: 'mock_access_token',
      refresh_token: 'mock_refresh_token',
      token_type: 'bearer',
      expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(), // 24h from now
    });
  }),

  http.post(`${API_BASE_URL}/api/v1/auth/register`, () => {
    return HttpResponse.json({
      id: 1,
      email: 'test@example.com',
      access_token: 'mock_access_token',
      refresh_token: 'mock_refresh_token',
      token_type: 'bearer',
      expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
    });
  }),

  http.post(`${API_BASE_URL}/api/v1/auth/refresh`, () => {
    return HttpResponse.json({
      access_token: 'new_mock_access_token',
      refresh_token: 'new_mock_refresh_token',
      token_type: 'bearer',
      expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
    });
  }),

  // Session management
  http.post(`${API_BASE_URL}/api/v1/auth/session`, () => {
    return HttpResponse.json({
      session_id: 'mock_session_id',
      name: 'New Chat Session',
      token: {
        access_token: 'mock_session_token',
        token_type: 'bearer',
        expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      },
      created_at: new Date().toISOString(),
    });
  }),

  http.get(`${API_BASE_URL}/api/v1/auth/sessions`, () => {
    return HttpResponse.json([
      {
        session_id: 'session_1',
        name: 'Previous Chat 1',
        token: {
          access_token: 'mock_session_token_1',
          token_type: 'bearer',
          expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
        },
        created_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
      },
      {
        session_id: 'session_2',
        name: 'Previous Chat 2',
        token: {
          access_token: 'mock_session_token_2',
          token_type: 'bearer',
          expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
        },
        created_at: new Date(Date.now() - 172800000).toISOString(), // 2 days ago
      },
    ]);
  }),

  http.patch(`${API_BASE_URL}/api/v1/auth/session/:sessionId/name`, () => {
    return HttpResponse.json({
      session_id: 'mock_session_id',
      name: 'Updated Chat Session',
      token: {
        access_token: 'mock_session_token',
        token_type: 'bearer',
        expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      },
    });
  }),

  http.delete(`${API_BASE_URL}/api/v1/auth/session/:sessionId`, () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // Chat endpoints
  http.post(`${API_BASE_URL}/api/v1/chatbot/chat`, () => {
    return HttpResponse.json({
      messages: [
        { role: 'user', content: 'Test question' },
        {
          role: 'assistant',
          content: 'Mock AI response for testing purposes.',
        },
      ],
      metadata: {
        model_used: 'mock-model',
        provider: 'test',
        strategy: 'mock',
      },
    });
  }),

  http.get(`${API_BASE_URL}/api/v1/chatbot/messages`, () => {
    return HttpResponse.json({
      messages: [
        { role: 'user', content: 'Previous question' },
        { role: 'assistant', content: 'Previous AI response' },
      ],
    });
  }),

  // Streaming endpoint - returns a ReadableStream
  http.post(`${API_BASE_URL}/api/v1/chatbot/chat/stream`, () => {
    const encoder = new TextEncoder();

    const stream = new ReadableStream({
      start(controller) {
        // Simulate streaming chunks
        const chunks = [
          'Mock',
          ' streaming',
          ' response',
          ' for',
          ' testing',
          ' purposes.',
        ];

        let index = 0;
        const interval = setInterval(() => {
          if (index < chunks.length) {
            controller.enqueue(encoder.encode(chunks[index]));
            index++;
          } else {
            controller.close();
            clearInterval(interval);
          }
        }, 100); // 100ms delay between chunks
      },
    });

    return new HttpResponse(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
    });
  }),
];
