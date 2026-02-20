import { authEvents } from './auth-events';

/**
 * Strip proactivity XML tags from AI content
 * These tags are used internally but should not be displayed to users
 * DEV-242: Fix raw XML tags showing after page refresh
 */
function stripProactivityTags(content: string): string {
  if (!content) return content;
  // Remove <answer>...</answer> tags but keep inner content
  const cleaned = content
    .replace(/<answer>\s*/gi, '')
    .replace(/\s*<\/answer>/gi, '');
  return cleaned.trim();
}

// Interactive question option from backend
export interface InteractiveOption {
  id: string;
  label: string;
  icon?: string;
  leads_to?: string;
  requires_input?: boolean;
}

// Input field for multi-field questions (Claude Code style)
export interface InputField {
  id: string;
  label: string;
  placeholder?: string;
  input_type: 'text' | 'number' | 'currency' | 'date';
  required: boolean;
  validation?: string;
}

// Interactive question from backend (proactivity feature)
// Supports both single_choice/multi_choice and multi_field types
export interface InteractiveQuestion {
  id: string;
  text: string;
  question_type: 'single_choice' | 'multi_choice' | 'multi_field';
  options: InteractiveOption[];
  fields?: InputField[]; // For multi_field questions
  allow_custom_input?: boolean;
  custom_input_placeholder?: string;
  prefilled_params?: Record<string, any>;
}

// Request for /questions/answer endpoint (proactivity feature)
// Supports both single-choice and multi-field question types
export interface QuestionAnswerRequest {
  question_id: string;
  selected_option?: string; // For single/multi_choice questions
  custom_input?: string;
  field_values?: Record<string, string>; // For multi_field questions
  session_id: string;
}

// Response from /questions/answer endpoint (proactivity feature)
export interface QuestionAnswerResponse {
  next_question?: InteractiveQuestion;
  answer?: string;
}

export type SseFrame = {
  content?: string;
  done?: boolean;
  seq?: number;
  sha1?: string;
  stream_id?: string;
  acc_len?: number;
  raw_len?: number;
  // Proactivity SSE event fields
  event_type?: string;
  interactive_question?: InteractiveQuestion;
  // DEV-242: Chain of Thought reasoning
  reasoning?: {
    tema_identificato?: string;
    fonti_utilizzate?: string[];
    elementi_chiave?: string[];
    conclusione?: string;
    confidence_label?: string;
    risk_warning?: string;
  };
  // DEV-242: Structured sources from LLM parsing
  structured_sources?: Array<{
    numero: number;
    data: string;
    ente: string;
    tipo: string;
    riferimento: string;
    url?: string;
  }>;
  // DEV-244: KB source URLs (deterministic, independent of LLM output)
  kb_source_urls?: Array<{
    title: string;
    url: string;
    type: string;
    date?: string; // Optional - may not be available for all sources
  }>;
  // DEV-245: Web verification results from Brave Search
  web_verification?: {
    caveats?: string[];
    has_caveats?: boolean;
    web_sources_checked?: number;
    verification_performed?: boolean;
    brave_ai_summary?: string;
    synthesized_response?: string;
    has_synthesized_response?: boolean;
  };
  // DEV-256: LLM metrics for model comparison feature
  response_time_ms?: number;
  tokens_used?: {
    input: number;
    output: number;
  };
  cost_cents?: number;
  model_used?: string;
  // DEV-256: Enriched prompt for model comparison feature
  enriched_prompt?: string;
  // allow any extra fields
  [k: string]: any;
};

// Types for API requests and responses
export interface RegisterRequest {
  email: string;
  password: string;
}

export interface LoginRequest {
  username: string;
  password: string;
  grant_type?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_at: string;
}

export interface UserResponse {
  id: number;
  email: string;
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_at: string;
}

export interface ApiError {
  detail: string;
}

export interface OAuthLoginResponse {
  authorization_url: string;
}

export interface OAuthUserInfo {
  id: number;
  email: string;
  name?: string;
  avatar_url?: string;
  provider: string;
}

// Attachment info returned from backend for persisted messages
export interface APIAttachmentInfo {
  id: string;
  filename: string;
  type?: string;
}

