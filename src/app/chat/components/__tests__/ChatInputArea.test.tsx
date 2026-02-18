/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatInputArea } from '../ChatInputArea';
import * as chatStateModule from '../../hooks/useChatState';
import * as chatSessionsModule from '../../hooks/useChatSessions';
import * as fileUploadModule from '../../hooks/useFileUpload';
import * as billingApi from '@/lib/api/billing';

// Mock the hooks
jest.mock('../../hooks/useChatState');
jest.mock('../../hooks/useChatSessions');
jest.mock('../../hooks/useFileUpload');
jest.mock('@/lib/api/billing');

// Mock StreamingHandler so startStreaming resolves with true (no real fetch)
const mockStartStreamingFn = jest.fn().mockResolvedValue(true);
const mockGetLastError = jest.fn().mockReturnValue(null);
jest.mock('../../handlers/StreamingHandler', () => ({
  StreamingHandler: jest.fn().mockImplementation(() => ({
    startStreaming: mockStartStreamingFn,
    cancelStreaming: jest.fn().mockResolvedValue(undefined),
    setConfig: jest.fn(),
    getLastError: mockGetLastError,
  })),
}));

const mockUseSharedChatState = jest.spyOn(
  chatStateModule,
  'useSharedChatState'
);
const mockUseSharedChatSessions = jest.spyOn(
  chatSessionsModule,
  'useSharedChatSessions'
);
const mockUseFileUpload = jest.spyOn(fileUploadModule, 'useFileUpload');

