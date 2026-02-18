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
}

/**
 * Smart scroll hook for chat messages
 *
 * Features:
 * - Auto-scroll to bottom on new messages
 * - Detects user scroll and pauses auto-scroll
 * - Resume auto-scroll when user scrolls to bottom
 * - Smooth scrolling animations
 * - Performance optimized
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
        scrollToBottom(true);
      }
    },
    [scrollToBottom]
  );

  // Handle user scroll to detect if they want to stop auto-scroll
  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;

    let scrollTimeout: NodeJS.Timeout;

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

      // Clear existing timeout
      if (scrollTimeout) {
        clearTimeout(scrollTimeout);
      }

      // Debounce scroll detection
      scrollTimeout = setTimeout(() => {
        if (isAtBottom()) {
          // User scrolled to bottom, resume auto-scroll
          autoScrollEnabled.current = true;
        } else {
          // User scrolled up, pause auto-scroll
          autoScrollEnabled.current = false;
        }
      }, 150);
    };

    container.addEventListener('scroll', handleScroll, { passive: true });

    // Initial state check on mount
    requestAnimationFrame(() => {
      updateScrollState();
    });

    return () => {
      container.removeEventListener('scroll', handleScroll);
      if (scrollTimeout) {
        clearTimeout(scrollTimeout);
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
  };
}