// DEV-241: Reasoning trace structure from backend
export interface ReasoningTrace {
  tema_identificato?: string;
  fonti_utilizzate?: string[];
  elementi_chiave?: string[];
  conclusione?: string;
}

// Chat-related types matching backend schemas
export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  attachments?: APIAttachmentInfo[];
  // DEV-241: Chain of Thought reasoning trace (assistant messages only)
  reasoning?: ReasoningTrace;
  // DEV-242: Structured sources for citations (assistant messages only)
  // IMPORTANT: This field is required for "Fonti" section to display after page refresh
  structured_sources?: Array<{
    numero: number;
    data: string;
    ente: string;
    tipo: string;
    riferimento: string;
    url?: string;
  }>;
  // DEV-244: KB source URLs for Fonti section (deterministic, independent of LLM output)
  // IMPORTANT: This field is required for Fonti section to display after page refresh
  kb_source_urls?: Array<{
    title: string;
    url: string;
    type: string;
    date?: string;
  }>;
}

export interface ChatRequest {
  messages: Message[];
}

export interface QueryClassificationMetadata {
  domain: string;
  action: string;
  confidence: number;
  sub_domain?: string;
  document_type?: string;
  fallback_used: boolean;
  domain_prompt_used: boolean;
  reasoning?: string;
}

export interface ResponseMetadata {
  model_used: string;
  provider: string;
  strategy: string;
  cost_eur?: number;
  processing_time_ms?: number;
  classification?: QueryClassificationMetadata;
}

export interface ChatResponse {
  messages: Message[];
  metadata?: ResponseMetadata;
}

export interface StreamResponse {
  content: string;
  done: boolean;
}

// Session-related types
export interface SessionResponse {
  session_id: string;
  name: string;
  token: TokenResponse;
  created_at?: string; // Optional for backward compatibility
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
}

class ApiClient {
  private baseUrl: string;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private currentSessionId: string | null = null;
  private currentSessionToken: string | null = null;

  // Refresh lock to prevent concurrent refresh attempts
  private refreshPromise: Promise<boolean> | null = null;

  constructor() {
    // Use environment variable or default to localhost for development
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    // Load tokens from localStorage if available
    if (typeof window !== 'undefined') {
      this.accessToken = localStorage.getItem('access_token');
      this.refreshToken = localStorage.getItem('refresh_token');
      this.currentSessionId = localStorage.getItem('current_session_id');
      this.currentSessionToken = localStorage.getItem('current_session_token');
    }
  }

  /**
   * Make authenticated API request with automatic token refresh
   */
  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const headers = new Headers(options.headers);

    // Add authorization header - prefer session token for chat endpoints only
    // Session management endpoints (/auth/session, /auth/sessions) should use access token (user token)
    const token = endpoint.includes('/chatbot/')
      ? this.currentSessionToken || this.accessToken
      : this.accessToken;

    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      // If unauthorized and we have a refresh token, try to refresh
      if (response.status === 401 && this.refreshToken) {
        const refreshed = await this.refreshAccessToken();
        if (refreshed && this.accessToken) {
          // Retry the original request with new token
          headers.set('Authorization', `Bearer ${this.accessToken}`);
          const retryResponse = await fetch(url, {
            ...options,
            headers,
          });
          return this.handleResponse<T>(retryResponse);
        }
      }