describe('ChatInputArea - Lazy session creation on first message', () => {
  const mockAddUserMessage = jest.fn();
  const mockCreateNewSession = jest.fn();
  const mockStartAIStreaming = jest.fn();
  const mockCompleteStreaming = jest.fn();
  const mockDispatch = jest.fn();
  const mockUpdateSessionName = jest.fn();
  const mockMarkSessionAsUsed = jest.fn();
  const mockUploadFile = jest.fn();
  const mockRemoveFile = jest.fn();
  const mockClearFiles = jest.fn();
  const mockGetAttachmentIds = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();

    // Re-setup StreamingHandler mock after clearAllMocks
    mockStartStreamingFn.mockResolvedValue(true);
    mockGetLastError.mockReturnValue(null);

    // Mock updateSessionName to return a resolved promise
    mockUpdateSessionName.mockResolvedValue(undefined);
    mockMarkSessionAsUsed.mockResolvedValue(undefined);
    mockGetAttachmentIds.mockReturnValue([]);

    mockUseSharedChatState.mockReturnValue({
      state: {
        messages: [],
        sessionMessages: [],
        currentSessionId: null,
        isStreaming: false,
        error: null,
        accumulatedContent: '',
      },
      addUserMessage: mockAddUserMessage,
      isCurrentlyStreaming: false,
      startAIStreaming: mockStartAIStreaming,
      completeStreaming: mockCompleteStreaming,
      dispatch: mockDispatch,
    } as any);

    // Mock useFileUpload hook
    mockUseFileUpload.mockReturnValue({
      files: [],
      uploading: false,
      uploadFile: mockUploadFile,
      removeFile: mockRemoveFile,
      clearFiles: mockClearFiles,
      getAttachmentIds: mockGetAttachmentIds,
      hasUploading: false,
      hasFiles: false,
      isAtLimit: false,
    } as any);
  });

  it('should create session when sending first message with no existing session', async () => {
    // Mock: No current session
    mockUseSharedChatSessions.mockReturnValue({
      sessions: [],
      currentSession: null,
      isLoadingHistory: false,
      isLoadingSessions: false,
      error: null,
      createNewSession: mockCreateNewSession,
      updateSessionName: mockUpdateSessionName,
      markSessionAsUsed: mockMarkSessionAsUsed,
      loadSession: jest.fn(),
      deleteSession: jest.fn(),
      refreshSessions: jest.fn(),
    } as any);

    // CRITICAL: Mock must return session with 'token' property (not 'session_token')
    mockStartAIStreaming.mockReturnValue('msg-123');
    mockCreateNewSession.mockResolvedValue({
      id: 'new-session-123',
      token: 'token-123',
      name: 'New Chat',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      isActive: true,
    });

    render(<ChatInputArea />);

    const textarea = screen.getByPlaceholderText(/fai una domanda/i);
    const sendButton = screen.getByRole('button', { name: /invia/i });

    // Type a message
    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      // This test SHOULD PASS if lazy creation already exists
      // We expect createNewSession to be called BEFORE addUserMessage
      expect(mockCreateNewSession).toHaveBeenCalledTimes(1);
      expect(mockAddUserMessage).toHaveBeenCalledWith(
        'Test message',
        undefined
      );
    });
  });

  it('should NOT create session when sending message with existing session', async () => {
    // Mock: Existing session
    mockUseSharedChatSessions.mockReturnValue({
      sessions: [
        {
          id: 'existing-session',
          name: 'Existing Chat',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          isActive: true,
        },
      ],
      currentSession: {
        id: 'existing-session',
        name: 'Existing Chat',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        isActive: true,
        token: 'token-123',
      },
      isLoadingHistory: false,
      isLoadingSessions: false,
      error: null,
      createNewSession: mockCreateNewSession,
      updateSessionName: mockUpdateSessionName,
      markSessionAsUsed: mockMarkSessionAsUsed,
      loadSession: jest.fn(),
      deleteSession: jest.fn(),
      refreshSessions: jest.fn(),
    } as any);

    mockStartAIStreaming.mockReturnValue('msg-123');
    mockUseSharedChatState.mockReturnValue({
      state: {
        messages: [],
        sessionMessages: [
          {
            type: 'user',
            content: 'Previous message',
            id: '1',
            timestamp: Date.now(),
          },
        ],
        currentSessionId: 'existing-session',
        isStreaming: false,
        error: null,
        accumulatedContent: '',
      },
      addUserMessage: mockAddUserMessage,
      isCurrentlyStreaming: false,
      startAIStreaming: mockStartAIStreaming,
      completeStreaming: mockCompleteStreaming,
      dispatch: mockDispatch,
    } as any);

    render(<ChatInputArea />);

    const textarea = screen.getByPlaceholderText(/fai una domanda/i);
    const sendButton = screen.getByRole('button', { name: /invia/i });

    // Type a message
    fireEvent.change(textarea, { target: { value: 'Another message' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      // This test SHOULD PASS - session should NOT be created again
      expect(mockCreateNewSession).not.toHaveBeenCalled();
      expect(mockAddUserMessage).toHaveBeenCalledWith(
        'Another message',
        undefined
      );
    });
  });

  it('should create session only once when sending multiple messages rapidly', async () => {
    mockUseSharedChatSessions.mockReturnValue({
      sessions: [],
      currentSession: null,
      isLoadingHistory: false,
      isLoadingSessions: false,
      error: null,
      createNewSession: mockCreateNewSession,
      updateSessionName: mockUpdateSessionName,
      markSessionAsUsed: mockMarkSessionAsUsed,
      loadSession: jest.fn(),
      deleteSession: jest.fn(),
      refreshSessions: jest.fn(),
    } as any);

    mockStartAIStreaming.mockReturnValue('msg-123');
    mockCreateNewSession.mockResolvedValue({
      id: 'new-session-123',
      token: 'token-123',
      name: 'New Chat',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      isActive: true,
    });

    render(<ChatInputArea />);

    const textarea = screen.getByPlaceholderText(/fai una domanda/i);
    const sendButton = screen.getByRole('button', { name: /invia/i });

    // Send multiple messages rapidly
    fireEvent.change(textarea, { target: { value: 'Message 1' } });
    fireEvent.click(sendButton);

    fireEvent.change(textarea, { target: { value: 'Message 2' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      // Session should be created only once
      expect(mockCreateNewSession).toHaveBeenCalledTimes(1);
    });
  });

  it('should render file attachment button', () => {
    mockUseSharedChatSessions.mockReturnValue({
      sessions: [],
      currentSession: null,
      isLoadingHistory: false,
      isLoadingSessions: false,
      error: null,
      createNewSession: mockCreateNewSession,
      updateSessionName: mockUpdateSessionName,
      markSessionAsUsed: mockMarkSessionAsUsed,
      loadSession: jest.fn(),
      deleteSession: jest.fn(),
      refreshSessions: jest.fn(),
    } as any);

    render(<ChatInputArea />);

    expect(screen.getByTestId('file-attachment-button')).toBeInTheDocument();
  });

  it('should render drag-drop zone', () => {
    mockUseSharedChatSessions.mockReturnValue({
      sessions: [],
      currentSession: null,
      isLoadingHistory: false,
      isLoadingSessions: false,
      error: null,
      createNewSession: mockCreateNewSession,
      updateSessionName: mockUpdateSessionName,
      markSessionAsUsed: mockMarkSessionAsUsed,
      loadSession: jest.fn(),
      deleteSession: jest.fn(),
      refreshSessions: jest.fn(),
    } as any);

    render(<ChatInputArea />);

    expect(screen.getByTestId('drag-drop-zone')).toBeInTheDocument();
  });

  it('should show attachment preview when files are present', () => {
    mockUseSharedChatSessions.mockReturnValue({
      sessions: [],
      currentSession: null,
      isLoadingHistory: false,
      isLoadingSessions: false,
      error: null,
      createNewSession: mockCreateNewSession,
      updateSessionName: mockUpdateSessionName,
      markSessionAsUsed: mockMarkSessionAsUsed,
      loadSession: jest.fn(),
      deleteSession: jest.fn(),
      refreshSessions: jest.fn(),
    } as any);

    mockUseFileUpload.mockReturnValue({
      files: [
        {
          id: 'doc-1',
          name: 'test.pdf',
          size: 1024,
          type: 'application/pdf',
          status: 'success',
        },
      ],
      uploading: false,
      uploadFile: mockUploadFile,
      removeFile: mockRemoveFile,
      clearFiles: mockClearFiles,
      getAttachmentIds: mockGetAttachmentIds,
      hasUploading: false,
      hasFiles: true,
      isAtLimit: false,
    } as any);

    render(<ChatInputArea />);

    expect(screen.getByTestId('attachment-preview')).toBeInTheDocument();
  });

  it('should show warning when files attached but no text', () => {
    mockUseSharedChatSessions.mockReturnValue({
      sessions: [],
      currentSession: null,
      isLoadingHistory: false,
      isLoadingSessions: false,
      error: null,
      createNewSession: mockCreateNewSession,
      updateSessionName: mockUpdateSessionName,
      markSessionAsUsed: mockMarkSessionAsUsed,
      loadSession: jest.fn(),
      deleteSession: jest.fn(),
      refreshSessions: jest.fn(),
    } as any);

    mockUseFileUpload.mockReturnValue({
      files: [
        {
          id: 'doc-1',
          name: 'test.pdf',
          size: 1024,
          type: 'application/pdf',
          status: 'success',
        },
      ],
      uploading: false,
      uploadFile: mockUploadFile,
      removeFile: mockRemoveFile,
      clearFiles: mockClearFiles,
      getAttachmentIds: mockGetAttachmentIds,
      hasUploading: false,
      hasFiles: true,
      isAtLimit: false,
    } as any);

    render(<ChatInputArea />);

    expect(screen.getByTestId('attachment-warning')).toBeInTheDocument();
    expect(
      screen.getByText('Aggiungi una domanda per inviare')
    ).toBeInTheDocument();
  });

  it('should show uploading placeholder when files uploading', () => {
    mockUseSharedChatSessions.mockReturnValue({
      sessions: [],
      currentSession: null,
      isLoadingHistory: false,
      isLoadingSessions: false,
      error: null,
      createNewSession: mockCreateNewSession,
      updateSessionName: mockUpdateSessionName,
      markSessionAsUsed: mockMarkSessionAsUsed,
      loadSession: jest.fn(),
      deleteSession: jest.fn(),
      refreshSessions: jest.fn(),
    } as any);

    mockUseFileUpload.mockReturnValue({
      files: [
        {
          id: 'uploading-1',
          name: 'test.pdf',
          size: 1024,
          type: 'application/pdf',
          status: 'uploading',
          progress: 50,
        },
      ],
      uploading: true,
      uploadFile: mockUploadFile,
      removeFile: mockRemoveFile,
      clearFiles: mockClearFiles,
      getAttachmentIds: mockGetAttachmentIds,
      hasUploading: true,
      hasFiles: true,
      isAtLimit: false,
    } as any);

    render(<ChatInputArea />);

    expect(
      screen.getByPlaceholderText(/caricamento in corso/i)
    ).toBeInTheDocument();
  });

  it('should disable file attachment button when at limit', () => {
    mockUseSharedChatSessions.mockReturnValue({
      sessions: [],
      currentSession: null,
      isLoadingHistory: false,
      isLoadingSessions: false,
      error: null,
      createNewSession: mockCreateNewSession,
      updateSessionName: mockUpdateSessionName,
      markSessionAsUsed: mockMarkSessionAsUsed,
      loadSession: jest.fn(),
      deleteSession: jest.fn(),
      refreshSessions: jest.fn(),
    } as any);

    mockUseFileUpload.mockReturnValue({
      files: Array(5).fill({
        id: 'doc',
        name: 'test.pdf',
        size: 1024,
        type: 'application/pdf',
        status: 'success',
      }),
      uploading: false,
      uploadFile: mockUploadFile,
      removeFile: mockRemoveFile,
      clearFiles: mockClearFiles,
      getAttachmentIds: mockGetAttachmentIds,
      hasUploading: false,
      hasFiles: true,
      isAtLimit: true,
    } as any);

    render(<ChatInputArea />);

    expect(screen.getByTestId('file-attachment-button')).toBeDisabled();
  });

  it('should pass attachment info to addUserMessage when files are uploaded', async () => {
    const mockFiles = [
      {
        id: 'doc-1',
        name: 'document.pdf',
        size: 1024,
        type: 'application/pdf',
        status: 'success' as const,
      },
      {
        id: 'doc-2',
        name: 'data.xlsx',
        size: 2048,
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        status: 'success' as const,
      },
    ];

    mockUseSharedChatSessions.mockReturnValue({
      sessions: [],
      currentSession: {
        id: 'existing-session',
        name: 'Existing Chat',
        token: 'token-123',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        isActive: true,
      },
      isLoadingHistory: false,
      isLoadingSessions: false,
      error: null,
      createNewSession: mockCreateNewSession,
      updateSessionName: mockUpdateSessionName,
      markSessionAsUsed: mockMarkSessionAsUsed,
      loadSession: jest.fn(),
      deleteSession: jest.fn(),
      refreshSessions: jest.fn(),
    } as any);

    mockUseFileUpload.mockReturnValue({
      files: mockFiles,
      uploading: false,
      uploadFile: mockUploadFile,
      removeFile: mockRemoveFile,
      clearFiles: mockClearFiles,
      getAttachmentIds: jest.fn().mockReturnValue(['doc-1', 'doc-2']),
      hasUploading: false,
      hasFiles: true,
      isAtLimit: false,
    } as any);

    mockStartAIStreaming.mockReturnValue('msg-123');

    render(<ChatInputArea />);

    const textarea = screen.getByPlaceholderText(/fai una domanda/i);
    const sendButton = screen.getByRole('button', { name: /invia/i });

    // Type a message
    fireEvent.change(textarea, { target: { value: 'Analyze these files' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      // Verify addUserMessage is called with content and attachment info
      expect(mockAddUserMessage).toHaveBeenCalledWith('Analyze these files', [
        {
          id: 'doc-1',
          filename: 'document.pdf',
          size: 1024,
          type: 'application/pdf',
        },
        {
          id: 'doc-2',
          filename: 'data.xlsx',
          size: 2048,
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        },
      ]);
    });
  });

  it('should clear files after successful send with attachments', async () => {
    const mockFiles = [
      {
        id: 'doc-1',
        name: 'document.pdf',
        size: 1024,
        type: 'application/pdf',
        status: 'success' as const,
      },
    ];

    mockUseSharedChatSessions.mockReturnValue({
      sessions: [],
      currentSession: {
        id: 'existing-session',
        name: 'Existing Chat',
        token: 'token-123',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        isActive: true,
      },
      isLoadingHistory: false,
      isLoadingSessions: false,
      error: null,
      createNewSession: mockCreateNewSession,
      updateSessionName: mockUpdateSessionName,
      markSessionAsUsed: mockMarkSessionAsUsed,
      loadSession: jest.fn(),
      deleteSession: jest.fn(),
      refreshSessions: jest.fn(),
    } as any);

    mockUseFileUpload.mockReturnValue({
      files: mockFiles,
      uploading: false,
      uploadFile: mockUploadFile,
      removeFile: mockRemoveFile,
      clearFiles: mockClearFiles,
      getAttachmentIds: jest.fn().mockReturnValue(['doc-1']),
      hasUploading: false,
      hasFiles: true,
      isAtLimit: false,
    } as any);

    mockStartAIStreaming.mockReturnValue('msg-123');

    render(<ChatInputArea />);

    const textarea = screen.getByPlaceholderText(/fai una domanda/i);
    const sendButton = screen.getByRole('button', { name: /invia/i });

    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      // Verify clearFiles is called after successful send
      expect(mockClearFiles).toHaveBeenCalled();
    });
  });
});

