'use client';

/**
 * AuthContext - Global Authentication State Provider
 *
 * Provides authentication state management for the application.
 * Subscribes to auth events from ApiClient and updates state accordingly.
 *
 * Features:
 * - Tracks authentication state (isAuthenticated, isLoading)
 * - Provides logout function
 * - Listens to auth events (login, logout, session-expired)
 * - Handles automatic redirect on session expiry (via callback)
 *
 * Usage:
 * ```tsx
 * // In layout or providers
 * <AuthProvider onSessionExpired={() => router.push('/signin')}>
 *   <App />
 * </AuthProvider>
 *
 * // In components
 * const { isAuthenticated, logout } = useAuth();
 * ```
 *
 * @module AuthContext
 */

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  type ReactNode,
} from 'react';
import { apiClient, authEvents } from '@/lib/api';

// Auth context value type
export interface AuthContextValue {
  /** Whether the user is currently authenticated */
  isAuthenticated: boolean;
  /** Whether auth state is being determined (initial load) */
  isLoading: boolean;
  /** Current user's studio_id (null if not yet loaded or no studio) */
  studioId: string | null;
  /** Current user's user_id (null if not yet loaded) */
  userId: number | null;
  /** Logout the current user */
  logout: () => Promise<void>;
}

// Create context with undefined default (will be provided by AuthProvider)
const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// Provider props
export interface AuthProviderProps {
  children: ReactNode;
  /** Callback when session expires (e.g., for redirect to signin) */
  onSessionExpired?: () => void;
}

/**
 * AuthProvider - Wraps the app to provide authentication context
 *
 * Subscribes to auth events and updates state accordingly.
 * Initial auth state is determined from ApiClient.isAuthenticated().
 */
export function AuthProvider({
  children,
  onSessionExpired,
}: AuthProviderProps) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [studioId, setStudioId] = useState<string | null>(null);
  const [userId, setUserId] = useState<number | null>(null);

  // Check initial auth state on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const authenticated = apiClient.isAuthenticated();
        setIsAuthenticated(authenticated);
        // Load stored profile data
        if (authenticated && typeof window !== 'undefined') {
          let currentStudioId = localStorage.getItem('studio_id');
          const storedUserId = localStorage.getItem('user_id');
          setUserId(storedUserId ? parseInt(storedUserId, 10) : null);

          // If studio_id is missing, fetch profile from backend
          // (triggers auto-provisioning and populates localStorage)
          if (!currentStudioId) {
            await apiClient.fetchUserProfile();
            currentStudioId = localStorage.getItem('studio_id');
          }
          setStudioId(currentStudioId);
        }
      } catch (error) {
        console.error(
          '[AuthContext] Error checking initial auth state:',
          error
        );
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  // Subscribe to auth events
  useEffect(() => {
    // Handle login events
    const unsubLogin = authEvents.on('login', () => {
      console.log('[AuthContext] Login event received');
      setIsAuthenticated(true);
      // Reload profile data from localStorage (set by fetchUserProfile)
      if (typeof window !== 'undefined') {
        setStudioId(localStorage.getItem('studio_id'));
        const storedUserId = localStorage.getItem('user_id');
        setUserId(storedUserId ? parseInt(storedUserId, 10) : null);
      }
    });

    // Handle logout events
    const unsubLogout = authEvents.on('logout', payload => {
      console.log('[AuthContext] Logout event received:', payload);
      setIsAuthenticated(false);
      setStudioId(null);
      setUserId(null);
    });

    // Handle session expired events
    const unsubSessionExpired = authEvents.on('session-expired', payload => {
      console.log('[AuthContext] Session expired event received:', payload);
      setIsAuthenticated(false);
      setStudioId(null);
      setUserId(null);

      // Call the onSessionExpired callback if provided
      if (onSessionExpired) {
        onSessionExpired();
      }
    });

    // Cleanup subscriptions on unmount
    return () => {
      unsubLogin();
      unsubLogout();
      unsubSessionExpired();
    };
  }, [onSessionExpired]);

  // Logout function
  const logout = useCallback(async () => {
    try {
      await apiClient.logout();
      // Note: The logout event will be emitted by apiClient.logout()
      // which will update isAuthenticated via the event listener
    } catch (error) {
      console.error('[AuthContext] Logout error:', error);
      // Even on error, the apiClient.logout() clears tokens and emits logout event
    }
  }, []);

  // Memoize context value to prevent unnecessary re-renders
  const contextValue = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated,
      isLoading,
      studioId,
      userId,
      logout,
    }),
    [isAuthenticated, isLoading, studioId, userId, logout]
  );

  return (
    <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
  );
}

/**
 * useAuthContext - Access the auth context value
 *
 * @throws Error if used outside of AuthProvider
 * @returns AuthContextValue
 */
export function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }

  return context;
}

// Export context for testing
export { AuthContext };
