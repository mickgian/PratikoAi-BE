'use client';

import React from 'react';
import { X, FileText, FileSpreadsheet, FileImage, File, AlertCircle, Loader2 } from 'lucide-react';
import { getFileIcon, formatFileSize, type UploadedFile } from '@/lib/api/documents';

interface AttachmentPreviewProps {
  /** List of uploaded files to display */
  files: UploadedFile[];
  /** Callback to remove a file by index */
  onRemove: (index: number) => void;
  /** Whether removal is disabled (e.g., during send) */
  disabled?: boolean;
}

/**
 * Get the icon component for a file type
 */
function FileIcon({ filename }: { filename: string }) {
  const iconType = getFileIcon(filename);

  const iconClass = 'w-4 h-4 flex-shrink-0';

  switch (iconType) {
    case 'pdf':
      return <FileText className={`${iconClass} text-red-500`} aria-label="PDF" />;
    case 'excel':
    case 'csv':
      return <FileSpreadsheet className={`${iconClass} text-green-600`} aria-label="Foglio di calcolo" />;
    case 'xml':
      return <FileText className={`${iconClass} text-orange-500`} aria-label="XML" />;
    case 'word':
      return <FileText className={`${iconClass} text-blue-500`} aria-label="Documento Word" />;
    case 'image':
      return <FileImage className={`${iconClass} text-purple-500`} aria-label="Immagine" />;
    default:
      return <File className={`${iconClass} text-gray-500`} aria-label="File" />;
  }
}

/**
 * Single attachment chip component
 */
function AttachmentChip({
  file,
  index,
  onRemove,
  disabled,
}: {
  file: UploadedFile;
  index: number;
  onRemove: (index: number) => void;
  disabled?: boolean;
}) {
  const isUploading = file.status === 'uploading';
  const isError = file.status === 'error';

  // Truncate filename if too long
  const displayName =
    file.name.length > 25 ? file.name.slice(0, 22) + '...' : file.name;

  // For errors, show the chip differently with error below
  if (isError) {
    return (
      <div
        className="flex flex-col gap-1"
        data-testid={`attachment-chip-${index}`}
        role="listitem"
      >
        <div
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm bg-red-50 border border-red-300 text-red-700"
        >
          <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" aria-label="Errore" />
          <span className="truncate max-w-[150px]" title={file.name}>
            {displayName}
          </span>
          <button
            type="button"
            onClick={() => onRemove(index)}
            disabled={disabled}
            className="p-0.5 rounded-full transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-red-300 text-red-400 hover:text-red-600 hover:bg-red-100"
            aria-label={`Rimuovi ${file.name}`}
            data-testid={`remove-attachment-${index}`}
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
        <span
          className="text-xs text-red-600 px-3 max-w-[280px]"
          data-testid={`attachment-error-${index}`}
        >
          {file.error}
        </span>
      </div>
    );
  }

  return (
    <div
      className={`
        inline-flex items-center gap-2
        px-3 py-1.5 rounded-lg
        text-sm
        transition-all duration-200
        ${
          isUploading
            ? 'bg-[#F8F5F1] border border-[#C4BDB4]/50 text-[#6B7280]'
            : 'bg-[#F8F5F1] border border-[#C4BDB4]/50 text-[#374151] hover:border-[#9A8F86]'
        }
      `}
      data-testid={`attachment-chip-${index}`}
      role="listitem"
    >
      {/* Icon or loading spinner */}
      {isUploading ? (
        <Loader2 className="w-4 h-4 animate-spin text-[#6B7280]" aria-label="Caricamento in corso" />
      ) : (
        <FileIcon filename={file.name} />
      )}

      {/* File name */}
      <span className="truncate max-w-[150px]" title={file.name}>
        {displayName}
      </span>

      {/* File size or progress */}
      <span className="text-xs text-[#9A8F86]">
        {isUploading && typeof file.progress === 'number'
          ? `${file.progress}%`
          : formatFileSize(file.size)}
      </span>

      {/* Remove button */}
      <button
        type="button"
        onClick={() => onRemove(index)}
        disabled={disabled || isUploading}
        className={`
          p-0.5 rounded-full
          transition-all duration-200
          focus:outline-none focus:ring-2 focus:ring-[#D8D1C8]
          ${
            disabled || isUploading
              ? 'text-[#C4BDB4]/50 cursor-not-allowed'
              : 'text-[#9A8F86] hover:text-[#374151] hover:bg-[#D8D1C8]/30'
          }
        `}
        aria-label={`Rimuovi ${file.name}`}
        data-testid={`remove-attachment-${index}`}
      >
        <X className="w-4 h-4" aria-hidden="true" />
      </button>
    </div>
  );
}

/**
 * Attachment preview component
 * Displays uploaded files as chips with remove buttons
 */
export function AttachmentPreview({ files, onRemove, disabled = false }: AttachmentPreviewProps) {
  if (files.length === 0) {
    return null;
  }

  return (
    <div
      className="flex flex-wrap gap-2 mb-3"
      role="list"
      aria-label="File allegati"
      data-testid="attachment-preview"
    >
      {files.map((file, index) => (
        <AttachmentChip
          key={file.id}
          file={file}
          index={index}
          onRemove={onRemove}
          disabled={disabled}
        />
      ))}
    </div>
  );
}
