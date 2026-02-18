'use client';

import React from 'react';
import type { Message, AttachmentInfo } from '../types/chat';
import { formatFileSize, getFileIcon } from '@/lib/api/documents';
import { FileText, FileSpreadsheet, FileImage, File } from 'lucide-react';

interface UserMessageProps {
  message: Message;
}

/**
 * Get the icon component for a file type (simplified version for message display)
 */
function AttachmentIcon({ filename }: { filename: string }) {
  const iconType = getFileIcon(filename);
  const iconClass = 'w-3.5 h-3.5 flex-shrink-0';

  switch (iconType) {
    case 'pdf':
      return (
        <FileText className={`${iconClass} text-red-600`} aria-hidden="true" />
      );
    case 'excel':
    case 'csv':
      return (
        <FileSpreadsheet
          className={`${iconClass} text-green-700`}
          aria-hidden="true"
        />
      );
    case 'xml':
      return (
        <FileText
          className={`${iconClass} text-orange-600`}
          aria-hidden="true"
        />
      );
    case 'word':
      return (
        <FileText className={`${iconClass} text-blue-600`} aria-hidden="true" />
      );
    case 'image':
      return (
        <FileImage
          className={`${iconClass} text-purple-600`}
          aria-hidden="true"
        />
      );
    default:
      return (
        <File className={`${iconClass} text-gray-600`} aria-hidden="true" />
      );
  }
}

/**
 * Single attachment chip for display in user message
 */
function MessageAttachmentChip({ attachment }: { attachment: AttachmentInfo }) {
  // Truncate filename if too long (show more of the filename)
  const displayName =
    attachment.filename.length > 35
      ? attachment.filename.slice(0, 32) + '...'
      : attachment.filename;

  return (
    <div
      className="
        inline-flex items-center gap-1.5
        px-2 py-1
        rounded-md
        text-xs
        bg-[#c49a6c]
        text-[#1E293B]
      "
      title={attachment.filename}
      data-testid="message-attachment"
    >
      <AttachmentIcon filename={attachment.filename} />
      <span className="truncate max-w-[200px]">{displayName}</span>
      {attachment.size && (
        <span className="text-[#4a3f35] text-[10px]">
          {formatFileSize(attachment.size)}
        </span>
      )}
    </div>
  );
}

/**
 * UserMessage component for displaying user messages
 * Implements CHAT_REQUIREMENTS.md Section 2 user message specifications
 *
 * Features:
 * - Right-aligned (ml-auto)
 * - Background: #d4a574 (Oro Antico)
 * - Max-width: 280px
 * - Border-radius: 16px with bottom-right squared
 * - Text color: #1E293B (Dark Slate)
 * - Subtle shadow for depth
 * - Preserves line breaks in content
 * - Displays attached files as chips
 */
export function UserMessage({ message }: UserMessageProps) {
  const hasAttachments = message.attachments && message.attachments.length > 0;

  return (
    <div
      data-testid="user-message"
      role="region"
      aria-label="Messaggio dell'utente"
      tabIndex={0}
      className="
          bg-[#d4a574]
          ml-auto
          max-w-[280px]
          p-3
          rounded-2xl
          rounded-br-md
          shadow-sm
        "
    >
      {/* Attachment chips */}
      {hasAttachments && (
        <div
          className="flex flex-wrap gap-1.5 mb-2"
          data-testid="message-attachments"
          aria-label="File allegati"
        >
          {message.attachments!.map(attachment => (
            <MessageAttachmentChip
              key={attachment.id}
              attachment={attachment}
            />
          ))}
        </div>
      )}

      {/* Message text */}
      <div
        data-testid="user-message-text"
        aria-describedby={`timestamp-${message.id}`}
        className="
            text-[#1E293B]
            text-sm
            leading-relaxed
            font-normal
            break-words
            whitespace-pre-wrap
          "
      >
        {message.content}
      </div>
    </div>
  );
}
