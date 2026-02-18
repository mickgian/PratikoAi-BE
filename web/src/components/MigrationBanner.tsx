/**
 * @file Migration Banner Component
 * @description UI banner for chat history migration from IndexedDB to PostgreSQL
 * Implements multi-device sync notification with user action
 */

'use client';

import { useState } from 'react';
import { X, Upload, Check, AlertCircle } from 'lucide-react';

interface MigrationBannerProps {
  /** Callback function to trigger migration */
  onSync: () => Promise<void>;
}

type SyncStatus = 'idle' | 'syncing' | 'success' | 'error';

/**
 * Migration Banner Component
 *
 * Displays a banner prompting users to sync their local chat history to the backend.
 * Supports multi-device sync and provides visual feedback during the process.
 *
 * @example
 * ```tsx
 * <MigrationBanner onSync={async () => {
 *   await importChatHistory(localMessages);
 * }} />
 * ```
 */
export function MigrationBanner({ onSync }: MigrationBannerProps) {
  const [isVisible, setIsVisible] = useState(true);
  const [syncStatus, setSyncStatus] = useState<SyncStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSync = async () => {
    setSyncStatus('syncing');
    setErrorMessage(null);

    try {
      await onSync();
      setSyncStatus('success');

      // Auto-hide banner after successful sync
      setTimeout(() => {
        setIsVisible(false);
      }, 3000);
    } catch (error) {
      setSyncStatus('error');
      setErrorMessage((error as Error).message || 'Sync failed');
    }
  };

  const handleClose = () => {
    setIsVisible(false);
  };

  const handleRetry = async () => {
    await handleSync();
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div
      role="alert"
      aria-live="polite"
      className="fixed bottom-0 left-0 right-0 z-50 p-4 md:bottom-4 md:left-4 md:right-auto md:max-w-md"
    >
      <div className="relative overflow-hidden rounded-lg border border-blue-200 bg-blue-50 shadow-lg dark:border-blue-800 dark:bg-blue-950">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 p-4">
          <div className="flex items-start gap-3">
            <Upload
              className="h-5 w-5 text-blue-600 dark:text-blue-400"
              aria-hidden="true"
            />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100">
                Local Chat History Detected
              </h3>
              <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">
                Sync your chat history to enable multi-device sync and automatic
                backups.
              </p>
            </div>
          </div>

          {/* Close Button */}
          <button
            onClick={handleClose}
            className="rounded-md p-1 text-blue-600 hover:bg-blue-100 dark:text-blue-400 dark:hover:bg-blue-900"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Status & Actions */}
        <div className="px-4 pb-4">
          {syncStatus === 'idle' && (
            <button
              onClick={handleSync}
              className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:bg-blue-500 dark:hover:bg-blue-600"
            >
              Sync Now
            </button>
          )}

          {syncStatus === 'syncing' && (
            <div className="flex items-center justify-center gap-2 rounded-md bg-blue-100 px-4 py-2 dark:bg-blue-900">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent dark:border-blue-400" />
              <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
                Syncing...
              </span>
            </div>
          )}

          {syncStatus === 'success' && (
            <div className="flex items-center justify-center gap-2 rounded-md bg-green-100 px-4 py-2 dark:bg-green-900">
              <Check className="h-4 w-4 text-green-600 dark:text-green-400" />
              <span className="text-sm font-medium text-green-700 dark:text-green-300">
                Successfully Synced!
              </span>
            </div>
          )}

          {syncStatus === 'error' && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 rounded-md bg-red-100 px-4 py-2 dark:bg-red-900">
                <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                <span className="text-sm font-medium text-red-700 dark:text-red-300">
                  Sync Failed: {errorMessage}
                </span>
              </div>
              <button
                onClick={handleRetry}
                className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:bg-blue-500 dark:hover:bg-blue-600"
              >
                Retry
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
