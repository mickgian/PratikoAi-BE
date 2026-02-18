/**
 * @file Document Upload API Client
 * @description API integration for file attachments in chat
 * Implements upload-first pattern: upload file -> get document ID -> send with chat
 */

// ============================================================================
// TypeScript Interfaces
// ============================================================================

/**
 * Supported file types for upload
 */
export const SUPPORTED_FILE_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.ms-excel': ['.xls'],
  'text/csv': ['.csv'],
  'application/xml': ['.xml'],
  'text/xml': ['.xml'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
} as const;

/**
 * File extensions accepted for upload
 */
export const ACCEPTED_FILE_EXTENSIONS = [
  '.pdf',
  '.xlsx',
  '.xls',
  '.csv',
  '.xml',
  '.docx',
  '.jpg',
  '.jpeg',
  '.png',
] as const;

/**
 * Maximum file size in bytes (10 MB)
 */
export const MAX_FILE_SIZE = 10 * 1024 * 1024;

/**
 * Maximum number of files per message
 */
export const MAX_FILES_PER_MESSAGE = 5;

/**
 * Single uploaded document from backend
 */
export interface UploadedDocument {
  /** Unique document ID (UUID) */
  id: string;
  /** Original filename */
  original_filename: string;
  /** File type (pdf, excel, etc.) */
  file_type: string;
  /** File size in bytes */
  file_size: number;
  /** File size in MB */
  file_size_mb: number;
  /** Processing status */
  status: string;
  /** Upload timestamp */
  upload_timestamp: string;
  /** Expiration timestamp */
  expires_at: string;
}

/**
 * Response from document upload endpoint
 */
export interface UploadDocumentResponse {
  /** Whether upload was successful */
  success: boolean;
  /** List of uploaded documents */
  uploaded_documents: UploadedDocument[];
  /** Total number of uploaded documents */
  total_uploaded: number;
  /** Any errors that occurred */
  errors: Array<{ filename: string; error: string }>;
  /** Message from backend */
  message: string;
}

/**
 * Error response from upload endpoint
 */
export interface UploadErrorResponse {
  detail: string;
  code?: string;
}

/**
 * Uploaded file with metadata for UI display
 */
export interface UploadedFile {
  /** Document ID from backend */
  id: string;
  /** Original file name */
  name: string;
  /** File size in bytes */
  size: number;
  /** MIME type */
  type: string;
  /** Upload status */
  status: 'uploading' | 'success' | 'error';
  /** Error message if failed */
  error?: string;
  /** Upload progress (0-100) */
  progress?: number;
}

// ============================================================================
// Configuration
// ============================================================================

/**
 * Get backend API base URL from environment
 */