      return this.handleResponse<T>(response);
    } catch (error) {
      // Handle network errors
      if (
        error instanceof TypeError &&
        error.message.includes('Failed to fetch')
      ) {
        throw new Error(
          `Impossibile connettersi al server. Verifica che il backend sia in funzione su ${this.baseUrl}`
        );
      }
      throw error;
    }
  }

  /**
   * Handle API response, throw error if not successful
   */
  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText || 'An unknown error occurred'}`,
      }));
      throw new Error(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      );
    }

    return response.json();
  }

  /**
   * Store authentication tokens
   * Also sets a cookie for middleware route protection (Edge Runtime compatible)
   */
  private storeTokens(accessToken: string, refreshToken: string) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;

    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('refresh_token', refreshToken);

      // Set auth status cookie for middleware (no sensitive data, just presence indicator)
      // SameSite=Lax for security, Path=/ for all routes
      document.cookie =
        'pratikoai_auth=1; path=/; SameSite=Lax; max-age=31536000';
    }
  }

  /**
   * Store session information
   */
  private storeSession(sessionId: string, sessionToken: string) {
    this.currentSessionId = sessionId;
    this.currentSessionToken = sessionToken;

    if (typeof window !== 'undefined') {
      localStorage.setItem('current_session_id', sessionId);
      localStorage.setItem('current_session_token', sessionToken);
    }
  }

  /**
   * Clear authentication tokens
   * Also clears the auth status cookie for middleware
   */
  private clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    this.currentSessionId = null;
    this.currentSessionToken = null;

    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('current_session_id');
      localStorage.removeItem('current_session_token');

      // Clear auth status cookie (set expiry in past)
      document.cookie = 'pratikoai_auth=; path=/; SameSite=Lax; max-age=0';
    }
  }

  /**
   * Register new user with email and password
   */
  async register(data: RegisterRequest): Promise<UserResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      const result = await this.handleResponse<UserResponse>(response);

      // Store tokens after successful registration
      this.storeTokens(result.access_token, result.refresh_token);

      // Emit login event for auth state subscribers
      authEvents.emit('login', { email: data.email });

      return result;
    } catch (error) {
      // Handle network errors
      if (
        error instanceof TypeError &&
        error.message.includes('Failed to fetch')
      ) {
        throw new Error(
          `Impossibile connettersi al server. Verifica che il backend sia in funzione su ${this.baseUrl}`
        );
      }
      throw error;
    }
  }

  /**
   * Login user with email and password
   */
  async login(email: string, password: string): Promise<AuthResponse> {
    try {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);
      formData.append('grant_type', 'password');

      const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
        method: 'POST',
        body: formData,
      });

      const result = await this.handleResponse<AuthResponse>(response);

      // Store tokens after successful login
      this.storeTokens(result.access_token, result.refresh_token);

      // Emit login event for auth state subscribers
      authEvents.emit('login', { email });

      return result;
    } catch (error) {
      // Handle network errors
      if (
        error instanceof TypeError &&
        error.message.includes('Failed to fetch')
      ) {
        throw new Error(
          `Impossibile connettersi al server. Verifica che il backend sia in funzione su ${this.baseUrl}`
        );
      }
      throw error;
    }
  }

  /**
   * Refresh access token using refresh token
   * Uses a lock to prevent concurrent refresh attempts (race condition mitigation)
   */
  async refreshAccessToken(): Promise<boolean> {
    if (!this.refreshToken) {
      return false;
    }

    // If refresh already in progress, wait for it (prevents concurrent 401 race conditions)
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = this._doRefreshToken();

    try {
      return await this.refreshPromise;
    } finally {
      this.refreshPromise = null;
    }
  }

  /**
   * Internal method to perform the actual token refresh
   */
  private async _doRefreshToken(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: this.refreshToken,
        }),
      });

      const result = await this.handleResponse<AuthResponse>(response);
      this.storeTokens(result.access_token, result.refresh_token);

      // Emit token-refreshed event
      authEvents.emit('token-refreshed', { expiresAt: result.expires_at });

      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);

      // Emit session-expired event before clearing tokens
      authEvents.emit('session-expired', {
        attemptedRefresh: true,
        originalError: error instanceof Error ? error : undefined,
      });

      this.clearTokens();

      // Emit logout event with session-expired reason
      authEvents.emit('logout', { reason: 'session-expired' });

      return false;
    }
  }

  /**
   * Logout user
   */
  async logout(): Promise<void> {
    try {
      await this.makeRequest('/api/v1/auth/logout', {
        method: 'POST',
      });
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      this.clearTokens();

      // Emit logout event for auth state subscribers
      authEvents.emit('logout', { reason: 'manual' });
    }
  }

  /**
   * Force clear all tokens and session data (for recovery from corrupted state)
   */
  forceClearTokens(): void {
    console.log('🔄 Force clearing all tokens and session data');
    this.clearTokens();

    // Emit logout event for auth state subscribers
    authEvents.emit('logout', { reason: 'token-invalid' });
  }

  /**
   * Check if user is currently authenticated
   */
  isAuthenticated(): boolean {
    console.log('🔐 [API_DEBUG] Checking authentication...');
    console.log('🔐 [API_DEBUG] Access token exists:', !!this.accessToken);
    console.log(
      '🔐 [API_DEBUG] Access token preview:',
      this.accessToken ? this.accessToken.substring(0, 20) + '...' : 'null'
    );

    // Basic check for token existence and format
    if (!this.accessToken) {
      console.log('❌ [API_DEBUG] No access token found');
      return false;
    }

    // Basic JWT format validation (should have 3 parts separated by dots)
    const tokenParts = this.accessToken.split('.');
    if (tokenParts.length !== 3) {
      console.warn(
        '🔍 [API_DEBUG] Access token appears to be malformed, clearing tokens'
      );
      console.warn(
        '🔍 [API_DEBUG] Token parts count:',
        tokenParts.length,
        'Expected: 3'
      );
      this.clearTokens();
      return false;
    }

    console.log('✅ [API_DEBUG] Authentication check passed');
    return true;
  }

  /**
   * Get current access token
   */
  getAccessToken(): string | null {
    return this.accessToken;
  }

  /**
   * Initiate Google OAuth login - get authorization URL
   */
  async initiateGoogleLogin(): Promise<OAuthLoginResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/google/login`);
      return await this.handleResponse<OAuthLoginResponse>(response);
    } catch (error) {
      if (
        error instanceof TypeError &&
        error.message.includes('Failed to fetch')
      ) {
        throw new Error(
          `Impossibile connettersi al server. Verifica che il backend sia in funzione su ${this.baseUrl}`
        );
      }
      throw error;
    }
  }

  /**
   * Initiate LinkedIn OAuth login - get authorization URL
   */
  async initiateLinkedInLogin(): Promise<OAuthLoginResponse> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/v1/auth/linkedin/login`
      );
      return await this.handleResponse<OAuthLoginResponse>(response);
    } catch (error) {
      if (
        error instanceof TypeError &&
        error.message.includes('Failed to fetch')
      ) {
        throw new Error(
          `Impossibile connettersi al server. Verifica che il backend sia in funzione su ${this.baseUrl}`
        );
      }
      throw error;
    }
  }

  /**
   * Handle OAuth callback (this would be called from the callback page)
   */
  async handleOAuthCallback(
    provider: 'google' | 'linkedin',
    code: string,
    state?: string
  ): Promise<AuthResponse> {
    try {
      const params = new URLSearchParams({ code });
      if (state) params.append('state', state);

      const response = await fetch(
        `${this.baseUrl}/api/v1/auth/${provider}/callback?${params.toString()}`
      );
      const result = await this.handleResponse<AuthResponse>(response);

      // Store tokens after successful OAuth login
      this.storeTokens(result.access_token, result.refresh_token);

      // Emit login event for auth state subscribers (email not available from OAuth response)
      authEvents.emit('login', {});

      return result;
    } catch (error) {
      if (
        error instanceof TypeError &&
        error.message.includes('Failed to fetch')
      ) {
        throw new Error(
          `Impossibile connettersi al server. Verifica che il backend sia in funzione su ${this.baseUrl}`
        );
      }
      throw error;
    }
  }

  /**
   * Open OAuth login popup window and handle the authentication flow
   */
  async loginWithProvider(
    provider: 'google' | 'linkedin'
  ): Promise<AuthResponse> {
    return new Promise(async (resolve, reject) => {
      try {
        // Get the OAuth authorization URL
        const loginResponse =
          provider === 'google'
            ? await this.initiateGoogleLogin()
            : await this.initiateLinkedInLogin();

        // Open popup window for OAuth flow
        const popup = window.open(
          loginResponse.authorization_url,
          `${provider}OAuth`,
          'width=500,height=600,scrollbars=yes,resizable=yes'
        );

        if (!popup) {
          reject(
            new Error(
              'Popup blocked. Please allow popups for OAuth authentication.'
            )
          );
          return;
        }

        // Listen for the OAuth callback
        const checkClosed = setInterval(() => {
          if (popup.closed) {
            clearInterval(checkClosed);
            reject(new Error('OAuth authentication was cancelled.'));
          }
        }, 1000);

        // Listen for messages from the OAuth callback
        const handleMessage = async (event: MessageEvent) => {
          // Verify origin for security
          if (event.origin !== window.location.origin) {
            return;
          }

          if (event.data.type === 'OAUTH_SUCCESS') {
            clearInterval(checkClosed);
            window.removeEventListener('message', handleMessage);
            popup.close();

            try {
              // Handle the OAuth callback with the authorization code
              const result = await this.handleOAuthCallback(
                provider,
                event.data.code,
                event.data.state
              );
              resolve(result);
            } catch (error) {
              reject(error);
            }
          } else if (event.data.type === 'OAUTH_ERROR') {
            clearInterval(checkClosed);
            window.removeEventListener('message', handleMessage);
            popup.close();
            reject(
              new Error(event.data.error || 'OAuth authentication failed.')
            );
          }
        };

        window.addEventListener('message', handleMessage);
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Login with Google OAuth
   */
  async loginWithGoogle(): Promise<AuthResponse> {
    return this.loginWithProvider('google');
  }

  /**
   * Login with LinkedIn OAuth
   */
  async loginWithLinkedIn(): Promise<AuthResponse> {
    return this.loginWithProvider('linkedin');
  }

  // Session management

  /**
   * Create a new chat session
   */
  async createSession(): Promise<SessionResponse> {
    return this.makeRequest<SessionResponse>('/api/v1/auth/session', {
      method: 'POST',
    });
  }

  /**
   * Get all user sessions
   */
  async getUserSessions(): Promise<SessionResponse[]> {
    return this.makeRequest<SessionResponse[]>('/api/v1/auth/sessions');
  }

  /**
   * Update session name
   */
  async updateSessionName(
    sessionId: string,
    name: string,
    sessionToken?: string
  ): Promise<SessionResponse> {
    console.log(
      '✏️ [API_DEBUG] Updating session name:',
      sessionId,
      'to:',
      name
    );
    console.log('✏️ [API_DEBUG] Session token provided:', !!sessionToken);

    // Use provided session token or fall back to current session token
    const tokenToUse =
      sessionToken || this.currentSessionToken || this.accessToken;

    const formData = new FormData();
    formData.append('name', name);

    const response = await fetch(
      `${this.baseUrl}/api/v1/auth/session/${sessionId}/name`,
      {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${tokenToUse}`,
        },
        body: formData,
      }
    );

    return this.handleResponse<SessionResponse>(response);
  }

  /**
   * Delete a session - requires session token
   */
  async deleteSession(sessionId: string, sessionToken?: string): Promise<void> {
    console.log('🗑️ [API_DEBUG] Attempting to delete session:', sessionId);
    console.log(
      '🗑️ [API_DEBUG] Current session info:',
      this.getCurrentSession()
    );
    console.log('🗑️ [API_DEBUG] Session token provided:', !!sessionToken);

    // Use provided session token or fall back to current session token
    const tokenToUse = sessionToken || this.currentSessionToken;

    if (!tokenToUse) {
      throw new Error('No session token available for deletion');
    }

    // Use the appropriate session token for delete operation
    const response = await fetch(
      `${this.baseUrl}/api/v1/auth/session/${sessionId}`,
      {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${tokenToUse}`,
        },
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText}`,
      }));

      console.error('🗑️ [API_DEBUG] Delete session failed:', errorData.detail);

      // If session not found or auth failed, and this is the current session, clear it locally
      if (
        errorData.detail.includes('Session not found') ||
        response.status === 404 ||
        errorData.detail.includes('Invalid authentication') ||
        response.status === 401
      ) {
        if (this.currentSessionId === sessionId) {
          console.log('🗑️ [API_DEBUG] Clearing invalid session locally');
          this.setCurrentSession('', '');
        }
      }

      throw new Error(errorData.detail);
    }
  }

  /**
   * Get current session info
   */
  getCurrentSession(): {
    sessionId: string | null;
    sessionToken: string | null;
  } {
    return {
      sessionId: this.currentSessionId,
      sessionToken: this.currentSessionToken,
    };
  }

  /**
   * Set current session
   */
  setCurrentSession(sessionId: string, sessionToken: string) {
    if (sessionId && sessionToken) {
      this.storeSession(sessionId, sessionToken);
    } else {
      // Clear session if empty values provided
      this.currentSessionId = null;
      this.currentSessionToken = null;
      if (typeof window !== 'undefined') {
        localStorage.removeItem('current_session_id');
        localStorage.removeItem('current_session_token');
      }
    }
  }

  // Chat functionality

  /**
   * Send a chat message using streaming (Server-Sent Events)
   * - Parses SSE lines robustly (handles \n / \r\n, keepalives, partial lines)
   * - Forwards full frames with `content` via onChunk(frame)
   * - Calls onDone(finalFrame?) exactly once when `done:true` is seen or the stream ends
   * - Ignores control/keepalive lines and "[DONE]"
   */
  async sendChatMessageStreaming(
    messages: Message[],
    onChunk: (frame: SseFrame) => void,
    onDone: (finalFrame?: SseFrame) => void,
    onError: (error: string) => void,
    options?: { skip_proactivity?: boolean }
  ): Promise<void> {
    console.log(
      '🚀 [API] sendChatMessageStreaming started with messages:',
      messages
    );

    try {
      await this.ensureSession();
      console.log(
        '✅ [API] Session ensured, token:',
        this.currentSessionToken ? 'present' : 'missing'
      );

      // DEV-007 Issue 6: Extract attachment_ids from last user message and send at top level
      // Backend expects attachment_ids at request body root, not inside messages
      const lastUserMessage = messages.findLast(m => m.role === 'user');
      const attachmentIds = (lastUserMessage as any)?.attachment_ids as
        | string[]
        | undefined;

      const requestBody = {
        messages: messages.map(m => ({ role: m.role, content: m.content })), // Clean messages (remove attachment_ids)
        ...(attachmentIds &&
          attachmentIds.length > 0 && { attachment_ids: attachmentIds }), // Add at top level
        ...(options?.skip_proactivity && { skip_proactivity: true }), // Skip proactivity for follow-up queries
      };

      console.log(
        '📤 [API] Making request to:',
        `${this.baseUrl}/api/v1/chatbot/chat/stream`
      );
      console.log('📤 [API] Request body:', requestBody);
      if (attachmentIds?.length) {
        console.log(
          '📎 [API] Attachments included:',
          attachmentIds.length,
          'file(s)'
        );
      }

      // DEV-257: Include bypass header if admin has dismissed the limit dialog
      const bypassHeaders: Record<string, string> =
        typeof window !== 'undefined' &&
        sessionStorage.getItem('cost_limit_bypass') === 'true'
          ? { 'X-Cost-Limit-Bypass': 'true' }
          : {};

      const response = await fetch(
        `${this.baseUrl}/api/v1/chatbot/chat/stream`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${this.currentSessionToken}`,
            Accept: 'text/event-stream',
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            ...bypassHeaders,
          },
          body: JSON.stringify(requestBody),
        }
      );

      console.log(
        '📥 [API] Response status:',
        response.status,
        response.statusText
      );
      console.log(
        '📥 [API] Response headers:',
        Object.fromEntries(response.headers.entries())
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({
          detail: `HTTP ${response.status}: ${response.statusText}`,
        }));

        // DEV-257: Downgrade expected 429 USAGE_LIMIT_EXCEEDED to warn (not error)
        if (
          response.status === 429 &&
          errorData.error_code === 'USAGE_LIMIT_EXCEEDED'
        ) {
          console.warn('⚠️ [API] Usage limit exceeded (429)');
        } else {
          console.error(
            '❌ [API] Response not ok:',
            response.status,
            response.statusText
          );
          console.error('❌ [API] Error data:', errorData);
        }

        // DEV-257: Handle 429 usage limit errors with structured info
        if (
          response.status === 429 &&
          errorData.error_code === 'USAGE_LIMIT_EXCEEDED'
        ) {
          onError(
            JSON.stringify({
              type: 'USAGE_LIMIT_EXCEEDED',
              message_it:
                errorData.message_it || 'Hai raggiunto il limite di utilizzo',
              limit_info: errorData.limit_info,
              options: errorData.options,
              can_bypass: errorData.can_bypass,
            })
          );
          return;
        }

        onError(errorData.detail);
        return;
      }

      if (!response.body) {
        console.error('❌ [API] No response body for streaming');
        onError('No response body for streaming');
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = '';
      let doneEmitted = false;
      let finalFrameSeen: SseFrame | undefined;
      let chunkCount = 0;

      console.log('🔄 [API] Starting to read stream...');

      try {
        for (;;) {
          const { done, value } = await reader.read();
          if (done) {
            console.log('✅ [API] Stream reading completed');
            break;
          }

          const rawChunk = decoder.decode(value, { stream: true });
          buffer += rawChunk;
          chunkCount++;

          console.log(
            `📦 [API] Chunk ${chunkCount} received (${rawChunk.length} chars):`,
            rawChunk.slice(0, 200) + (rawChunk.length > 200 ? '...' : '')
          );

          // Backend ALWAYS sends proper SSE format: data: {"content":"...", "done":false}\n\n
          // Process buffer by lines to extract complete SSE events
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? ''; // Keep incomplete line in buffer

          console.log(`🔍 [API] Processing ${lines.length} lines from buffer`);

          for (let line of lines) {
            line = line.trim();
            if (!line) {
              console.log('⏭️ [API] Skipping empty line');
              continue;
            }

            console.log('🔍 [API] Processing line:', line);

            // Handle proper SSE format
            if (line.startsWith('data:')) {
              const jsonStr = line.slice(5).trim();
              if (!jsonStr) {
                console.log('⏭️ [API] Skipping empty data field');
                continue;
              }

              console.log('📝 [API] Parsing SSE JSON:', jsonStr);

              // Classic SSE sentinel some libs use
              if (jsonStr === '[DONE]') {
                console.log(
                  '🏁 [API] Received [DONE] sentinel, calling onDone'
                );
                if (!doneEmitted) {
                  doneEmitted = true;
                  onDone();
                }
                continue;
              }

              let frame: SseFrame | null = null;
              try {
                frame = JSON.parse(jsonStr) as SseFrame;
                console.log('✅ [API] Parsed SSE frame:', frame);
              } catch (parseError) {
                console.error(
                  '❌ [API] SSE parse error for payload:',
                  jsonStr.slice(0, 180),
                  parseError
                );
                continue;
              }
              if (!frame) {
                console.log('⚠️ [API] Frame is null, skipping');
                continue;
              }

              // If this is a final frame, remember it and trigger onDone once
              if (frame.done === true) {
                console.log('🏁 [API] Final frame detected:', frame);
                finalFrameSeen = frame;

                // DEV-256: Forward done frame to onChunk FIRST so handlers can extract
                // enriched_prompt and other metadata before stream completes
                onChunk(frame);

                if (!doneEmitted) {
                  doneEmitted = true;
                  console.log('📞 [API] Calling onDone with final frame');
                  onDone(finalFrameSeen);
                }
                // Do not forward finals as regular chunks (already forwarded above)
                continue;
              }

              // Forward frames that carry content, proactivity, OR metadata events
              const hasContent =
                typeof frame.content === 'string' && frame.content.length > 0;
              const hasProactivity = frame.interactive_question;
              // DEV-244/245: Also forward KB source URLs, reasoning, and web verification frames
              // DEV-256: Also forward enriched_prompt frames for model comparison
              const hasMetadata =
                (frame.kb_source_urls && frame.kb_source_urls.length > 0) ||
                frame.reasoning ||
                frame.web_verification ||
                !!frame.enriched_prompt;

              if (hasContent || hasProactivity || hasMetadata) {
                if (hasContent) {
                  console.log(
                    '📤 [API] Forwarding SSE content chunk:',
                    frame.content!.length,
                    'chars:',
                    frame.content!.slice(0, 100)
                  );
                }
                if (hasProactivity) {
                  console.log(
                    '📤 [API] Forwarding SSE proactivity frame:',
                    frame.event_type || 'proactivity',
                    frame.interactive_question ? 'with question' : ''
                  );
                }
                // DEV-244/245: Log metadata frames
                if (hasMetadata) {
                  console.log(
                    '📤 [API] Forwarding SSE metadata frame:',
                    frame.event_type || 'metadata',
                    frame.kb_source_urls
                      ? `with ${frame.kb_source_urls.length} KB sources`
                      : '',
                    frame.reasoning ? 'with reasoning' : '',
                    frame.web_verification ? 'with web verification' : '',
                    frame.enriched_prompt
                      ? `with enriched_prompt (${frame.enriched_prompt.length} chars)`
                      : ''
                  );
                }
                onChunk(frame);
              } else {
                console.log(
                  '⏭️ [API] Skipping SSE frame without content/proactivity/metadata:',
                  frame
                );
              }
              continue;
            }

            // Handle SSE comments / keepalives
            if (line.startsWith(':')) {
              console.log('⏭️ [API] Skipping SSE comment/keepalive:', line);
              continue;
            }

            // STRICT: Any non-empty line that isn't "data:" or ":" is invalid SSE
            if (line.length > 0) {
              console.error(
                '❌ [API] Invalid SSE format - line must start with "data:" or ":":',
                line.slice(0, 100)
              );
              onError(
                `Invalid SSE format: unexpected line "${line.slice(0, 50)}..."`
              );
              return;
            }
          }
        }
      } finally {
        // Always release the reader
        try {
          reader.releaseLock();
        } catch {}
      }

      // Network ended without an explicit final? Ensure single onDone()
      if (!doneEmitted) {
        console.log('📞 [API] Stream ended naturally, calling onDone');
        onDone(finalFrameSeen);
      }
    } catch (error: any) {
      // If this is a re-throw from onError for a usage limit, just propagate
      let isUsageLimitRethrow = false;
      try {
        if (JSON.parse(error?.message)?.type === 'USAGE_LIMIT_EXCEEDED')
          isUsageLimitRethrow = true;
      } catch {
        /* not JSON, not a usage limit re-throw */
      }

      if (isUsageLimitRethrow) {
        throw error; // Already handled, just propagate to startStreaming
      }

      console.error('❌ [API] Error in sendChatMessageStreaming:', error);
      if (
        error instanceof TypeError &&
        error.message.includes('Failed to fetch')
      ) {
        onError(
          'Impossibile connettersi al server. Verifica che il backend sia in funzione.'
        );
      } else {
        onError(error?.message || "Errore durante l'invio del messaggio");
      }
    }
  }

  /**
   * Send a chat message using regular HTTP request (non-streaming fallback)
   */
  async sendChatMessage(messages: Message[]): Promise<ChatResponse> {
    // Ensure we have a session
    await this.ensureSession();

    return this.makeRequest<ChatResponse>('/api/v1/chatbot/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ messages }),
    });
  }

  /**
   * Get chat history for the current session
   * DEV-242: Strips proactivity XML tags from assistant messages
   */
  async getChatHistory(): Promise<ChatResponse> {
    if (!this.currentSessionToken) {
      throw new Error('No active session. Please create a session first.');
    }

    const response = await this.makeRequest<ChatResponse>(
      '/api/v1/chatbot/messages'
    );

    // DEV-242: Strip XML tags from assistant messages
    // These tags are stripped during streaming but not when loading from history
    if (response.messages) {
      response.messages = response.messages.map(msg => ({
        ...msg,
        content:
          msg.role === 'assistant'
            ? stripProactivityTags(msg.content)
            : msg.content,
      }));
    }

    return response;
  }

  /**
   * Clear chat history for the current session
   */
  async clearChatHistory(): Promise<{ message: string }> {
    if (!this.currentSessionToken) {
      throw new Error('No active session. Please create a session first.');
    }

    return this.makeRequest<{ message: string }>('/api/v1/chatbot/messages', {
      method: 'DELETE',
    });
  }

  /**
   * Answer an interactive question (proactivity feature - DEV-161)
   *
   * Calls the /questions/answer endpoint to process user's answer.
   * Returns either the next question (multi-step flow) or the final answer.
   */
  async answerQuestion(
    request: QuestionAnswerRequest
  ): Promise<QuestionAnswerResponse> {
    if (!this.currentSessionToken) {
      throw new Error('No active session. Please create a session first.');
    }

    return this.makeRequest<QuestionAnswerResponse>(
      '/api/v1/chatbot/questions/answer',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      }
    );
  }

  /**
   * Ensure we have an active session for chat operations
   */
  private async ensureSession(): Promise<void> {
    if (!this.currentSessionId || !this.currentSessionToken) {
      console.log('No active session, creating new session...');
      const session = await this.createSession();
      this.storeSession(session.session_id, session.token.access_token);
      console.log('Created new session:', session.session_id);
    }
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Re-export authEvents for convenient access
export { authEvents } from './auth-events';

// Export default for convenience
export default apiClient;
