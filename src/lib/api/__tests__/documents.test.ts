/**
 * @jest-environment jsdom
 */
import {
  uploadDocument,
  isValidFileType,
  isValidFileSize,
  validateFile,
  validateFileCount,
  getFileIcon,
  formatFileSize,
  MAX_FILE_SIZE,
  MAX_FILES_PER_MESSAGE,
  ACCEPTED_FILE_EXTENSIONS,
} from '../documents';

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock XMLHttpRequest
const mockXHRInstance = {
  open: jest.fn(),
  send: jest.fn(),
  setRequestHeader: jest.fn(),
  upload: {
    addEventListener: jest.fn(),
  },
  addEventListener: jest.fn(),
  status: 200,
  responseText: '',
};
const mockXHR = jest.fn(() => mockXHRInstance);
(global as any).XMLHttpRequest = mockXHR;

describe('documents API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.getItem.mockReturnValue('test-session-token');
  });

  describe('isValidFileType', () => {
    it('should accept PDF files', () => {
      const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
      expect(isValidFileType(file)).toBe(true);
    });

    it('should accept Excel files (.xlsx)', () => {
      const file = new File(['content'], 'test.xlsx', {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      expect(isValidFileType(file)).toBe(true);
    });

    it('should accept Excel files (.xls)', () => {
      const file = new File(['content'], 'test.xls', {
        type: 'application/vnd.ms-excel',
      });
      expect(isValidFileType(file)).toBe(true);
    });

    it('should accept CSV files', () => {
      const file = new File(['content'], 'test.csv', { type: 'text/csv' });
      expect(isValidFileType(file)).toBe(true);
    });

    it('should accept XML files', () => {
      const file = new File(['content'], 'test.xml', { type: 'application/xml' });
      expect(isValidFileType(file)).toBe(true);
    });

    it('should accept Word files (.docx)', () => {
      const file = new File(['content'], 'test.docx', {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      });
      expect(isValidFileType(file)).toBe(true);
    });

    it('should accept JPEG images', () => {
      const file = new File(['content'], 'test.jpg', { type: 'image/jpeg' });
      expect(isValidFileType(file)).toBe(true);
    });

    it('should accept PNG images', () => {
      const file = new File(['content'], 'test.png', { type: 'image/png' });
      expect(isValidFileType(file)).toBe(true);
    });

    it('should reject unsupported file types', () => {
      const file = new File(['content'], 'test.exe', { type: 'application/x-executable' });
      expect(isValidFileType(file)).toBe(false);
    });

    it('should accept files by extension when MIME type is empty', () => {
      const file = new File(['content'], 'test.pdf', { type: '' });
      expect(isValidFileType(file)).toBe(true);
    });
  });

  describe('isValidFileSize', () => {
    it('should accept files under 10 MB', () => {
      const content = new Uint8Array(5 * 1024 * 1024); // 5 MB
      const file = new File([content], 'test.pdf', { type: 'application/pdf' });
      expect(isValidFileSize(file)).toBe(true);
    });

    it('should accept files exactly 10 MB', () => {
      const content = new Uint8Array(10 * 1024 * 1024); // 10 MB
      const file = new File([content], 'test.pdf', { type: 'application/pdf' });
      expect(isValidFileSize(file)).toBe(true);
    });

    it('should reject files over 10 MB', () => {
      const content = new Uint8Array(11 * 1024 * 1024); // 11 MB
      const file = new File([content], 'test.pdf', { type: 'application/pdf' });
      expect(isValidFileSize(file)).toBe(false);
    });
  });

  describe('validateFile', () => {
    it('should return valid for supported file under size limit', () => {
      const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
      const result = validateFile(file);
      expect(result.valid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('should return error for unsupported file type', () => {
      const file = new File(['content'], 'test.exe', { type: 'application/x-executable' });
      const result = validateFile(file);
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Tipo di file non supportato');
    });

    it('should return error for file over size limit', () => {
      const content = new Uint8Array(11 * 1024 * 1024);
      const file = new File([content], 'test.pdf', { type: 'application/pdf' });
      const result = validateFile(file);
      expect(result.valid).toBe(false);
      expect(result.error).toBe('File troppo grande (max 10 MB)');
    });
  });

  describe('validateFileCount', () => {
    it('should return valid when under limit', () => {
      const result = validateFileCount(3);
      expect(result.valid).toBe(true);
    });

    it('should return error when at limit', () => {
      const result = validateFileCount(5);
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Massimo 5 file per messaggio');
    });

    it('should return error when over limit', () => {
      const result = validateFileCount(6);
      expect(result.valid).toBe(false);
    });
  });

  describe('getFileIcon', () => {
    it('should return pdf icon for PDF files', () => {
      expect(getFileIcon('document.pdf')).toBe('pdf');
    });

    it('should return excel icon for Excel files', () => {
      expect(getFileIcon('data.xlsx')).toBe('excel');
      expect(getFileIcon('data.xls')).toBe('excel');
    });

    it('should return csv icon for CSV files', () => {
      expect(getFileIcon('data.csv')).toBe('csv');
    });

    it('should return xml icon for XML files', () => {
      expect(getFileIcon('config.xml')).toBe('xml');
    });

    it('should return word icon for Word files', () => {
      expect(getFileIcon('document.docx')).toBe('word');
    });

    it('should return image icon for images', () => {
      expect(getFileIcon('photo.jpg')).toBe('image');
      expect(getFileIcon('photo.jpeg')).toBe('image');
      expect(getFileIcon('photo.png')).toBe('image');
    });

    it('should return file icon for unknown types', () => {
      expect(getFileIcon('unknown.xyz')).toBe('file');
    });
  });

  describe('formatFileSize', () => {
    it('should format bytes', () => {
      expect(formatFileSize(500)).toBe('500 B');
    });

    it('should format kilobytes', () => {
      expect(formatFileSize(1024)).toBe('1.0 KB');
      expect(formatFileSize(2560)).toBe('2.5 KB');
    });

    it('should format megabytes', () => {
      expect(formatFileSize(1024 * 1024)).toBe('1.0 MB');
      expect(formatFileSize(2.5 * 1024 * 1024)).toBe('2.5 MB');
    });
  });

  describe('uploadDocument', () => {
    it('should throw error when file type is invalid', async () => {
      const file = new File(['content'], 'test.exe', { type: 'application/x-executable' });

      await expect(uploadDocument(file)).rejects.toThrow('Tipo di file non supportato');
    });

    it('should throw error when file is too large', async () => {
      const content = new Uint8Array(11 * 1024 * 1024);
      const file = new File([content], 'test.pdf', { type: 'application/pdf' });

      await expect(uploadDocument(file)).rejects.toThrow('File troppo grande (max 10 MB)');
    });

    it('should throw error when no session token and no access token', async () => {
      mockLocalStorage.getItem.mockReturnValue(null);
      const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });

      await expect(uploadDocument(file)).rejects.toThrow('Sessione non valida');
    });

    it('should use access_token when current_session_token is not available', async () => {
      // current_session_token is null, but access_token is available
      mockLocalStorage.getItem.mockImplementation((key: string) => {
        if (key === 'current_session_token') return null;
        if (key === 'access_token') return 'fallback-access-token';
        return null;
      });

      const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
      const mockUploadedDocument = {
        id: 'doc-123',
        original_filename: 'test.pdf',
        file_type: 'pdf',
        file_size: 7,
        file_size_mb: 0.000007,
        status: 'processed',
        upload_timestamp: '2024-01-01T00:00:00Z',
        expires_at: '2024-01-02T00:00:00Z',
      };
      const mockResponse = {
        success: true,
        uploaded_documents: [mockUploadedDocument],
        total_uploaded: 1,
        errors: [],
        message: 'Upload successful',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await uploadDocument(file);

      expect(result).toEqual(mockUploadedDocument);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/documents/upload'),
        expect.objectContaining({
          headers: {
            Authorization: 'Bearer fallback-access-token',
          },
        })
      );
    });

    it('should prioritize current_session_token over access_token', async () => {
      // Both tokens available, should use current_session_token
      mockLocalStorage.getItem.mockImplementation((key: string) => {
        if (key === 'current_session_token') return 'session-token-priority';
        if (key === 'access_token') return 'access-token-secondary';
        return null;
      });

      const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
      const mockUploadedDocument = {
        id: 'doc-456',
        original_filename: 'test.pdf',
        file_type: 'pdf',
        file_size: 7,
        file_size_mb: 0.000007,
        status: 'processed',
        upload_timestamp: '2024-01-01T00:00:00Z',
        expires_at: '2024-01-02T00:00:00Z',
      };
      const mockResponse = {
        success: true,
        uploaded_documents: [mockUploadedDocument],
        total_uploaded: 1,
        errors: [],
        message: 'Upload successful',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await uploadDocument(file);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/documents/upload'),
        expect.objectContaining({
          headers: {
            Authorization: 'Bearer session-token-priority',
          },
        })
      );
    });

    it('should upload file successfully', async () => {
      const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
      const mockUploadedDocument = {
        id: 'doc-123',
        original_filename: 'test.pdf',
        file_type: 'pdf',
        file_size: 7,
        file_size_mb: 0.000007,
        status: 'processed',
        upload_timestamp: '2024-01-01T00:00:00Z',
        expires_at: '2024-01-02T00:00:00Z',
      };
      const mockResponse = {
        success: true,
        uploaded_documents: [mockUploadedDocument],
        total_uploaded: 1,
        errors: [],
        message: 'Upload successful',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await uploadDocument(file);

      expect(result).toEqual(mockUploadedDocument);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/documents/upload'),
        expect.objectContaining({
          method: 'POST',
          headers: {
            Authorization: 'Bearer test-session-token',
          },
        })
      );
    });

    it('should handle upload error', async () => {
      const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Server error' }),
      });

      await expect(uploadDocument(file)).rejects.toThrow('Server error');
    });
  });

  describe('constants', () => {
    it('should have correct max file size (10 MB)', () => {
      expect(MAX_FILE_SIZE).toBe(10 * 1024 * 1024);
    });

    it('should have correct max files per message', () => {
      expect(MAX_FILES_PER_MESSAGE).toBe(5);
    });

    it('should have all expected file extensions', () => {
      expect(ACCEPTED_FILE_EXTENSIONS).toContain('.pdf');
      expect(ACCEPTED_FILE_EXTENSIONS).toContain('.xlsx');
      expect(ACCEPTED_FILE_EXTENSIONS).toContain('.xls');
      expect(ACCEPTED_FILE_EXTENSIONS).toContain('.csv');
      expect(ACCEPTED_FILE_EXTENSIONS).toContain('.xml');
      expect(ACCEPTED_FILE_EXTENSIONS).toContain('.docx');
      expect(ACCEPTED_FILE_EXTENSIONS).toContain('.jpg');
      expect(ACCEPTED_FILE_EXTENSIONS).toContain('.jpeg');
      expect(ACCEPTED_FILE_EXTENSIONS).toContain('.png');
    });
  });
});
