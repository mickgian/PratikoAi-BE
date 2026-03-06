'use client';

import { useRef, useEffect, useCallback, useState } from 'react';

interface UseSmartScrollOptions {
  /** Enable auto-scroll to bottom on new messages */
  autoScroll?: boolean;
  /** Threshold in pixels to determine if user is at bottom */
  bottomThreshold?: number;
  /** Smooth scrolling behavior */
  smooth?: boolean;
}

interface UseSmartScrollReturn {
  /** Ref to attach to the scrollable container */
  scrollRef: React.RefObject<HTMLDivElement | null>;
  /** Ref to attach to the bottom anchor element */
  bottomRef: React.RefObject<HTMLDivElement | null>;
  /** Force scroll to bottom */
  scrollToBottom: (force?: boolean) => void;
  /** Force scroll to top */
  scrollToTop: () => void;
  /** Check if user is at bottom */
  isAtBottom: () => boolean;
  /** Enable/disable auto-scroll */
  setAutoScroll: (enabled: boolean) => void;
  /** Whether to show the "scroll to top" button */
  showScrollToTop: boolean;
  /** Whether to show the "scroll to bottom" button */
  showScrollToBottom: boolean;
  /** Whether the user has intentionally scrolled away from the bottom */
  isUserScrolledUp: boolean;
}

/**
 * Smart scroll hook for chat messages — "sticky scroll" pattern.
 *
 * Industry-standard behavior (ChatGPT, Claude.ai, Slack, Discord):
 * - Auto-scroll only while "stuck to bottom"
 * - Instant disengage when user scrolls up (no debounce)
 * - Re-engage only when user scrolls back to bottom (debounced)
 * - Programmatic scrolls never trigger disengage
 */
export function useSmartScroll(
  options: UseSmartScrollOptions = {}
): UseSmartScrollReturn {
  const { autoScroll = true, bottomThreshold = 50, smooth = true } = options;

  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const autoScrollEnabled = useRef(autoScroll);
  const isScrollingProgrammatically = useRef(false);

  const [isNearTop, setIsNearTop] = useState(true);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const [canScroll, setCanScroll] = useState(false);
  const [isUserScrolledUp, setIsUserScrolledUp] = useState(false);

  const isAtBottom = useCallback((): boolean => {
    if (!scrollRef.current) return true;

    const container = scrollRef.current;
    const scrollBottom = container.scrollTop + container.clientHeight;
    const isBottom = container.scrollHeight - scrollBottom <= bottomThreshold;

    return isBottom;
  }, [bottomThreshold]);

  const scrollToBottom = useCallback(
    (force = false) => {
      if (!bottomRef.current || (!autoScrollEnabled.current && !force)) return;

      // Prevent scroll event handler from disabling auto-scroll
      isScrollingProgrammatically.current = true;

      bottomRef.current.scrollIntoView({
        behavior: smooth ? 'smooth' : 'auto',
        block: 'end',
      });

      // Reset flag after scroll completes
      setTimeout(() => {
        isScrollingProgrammatically.current = false;
      }, 300);

      // Force also re-engages auto-scroll and clears the "scrolled up" state
      if (force) {
        autoScrollEnabled.current = true;
        setIsUserScrolledUp(false);
      }
    },
    [smooth]
  );

  const scrollToTop = useCallback(() => {
    if (!scrollRef.current) return;
    isScrollingProgrammatically.current = true;
    scrollRef.current.scrollTo({
      top: 0,
      behavior: smooth ? 'smooth' : 'auto',
    });
    setTimeout(() => {
      isScrollingProgrammatically.current = false;
    }, 300);
  }, [smooth]);

  const setAutoScroll = useCallback(
    (enabled: boolean) => {
      autoScrollEnabled.current = enabled;
      if (enabled) {
        setIsUserScrolledUp(false);
        scrollToBottom(true);
      }
    },
    [scrollToBottom]
  );

  // Handle user scroll to detect if they want to stop auto-scroll
  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;

    let reEngageTimeout: NodeJS.Timeout;

    const updateScrollState = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      setCanScroll(scrollHeight > clientHeight);
      setIsNearTop(scrollTop <= 200);
      setIsNearBottom(
        scrollHeight - scrollTop - clientHeight <= bottomThreshold
      );
    };

    const handleScroll = () => {
      // Always update button visibility state (even during programmatic scrolls)
      updateScrollState();

      // Only update auto-scroll ref for user-initiated scrolls
      if (isScrollingProgrammatically.current) return;

      // Clear existing re-engage timeout
      if (reEngageTimeout) {
        clearTimeout(reEngageTimeout);
      }

      if (isAtBottom()) {
        // User scrolled back to bottom — debounce re-engage to avoid
        // false positives from content-growth pushing scroll position
        reEngageTimeout = setTimeout(() => {
          autoScrollEnabled.current = true;
          setIsUserScrolledUp(false);
        }, 150);
      } else {
        // User scrolled up — INSTANT disengage, no debounce.
        // This is the key fix: the user must never fight the auto-scroll.
        autoScrollEnabled.current = false;
        setIsUserScrolledUp(true);
      }
    };

    container.addEventListener('scroll', handleScroll, { passive: true });

    // Initial state check on mount
    requestAnimationFrame(() => {
      updateScrollState();
    });

    return () => {
      container.removeEventListener('scroll', handleScroll);
      if (reEngageTimeout) {
        clearTimeout(reEngageTimeout);
      }
    };
  }, [isAtBottom, bottomThreshold]);

  return {
    scrollRef,
    bottomRef,
    scrollToBottom,
    scrollToTop,
    isAtBottom,
    setAutoScroll,
    showScrollToTop: canScroll && !isNearTop,
    showScrollToBottom: canScroll && !isNearBottom,
    isUserScrolledUp,
  };
}
