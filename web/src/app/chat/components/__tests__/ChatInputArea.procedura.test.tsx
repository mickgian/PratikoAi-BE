/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatInputArea } from '../ChatInputArea';
import * as chatStateModule from '../../hooks/useChatState';
import * as chatSessionsModule from '../../hooks/useChatSessions';
import * as fileUploadModule from '../../hooks/useFileUpload';
import * as procedureApi from '@/lib/api/procedure';

// Mock the hooks
jest.mock('../../hooks/useChatState');
jest.mock('../../hooks/useChatSessions');
jest.mock('../../hooks/useFileUpload');
jest.mock('@/lib/api/billing');
jest.mock('@/lib/api/procedure');

// Mock StreamingHandler
jest.mock('../../handlers/StreamingHandler', () => ({
  StreamingHandler: jest.fn().mockImplementation(() => ({
    startStreaming: jest.fn().mockResolvedValue(true),
    cancelStreaming: jest.fn().mockResolvedValue(undefined),
    setConfig: jest.fn(),
    getLastError: jest.fn().mockReturnValue(null),
  })),
}));

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

const mockProcedures: procedureApi.ProceduraResponse[] = [
  {
    id: 'proc-1',
    code: 'apertura-srl',
    title: 'Apertura S.r.l.',
    description: 'Procedura per apertura SRL',
    category: 'apertura',
    steps: [
      { title: 'Passo 1', checklist: ['Item 1'], documents: ['Doc 1'] },
      { title: 'Passo 2' },
    ],
    estimated_time_minutes: 120,
    version: 1,
    is_active: true,
  },
  {
    id: 'proc-2',
    code: 'dichiarazione-iva',
    title: 'Dichiarazione IVA',
    description: 'Dichiarazione IVA trimestrale',
    category: 'fiscale',
    steps: [{ title: 'Compilazione' }],
    estimated_time_minutes: 60,
    version: 1,
    is_active: true,
  },
];

describe('ChatInputArea - /procedura command', () => {
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
    mockUpdateSessionName.mockResolvedValue(undefined);
    mockMarkSessionAsUsed.mockResolvedValue(undefined);
    mockGetAttachmentIds.mockReturnValue([]);

    jest.spyOn(chatStateModule, 'useSharedChatState').mockReturnValue({
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

    jest.spyOn(chatSessionsModule, 'useSharedChatSessions').mockReturnValue({
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

  it('should open procedure dialog on /procedura and call listProcedure', async () => {
    (procedureApi.listProcedure as jest.Mock).mockResolvedValue(mockProcedures);

    render(<ChatInputArea />);

    const textarea = screen.getByPlaceholderText(/fai una domanda/i);
    const sendButton = screen.getByRole('button', { name: /invia/i });

    fireEvent.change(textarea, { target: { value: '/procedura' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(procedureApi.listProcedure).toHaveBeenCalledTimes(1);
      expect(procedureApi.listProcedure).toHaveBeenCalledWith(undefined);
      expect(screen.getByTestId('procedura-dialog')).toBeInTheDocument();
    });

    // Should NOT trigger streaming or session creation
    expect(mockStartAIStreaming).not.toHaveBeenCalled();
    expect(mockCreateNewSession).not.toHaveBeenCalled();
    expect(mockAddUserMessage).not.toHaveBeenCalled();
  });

  it('should pass category when /procedura has a query argument', async () => {
    (procedureApi.listProcedure as jest.Mock).mockResolvedValue([
      mockProcedures[0],
    ]);

    render(<ChatInputArea />);

    const textarea = screen.getByPlaceholderText(/fai una domanda/i);
    const sendButton = screen.getByRole('button', { name: /invia/i });

    fireEvent.change(textarea, { target: { value: '/procedura apertura' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(procedureApi.listProcedure).toHaveBeenCalledWith('apertura');
      expect(screen.getByTestId('procedura-dialog')).toBeInTheDocument();
    });
  });

  it('should show error state when API fails', async () => {
    (procedureApi.listProcedure as jest.Mock).mockRejectedValue(
      new Error('Network error')
    );

    render(<ChatInputArea />);

    const textarea = screen.getByPlaceholderText(/fai una domanda/i);
    const sendButton = screen.getByRole('button', { name: /invia/i });

    fireEvent.change(textarea, { target: { value: '/procedura' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(screen.getByTestId('procedura-dialog')).toBeInTheDocument();
      expect(
        screen.getByText(
          'Errore nel recupero delle procedure. Riprova tra qualche istante.'
        )
      ).toBeInTheDocument();
    });
  });

  it('should close dialog and clear state when onClose is called', async () => {
    (procedureApi.listProcedure as jest.Mock).mockResolvedValue(mockProcedures);

    render(<ChatInputArea />);

    const textarea = screen.getByPlaceholderText(/fai una domanda/i);
    const sendButton = screen.getByRole('button', { name: /invia/i });

    fireEvent.change(textarea, { target: { value: '/procedura' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(screen.getByTestId('procedura-dialog')).toBeInTheDocument();
    });

    // Press Escape to close
    fireEvent.keyDown(document, { key: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByTestId('procedura-dialog')).not.toBeInTheDocument();
    });
  });
});
