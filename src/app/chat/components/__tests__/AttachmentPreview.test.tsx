/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { AttachmentPreview } from '../AttachmentPreview';
import type { UploadedFile } from '@/lib/api/documents';

describe('AttachmentPreview', () => {
  const mockOnRemove = jest.fn();

  const createMockFile = (overrides: Partial<UploadedFile> = {}): UploadedFile => ({
    id: 'doc-123',
    name: 'test.pdf',
    size: 1024 * 1024, // 1 MB
    type: 'application/pdf',
    status: 'success',
    ...overrides,
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render nothing when no files', () => {
    const { container } = render(<AttachmentPreview files={[]} onRemove={mockOnRemove} />);

    expect(container.firstChild).toBeNull();
  });

  it('should render file chips for uploaded files', () => {
    const files: UploadedFile[] = [
      createMockFile({ id: 'doc-1', name: 'document.pdf' }),
      createMockFile({ id: 'doc-2', name: 'data.xlsx' }),
    ];

    render(<AttachmentPreview files={files} onRemove={mockOnRemove} />);

    expect(screen.getByTestId('attachment-preview')).toBeInTheDocument();
    expect(screen.getByTestId('attachment-chip-0')).toBeInTheDocument();
    expect(screen.getByTestId('attachment-chip-1')).toBeInTheDocument();
  });

  it('should display file name', () => {
    const files: UploadedFile[] = [createMockFile({ name: 'important-document.pdf' })];

    render(<AttachmentPreview files={files} onRemove={mockOnRemove} />);

    expect(screen.getByText('important-document.pdf')).toBeInTheDocument();
  });

  it('should truncate long file names', () => {
    const files: UploadedFile[] = [
      createMockFile({ name: 'this-is-a-very-long-filename-that-should-be-truncated.pdf' }),
    ];

    render(<AttachmentPreview files={files} onRemove={mockOnRemove} />);

    // Should show truncated name (22 chars + '...')
    expect(screen.getByText('this-is-a-very-long-fi...')).toBeInTheDocument();
  });

  it('should display formatted file size', () => {
    const files: UploadedFile[] = [createMockFile({ size: 2.5 * 1024 * 1024 })]; // 2.5 MB

    render(<AttachmentPreview files={files} onRemove={mockOnRemove} />);

    expect(screen.getByText('2.5 MB')).toBeInTheDocument();
  });

  it('should call onRemove when remove button is clicked', () => {
    const files: UploadedFile[] = [createMockFile()];

    render(<AttachmentPreview files={files} onRemove={mockOnRemove} />);

    const removeButton = screen.getByTestId('remove-attachment-0');
    fireEvent.click(removeButton);

    expect(mockOnRemove).toHaveBeenCalledWith(0);
  });

  it('should show uploading state with progress', () => {
    const files: UploadedFile[] = [
      createMockFile({ status: 'uploading', progress: 45 }),
    ];

    render(<AttachmentPreview files={files} onRemove={mockOnRemove} />);

    expect(screen.getByText('45%')).toBeInTheDocument();
    expect(screen.getByLabelText('Caricamento in corso')).toBeInTheDocument();
  });

  it('should show error state with message', () => {
    const files: UploadedFile[] = [
      createMockFile({ status: 'error', error: 'Tipo di file non supportato' }),
    ];

    render(<AttachmentPreview files={files} onRemove={mockOnRemove} />);

    expect(screen.getByText('Tipo di file non supportato')).toBeInTheDocument();
    expect(screen.getByLabelText('Errore')).toBeInTheDocument();
  });

  it('should disable remove button when disabled prop is true', () => {
    const files: UploadedFile[] = [createMockFile()];

    render(<AttachmentPreview files={files} onRemove={mockOnRemove} disabled />);

    const removeButton = screen.getByTestId('remove-attachment-0');
    expect(removeButton).toBeDisabled();
  });

  it('should disable remove button during upload', () => {
    const files: UploadedFile[] = [
      createMockFile({ status: 'uploading', progress: 50 }),
    ];

    render(<AttachmentPreview files={files} onRemove={mockOnRemove} />);

    const removeButton = screen.getByTestId('remove-attachment-0');
    expect(removeButton).toBeDisabled();
  });

  it('should have correct accessibility attributes', () => {
    const files: UploadedFile[] = [createMockFile({ name: 'document.pdf' })];

    render(<AttachmentPreview files={files} onRemove={mockOnRemove} />);

    const container = screen.getByTestId('attachment-preview');
    expect(container).toHaveAttribute('role', 'list');
    expect(container).toHaveAttribute('aria-label', 'File allegati');

    const removeButton = screen.getByTestId('remove-attachment-0');
    expect(removeButton).toHaveAttribute('aria-label', 'Rimuovi document.pdf');
  });

  it('should display correct icons for different file types', () => {
    const files: UploadedFile[] = [
      createMockFile({ id: 'pdf', name: 'doc.pdf', type: 'application/pdf' }),
    ];

    render(<AttachmentPreview files={files} onRemove={mockOnRemove} />);

    // PDF icon should be present
    expect(screen.getByLabelText('PDF')).toBeInTheDocument();
  });

  it('should handle multiple file types with correct icons', () => {
    const files: UploadedFile[] = [
      createMockFile({ id: 'pdf', name: 'doc.pdf' }),
      createMockFile({ id: 'xlsx', name: 'data.xlsx' }),
      createMockFile({ id: 'jpg', name: 'image.jpg' }),
    ];

    render(<AttachmentPreview files={files} onRemove={mockOnRemove} />);

    expect(screen.getByLabelText('PDF')).toBeInTheDocument();
    expect(screen.getByLabelText('Foglio di calcolo')).toBeInTheDocument();
    expect(screen.getByLabelText('Immagine')).toBeInTheDocument();
  });
});
