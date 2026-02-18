/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { FileAttachment } from '../FileAttachment';

describe('FileAttachment', () => {
  const mockOnFilesSelected = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render the attachment button', () => {
    render(<FileAttachment onFilesSelected={mockOnFilesSelected} />);

    const button = screen.getByTestId('file-attachment-button');
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute('aria-label', 'Allega file');
  });

  it('should have Italian tooltip', () => {
    render(<FileAttachment onFilesSelected={mockOnFilesSelected} />);

    const button = screen.getByTestId('file-attachment-button');
    expect(button).toHaveAttribute('title', 'Allega file');
  });

  it('should open file picker when clicked', () => {
    render(<FileAttachment onFilesSelected={mockOnFilesSelected} />);

    const input = screen.getByTestId('file-input') as HTMLInputElement;
    const clickSpy = jest.spyOn(input, 'click');

    const button = screen.getByTestId('file-attachment-button');
    fireEvent.click(button);

    expect(clickSpy).toHaveBeenCalled();
  });

  it('should call onFilesSelected when files are selected', () => {
    render(<FileAttachment onFilesSelected={mockOnFilesSelected} />);

    const input = screen.getByTestId('file-input') as HTMLInputElement;
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });

    fireEvent.change(input, { target: { files: [file] } });

    expect(mockOnFilesSelected).toHaveBeenCalledWith([file]);
  });

  it('should accept multiple files', () => {
    render(<FileAttachment onFilesSelected={mockOnFilesSelected} />);

    const input = screen.getByTestId('file-input') as HTMLInputElement;
    expect(input).toHaveAttribute('multiple');
  });

  it('should accept correct file types', () => {
    render(<FileAttachment onFilesSelected={mockOnFilesSelected} />);

    const input = screen.getByTestId('file-input') as HTMLInputElement;
    expect(input.accept).toContain('.pdf');
    expect(input.accept).toContain('.xlsx');
    expect(input.accept).toContain('.csv');
    expect(input.accept).toContain('.xml');
    expect(input.accept).toContain('.docx');
    expect(input.accept).toContain('.jpg');
    expect(input.accept).toContain('.png');
  });

  it('should be disabled when disabled prop is true', () => {
    render(<FileAttachment onFilesSelected={mockOnFilesSelected} disabled />);

    const button = screen.getByTestId('file-attachment-button');
    expect(button).toBeDisabled();
  });

  it('should be disabled when at file limit', () => {
    render(<FileAttachment onFilesSelected={mockOnFilesSelected} isAtLimit />);

    const button = screen.getByTestId('file-attachment-button');
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('title', 'Massimo 5 file per messaggio');
  });

  it('should not open file picker when disabled', () => {
    render(<FileAttachment onFilesSelected={mockOnFilesSelected} disabled />);

    const input = screen.getByTestId('file-input') as HTMLInputElement;
    const clickSpy = jest.spyOn(input, 'click');

    const button = screen.getByTestId('file-attachment-button');
    fireEvent.click(button);

    expect(clickSpy).not.toHaveBeenCalled();
  });

  it('should handle keyboard activation (Enter)', () => {
    render(<FileAttachment onFilesSelected={mockOnFilesSelected} />);

    const input = screen.getByTestId('file-input') as HTMLInputElement;
    const clickSpy = jest.spyOn(input, 'click');

    const button = screen.getByTestId('file-attachment-button');
    fireEvent.keyDown(button, { key: 'Enter' });

    expect(clickSpy).toHaveBeenCalled();
  });

  it('should handle keyboard activation (Space)', () => {
    render(<FileAttachment onFilesSelected={mockOnFilesSelected} />);

    const input = screen.getByTestId('file-input') as HTMLInputElement;
    const clickSpy = jest.spyOn(input, 'click');

    const button = screen.getByTestId('file-attachment-button');
    fireEvent.keyDown(button, { key: ' ' });

    expect(clickSpy).toHaveBeenCalled();
  });

  it('should reset file input after selection to allow re-selecting same file', () => {
    render(<FileAttachment onFilesSelected={mockOnFilesSelected} />);

    const input = screen.getByTestId('file-input') as HTMLInputElement;
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });

    fireEvent.change(input, { target: { files: [file] } });

    expect(input.value).toBe('');
  });
});
