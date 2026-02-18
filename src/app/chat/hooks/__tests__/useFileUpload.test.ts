/**
 * @jest-environment jsdom
 */
import { renderHook, act } from '@testing-library/react';
import { useFileUpload } from '../useFileUpload';
import * as documentsApi from '@/lib/api/documents';

// Mock the documents API
jest.mock('@/lib/api/documents', () => ({
  uploadDocument: jest.fn(),
  validateFile: jest.fn(),
  validateFileCount: jest.fn(),
  MAX_FILES_PER_MESSAGE: 5,
}));

const mockUploadDocument = documentsApi.uploadDocument as jest.Mock;
const mockValidateFile = documentsApi.validateFile as jest.Mock;
const mockValidateFileCount = documentsApi.validateFileCount as jest.Mock;

describe('useFileUpload', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default to valid file
    mockValidateFile.mockReturnValue({ valid: true });
    mockValidateFileCount.mockReturnValue({ valid: true });
  });

  it('should initialize with empty state', () => {
    const { result } = renderHook(() => useFileUpload());

    expect(result.current.files).toEqual([]);
    expect(result.current.uploading).toBe(false);
    expect(result.current.hasFiles).toBe(false);
    expect(result.current.hasUploading).toBe(false);
    expect(result.current.isAtLimit).toBe(false);
    expect(result.current.getAttachmentIds()).toEqual([]);
  });

  it('should upload file successfully', async () => {
    mockUploadDocument.mockResolvedValueOnce({
      id: 'doc-123',
      filename: 'test.pdf',
      content_type: 'application/pdf',
      size: 1000,
      created_at: '2024-01-01T00:00:00Z',
    });

    const { result } = renderHook(() => useFileUpload());
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });

    await act(async () => {
      await result.current.uploadFile(file);
    });

    expect(result.current.files).toHaveLength(1);
    expect(result.current.files[0].id).toBe('doc-123');
    expect(result.current.files[0].status).toBe('success');
    expect(result.current.files[0].name).toBe('test.pdf');
    expect(result.current.hasFiles).toBe(true);
  });

  it('should handle upload error', async () => {
    mockUploadDocument.mockRejectedValueOnce(new Error('Upload failed'));

    const { result } = renderHook(() => useFileUpload());
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });

    await act(async () => {
      await result.current.uploadFile(file);
    });

    expect(result.current.files).toHaveLength(1);
    expect(result.current.files[0].status).toBe('error');
    expect(result.current.files[0].error).toBe('Upload failed');
  });

  it('should reject invalid file type', async () => {
    mockValidateFile.mockReturnValue({ valid: false, error: 'Tipo di file non supportato' });

    const { result } = renderHook(() => useFileUpload());
    const file = new File(['content'], 'test.exe', { type: 'application/x-executable' });

    await act(async () => {
      await result.current.uploadFile(file);
    });

    expect(result.current.files).toHaveLength(1);
    expect(result.current.files[0].status).toBe('error');
    expect(result.current.files[0].error).toBe('Tipo di file non supportato');
    expect(mockUploadDocument).not.toHaveBeenCalled();
  });

  it('should reject when file count limit reached', async () => {
    mockValidateFileCount.mockReturnValue({ valid: false, error: 'Massimo 5 file per messaggio' });

    const { result } = renderHook(() => useFileUpload());
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });

    await act(async () => {
      await result.current.uploadFile(file);
    });

    expect(result.current.files).toHaveLength(1);
    expect(result.current.files[0].status).toBe('error');
    expect(result.current.files[0].error).toBe('Massimo 5 file per messaggio');
    expect(mockUploadDocument).not.toHaveBeenCalled();
  });

  it('should remove file by index', async () => {
    mockUploadDocument
      .mockResolvedValueOnce({ id: 'doc-1', filename: 'file1.pdf', content_type: 'application/pdf', size: 100, created_at: '' })
      .mockResolvedValueOnce({ id: 'doc-2', filename: 'file2.pdf', content_type: 'application/pdf', size: 100, created_at: '' });

    const { result } = renderHook(() => useFileUpload());

    await act(async () => {
      await result.current.uploadFile(new File([''], 'file1.pdf', { type: 'application/pdf' }));
    });

    await act(async () => {
      await result.current.uploadFile(new File([''], 'file2.pdf', { type: 'application/pdf' }));
    });

    expect(result.current.files).toHaveLength(2);

    act(() => {
      result.current.removeFile(0);
    });

    expect(result.current.files).toHaveLength(1);
    expect(result.current.files[0].id).toBe('doc-2');
  });

  it('should clear all files', async () => {
    mockUploadDocument.mockResolvedValue({ id: 'doc-1', filename: 'file1.pdf', content_type: 'application/pdf', size: 100, created_at: '' });

    const { result } = renderHook(() => useFileUpload());

    await act(async () => {
      await result.current.uploadFile(new File([''], 'file1.pdf', { type: 'application/pdf' }));
    });

    expect(result.current.files).toHaveLength(1);

    act(() => {
      result.current.clearFiles();
    });

    expect(result.current.files).toHaveLength(0);
    expect(result.current.hasFiles).toBe(false);
  });

  it('should return only successful upload IDs', async () => {
    mockUploadDocument.mockResolvedValueOnce({ id: 'doc-1', filename: 'file1.pdf', content_type: 'application/pdf', size: 100, created_at: '' });

    const { result } = renderHook(() => useFileUpload());

    // Upload successful file
    await act(async () => {
      await result.current.uploadFile(new File([''], 'file1.pdf', { type: 'application/pdf' }));
    });

    // Upload error file
    mockValidateFile.mockReturnValueOnce({ valid: false, error: 'Invalid' });
    await act(async () => {
      await result.current.uploadFile(new File([''], 'bad.exe', { type: '' }));
    });

    const attachmentIds = result.current.getAttachmentIds();
    expect(attachmentIds).toEqual(['doc-1']);
  });

  it('should track uploading state', async () => {
    let resolveUpload: (value: any) => void;
    const uploadPromise = new Promise((resolve) => {
      resolveUpload = resolve;
    });
    mockUploadDocument.mockReturnValue(uploadPromise);

    const { result } = renderHook(() => useFileUpload());
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });

    // Start upload
    act(() => {
      result.current.uploadFile(file);
    });

    // Check uploading state
    expect(result.current.hasUploading).toBe(true);
    expect(result.current.files[0].status).toBe('uploading');

    // Complete upload
    await act(async () => {
      resolveUpload!({ id: 'doc-123', filename: 'test.pdf', content_type: 'application/pdf', size: 100, created_at: '' });
      await uploadPromise;
    });

    expect(result.current.hasUploading).toBe(false);
    expect(result.current.files[0].status).toBe('success');
  });

  it('should check if at file limit', async () => {
    const { result } = renderHook(() => useFileUpload());

    // Initially not at limit
    expect(result.current.isAtLimit).toBe(false);

    // Mock 5 files uploaded
    mockUploadDocument.mockResolvedValue({ id: 'doc', filename: 'f.pdf', content_type: 'application/pdf', size: 100, created_at: '' });

    for (let i = 0; i < 5; i++) {
      await act(async () => {
        await result.current.uploadFile(new File([''], `file${i}.pdf`, { type: 'application/pdf' }));
      });
    }

    expect(result.current.files).toHaveLength(5);
    expect(result.current.isAtLimit).toBe(true);
  });
});
