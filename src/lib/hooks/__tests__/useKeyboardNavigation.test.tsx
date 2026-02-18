/**
 * @jest-environment jsdom
 */
import { renderHook, act } from '@testing-library/react';
import { useKeyboardNavigation } from '../useKeyboardNavigation';
import { KeyboardEvent } from 'react';

// Helper to create mock keyboard events
const createKeyboardEvent = (key: string): KeyboardEvent => {
  return {
    key,
    preventDefault: jest.fn(),
    target: { tagName: 'DIV' } as HTMLElement,
  } as unknown as KeyboardEvent;
};

const createInputKeyboardEvent = (key: string): KeyboardEvent => {
  return {
    key,
    preventDefault: jest.fn(),
    target: { tagName: 'INPUT' } as HTMLElement,
  } as unknown as KeyboardEvent;
};

describe('useKeyboardNavigation', () => {
  const defaultItems = ['item-1', 'item-2', 'item-3', 'item-4'];
  const mockOnSelect = jest.fn();
  const mockOnCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Initialization', () => {
    it('should initialize with selectedIndex of 0 by default', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
        })
      );

      expect(result.current.selectedIndex).toBe(0);
    });

    it('should initialize with custom initialIndex when provided', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
          initialIndex: 2,
        })
      );

      expect(result.current.selectedIndex).toBe(2);
    });

    it('should reset selectedIndex to 0 when items change', () => {
      const { result, rerender } = renderHook(
        ({ items }) =>
          useKeyboardNavigation({
            items,
            onSelect: mockOnSelect,
          }),
        { initialProps: { items: defaultItems } }
      );

      // Change selected index
      act(() => {
        result.current.setSelectedIndex(2);
      });
      expect(result.current.selectedIndex).toBe(2);

      // Change items - should reset to 0
      rerender({ items: ['new-1', 'new-2'] });
      expect(result.current.selectedIndex).toBe(0);
    });
  });

  describe('Arrow Key Navigation', () => {
    it('should move selection down with ArrowDown', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
        })
      );

      act(() => {
        result.current.handleKeyDown(createKeyboardEvent('ArrowDown'));
      });

      expect(result.current.selectedIndex).toBe(1);
    });

    it('should move selection up with ArrowUp', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
          initialIndex: 2,
        })
      );

      act(() => {
        result.current.handleKeyDown(createKeyboardEvent('ArrowUp'));
      });

      expect(result.current.selectedIndex).toBe(1);
    });

    it('should wrap around from last to first with ArrowDown', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
          initialIndex: 3, // Last item
        })
      );

      act(() => {
        result.current.handleKeyDown(createKeyboardEvent('ArrowDown'));
      });

      expect(result.current.selectedIndex).toBe(0);
    });

    it('should wrap around from first to last with ArrowUp', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
          initialIndex: 0, // First item
        })
      );

      act(() => {
        result.current.handleKeyDown(createKeyboardEvent('ArrowUp'));
      });

      expect(result.current.selectedIndex).toBe(3);
    });

    it('should call preventDefault on arrow key events', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
        })
      );

      const event = createKeyboardEvent('ArrowDown');
      act(() => {
        result.current.handleKeyDown(event);
      });

      expect(event.preventDefault).toHaveBeenCalled();
    });
  });

  describe('Enter Key Selection', () => {
    it('should call onSelect with current item when Enter is pressed', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
          initialIndex: 1,
        })
      );

      act(() => {
        result.current.handleKeyDown(createKeyboardEvent('Enter'));
      });

      expect(mockOnSelect).toHaveBeenCalledWith('item-2');
    });

    it('should call preventDefault on Enter', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
        })
      );

      const event = createKeyboardEvent('Enter');
      act(() => {
        result.current.handleKeyDown(event);
      });

      expect(event.preventDefault).toHaveBeenCalled();
    });
  });

  describe('Escape Key Cancel', () => {
    it('should call onCancel when Escape is pressed', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
          onCancel: mockOnCancel,
        })
      );

      act(() => {
        result.current.handleKeyDown(createKeyboardEvent('Escape'));
      });

      expect(mockOnCancel).toHaveBeenCalled();
    });

    it('should not throw when Escape is pressed without onCancel', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
        })
      );

      expect(() => {
        act(() => {
          result.current.handleKeyDown(createKeyboardEvent('Escape'));
        });
      }).not.toThrow();
    });

    it('should call preventDefault on Escape', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
          onCancel: mockOnCancel,
        })
      );

      const event = createKeyboardEvent('Escape');
      act(() => {
        result.current.handleKeyDown(event);
      });

      expect(event.preventDefault).toHaveBeenCalled();
    });
  });

  describe('Number Key Direct Selection', () => {
    it('should select item 1 when key 1 is pressed', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
          initialIndex: 2,
        })
      );

      act(() => {
        result.current.handleKeyDown(createKeyboardEvent('1'));
      });

      expect(result.current.selectedIndex).toBe(0);
      expect(mockOnSelect).toHaveBeenCalledWith('item-1');
    });

    it('should select item 4 when key 4 is pressed', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
        })
      );

      act(() => {
        result.current.handleKeyDown(createKeyboardEvent('4'));
      });

      expect(result.current.selectedIndex).toBe(3);
      expect(mockOnSelect).toHaveBeenCalledWith('item-4');
    });

    it('should ignore number keys beyond items length', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems, // 4 items
          onSelect: mockOnSelect,
        })
      );

      act(() => {
        result.current.handleKeyDown(createKeyboardEvent('5'));
      });

      expect(mockOnSelect).not.toHaveBeenCalled();
    });

    it('should ignore key 0', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
        })
      );

      act(() => {
        result.current.handleKeyDown(createKeyboardEvent('0'));
      });

      expect(mockOnSelect).not.toHaveBeenCalled();
    });

    it('should support keys 1-9 for up to 9 items', () => {
      const nineItems = Array.from({ length: 9 }, (_, i) => `item-${i + 1}`);
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: nineItems,
          onSelect: mockOnSelect,
        })
      );

      act(() => {
        result.current.handleKeyDown(createKeyboardEvent('9'));
      });

      expect(result.current.selectedIndex).toBe(8);
      expect(mockOnSelect).toHaveBeenCalledWith('item-9');
    });

    it('should call preventDefault on number key selection', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
        })
      );

      const event = createKeyboardEvent('2');
      act(() => {
        result.current.handleKeyDown(event);
      });

      expect(event.preventDefault).toHaveBeenCalled();
    });
  });

  describe('Disabled State', () => {
    it('should ignore all keyboard events when disabled', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
          onCancel: mockOnCancel,
          enabled: false,
        })
      );

      act(() => {
        result.current.handleKeyDown(createKeyboardEvent('ArrowDown'));
        result.current.handleKeyDown(createKeyboardEvent('Enter'));
        result.current.handleKeyDown(createKeyboardEvent('Escape'));
        result.current.handleKeyDown(createKeyboardEvent('1'));
      });

      expect(result.current.selectedIndex).toBe(0);
      expect(mockOnSelect).not.toHaveBeenCalled();
      expect(mockOnCancel).not.toHaveBeenCalled();
    });

    it('should re-enable when enabled changes to true', () => {
      const { result, rerender } = renderHook(
        ({ enabled }) =>
          useKeyboardNavigation({
            items: defaultItems,
            onSelect: mockOnSelect,
            enabled,
          }),
        { initialProps: { enabled: false } }
      );

      // Should not work when disabled
      act(() => {
        result.current.handleKeyDown(createKeyboardEvent('ArrowDown'));
      });
      expect(result.current.selectedIndex).toBe(0);

      // Enable
      rerender({ enabled: true });

      // Should work when enabled
      act(() => {
        result.current.handleKeyDown(createKeyboardEvent('ArrowDown'));
      });
      expect(result.current.selectedIndex).toBe(1);
    });
  });

  describe('Empty Items Array', () => {
    it('should not crash with empty items array', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: [],
          onSelect: mockOnSelect,
        })
      );

      expect(() => {
        act(() => {
          result.current.handleKeyDown(createKeyboardEvent('ArrowDown'));
          result.current.handleKeyDown(createKeyboardEvent('Enter'));
        });
      }).not.toThrow();

      expect(mockOnSelect).not.toHaveBeenCalled();
    });
  });

  describe('Input Field Handling', () => {
    it('should ignore arrow keys when focus is on an input', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
        })
      );

      act(() => {
        result.current.handleKeyDown(createInputKeyboardEvent('ArrowDown'));
      });

      expect(result.current.selectedIndex).toBe(0);
    });

    it('should ignore Enter when focus is on an input', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
        })
      );

      act(() => {
        result.current.handleKeyDown(createInputKeyboardEvent('Enter'));
      });

      expect(mockOnSelect).not.toHaveBeenCalled();
    });

    it('should still handle Escape in inputs to cancel', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
          onCancel: mockOnCancel,
        })
      );

      const event = createInputKeyboardEvent('Escape');
      act(() => {
        result.current.handleKeyDown(event);
      });

      expect(mockOnCancel).toHaveBeenCalled();
      expect(event.preventDefault).toHaveBeenCalled();
    });

    it('should ignore number keys when focus is on an input', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
        })
      );

      act(() => {
        result.current.handleKeyDown(createInputKeyboardEvent('1'));
      });

      expect(mockOnSelect).not.toHaveBeenCalled();
    });

    it('should handle TEXTAREA same as INPUT', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
          onCancel: mockOnCancel,
        })
      );

      const textareaEvent = {
        key: 'ArrowDown',
        preventDefault: jest.fn(),
        target: { tagName: 'TEXTAREA' } as HTMLElement,
      } as unknown as KeyboardEvent;

      act(() => {
        result.current.handleKeyDown(textareaEvent);
      });

      expect(result.current.selectedIndex).toBe(0);
    });
  });

  describe('setSelectedIndex Manual Control', () => {
    it('should allow manual setting of selectedIndex', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
        })
      );

      act(() => {
        result.current.setSelectedIndex(3);
      });

      expect(result.current.selectedIndex).toBe(3);
    });
  });

  describe('Other Keys', () => {
    it('should ignore unhandled keys', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
        })
      );

      const event = createKeyboardEvent('Tab');
      act(() => {
        result.current.handleKeyDown(event);
      });

      expect(result.current.selectedIndex).toBe(0);
      expect(mockOnSelect).not.toHaveBeenCalled();
      expect(event.preventDefault).not.toHaveBeenCalled();
    });

    it('should ignore letter keys', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigation({
          items: defaultItems,
          onSelect: mockOnSelect,
        })
      );

      act(() => {
        result.current.handleKeyDown(createKeyboardEvent('a'));
        result.current.handleKeyDown(createKeyboardEvent('z'));
      });

      expect(mockOnSelect).not.toHaveBeenCalled();
    });
  });
});
