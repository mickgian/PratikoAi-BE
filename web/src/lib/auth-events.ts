/**
 * Auth Events Module
 *
 * Provides a typed event emitter for authentication state changes.
 * Used by ApiClient to notify subscribers (e.g., AuthContext) of auth events.
 *
 * Events:
 * - login: User successfully logged in
 * - logout: User logged out (manual or automatic)
 * - session-expired: Token refresh failed, user needs to re-authenticate
 * - token-refreshed: Access token was successfully refreshed
 *
 * @module auth-events
 */

// Event types
export type AuthEventType =
  | 'login'
  | 'logout'
  | 'session-expired'
  | 'token-refreshed';

// Event payload types
export interface LoginEventPayload {
  email?: string;
}

export interface LogoutEventPayload {
  reason?: 'manual' | 'session-expired' | 'token-invalid';
}

export interface SessionExpiredEventPayload {
  originalError?: Error;
  attemptedRefresh: boolean;
}

export interface TokenRefreshedEventPayload {
  expiresAt?: string;
}

// Map event types to their payloads
export interface AuthEventPayloadMap {
  login: LoginEventPayload;
  logout: LogoutEventPayload;
  'session-expired': SessionExpiredEventPayload;
  'token-refreshed': TokenRefreshedEventPayload;
}

// Listener type
export type AuthEventListener<T extends AuthEventType> = (
  payload: AuthEventPayloadMap[T]
) => void;

/**
 * Typed Auth Event Emitter
 *
 * Singleton pattern ensures all auth state changes are coordinated
 * through a single event bus.
 */
class AuthEventEmitter {
  private listeners: Map<AuthEventType, Set<AuthEventListener<any>>> =
    new Map();

  /**
   * Subscribe to an auth event
   *
   * @param event - The event type to listen for
   * @param listener - Callback function to invoke when event is emitted
   * @returns Unsubscribe function
   */
  on<T extends AuthEventType>(
    event: T,
    listener: AuthEventListener<T>
  ): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }

    this.listeners.get(event)!.add(listener);

    // Return unsubscribe function
    return () => {
      this.listeners.get(event)?.delete(listener);
    };
  }

  /**
   * Emit an auth event
   *
   * @param event - The event type to emit
   * @param payload - Event-specific data
   */
  emit<T extends AuthEventType>(event: T, payload: AuthEventPayloadMap[T]) {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.forEach(listener => {
        try {
          listener(payload);
        } catch (error) {
          console.error(`[AuthEvents] Error in ${event} listener:`, error);
        }
      });
    }
  }

  /**
   * Remove all listeners for a specific event
   *
   * @param event - The event type to clear listeners for
   */
  off(event: AuthEventType) {
    this.listeners.delete(event);
  }

  /**
   * Remove all listeners
   */
  clear() {
    this.listeners.clear();
  }

  /**
   * Get the count of listeners for a specific event (useful for testing)
   */
  listenerCount(event: AuthEventType): number {
    return this.listeners.get(event)?.size ?? 0;
  }
}

// Export singleton instance
export const authEvents = new AuthEventEmitter();

// Export default for convenience
export default authEvents;
