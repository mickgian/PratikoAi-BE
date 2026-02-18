/**
 * @jest-environment jsdom
 */
import { render, screen } from '@testing-library/react';
import { UserMessage } from '../UserMessage';
import type { Message, AttachmentInfo } from '../../types/chat';

describe('UserMessage', () => {
  const createMockMessage = (overrides: Partial<Message> = {}): Message => ({
    id: 'msg-123',
    type: 'user',
    content: 'Test message content',
    timestamp: '2024-01-15T10:30:00Z',
    ...overrides,
  });

  const createMockAttachment = (
    overrides: Partial<AttachmentInfo> = {}
  ): AttachmentInfo => ({
    id: 'doc-123',
    filename: 'test.pdf',
    size: 1024 * 1024, // 1 MB
    type: 'application/pdf',
    ...overrides,
  });

  describe('Basic rendering', () => {
    it('should render message content', () => {
      const message = createMockMessage({
        content: 'Hello, this is a test message',
      });

      render(<UserMessage message={message} />);

      expect(
        screen.getByText('Hello, this is a test message')
      ).toBeInTheDocument();
    });

    it('should have correct accessibility attributes', () => {
      const message = createMockMessage();

      render(<UserMessage message={message} />);

      const container = screen.getByTestId('user-message');
      expect(container).toHaveAttribute('role', 'region');
      expect(container).toHaveAttribute('aria-label', "Messaggio dell'utente");
      expect(container).toHaveAttribute('tabIndex', '0');
    });

    it('should preserve whitespace in message content', () => {
      const message = createMockMessage({ content: 'Line 1\nLine 2\nLine 3' });

      render(<UserMessage message={message} />);

      const textElement = screen.getByTestId('user-message-text');
      expect(textElement).toHaveClass('whitespace-pre-wrap');
    });
  });

  describe('Message without attachments', () => {
    it('should not render attachments container when no attachments', () => {
      const message = createMockMessage({ attachments: undefined });

      render(<UserMessage message={message} />);

      expect(
        screen.queryByTestId('message-attachments')
      ).not.toBeInTheDocument();
    });

    it('should not render attachments container when attachments array is empty', () => {
      const message = createMockMessage({ attachments: [] });

      render(<UserMessage message={message} />);

      expect(
        screen.queryByTestId('message-attachments')
      ).not.toBeInTheDocument();
    });
  });

  describe('Message with attachments', () => {
    it('should render attachments container when attachments exist', () => {
      const message = createMockMessage({
        attachments: [createMockAttachment()],
      });

      render(<UserMessage message={message} />);

      expect(screen.getByTestId('message-attachments')).toBeInTheDocument();
    });

    it('should render attachment chip for each attachment', () => {
      const message = createMockMessage({
        attachments: [
          createMockAttachment({ id: 'doc-1', filename: 'document.pdf' }),
          createMockAttachment({ id: 'doc-2', filename: 'data.xlsx' }),
          createMockAttachment({ id: 'doc-3', filename: 'image.png' }),
        ],
      });

      render(<UserMessage message={message} />);

      const attachmentChips = screen.getAllByTestId('message-attachment');
      expect(attachmentChips).toHaveLength(3);
    });

    it('should display attachment filename', () => {
      const message = createMockMessage({
        attachments: [createMockAttachment({ filename: 'important-doc.pdf' })],
      });

      render(<UserMessage message={message} />);

      expect(screen.getByText('important-doc.pdf')).toBeInTheDocument();
    });

    it('should truncate long filenames', () => {
      const message = createMockMessage({
        attachments: [
          createMockAttachment({
            filename:
              'this-is-a-very-long-filename-that-should-be-truncated.pdf',
          }),
        ],
      });

      render(<UserMessage message={message} />);

      // Should show truncated name (32 chars + '...')
      expect(
        screen.getByText('this-is-a-very-long-filename-tha...')
      ).toBeInTheDocument();
    });

    it('should display formatted file size when available', () => {
      const message = createMockMessage({
        attachments: [createMockAttachment({ size: 2.5 * 1024 * 1024 })], // 2.5 MB
      });

      render(<UserMessage message={message} />);

      expect(screen.getByText('2.5 MB')).toBeInTheDocument();
    });

    it('should not display file size when not available', () => {
      const message = createMockMessage({
        attachments: [createMockAttachment({ size: undefined })],
      });

      render(<UserMessage message={message} />);

      // The MB suffix should not appear
      expect(screen.queryByText(/MB|KB|B$/)).not.toBeInTheDocument();
    });

    it('should show attachment chip title with full filename', () => {
      const longFilename = 'this-is-a-very-long-filename.pdf';
      const message = createMockMessage({
        attachments: [createMockAttachment({ filename: longFilename })],
      });

      render(<UserMessage message={message} />);

      const chip = screen.getByTestId('message-attachment');
      expect(chip).toHaveAttribute('title', longFilename);
    });

    it('should have correct accessibility for attachments container', () => {
      const message = createMockMessage({
        attachments: [createMockAttachment()],
      });

      render(<UserMessage message={message} />);

      const container = screen.getByTestId('message-attachments');
      expect(container).toHaveAttribute('aria-label', 'File allegati');
    });
  });

  describe('File type icons', () => {
    it('should display PDF icon for PDF files', () => {
      const message = createMockMessage({
        attachments: [createMockAttachment({ filename: 'document.pdf' })],
      });

      render(<UserMessage message={message} />);

      // The icon should be present (aria-hidden so we check via structure)
      const chip = screen.getByTestId('message-attachment');
      expect(chip.querySelector('svg')).toBeInTheDocument();
    });

    it('should display Excel icon for XLSX files', () => {
      const message = createMockMessage({
        attachments: [createMockAttachment({ filename: 'data.xlsx' })],
      });

      render(<UserMessage message={message} />);

      const chip = screen.getByTestId('message-attachment');
      expect(chip.querySelector('svg')).toBeInTheDocument();
    });

    it('should display image icon for image files', () => {
      const message = createMockMessage({
        attachments: [createMockAttachment({ filename: 'photo.jpg' })],
      });

      render(<UserMessage message={message} />);

      const chip = screen.getByTestId('message-attachment');
      expect(chip.querySelector('svg')).toBeInTheDocument();
    });
  });

  describe('Multiple attachments', () => {
    it('should render all attachments with different types', () => {
      const message = createMockMessage({
        attachments: [
          createMockAttachment({ id: 'pdf', filename: 'document.pdf' }),
          createMockAttachment({ id: 'xlsx', filename: 'data.xlsx' }),
          createMockAttachment({ id: 'csv', filename: 'data.csv' }),
          createMockAttachment({ id: 'jpg', filename: 'image.jpg' }),
          createMockAttachment({ id: 'xml', filename: 'config.xml' }),
        ],
      });

      render(<UserMessage message={message} />);

      const attachmentChips = screen.getAllByTestId('message-attachment');
      expect(attachmentChips).toHaveLength(5);

      expect(screen.getByText('document.pdf')).toBeInTheDocument();
      expect(screen.getByText('data.xlsx')).toBeInTheDocument();
      expect(screen.getByText('data.csv')).toBeInTheDocument();
      expect(screen.getByText('image.jpg')).toBeInTheDocument();
      expect(screen.getByText('config.xml')).toBeInTheDocument();
    });

    it('should render attachments before message text', () => {
      const message = createMockMessage({
        content: 'Message with attachments',
        attachments: [createMockAttachment()],
      });

      render(<UserMessage message={message} />);

      const messageContainer = screen.getByTestId('user-message');
      const attachmentsContainer = screen.getByTestId('message-attachments');
      const textContainer = screen.getByTestId('user-message-text');

      // Check that attachments appear before text in DOM order
      const children = Array.from(messageContainer.children);
      const attachmentsIndex = children.indexOf(attachmentsContainer);
      const textIndex = children.indexOf(textContainer);

      expect(attachmentsIndex).toBeLessThan(textIndex);
    });
  });

  describe('Styling', () => {
    it('should have correct background color class', () => {
      const message = createMockMessage();

      render(<UserMessage message={message} />);

      const container = screen.getByTestId('user-message');
      expect(container).toHaveClass('bg-[#d4a574]');
    });

    it('should be right-aligned', () => {
      const message = createMockMessage();

      render(<UserMessage message={message} />);

      const container = screen.getByTestId('user-message');
      expect(container).toHaveClass('ml-auto');
    });

    it('should have max-width constraint', () => {
      const message = createMockMessage();

      render(<UserMessage message={message} />);

      const container = screen.getByTestId('user-message');
      expect(container).toHaveClass('max-w-[280px]');
    });
  });
});