function getApiBaseUrl(): string {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

/**
 * Get session token from localStorage
 * Tries current_session_token first, then falls back to access_token
 */
function getSessionToken(): string | null {
  if (typeof window === 'undefined') return null;
  return (
    localStorage.getItem('current_session_token') ||
    localStorage.getItem('access_token')
  );
}

// ============================================================================
// Validation Functions
// ============================================================================

/**
 * Check if file type is supported
 * @param file - File to validate
 * @returns true if file type is supported
 */
export function isValidFileType(file: File): boolean {
  const mimeType = file.type;
  const extension = '.' + file.name.split('.').pop()?.toLowerCase();

  // Check MIME type
  if (mimeType && mimeType in SUPPORTED_FILE_TYPES) {
    return true;
  }

  // Fallback to extension check
  return ACCEPTED_FILE_EXTENSIONS.includes(extension as typeof ACCEPTED_FILE_EXTENSIONS[number]);
}

/**
 * Check if file size is within limit
 * @param file - File to validate
 * @returns true if file size is within limit
 */
export function isValidFileSize(file: File): boolean {
  return file.size <= MAX_FILE_SIZE;
}

/**
 * Validate file for upload
 * @param file - File to validate
 * @returns Validation result with error message if invalid
 */
export function validateFile(file: File): { valid: boolean; error?: string } {
  if (!isValidFileType(file)) {
    return {
      valid: false,
      error: 'Tipo di file non supportato',
    };
  }

  if (!isValidFileSize(file)) {
    return {
      valid: false,
      error: 'File troppo grande (max 10 MB)',
    };
  }

  return { valid: true };
}

/**
 * Validate file count
 * @param currentCount - Current number of files
 * @returns Validation result with error message if invalid
 */
export function validateFileCount(currentCount: number): { valid: boolean; error?: string } {
  if (currentCount >= MAX_FILES_PER_MESSAGE) {
    return {
      valid: false,
      error: 'Massimo 5 file per messaggio',
    };
  }
  return { valid: true };
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Upload a document file to the backend
 *
 * @param file - File to upload
 * @param onProgress - Optional callback for upload progress (0-100)
 * @returns Uploaded document with ID
 * @throws Error if upload fails or validation fails
 *
 * @example
 * ```typescript
 * const result = await uploadDocument(file, (progress) => {
 *   console.log(`Upload progress: ${progress}%`);
 * });
 * console.log(`Document ID: ${result.id}`);
 * ```
 */
export async function uploadDocument(
  file: File,
  onProgress?: (progress: number) => void
): Promise<UploadedDocument> {
  // Validate file before upload
  const validation = validateFile(file);
  if (!validation.valid) {
    throw new Error(validation.error);
  }

  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/documents/upload`;

  const token = getSessionToken();
  if (!token) {
    throw new Error('Sessione non valida. Effettua il login.');
  }

  // Create form data - backend expects 'files' (plural)
  const formData = new FormData();
  formData.append('files', file);

  // If progress callback provided, use XMLHttpRequest for progress events
  if (onProgress) {
    return uploadWithProgress(url, formData, token, onProgress);
  }

  // Simple fetch for no progress tracking
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData: UploadErrorResponse = await response.json().catch(() => ({
      detail: `HTTP ${response.status}: ${response.statusText}`,
    }));
    throw new Error(errorData.detail || 'Errore durante il caricamento del file');
  }

  const result: UploadDocumentResponse = await response.json();

  // Check for upload errors
  if (!result.success || result.uploaded_documents.length === 0) {
    const errorMsg = result.errors?.[0]?.error || 'Errore durante il caricamento del file';
    throw new Error(errorMsg);
  }

  // Return the first uploaded document
  return result.uploaded_documents[0];
}

/**
 * Upload with progress tracking using XMLHttpRequest
 */
function uploadWithProgress(
  url: string,
  formData: FormData,
  token: string,
  onProgress: (progress: number) => void
): Promise<UploadedDocument> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        const progress = Math.round((event.loaded / event.total) * 100);
        onProgress(progress);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const result: UploadDocumentResponse = JSON.parse(xhr.responseText);

          // Check for upload errors
          if (!result.success || result.uploaded_documents.length === 0) {
            const errorMsg = result.errors?.[0]?.error || 'Errore durante il caricamento del file';
            reject(new Error(errorMsg));
            return;
          }

          // Return the first uploaded document
          resolve(result.uploaded_documents[0]);
        } catch (parseError) {
          // DEV-007: Log parsing error for debugging (individual logs to avoid Next.js interception)
          console.log('=== Upload response parsing failed ===');
          console.log('HTTP Status:', xhr.status);
          console.log('Status Text:', xhr.statusText);
          console.log('Response Length:', xhr.responseText?.length ?? 0);
          console.log('Response Preview:', xhr.responseText?.substring(0, 500) || '(empty)');
          console.log('Parse Error:', parseError instanceof Error ? parseError.message : String(parseError));
          console.log('======================================');
          reject(new Error(`Errore nel parsing della risposta (status ${xhr.status})`));
        }
      } else {
        try {
          const errorData = JSON.parse(xhr.responseText);
          reject(new Error(errorData.detail || 'Errore durante il caricamento'));
        } catch {
          reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
        }
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Errore di rete durante il caricamento'));
    });

    xhr.addEventListener('abort', () => {
      reject(new Error('Caricamento annullato'));
    });

    xhr.open('POST', url);
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.send(formData);
  });
}

/**
 * Get file icon based on file type
 * @param filename - File name with extension
 * @returns Icon identifier for the file type
 */
export function getFileIcon(filename: string): 'pdf' | 'excel' | 'csv' | 'xml' | 'word' | 'image' | 'file' {
  const extension = filename.split('.').pop()?.toLowerCase();

  switch (extension) {
    case 'pdf':
      return 'pdf';
    case 'xlsx':
    case 'xls':
      return 'excel';
    case 'csv':
      return 'csv';
    case 'xml':
      return 'xml';
    case 'docx':
      return 'word';
    case 'jpg':
    case 'jpeg':
    case 'png':
      return 'image';
    default:
      return 'file';
  }
}

/**
 * Format file size for display
 * @param bytes - File size in bytes
 * @returns Formatted string (e.g., "2.3 MB", "500 KB")
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
