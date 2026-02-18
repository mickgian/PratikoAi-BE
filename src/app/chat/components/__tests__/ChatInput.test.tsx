/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInput } from '../ChatInput';

describe('ChatInput - Slash command menu integration', () => {
  const onSendMessage = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows command menu when input starts with "/"', () => {
    render(<ChatInput onSendMessage={onSendMessage} />);
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: '/' } });
    expect(screen.getByTestId('slash-command-menu')).toBeInTheDocument();
  });

  it('does NOT show command menu for normal text', () => {
    render(<ChatInput onSendMessage={onSendMessage} />);
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'ciao' } });
    expect(screen.queryByTestId('slash-command-menu')).not.toBeInTheDocument();
  });

  it('does NOT show command menu when disabled', () => {
    render(<ChatInput onSendMessage={onSendMessage} disabled />);
    const textarea = screen.getByRole('textbox');
    // disabled textarea can't change, but verify no menu rendered
    expect(screen.queryByTestId('slash-command-menu')).not.toBeInTheDocument();
  });

  it('clicking a command executes it immediately via onSlashCommand', () => {
    const onSlashCommand = jest.fn();
    render(
      <ChatInput
        onSendMessage={onSendMessage}
        onSlashCommand={onSlashCommand}
      />
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/' } });

    // Click the command option (use mouseDown as the component uses onMouseDown)
    const cmd = screen.getByTestId('slash-cmd-/utilizzo');
    fireEvent.mouseDown(cmd);

    expect(onSlashCommand).toHaveBeenCalledWith('/utilizzo');
    expect(onSendMessage).not.toHaveBeenCalled();
    expect(textarea.value).toBe('');
  });

  it('Enter on highlighted command executes it via onSlashCommand', () => {
    const onSlashCommand = jest.fn();
    render(
      <ChatInput
        onSendMessage={onSendMessage}
        onSlashCommand={onSlashCommand}
      />
    );
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: '/' } });

    // Press Enter while command menu is open
    fireEvent.keyDown(textarea, { key: 'Enter' });

    expect(onSlashCommand).toHaveBeenCalledWith('/utilizzo');
    expect(onSendMessage).not.toHaveBeenCalled();
  });

  it('Tab autocompletes command into input without sending', () => {
    render(<ChatInput onSendMessage={onSendMessage} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/' } });

    fireEvent.keyDown(textarea, { key: 'Tab' });

    expect(textarea.value).toBe('/utilizzo');
    expect(onSendMessage).not.toHaveBeenCalled();
  });

  it('hides menu when filter yields no matches', () => {
    render(<ChatInput onSendMessage={onSendMessage} />);
    const textarea = screen.getByRole('textbox');

    fireEvent.change(textarea, { target: { value: '/' } });
    expect(screen.getByTestId('slash-command-menu')).toBeInTheDocument();

    fireEvent.change(textarea, { target: { value: '/xyz' } });
    expect(screen.queryByTestId('slash-command-menu')).not.toBeInTheDocument();
  });

  it('Escape closes the menu and clears input', () => {
    render(<ChatInput onSendMessage={onSendMessage} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '/' } });
    expect(screen.getByTestId('slash-command-menu')).toBeInTheDocument();

    fireEvent.keyDown(textarea, { key: 'Escape' });
    expect(textarea.value).toBe('');
  });
});

describe('ChatInput - Slash command routing', () => {
  const onSendMessage = jest.fn();
  const onSlashCommand = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('routes slash commands to onSlashCommand, not onSendMessage', () => {
    render(
      <ChatInput
        onSendMessage={onSendMessage}
        onSlashCommand={onSlashCommand}
      />
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;

    // Type the full command and submit via form
    fireEvent.change(textarea, { target: { value: '/utilizzo' } });
    fireEvent.submit(screen.getByTestId('chat-input-form'));

    expect(onSlashCommand).toHaveBeenCalledWith('/utilizzo');
    expect(onSendMessage).not.toHaveBeenCalled();
    expect(textarea.value).toBe('');
  });

  it('falls through to onSendMessage when onSlashCommand is NOT provided', () => {
    render(<ChatInput onSendMessage={onSendMessage} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;

    fireEvent.change(textarea, { target: { value: '/utilizzo' } });
    fireEvent.submit(screen.getByTestId('chat-input-form'));

    expect(onSendMessage).toHaveBeenCalledWith('/utilizzo');
  });

  it('sends normal messages to onSendMessage even when onSlashCommand is provided', () => {
    render(
      <ChatInput
        onSendMessage={onSendMessage}
        onSlashCommand={onSlashCommand}
      />
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;

    fireEvent.change(textarea, { target: { value: 'Ciao!' } });
    fireEvent.submit(screen.getByTestId('chat-input-form'));

    expect(onSendMessage).toHaveBeenCalledWith('Ciao!');
    expect(onSlashCommand).not.toHaveBeenCalled();
  });
});
