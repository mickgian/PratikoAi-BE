'use client';

import { useState, useCallback } from 'react';
import {
  uploadDocument,
  validateFile,
  validateFileCount,
  MAX_FILES_PER_MESSAGE,
  type UploadedFile,
} from '@/lib/api/documents';

/**
 * State and actions for file upload management
 */
export interface UseFileUploadReturn {
  /** List of uploaded files with their status */
  files: UploadedFile[];
  /** Whether any file is currently uploading */
  uploading: boolean;
  /** Upload a file and add to the list */
  uploadFile: (file: File) => Promise<void>;
  /** Remove a file from the list by index */
  removeFile: (index: number) => void;
  /** Clear all files from the list */
  clearFiles: () => void;
  /** Get list of document IDs for successfully uploaded files */
  getAttachmentIds: () => string[];
  /** Check if uploads are in progress */
  hasUploading: boolean;
  /** Check if there are any files */
  hasFiles: boolean;
  /** Check if file count limit is reached */
  isAtLimit: boolean;
}

/**
 * Hook for managing file uploads in chat
 *
 * @returns File upload state and actions
 *
 * @example
 * ```tsx
 * const { files, uploading, uploadFile, removeFile, clearFiles, getAttachmentIds } = useFileUpload();
 *
 * // Upload a file
 * await uploadFile(selectedFile);
 *
 * // Get IDs for chat request
 * const attachmentIds = getAttachmentIds();
 * ```
 */
export function useFileUpload(): UseFileUploadReturn {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);

  /**
   * Upload a file and add it to the list
   */
  const uploadFile = useCallback(async (file: File) => {
    // Validate file count
    const countValidation = validateFileCount(files.length);
    if (!countValidation.valid) {
      // Add as error immediately
      const errorFile: UploadedFile = {
        id: `error-${Date.now()}`,
        name: file.name,
        size: file.size,
        type: file.type,
        status: 'error',
        error: countValidation.error,
      };
      setFiles((prev) => [...prev, errorFile]);
      return;
    }

    // Validate file
    const validation = validateFile(file);
    if (!validation.valid) {
      // Add as error immediately
      const errorFile: UploadedFile = {
        id: `error-${Date.now()}`,
        name: file.name,
        size: file.size,
        type: file.type,
        status: 'error',
        error: validation.error,
      };
      setFiles((prev) => [...prev, errorFile]);
      return;
    }

    // Create placeholder entry for uploading state
    const uploadingFile: UploadedFile = {
      id: `uploading-${Date.now()}`,
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'uploading',
      progress: 0,
    };

    setFiles((prev) => [...prev, uploadingFile]);
    setUploading(true);

    try {
      const result = await uploadDocument(file, (progress) => {
        // Update progress
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadingFile.id ? { ...f, progress } : f
          )
        );
      });

      // Update with success
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadingFile.id
            ? {
                ...f,
                id: result.id,
                status: 'success' as const,
                progress: 100,
              }
            : f
        )
      );
    } catch (error) {
      // Update with error
      const errorMessage = error instanceof Error ? error.message : 'Errore durante il caricamento';
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadingFile.id
            ? {
                ...f,
                status: 'error' as const,
                error: errorMessage,
              }
            : f
        )
      );
    } finally {
      setUploading(false);
    }
  }, [files.length]);

  /**
   * Remove a file from the list by index
   */
  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  /**
   * Clear all files from the list
   */
  const clearFiles = useCallback(() => {
    setFiles([]);
  }, []);

  /**
   * Get list of document IDs for successfully uploaded files
   */
  const getAttachmentIds = useCallback((): string[] => {
    return files
      .filter((f) => f.status === 'success' && !f.id.startsWith('error-') && !f.id.startsWith('uploading-'))
      .map((f) => f.id);
  }, [files]);

  const hasUploading = files.some((f) => f.status === 'uploading');
  const hasFiles = files.length > 0;
  const isAtLimit = files.length >= MAX_FILES_PER_MESSAGE;

  return {
    files,
    uploading,
    uploadFile,
    removeFile,
    clearFiles,
    getAttachmentIds,
    hasUploading,
    hasFiles,
    isAtLimit,
  };
}
