'use client';

import { useRef, useCallback } from 'react';

const STORAGE_KEY = 'pratiko_input_history';
const MAX_ENTRIES = 10;

function readHistory(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeHistory(entries: string[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    /* quota exceeded or private mode — ignore */
  }
}

interface UseInputHistoryReturn {
  addToHistory: (message: string) => void;
  navigateUp: (currentInput: string) => string | null;
  navigateDown: () => string | null;
  resetNavigation: () => void;
}

/**
 * Terminal-style input history backed by localStorage.
 *
 * - Stores the last 10 unique user messages (newest first).
 * - ArrowUp/Down navigates; the current draft is preserved.
 * - Reads localStorage lazily on each navigation (handles multi-tab).
 */
export function useInputHistory(): UseInputHistoryReturn {
  // -1 = not navigating, 0 = most recent, etc.
  const indexRef = useRef(-1);
  const draftRef = useRef('');

  const addToHistory = useCallback((message: string) => {
    const trimmed = message.trim();
    if (!trimmed) return;
    const history = readHistory();
    // Remove duplicates, then prepend
    const deduped = history.filter(h => h !== trimmed);
    deduped.unshift(trimmed);
    writeHistory(deduped.slice(0, MAX_ENTRIES));
  }, []);

  const navigateUp = useCallback((currentInput: string): string | null => {
    const history = readHistory();
    if (history.length === 0) return null;

    if (indexRef.current === -1) {
      // First press: save draft, jump to newest entry
      draftRef.current = currentInput;
      indexRef.current = 0;
      return history[0];
    }

    // Already navigating: go older
    const nextIndex = indexRef.current + 1;
    if (nextIndex >= history.length) return null; // already at oldest
    indexRef.current = nextIndex;
    return history[nextIndex];
  }, []);

  const navigateDown = useCallback((): string | null => {
    if (indexRef.current <= -1) return null; // not navigating

    const nextIndex = indexRef.current - 1;
    if (nextIndex < 0) {
      // Back to draft
      indexRef.current = -1;
      return draftRef.current;
    }

    const history = readHistory();
    indexRef.current = nextIndex;
    return history[nextIndex] ?? draftRef.current;
  }, []);

  const resetNavigation = useCallback(() => {
    indexRef.current = -1;
    draftRef.current = '';
  }, []);

  return { addToHistory, navigateUp, navigateDown, resetNavigation };
}
