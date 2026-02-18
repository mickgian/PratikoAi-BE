'use client';

/**
 * Providers - Root provider wrapper for the application
 *
 * Wraps the application with all necessary context providers.
 * Currently includes AuthProvider for authentication state management.
 *
 * @module providers
 */

import { type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { AuthProvider } from '@/contexts/AuthContext';

interface ProvidersProps {
  children: ReactNode;
}

/**
 * Providers - Wraps the app with all context providers
 *
 * Handles:
 * - AuthProvider with session expiry redirect
 */
export function Providers({ children }: ProvidersProps) {
  const router = useRouter();

  // Handle session expiry by redirecting to signin
  const handleSessionExpired = () => {
    console.log('[Providers] Session expired, redirecting to signin...');

    // Get current path for return URL
    const currentPath =
      typeof window !== 'undefined' ? window.location.pathname : '/';

    // Only add returnUrl if not already on signin or public pages
    const publicPaths = ['/', '/signin', '/signup'];
    const returnUrl = publicPaths.includes(currentPath) ? '' : currentPath;

    // Build redirect URL
    const redirectUrl = returnUrl
      ? `/signin?returnUrl=${encodeURIComponent(returnUrl)}`
      : '/signin';

    router.push(redirectUrl);
  };

  return (
    <AuthProvider onSessionExpired={handleSessionExpired}>
      {children}
    </AuthProvider>
  );
}
