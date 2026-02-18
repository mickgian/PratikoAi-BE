/**
 * Tests for useAuth Hook
 *
 * Tests the thin wrapper around AuthContext.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { useAuth, type AuthContextValue } from '../useAuth';
import { AuthProvider } from '@/contexts/AuthContext';
import { apiClient, authEvents } from '@/lib/api';

// Mock the API client and auth events
jest.mock('@/lib/api', () => ({
  apiClient: {
    isAuthenticated: jest.fn(),
    logout: jest.fn(),
  },
  authEvents: {
    on: jest.fn(() => jest.fn()), // Return unsubscribe function
  },
}));

// Test component that uses the hook
function TestComponent({
  onRender,
}: {
  onRender?: (value: AuthContextValue) => void;
}) {
  const auth = useAuth();
  onRender?.(auth);
  return (
    <div>
      <span data-testid="is-authenticated">{String(auth.isAuthenticated)}</span>
      <span data-testid="is-loading">{String(auth.isLoading)}</span>
    </div>
  );
}

describe('useAuth', () => {
  const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

  beforeEach(() => {
    jest.clearAllMocks();
    mockApiClient.isAuthenticated.mockReturnValue(false);
    mockApiClient.logout.mockResolvedValue(undefined);
  });

  it('should return auth context value when used within AuthProvider', async () => {
    let authValue: AuthContextValue | undefined;

    render(
      <AuthProvider>
        <TestComponent onRender={value => (authValue = value)} />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });

    expect(authValue).toBeDefined();
    expect(typeof authValue?.isAuthenticated).toBe('boolean');
    expect(typeof authValue?.isLoading).toBe('boolean');
    expect(typeof authValue?.logout).toBe('function');
  });

  it('should throw error when used outside AuthProvider', () => {
    // Suppress console.error for this test
    const consoleError = jest.spyOn(console, 'error').mockImplementation();

    expect(() => {
      render(<TestComponent />);
    }).toThrow('useAuthContext must be used within an AuthProvider');

    consoleError.mockRestore();
  });

  it('should reflect authenticated state from context', async () => {
    mockApiClient.isAuthenticated.mockReturnValue(true);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });

    expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
  });

  it('should reflect non-authenticated state from context', async () => {
    mockApiClient.isAuthenticated.mockReturnValue(false);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });

    expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
  });

  it('should provide logout function from context', async () => {
    let authValue: AuthContextValue | undefined;

    render(
      <AuthProvider>
        <TestComponent onRender={value => (authValue = value)} />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });

    // Call logout
    await authValue?.logout();

    expect(mockApiClient.logout).toHaveBeenCalled();
  });
});
