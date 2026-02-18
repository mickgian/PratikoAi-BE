'use client';

import React, { useRef, useCallback } from 'react';
import { Paperclip } from 'lucide-react';
import { ACCEPTED_FILE_EXTENSIONS } from '@/lib/api/documents';

interface FileAttachmentProps {
  /** Callback when files are selected */
  onFilesSelected: (files: File[]) => void;
  /** Whether the button is disabled */
  disabled?: boolean;
  /** Whether file limit is reached */
  isAtLimit?: boolean;
}

/**
 * File attachment button component
 * Provides a paperclip button to select files for upload
 */
export function FileAttachment({
  onFilesSelected,
  disabled = false,
  isAtLimit = false,
}: FileAttachmentProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = useCallback(() => {
    if (!disabled && !isAtLimit && fileInputRef.current) {
      fileInputRef.current.click();
    }
  }, [disabled, isAtLimit]);

  const handleFileChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const files = event.target.files;
      if (files && files.length > 0) {
        onFilesSelected(Array.from(files));
        // Reset input to allow selecting the same file again
        event.target.value = '';
      }
    },
    [onFilesSelected]
  );

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLButtonElement>) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        handleClick();
      }
    },
    [handleClick]
  );

  const acceptedTypes = ACCEPTED_FILE_EXTENSIONS.join(',');
  const isDisabled = disabled || isAtLimit;

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        disabled={isDisabled}
        className={`
          flex items-center justify-center
          p-2 rounded-lg
          transition-all duration-200
          focus:outline-none focus:ring-2 focus:ring-[#D8D1C8]
          ${
            isDisabled
              ? 'text-[#C4BDB4]/50 cursor-not-allowed'
              : 'text-[#6B7280] hover:text-[#2F3E46] hover:bg-[#D8D1C8]/30'
          }
        `}
        aria-label="Allega file"
        title={isAtLimit ? 'Massimo 5 file per messaggio' : 'Allega file'}
        data-testid="file-attachment-button"
      >
        <Paperclip className="w-5 h-5" aria-hidden="true" />
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept={acceptedTypes}
        onChange={handleFileChange}
        multiple
        className="hidden"
        aria-hidden="true"
        data-testid="file-input"
      />
    </>
  );
}
