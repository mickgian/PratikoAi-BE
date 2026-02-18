import type { Message, SessionResponse } from '@/lib/api';

export const mockMessages: Message[] = [
  { role: 'user', content: 'What is the forfettario regime?' },
  {
    role: 'assistant',
    content:
      '### 1. Definition\n\nThe forfettario regime is a simplified tax regime for small businesses and professionals in Italy. It allows determining taxable income in a flat-rate manner by applying a profitability coefficient to revenues or fees received, without the need to maintain complex accounting.',
  },
];

export const mockSessionResponse: SessionResponse = {
  session_id: 'test-session-123',
  name: 'Test Chat Session',
  token: {
    access_token: 'test-session-token-abc',
    token_type: 'bearer',
    expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
  },
  created_at: new Date().toISOString(),
};

export const mockSessions: SessionResponse[] = [
  {
    session_id: 'session-1',
    name: 'Previous Chat 1',
    token: {
      access_token: 'token-1',
      token_type: 'bearer',
      expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
    },
    created_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    session_id: 'session-2',
    name: 'Previous Chat 2',
    token: {
      access_token: 'token-2',
      token_type: 'bearer',
      expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
    },
    created_at: new Date(Date.now() - 172800000).toISOString(),
  },
];

export const mockStreamingChunks = [
  { content: '###', done: false },
  { content: ' 1.', done: false },
  { content: ' Definition', done: false },
  { content: '\n\nThe', done: false },
  { content: ' forfettario', done: false },
  { content: ' regime', done: false },
  { content: ' is', done: false },
  { content: ' a', done: false },
  { content: ' simplified', done: false },
  { content: ' tax', done: false },
  { content: ' system', done: false },
  { content: '.', done: true },
];

export const mockAuthResponse = {
  access_token: 'mock-access-token',
  refresh_token: 'mock-refresh-token',
  token_type: 'bearer',
  expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
};

export const mockUserResponse = {
  id: 1,
  email: 'test@example.com',
  ...mockAuthResponse,
};
