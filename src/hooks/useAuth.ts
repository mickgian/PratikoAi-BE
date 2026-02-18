/**
 * useAuth Hook
 *
 * Thin wrapper around AuthContext for convenient access to auth state.
 *
 * Usage:
 * ```tsx
 * const { isAuthenticated, isLoading, logout } = useAuth();
 *
 * if (isLoading) return <Spinner />;
 * if (!isAuthenticated) return <Redirect to="/signin" />;
 * ```
 *
 * @module useAuth
 */

import { useAuthContext, type AuthContextValue } from '@/contexts/AuthContext';

/**
 * useAuth - Access authentication state and actions
 *
 * @returns AuthContextValue - { isAuthenticated, isLoading, logout }
 * @throws Error if used outside of AuthProvider
 */
export function useAuth(): AuthContextValue {
  return useAuthContext();
}

// Re-export types for convenience
export type { AuthContextValue } from '@/contexts/AuthContext';
