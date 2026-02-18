'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Upload } from 'lucide-react';
import { isValidFileType } from '@/lib/api/documents';

interface DragDropZoneProps {
  /** Child elements to render inside the zone */
  children: React.ReactNode;
  /** Callback when files are dropped */
  onFilesDropped: (files: File[]) => void;
  /** Whether drag-drop is disabled */
  disabled?: boolean;
}

/**
 * Drag and drop zone wrapper component
 * Provides visual feedback when files are dragged over the chat area
 */
export function DragDropZone({
  children,
  onFilesDropped,
  disabled = false,
}: DragDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const dragCounterRef = useRef(0);

  // Reset drag state when disabled changes
  useEffect(() => {
    if (disabled) {
      setIsDragging(false);
      dragCounterRef.current = 0;
    }
  }, [disabled]);

  const handleDragEnter = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();

      if (disabled) return;

      dragCounterRef.current++;
      if (event.dataTransfer.types.includes('Files')) {
        setIsDragging(true);
      }
    },
    [disabled]
  );

  const handleDragLeave = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();

      if (disabled) return;

      dragCounterRef.current--;
      if (dragCounterRef.current === 0) {
        setIsDragging(false);
      }
    },
    [disabled]
  );

  const handleDragOver = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();

      if (disabled) return;

      // Set the dropEffect to show it's a valid drop target
      if (event.dataTransfer.types.includes('Files')) {
        event.dataTransfer.dropEffect = 'copy';
      }
    },
    [disabled]
  );

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();

      setIsDragging(false);
      dragCounterRef.current = 0;

      if (disabled) return;

      const files = Array.from(event.dataTransfer.files);
      if (files.length > 0) {
        // Filter to only valid file types
        const validFiles = files.filter(isValidFileType);
        if (validFiles.length > 0) {
          onFilesDropped(validFiles);
        }
      }
    },
    [disabled, onFilesDropped]
  );

  return (
    <div
      className="relative"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      data-testid="drag-drop-zone"
    >
      {children}

      {/* Drag overlay */}
      {isDragging && !disabled && (
        <div
          className="
            absolute inset-0
            bg-[#2F3E46]/10
            border-2 border-dashed border-[#2F3E46]
            rounded-lg
            flex flex-col items-center justify-center
            z-50
            pointer-events-none
          "
          data-testid="drag-overlay"
          aria-live="polite"
        >
          <div className="bg-white/90 backdrop-blur-sm rounded-lg p-6 shadow-lg flex flex-col items-center">
            <Upload className="w-10 h-10 text-[#2F3E46] mb-3" aria-hidden="true" />
            <p className="text-[#2F3E46] font-medium text-lg">
              Trascina qui i file
            </p>
            <p className="text-[#6B7280] text-sm mt-1">
              PDF, Excel, CSV, XML, Word, Immagini
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
