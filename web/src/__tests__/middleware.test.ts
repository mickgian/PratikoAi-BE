/**
 * Tests for Route Protection Middleware
 *
 * Tests authentication middleware for protected routes.
 * Uses mocked NextRequest/NextResponse since actual Edge Runtime APIs
 * are not available in Jest.
 */

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { middleware } from '../middleware';

// Mock NextResponse
const mockNext = jest.fn(() => ({ type: 'next' }));
const mockRedirect = jest.fn((url: URL) => ({
  type: 'redirect',
  url: url.toString(),
}));
const mockRewrite = jest.fn((url: URL) => ({
  type: 'rewrite',
  url: url.toString(),
}));

jest.mock('next/server', () => ({
  NextResponse: {
    next: () => mockNext(),
    redirect: (url: URL) => mockRedirect(url),
    rewrite: (url: URL) => mockRewrite(url),
  },
}));

/**
 * Create a URL with clone() to simulate NextURL behaviour
 */
function createCloneableUrl(base: string): URL & { clone: () => URL } {
  const url = new URL(base) as URL & { clone: () => URL };
  url.clone = () => createCloneableUrl(url.toString());
  return url;
}

/**
 * Create a mock NextRequest object
 */
function createMockRequest(
  path: string,
  options: {
    cookies?: Record<string, string>;
    origin?: string;
  } = {}
): NextRequest {
  const origin = options.origin ?? 'http://localhost:3000';
  const nextUrl = createCloneableUrl(`${origin}${path}`);

  const hostHeader = new URL(`${origin}`).host;

  return {
    nextUrl,
    url: nextUrl.toString(),
    headers: {
      get: (name: string) => (name === 'host' ? hostHeader : null),
    },
    cookies: {
      get: (name: string) => {
        const value = options.cookies?.[name];
        return value !== undefined ? { name, value } : undefined;
      },
      getAll: () =>
        Object.entries(options.cookies || {}).map(([name, value]) => ({
          name,
          value,
        })),
      has: (name: string) => name in (options.cookies || {}),
      set: jest.fn(),
      delete: jest.fn(),
      clear: jest.fn(),
    },
  } as unknown as NextRequest;
}

