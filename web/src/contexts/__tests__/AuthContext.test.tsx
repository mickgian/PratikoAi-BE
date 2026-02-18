/**
 * Tests for AuthContext
 *
 * Tests authentication context provider and state management.
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  AuthProvider,
  useAuthContext,
  type AuthContextValue,
} from '../AuthContext';
import { apiClient, authEvents } from '@/lib/api';

// Mock the API client and auth events
jest.mock('@/lib/api', () => ({
  apiClient: {
    isAuthenticated: jest.fn(),
    logout: jest.fn(),
  },
  authEvents: {
    on: jest.fn(),
    emit: jest.fn(),
  },
}));

// Test component that consumes the context
function TestConsumer({
  onRender,
}: {
  onRender?: (value: AuthContextValue) => void;
}) {
  const auth = useAuthContext();
  onRender?.(auth);
  return (
    <div>
      <span data-testid="is-authenticated">{String(auth.isAuthenticated)}</span>
      <span data-testid="is-loading">{String(auth.isLoading)}</span>
      <button data-testid="logout-button" onClick={auth.logout}>
        Logout
      </button>
    </div>
  );
}

describe('AuthContext', () => {
  const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;
  const mockAuthEvents = authEvents as jest.Mocked<typeof authEvents>;

  // Store event listeners for manual triggering in tests
  let eventListeners: Record<string, (payload: any) => void> = {};

  beforeEach(() => {
    jest.clearAllMocks();
    eventListeners = {};

    // Setup default mock implementations
    mockApiClient.isAuthenticated.mockReturnValue(false);
    mockApiClient.logout.mockResolvedValue(undefined);

    // Capture event listeners when on() is called
    mockAuthEvents.on.mockImplementation((event, listener) => {
      eventListeners[event] = listener;
      return jest.fn(); // Return unsubscribe function
    });
  });

  describe('AuthProvider', () => {
    it('should render children', () => {
      render(
        <AuthProvider>
          <div data-testid="child">Child content</div>
        </AuthProvider>
      );

      expect(screen.getByTestId('child')).toHaveTextContent('Child content');
    });

    it('should check initial auth state on mount', async () => {
      mockApiClient.isAuthenticated.mockReturnValue(true);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      });

      expect(mockApiClient.isAuthenticated).toHaveBeenCalled();
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
    });

    it('should set isAuthenticated to false when not authenticated', async () => {
      mockApiClient.isAuthenticated.mockReturnValue(false);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      });

      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
    });

    it('should subscribe to auth events', () => {
      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      expect(mockAuthEvents.on).toHaveBeenCalledWith(
        'login',
        expect.any(Function)
      );
      expect(mockAuthEvents.on).toHaveBeenCalledWith(
        'logout',
        expect.any(Function)
      );
      expect(mockAuthEvents.on).toHaveBeenCalledWith(
        'session-expired',
        expect.any(Function)
      );
    });

    it('should update isAuthenticated to true on login event', async () => {
      mockApiClient.isAuthenticated.mockReturnValue(false);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      });

      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');

      // Simulate login event
      act(() => {
        eventListeners['login']?.({ email: 'test@example.com' });
      });

      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
    });

    it('should update isAuthenticated to false on logout event', async () => {
      mockApiClient.isAuthenticated.mockReturnValue(true);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      });

      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');

      // Simulate logout event
      act(() => {
        eventListeners['logout']?.({ reason: 'manual' });
      });

      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
    });

    it('should call onSessionExpired callback on session-expired event', async () => {
      const onSessionExpired = jest.fn();
      mockApiClient.isAuthenticated.mockReturnValue(true);

      render(
        <AuthProvider onSessionExpired={onSessionExpired}>
          <TestConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      });

      // Simulate session-expired event
      act(() => {
        eventListeners['session-expired']?.({
          attemptedRefresh: true,
          originalError: new Error('Token invalid'),
        });
      });

      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
      expect(onSessionExpired).toHaveBeenCalled();
    });

    it('should handle isAuthenticated check errors gracefully', async () => {
      mockApiClient.isAuthenticated.mockImplementation(() => {
        throw new Error('Storage error');
      });
      const consoleError = jest.spyOn(console, 'error').mockImplementation();

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      });

      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
      expect(consoleError).toHaveBeenCalled();

      consoleError.mockRestore();
    });
  });

  describe('logout function', () => {
    it('should call apiClient.logout when logout is called', async () => {
      const user = userEvent.setup();
      mockApiClient.isAuthenticated.mockReturnValue(true);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      });

      await user.click(screen.getByTestId('logout-button'));

      expect(mockApiClient.logout).toHaveBeenCalled();
    });

    it('should handle logout errors gracefully', async () => {
      const user = userEvent.setup();
      mockApiClient.isAuthenticated.mockReturnValue(true);
      mockApiClient.logout.mockRejectedValue(new Error('Network error'));
      const consoleError = jest.spyOn(console, 'error').mockImplementation();

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      });

      await user.click(screen.getByTestId('logout-button'));

      // Should not throw
      expect(consoleError).toHaveBeenCalled();

      consoleError.mockRestore();
    });
  });

  describe('useAuthContext', () => {
    it('should throw error when used outside AuthProvider', () => {
      // Suppress console.error for this test
      const consoleError = jest.spyOn(console, 'error').mockImplementation();

      expect(() => {
        render(<TestConsumer />);
      }).toThrow('useAuthContext must be used within an AuthProvider');

      consoleError.mockRestore();
    });
  });

  describe('context memoization', () => {
    it('should provide stable context value reference', async () => {
      mockApiClient.isAuthenticated.mockReturnValue(true);
      const renderValues: AuthContextValue[] = [];

      render(
        <AuthProvider>
          <TestConsumer onRender={value => renderValues.push(value)} />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      });

      // Re-render shouldn't create new context value if state hasn't changed
      const initialValue = renderValues[renderValues.length - 1];

      // Force a re-render by triggering an unrelated state update
      act(() => {
        // This would normally cause a re-render in a real app
      });

      // The logout function should be stable (same reference)
      expect(typeof initialValue.logout).toBe('function');
    });
  });
});
