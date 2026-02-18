/**
 * Tests for Auth Events Module
 *
 * Tests the typed event emitter for authentication state changes.
 */

import { authEvents } from '../auth-events';

describe('AuthEventEmitter', () => {
  // Clean up after each test
  afterEach(() => {
    authEvents.clear();
  });

  describe('on() - Subscribe to events', () => {
    it('should subscribe to login events', () => {
      const listener = jest.fn();
      authEvents.on('login', listener);

      authEvents.emit('login', { email: 'test@example.com' });

      expect(listener).toHaveBeenCalledWith({ email: 'test@example.com' });
      expect(listener).toHaveBeenCalledTimes(1);
    });

    it('should subscribe to logout events', () => {
      const listener = jest.fn();
      authEvents.on('logout', listener);

      authEvents.emit('logout', { reason: 'manual' });

      expect(listener).toHaveBeenCalledWith({ reason: 'manual' });
    });

    it('should subscribe to session-expired events', () => {
      const listener = jest.fn();
      authEvents.on('session-expired', listener);

      authEvents.emit('session-expired', {
        attemptedRefresh: true,
        originalError: new Error('Token invalid'),
      });

      expect(listener).toHaveBeenCalledWith({
        attemptedRefresh: true,
        originalError: expect.any(Error),
      });
    });

    it('should subscribe to token-refreshed events', () => {
      const listener = jest.fn();
      authEvents.on('token-refreshed', listener);

      authEvents.emit('token-refreshed', { expiresAt: '2025-12-31T23:59:59Z' });

      expect(listener).toHaveBeenCalledWith({
        expiresAt: '2025-12-31T23:59:59Z',
      });
    });

    it('should allow multiple listeners for the same event', () => {
      const listener1 = jest.fn();
      const listener2 = jest.fn();
      const listener3 = jest.fn();

      authEvents.on('login', listener1);
      authEvents.on('login', listener2);
      authEvents.on('login', listener3);

      authEvents.emit('login', { email: 'test@example.com' });

      expect(listener1).toHaveBeenCalledTimes(1);
      expect(listener2).toHaveBeenCalledTimes(1);
      expect(listener3).toHaveBeenCalledTimes(1);
    });

    it('should return an unsubscribe function', () => {
      const listener = jest.fn();
      const unsubscribe = authEvents.on('login', listener);

      // First emit should trigger listener
      authEvents.emit('login', { email: 'test@example.com' });
      expect(listener).toHaveBeenCalledTimes(1);

      // Unsubscribe
      unsubscribe();

      // Second emit should not trigger listener
      authEvents.emit('login', { email: 'test2@example.com' });
      expect(listener).toHaveBeenCalledTimes(1);
    });
  });

  describe('emit() - Emit events', () => {
    it('should not throw when emitting with no listeners', () => {
      expect(() => {
        authEvents.emit('login', { email: 'test@example.com' });
      }).not.toThrow();
    });

    it('should handle listener errors gracefully', () => {
      const errorListener = jest.fn().mockImplementation(() => {
        throw new Error('Listener error');
      });
      const normalListener = jest.fn();
      const consoleError = jest
        .spyOn(console, 'error')
        .mockImplementation(() => {});

      authEvents.on('login', errorListener);
      authEvents.on('login', normalListener);

      // Should not throw
      expect(() => {
        authEvents.emit('login', { email: 'test@example.com' });
      }).not.toThrow();

      // Error listener should have been called
      expect(errorListener).toHaveBeenCalled();

      // Normal listener should still be called
      expect(normalListener).toHaveBeenCalled();

      // Error should be logged
      expect(consoleError).toHaveBeenCalled();

      consoleError.mockRestore();
    });

    it('should emit events with correct payload types', () => {
      const loginListener = jest.fn();
      const logoutListener = jest.fn();

      authEvents.on('login', loginListener);
      authEvents.on('logout', logoutListener);

      authEvents.emit('login', { email: 'user@test.com' });
      authEvents.emit('logout', { reason: 'session-expired' });

      expect(loginListener).toHaveBeenCalledWith({ email: 'user@test.com' });
      expect(logoutListener).toHaveBeenCalledWith({
        reason: 'session-expired',
      });
    });
  });

  describe('off() - Remove listeners for an event', () => {
    it('should remove all listeners for a specific event', () => {
      const loginListener = jest.fn();
      const logoutListener = jest.fn();

      authEvents.on('login', loginListener);
      authEvents.on('logout', logoutListener);

      authEvents.off('login');

      authEvents.emit('login', { email: 'test@example.com' });
      authEvents.emit('logout', { reason: 'manual' });

      expect(loginListener).not.toHaveBeenCalled();
      expect(logoutListener).toHaveBeenCalled();
    });

    it('should not throw when removing non-existent event listeners', () => {
      expect(() => {
        authEvents.off('login');
      }).not.toThrow();
    });
  });

  describe('clear() - Remove all listeners', () => {
    it('should remove all listeners for all events', () => {
      const loginListener = jest.fn();
      const logoutListener = jest.fn();
      const expiredListener = jest.fn();

      authEvents.on('login', loginListener);
      authEvents.on('logout', logoutListener);
      authEvents.on('session-expired', expiredListener);

      authEvents.clear();

      authEvents.emit('login', { email: 'test@example.com' });
      authEvents.emit('logout', { reason: 'manual' });
      authEvents.emit('session-expired', { attemptedRefresh: false });

      expect(loginListener).not.toHaveBeenCalled();
      expect(logoutListener).not.toHaveBeenCalled();
      expect(expiredListener).not.toHaveBeenCalled();
    });
  });

  describe('listenerCount() - Get listener count', () => {
    it('should return 0 for events with no listeners', () => {
      expect(authEvents.listenerCount('login')).toBe(0);
    });

    it('should return correct count for events with listeners', () => {
      authEvents.on('login', jest.fn());
      authEvents.on('login', jest.fn());
      authEvents.on('logout', jest.fn());

      expect(authEvents.listenerCount('login')).toBe(2);
      expect(authEvents.listenerCount('logout')).toBe(1);
      expect(authEvents.listenerCount('session-expired')).toBe(0);
    });

    it('should update count after unsubscribe', () => {
      const unsubscribe1 = authEvents.on('login', jest.fn());
      authEvents.on('login', jest.fn());

      expect(authEvents.listenerCount('login')).toBe(2);

      unsubscribe1();

      expect(authEvents.listenerCount('login')).toBe(1);
    });
  });

  describe('Integration scenarios', () => {
    it('should handle full auth flow: login -> token-refresh -> logout', () => {
      const events: string[] = [];

      authEvents.on('login', () => events.push('login'));
      authEvents.on('token-refreshed', () => events.push('token-refreshed'));
      authEvents.on('logout', () => events.push('logout'));

      // Simulate auth flow
      authEvents.emit('login', { email: 'user@test.com' });
      authEvents.emit('token-refreshed', { expiresAt: '2025-12-31' });
      authEvents.emit('logout', { reason: 'manual' });

      expect(events).toEqual(['login', 'token-refreshed', 'logout']);
    });

    it('should handle session expiry flow: session-expired -> logout', () => {
      const events: string[] = [];

      authEvents.on('session-expired', () => events.push('session-expired'));
      authEvents.on('logout', () => events.push('logout'));

      // Simulate session expiry
      authEvents.emit('session-expired', {
        attemptedRefresh: true,
        originalError: new Error('Refresh failed'),
      });
      authEvents.emit('logout', { reason: 'session-expired' });

      expect(events).toEqual(['session-expired', 'logout']);
    });
  });
});