describe('middleware', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Protected routes', () => {
    it('should redirect unauthenticated users from /chat to /signin', () => {
      const request = createMockRequest('/chat');

      middleware(request);

      expect(mockRedirect).toHaveBeenCalled();
      const redirectUrl = mockRedirect.mock.calls[0][0];
      expect(redirectUrl.pathname).toBe('/signin');
      expect(redirectUrl.searchParams.get('returnUrl')).toBe('/chat');
    });

    it('should redirect unauthenticated users from /chat/123 to /signin', () => {
      const request = createMockRequest('/chat/123');

      middleware(request);

      expect(mockRedirect).toHaveBeenCalled();
      const redirectUrl = mockRedirect.mock.calls[0][0];
      expect(redirectUrl.pathname).toBe('/signin');
      expect(redirectUrl.searchParams.get('returnUrl')).toBe('/chat/123');
    });

    it('should allow authenticated users to access /chat', () => {
      const request = createMockRequest('/chat', {
        cookies: { pratikoai_auth: '1' },
      });

      middleware(request);

      expect(mockNext).toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should allow authenticated users to access /chat/123', () => {
      const request = createMockRequest('/chat/123', {
        cookies: { pratikoai_auth: '1' },
      });

      middleware(request);

      expect(mockNext).toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });
  });

  describe('Public routes', () => {
    it('should allow unauthenticated users to access /', () => {
      const request = createMockRequest('/');

      middleware(request);

      expect(mockNext).toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should allow unauthenticated users to access /signin', () => {
      const request = createMockRequest('/signin');

      middleware(request);

      expect(mockNext).toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should allow unauthenticated users to access /signup', () => {
      const request = createMockRequest('/signup');

      middleware(request);

      expect(mockNext).toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should allow authenticated users to access public routes', () => {
      const request = createMockRequest('/signin', {
        cookies: { pratikoai_auth: '1' },
      });

      middleware(request);

      expect(mockNext).toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });
  });

  describe('API routes and static files', () => {
    it('should skip middleware for API routes', () => {
      const request = createMockRequest('/api/v1/auth/login');

      middleware(request);

      expect(mockNext).toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should skip middleware for _next routes', () => {
      const request = createMockRequest('/_next/static/chunks/main.js');

      middleware(request);

      expect(mockNext).toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });

    it('should skip middleware for static files', () => {
      const request = createMockRequest('/favicon.ico');

      middleware(request);

      expect(mockNext).toHaveBeenCalled();
      expect(mockRedirect).not.toHaveBeenCalled();
    });
  });

  describe('Cookie validation', () => {
    it('should reject invalid auth cookie values', () => {
      const request = createMockRequest('/chat', {
        cookies: { pratikoai_auth: 'invalid' },
      });

      middleware(request);

      expect(mockRedirect).toHaveBeenCalled();
    });

    it('should reject empty auth cookie values', () => {
      const request = createMockRequest('/chat', {
        cookies: { pratikoai_auth: '' },
      });

      middleware(request);

      expect(mockRedirect).toHaveBeenCalled();
    });

    it('should reject missing auth cookie', () => {
      const request = createMockRequest('/chat', {
        cookies: {},
      });

      middleware(request);

      expect(mockRedirect).toHaveBeenCalled();
    });
  });

  describe('Reverse proxy (QA/Production)', () => {
    it('should redirect to the external host, not localhost, behind a reverse proxy', () => {
      // Simulate a request arriving through Caddy reverse proxy where
      // nextUrl reflects the real origin (trustHostHeader: true)
      const request = createMockRequest('/chat', {
        origin: 'https://app-qa.pratiko.app',
      });

      middleware(request);

      expect(mockRedirect).toHaveBeenCalled();
      const redirectUrl = mockRedirect.mock.calls[0][0];
      expect(redirectUrl.toString()).toContain('https://app-qa.pratiko.app');
      expect(redirectUrl.toString()).not.toContain('localhost');
      expect(redirectUrl.pathname).toBe('/signin');
      expect(redirectUrl.searchParams.get('returnUrl')).toBe('/chat');
    });
  });

  describe('returnUrl security', () => {
    it('should include valid returnUrl in redirect', () => {
      const request = createMockRequest('/chat');

      middleware(request);

      const redirectUrl = mockRedirect.mock.calls[0][0];
      expect(redirectUrl.searchParams.get('returnUrl')).toBe('/chat');
    });

    it('should include deep path in returnUrl', () => {
      const request = createMockRequest('/chat/session/abc123');

      middleware(request);

      const redirectUrl = mockRedirect.mock.calls[0][0];
      expect(redirectUrl.searchParams.get('returnUrl')).toBe(
        '/chat/session/abc123'
      );
    });
  });

  describe('Placeholder rewrite (www.pratiko.app)', () => {
    it('should rewrite www.pratiko.app to /placeholder', () => {
      const request = createMockRequest('/', {
        origin: 'https://www.pratiko.app',
      });

      middleware(request);

      expect(mockRewrite).toHaveBeenCalled();
      const rewriteUrl = mockRewrite.mock.calls[0][0];
      expect(rewriteUrl.pathname).toBe('/placeholder');
    });

    it('should rewrite pratiko.app (bare domain) to /placeholder', () => {
      const request = createMockRequest('/any-path', {
        origin: 'https://pratiko.app',
      });

      middleware(request);

      expect(mockRewrite).toHaveBeenCalled();
      const rewriteUrl = mockRewrite.mock.calls[0][0];
      expect(rewriteUrl.pathname).toBe('/placeholder');
    });

    it('should NOT rewrite app-qa.pratiko.app', () => {
      const request = createMockRequest('/', {
        origin: 'https://app-qa.pratiko.app',
      });

      middleware(request);

      expect(mockRewrite).not.toHaveBeenCalled();
      expect(mockNext).toHaveBeenCalled();
    });
  });
});
