/**
 * Next.js Middleware for Route Protection
 *
 * Protects authenticated routes by checking for auth status cookie.
 * Runs on Edge Runtime - cannot access localStorage, uses cookies instead.
 *
 * The auth status cookie (pratikoai_auth) is set by ApiClient when user logs in
 * and cleared when user logs out.
 *
 * Protected routes:
 * - /chat/* - Chat interface
 * - /profile/* - User profile
 * - /settings/* - User settings
 *
 * Public routes (always accessible):
 * - / - Landing page
 * - /signin - Sign in page
 * - /signup - Sign up page
 * - /api/* - API routes
 * - /_next/* - Next.js internals
 * - /favicon.ico, /robots.txt, etc.
 *
 * @module middleware
 */

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that require authentication
const PROTECTED_ROUTES = ['/chat', '/expert', '/account'];

// Routes that are always public
const PUBLIC_ROUTES = ['/', '/signin', '/signup'];

/**
 * Validates that a return URL is internal (prevents open redirect attacks)
 *
 * @param url - The URL to validate
 * @returns true if the URL is safe to use as a redirect target
 */
function isValidReturnUrl(url: string): boolean {
  // Must be a relative path starting with /
  // Must NOT contain protocol, double slashes, or external domains
  if (!url.startsWith('/')) return false;
  if (url.startsWith('//')) return false;
  if (url.includes(':')) return false;
  if (url.includes('\\')) return false;

  // Decode and re-check to prevent encoded attacks
  try {
    const decoded = decodeURIComponent(url);
    if (!decoded.startsWith('/')) return false;
    if (decoded.startsWith('//')) return false;
    if (decoded.includes(':')) return false;
  } catch {
    return false;
  }

  return true;
}

/**
 * Check if the current path is a protected route
 */
function isProtectedRoute(pathname: string): boolean {
  return PROTECTED_ROUTES.some(
    route => pathname === route || pathname.startsWith(`${route}/`)
  );
}

/**
 * Check if the current path is a public route
 * Note: Currently not used since we only check protected routes,
 * but kept for potential future use (e.g., redirecting authenticated users from signin)
 */
function _isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.includes(pathname);
}

/**
 * Check if the user has an auth cookie (indicates logged in state)
 */
function hasAuthCookie(request: NextRequest): boolean {
  const authCookie = request.cookies.get('pratikoai_auth');
  return authCookie?.value === '1';
}

export function middleware(request: NextRequest) {
  // Rewrite www.pratiko.app (production placeholder) to /placeholder page
  const host = request.headers.get('host') || '';
  if (host.startsWith('www.pratiko.app') || host === 'pratiko.app') {
    const url = request.nextUrl.clone();
    url.pathname = '/placeholder';
    return NextResponse.rewrite(url);
  }

  const { pathname } = request.nextUrl;

  // Skip middleware for API routes, static files, and Next.js internals
  if (
    pathname.startsWith('/api/') ||
    pathname.startsWith('/_next/') ||
    pathname.includes('.') // Static files like .ico, .png, etc.
  ) {
    return NextResponse.next();
  }

  // Check if route is protected
  if (isProtectedRoute(pathname)) {
    // Check for auth cookie
    if (!hasAuthCookie(request)) {
      // Build redirect URL using nextUrl.clone() to preserve the real host/protocol
      // behind a reverse proxy (avoids redirecting to localhost:3000)
      const signinUrl = request.nextUrl.clone();
      signinUrl.pathname = '/signin';
      signinUrl.search = '';

      // Add return URL if valid
      if (isValidReturnUrl(pathname)) {
        signinUrl.searchParams.set('returnUrl', pathname);
      }

      console.log(
        `[Middleware] Redirecting unauthenticated user from ${pathname} to ${signinUrl.pathname}`
      );

      return NextResponse.redirect(signinUrl);
    }
  }

  // Allow authenticated users on public auth pages to continue
  // (they can still access signin/signup if they want)

  return NextResponse.next();
}

// Configure which paths the middleware should run on
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder files
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