// DEV-257: /utilizzo slash command → modal dialog tests
describe('ChatInputArea - /utilizzo command', () => {
  const mockDispatch = jest.fn();
  const mockAddUserMessage = jest.fn();
  const mockStartAIStreaming = jest.fn();
  const mockCompleteStreaming = jest.fn();
  const mockCreateNewSession = jest.fn();
  const mockUpdateSessionName = jest.fn().mockResolvedValue(undefined);
  const mockMarkSessionAsUsed = jest.fn().mockResolvedValue(undefined);
  const mockGetAttachmentIds = jest.fn().mockReturnValue([]);

  const mockUseSharedChatState = jest.spyOn(
    chatStateModule,
    'useSharedChatState'
  );
  const mockUseSharedChatSessions = jest.spyOn(
    chatSessionsModule,
    'useSharedChatSessions'
  );
  const mockUseFileUpload = jest.spyOn(fileUploadModule, 'useFileUpload');

  beforeEach(() => {
    jest.clearAllMocks();
    mockUpdateSessionName.mockResolvedValue(undefined);
    mockMarkSessionAsUsed.mockResolvedValue(undefined);
    mockGetAttachmentIds.mockReturnValue([]);

    mockUseSharedChatState.mockReturnValue({
      state: {
        messages: [],
        sessionMessages: [],
        currentSessionId: null,
        isStreaming: false,
        error: null,
        accumulatedContent: '',
      },
      addUserMessage: mockAddUserMessage,
      isCurrentlyStreaming: false,
      startAIStreaming: mockStartAIStreaming,
      completeStreaming: mockCompleteStreaming,
      dispatch: mockDispatch,
    } as any);

    mockUseSharedChatSessions.mockReturnValue({
      sessions: [],
      currentSession: null,
      isLoadingHistory: false,
      isLoadingSessions: false,
      error: null,
      createNewSession: mockCreateNewSession,
      updateSessionName: mockUpdateSessionName,
      markSessionAsUsed: mockMarkSessionAsUsed,
      loadSession: jest.fn(),
      deleteSession: jest.fn(),
      refreshSessions: jest.fn(),
    } as any);

    mockUseFileUpload.mockReturnValue({
      files: [],
      uploading: false,
      uploadFile: jest.fn(),
      removeFile: jest.fn(),
      clearFiles: jest.fn(),
      getAttachmentIds: mockGetAttachmentIds,
      hasUploading: false,
      hasFiles: false,
      isAtLimit: false,
    } as any);
  });

  it('should open usage dialog on /utilizzo success', async () => {
    const mockUsageData = {
      plan_slug: 'starter',
      plan_name: 'Starter',
      window_5h: {
        window_type: '5h',
        current_cost_eur: 0.1,
        limit_cost_eur: 1.0,
        usage_percentage: 10,
        reset_at: null,
        reset_in_minutes: 60,
      },
      window_7d: {
        window_type: '7d',
        current_cost_eur: 0.5,
        limit_cost_eur: 5.0,
        usage_percentage: 10,
        reset_at: null,
        reset_in_minutes: 1440,
      },
      credits: { balance_eur: 5.0, extra_usage_enabled: true },
      is_admin: false,
      message_it: 'OK',
    };

    (billingApi.getUsageStatus as jest.Mock).mockResolvedValue(mockUsageData);

    render(<ChatInputArea />);

    const textarea = screen.getByPlaceholderText(/fai una domanda/i);
    const sendButton = screen.getByRole('button', { name: /invia/i });

    fireEvent.change(textarea, { target: { value: '/utilizzo' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(billingApi.getUsageStatus).toHaveBeenCalledTimes(1);
      expect(screen.getByTestId('usage-dialog')).toBeInTheDocument();
      expect(screen.getByTestId('usage-card')).toBeInTheDocument();
    });

    // Should NOT trigger streaming or session creation
    expect(mockStartAIStreaming).not.toHaveBeenCalled();
    expect(mockCreateNewSession).not.toHaveBeenCalled();
    expect(mockAddUserMessage).not.toHaveBeenCalled();
    // Should NOT dispatch any command action
    expect(mockDispatch).not.toHaveBeenCalledWith(
      expect.objectContaining({ type: 'ADD_COMMAND_RESPONSE' })
    );
  });

  it('should open usage dialog case-insensitively with /UTILIZZO', async () => {
    (billingApi.getUsageStatus as jest.Mock).mockResolvedValue({
      plan_slug: 'starter',
      plan_name: 'Starter',
      window_5h: {
        window_type: '5h',
        current_cost_eur: 0,
        limit_cost_eur: 1,
        usage_percentage: 0,
        reset_at: null,
        reset_in_minutes: null,
      },
      window_7d: {
        window_type: '7d',
        current_cost_eur: 0,
        limit_cost_eur: 5,
        usage_percentage: 0,
        reset_at: null,
        reset_in_minutes: null,
      },
      credits: { balance_eur: 0, extra_usage_enabled: false },
      is_admin: false,
      message_it: '',
    });

    render(<ChatInputArea />);

    const textarea = screen.getByPlaceholderText(/fai una domanda/i);
    const sendButton = screen.getByRole('button', { name: /invia/i });

    fireEvent.change(textarea, { target: { value: '/UTILIZZO' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(billingApi.getUsageStatus).toHaveBeenCalledTimes(1);
      expect(screen.getByTestId('usage-dialog')).toBeInTheDocument();
    });

    // Should NOT create session or add message
    expect(mockCreateNewSession).not.toHaveBeenCalled();
    expect(mockAddUserMessage).not.toHaveBeenCalled();
  });

  it('should show error dialog when API fails', async () => {
    (billingApi.getUsageStatus as jest.Mock).mockRejectedValue(
      new Error('Network error')
    );

    render(<ChatInputArea />);

    const textarea = screen.getByPlaceholderText(/fai una domanda/i);
    const sendButton = screen.getByRole('button', { name: /invia/i });

    fireEvent.change(textarea, { target: { value: '/utilizzo' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(screen.getByTestId('usage-dialog')).toBeInTheDocument();
      expect(
        screen.getByText(
          'Errore nel recupero dei dati di utilizzo. Riprova tra qualche istante.'
        )
      ).toBeInTheDocument();
    });

    // Should NOT create session or add message even on error
    expect(mockCreateNewSession).not.toHaveBeenCalled();
    expect(mockAddUserMessage).not.toHaveBeenCalled();
  });

  it('should not intercept normal messages that are not /utilizzo', async () => {
    mockStartAIStreaming.mockReturnValue('msg-123');

    // Provide a current session so the normal send flow proceeds
    mockUseSharedChatSessions.mockReturnValue({
      sessions: [],
      currentSession: {
        id: 'existing-session',
        name: 'Chat',
        token: 'token-123',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        isActive: true,
      },
      isLoadingHistory: false,
      isLoadingSessions: false,
      error: null,
      createNewSession: mockCreateNewSession,
      updateSessionName: mockUpdateSessionName,
      markSessionAsUsed: mockMarkSessionAsUsed,
      loadSession: jest.fn(),
      deleteSession: jest.fn(),
      refreshSessions: jest.fn(),
    } as any);

    render(<ChatInputArea />);

    const textarea = screen.getByPlaceholderText(/fai una domanda/i);
    const sendButton = screen.getByRole('button', { name: /invia/i });

    fireEvent.change(textarea, {
      target: { value: 'Come funziona il bilancio?' },
    });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(billingApi.getUsageStatus).not.toHaveBeenCalled();
      expect(mockAddUserMessage).toHaveBeenCalled();
    });
  });
});

// DEV-257: FORCE_STOP_STREAMING dispatched on 429
describe('ChatInputArea - FORCE_STOP_STREAMING on 429', () => {
  const mockDispatch = jest.fn();
  const mockAddUserMessage = jest.fn();
  const mockStartAIStreaming = jest.fn();
  const mockCompleteStreaming = jest.fn();
  const mockCreateNewSession = jest.fn();
  const mockUpdateSessionName = jest.fn().mockResolvedValue(undefined);
  const mockMarkSessionAsUsed = jest.fn().mockResolvedValue(undefined);
  const mockGetAttachmentIds = jest.fn().mockReturnValue([]);

  beforeEach(() => {
    jest.clearAllMocks();
    mockGetAttachmentIds.mockReturnValue([]);

    // Simulate 429 failure: startStreaming returns false, getLastError returns usage limit error
    mockStartStreamingFn.mockResolvedValue(false);
    mockGetLastError.mockReturnValue(
      new Error(
        JSON.stringify({
          type: 'USAGE_LIMIT_EXCEEDED',
          message_it: 'Limite raggiunto',
          limit_info: {
            cost_consumed_eur: 0.05,
            cost_limit_eur: 0.04,
            reset_at: new Date(Date.now() + 3600000).toISOString(),
            reset_in_minutes: 60,
          },
          can_bypass: false,
        })
      )
    );

    jest.spyOn(chatStateModule, 'useSharedChatState').mockReturnValue({
      state: {
        messages: [],
        sessionMessages: [],
        currentSessionId: 'sess-1',
        isStreaming: false,
        error: null,
        accumulatedContent: '',
      },
      addUserMessage: mockAddUserMessage,
      isCurrentlyStreaming: false,
      startAIStreaming: mockStartAIStreaming.mockReturnValue('msg-429'),
      completeStreaming: mockCompleteStreaming,
      dispatch: mockDispatch,
    } as any);

    jest.spyOn(chatSessionsModule, 'useSharedChatSessions').mockReturnValue({
      sessions: [],
      currentSession: {
        id: 'sess-1',
        name: 'Chat',
        token: 'token-1',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        isActive: true,
      },
      isLoadingHistory: false,
      isLoadingSessions: false,
      error: null,
      createNewSession: mockCreateNewSession,
      updateSessionName: mockUpdateSessionName,
      markSessionAsUsed: mockMarkSessionAsUsed,
      loadSession: jest.fn(),
      deleteSession: jest.fn(),
      refreshSessions: jest.fn(),
    } as any);

    jest.spyOn(fileUploadModule, 'useFileUpload').mockReturnValue({
      files: [],
      uploading: false,
      uploadFile: jest.fn(),
      removeFile: jest.fn(),
      clearFiles: jest.fn(),
      getAttachmentIds: mockGetAttachmentIds,
      hasUploading: false,
      hasFiles: false,
      isAtLimit: false,
    } as any);
  });

  it('should dispatch FORCE_STOP_STREAMING after SET_USAGE_LIMIT on 429', async () => {
    render(<ChatInputArea />);

    const textarea = screen.getByPlaceholderText(/fai una domanda/i);
    const sendButton = screen.getByRole('button', { name: /invia/i });

    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      // SET_USAGE_LIMIT should be dispatched
      expect(mockDispatch).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'SET_USAGE_LIMIT' })
      );
      // FORCE_STOP_STREAMING should be dispatched after
      expect(mockDispatch).toHaveBeenCalledWith({
        type: 'FORCE_STOP_STREAMING',
      });
    });

    // Verify order: SET_USAGE_LIMIT before FORCE_STOP_STREAMING
    const calls = mockDispatch.mock.calls.map((c: any[]) => c[0]?.type);
    const limitIdx = calls.indexOf('SET_USAGE_LIMIT');
    const stopIdx = calls.indexOf('FORCE_STOP_STREAMING');
    expect(limitIdx).toBeGreaterThanOrEqual(0);
    expect(stopIdx).toBeGreaterThan(limitIdx);
  });
});
