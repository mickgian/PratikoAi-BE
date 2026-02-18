'use client';
import { useState, useCallback, useEffect, KeyboardEvent } from 'react';

/**
 * Options for the useKeyboardNavigation hook
 */
export interface UseKeyboardNavigationOptions {
  /** Array of item IDs to navigate through */
  items: string[];
  /** Callback when an item is selected (Enter or number key) */
  onSelect: (itemId: string) => void;
  /** Optional callback when navigation is cancelled (Escape) */
  onCancel?: () => void;
  /** Whether keyboard navigation is enabled (default: true) */
  enabled?: boolean;
  /** Initial selected index (default: 0) */
  initialIndex?: number;
}

/**
 * Return value from the useKeyboardNavigation hook
 */
export interface UseKeyboardNavigationReturn {
  /** Currently selected index */
  selectedIndex: number;
  /** Function to manually set the selected index */
  setSelectedIndex: (index: number) => void;
  /** Keyboard event handler to attach to a container element */
  handleKeyDown: (event: KeyboardEvent) => void;
}

/**
 * Custom hook for managing keyboard navigation in lists/options.
 *
 * Features:
 * - Arrow key navigation (Up/Down) with wraparound
 * - Enter key to select current item
 * - Escape key to cancel
 * - Number keys 1-9 for direct selection
 * - Input field detection to avoid conflicts
 *
 * @example
 * ```tsx
 * const { selectedIndex, handleKeyDown } = useKeyboardNavigation({
 *   items: options.map(o => o.id),
 *   onSelect: (id) => handleOptionSelect(id),
 *   onCancel: () => setIsOpen(false),
 * });
 *
 * return (
 *   <div onKeyDown={handleKeyDown} tabIndex={0}>
 *     {options.map((opt, idx) => (
 *       <button key={opt.id} aria-selected={selectedIndex === idx}>
 *         {opt.label}
 *       </button>
 *     ))}
 *   </div>
 * );
 * ```
 */
export function useKeyboardNavigation({
  items,
  onSelect,
  onCancel,
  enabled = true,
  initialIndex = 0,
}: UseKeyboardNavigationOptions): UseKeyboardNavigationReturn {
  const [selectedIndex, setSelectedIndex] = useState(initialIndex);
  const [prevItemsLength, setPrevItemsLength] = useState(items.length);

  // Reset index when items array length changes (not on initial render)
  useEffect(() => {
    if (items.length !== prevItemsLength) {
      setSelectedIndex(0);
      setPrevItemsLength(items.length);
    }
  }, [items.length, prevItemsLength]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled || items.length === 0) return;

      // Check if user is typing in an input field
      const target = event.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
        // Only handle Escape in inputs (allow canceling from input)
        if (event.key === 'Escape' && onCancel) {
          event.preventDefault();
          onCancel();
        }
        return;
      }

      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          setSelectedIndex(prev => (prev + 1) % items.length);
          break;

        case 'ArrowUp':
          event.preventDefault();
          setSelectedIndex(prev => (prev - 1 + items.length) % items.length);
          break;

        case 'Enter':
          event.preventDefault();
          if (items[selectedIndex]) {
            onSelect(items[selectedIndex]);
          }
          break;

        case 'Escape':
          event.preventDefault();
          onCancel?.();
          break;

        default:
          // Handle number keys 1-9 for direct selection
          const num = parseInt(event.key, 10);
          if (num >= 1 && num <= 9 && num <= items.length) {
            event.preventDefault();
            setSelectedIndex(num - 1);
            onSelect(items[num - 1]);
          }
      }
    },
    [enabled, items, selectedIndex, onSelect, onCancel]
  );

  return { selectedIndex, setSelectedIndex, handleKeyDown };
}
