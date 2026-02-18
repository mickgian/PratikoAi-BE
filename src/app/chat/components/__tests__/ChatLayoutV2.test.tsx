/**
 * @file ChatLayoutV2 Tests
 * @description Tests for ChatLayoutV2 with migration banner integration
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatLayoutV2 } from '../ChatLayoutV2';
import { useSharedChatSessions } from '../../hooks/useChatSessions';
import { useChatStorageV2 } from '../../hooks/useChatStorageV2';

// Mock dependencies
jest.mock('../../hooks/useChatSessions', () => ({
  useSharedChatSessions: jest.fn(),
}));

jest.mock('../../hooks/useChatStorageV2');

jest.mock('@/components/MigrationBanner', () => ({
  MigrationBanner: ({ onSync }: { onSync: () => Promise<void> }) => (
    <div data-testid="migration-banner">
      <p>Migration banner</p>
      <button onClick={onSync} data-testid="sync-button">
        Sync Now
      </button>
    </div>
  ),
}));

jest.mock('../ChatHeader', () => ({
  ChatHeader: () => <div data-testid="chat-header">Header</div>,
}));

jest.mock('../ChatSidebar', () => ({
  ChatSidebar: () => <div data-testid="chat-sidebar">Sidebar</div>,
}));

jest.mock('../ChatMessagesArea', () => ({
  ChatMessagesArea: () => <div data-testid="chat-messages-area">Messages</div>,
}));

jest.mock('../ChatInputArea', () => ({
  ChatInputArea: () => <div data-testid="chat-input-area">Input</div>,
}));

describe('ChatLayoutV2', () => {
  const mockSession = {
    id: 'test-session',
    name: 'Test Session',
    created_at: '2025-11-29',
    isActive: true,
  };

  beforeEach(() => {
    jest.clearAllMocks();

    (useSharedChatSessions as jest.Mock).mockReturnValue({
      currentSession: mockSession,
    });

    (useChatStorageV2 as jest.Mock).mockReturnValue({
      messages: [],
      isLoading: false,
      error: null,
      migrationNeeded: false,
      migrateToBackend: jest.fn(),
      reload: jest.fn(),
    });
  });

  it('should render chat layout components', () => {
    render(<ChatLayoutV2 />);

    expect(screen.getByTestId('chat-layout-v2')).toBeInTheDocument();
    expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    expect(screen.getByTestId('chat-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('chat-messages-area')).toBeInTheDocument();
    expect(screen.getByTestId('chat-input-area')).toBeInTheDocument();
  });

  it('should not show migration banner when migrationNeeded is false', () => {
    render(<ChatLayoutV2 />);

    expect(screen.queryByTestId('migration-banner')).not.toBeInTheDocument();
  });

  it('should show migration banner when migrationNeeded is true', () => {
    (useChatStorageV2 as jest.Mock).mockReturnValue({
      messages: [],
      isLoading: false,
      error: null,
      migrationNeeded: true,
      migrateToBackend: jest.fn(),
      reload: jest.fn(),
    });

    render(<ChatLayoutV2 />);

    expect(screen.getByTestId('migration-banner')).toBeInTheDocument();
  });

  it('should not show migration banner when no session exists', () => {
    (useSharedChatSessions as jest.Mock).mockReturnValue({
      currentSession: null,
    });

    (useChatStorageV2 as jest.Mock).mockReturnValue({
      messages: [],
      isLoading: false,
      error: null,
      migrationNeeded: true,
      migrateToBackend: jest.fn(),
      reload: jest.fn(),
    });

    render(<ChatLayoutV2 />);

    // Should not show banner because no session
    expect(screen.queryByTestId('migration-banner')).not.toBeInTheDocument();
  });

  it('should call migrateToBackend and reload when sync button clicked', async () => {
    const mockMigrate = jest.fn().mockResolvedValue(undefined);
    const mockReload = jest.fn().mockResolvedValue(undefined);

    (useChatStorageV2 as jest.Mock).mockReturnValue({
      messages: [],
      isLoading: false,
      error: null,
      migrationNeeded: true,
      migrateToBackend: mockMigrate,
      reload: mockReload,
    });

    render(<ChatLayoutV2 />);

    const syncButton = screen.getByTestId('sync-button');
    fireEvent.click(syncButton);

    await waitFor(() => {
      expect(mockMigrate).toHaveBeenCalled();
      expect(mockReload).toHaveBeenCalled();
    });
  });

  it('should use current session ID for storage hook', () => {
    render(<ChatLayoutV2 />);

    expect(useChatStorageV2).toHaveBeenCalledWith('test-session');
  });

  it('should use empty string when no session', () => {
    (useSharedChatSessions as jest.Mock).mockReturnValue({
      currentSession: null,
    });

    render(<ChatLayoutV2 />);

    expect(useChatStorageV2).toHaveBeenCalledWith('');
  });
});
