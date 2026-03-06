/**
 * @jest-environment jsdom
 */
import React from 'react';
import { render, act } from '@testing-library/react';
import { useSmartScroll } from '../useSmartScroll';

// We need a test component because useSmartScroll attaches scroll listeners
// via useEffect on mount using the scrollRef. Bare renderHook doesn't provide
// a real DOM element for the ref, so the listener never attaches.
interface HookResult {
  scrollToBottom: (force?: boolean) => void;
  scrollToTop: () => void;
  setAutoScroll: (enabled: boolean) => void;
  isAtBottom: () => boolean;
  showScrollToTop: boolean;
  showScrollToBottom: boolean;
  isUserScrolledUp: boolean;
  scrollRef: React.RefObject<HTMLDivElement | null>;
}

let hookResult: HookResult;

function TestComponent() {
  const result = useSmartScroll({ bottomThreshold: 50, smooth: false });
  hookResult = result;

  return React.createElement(
    'div',
    {
      ref: result.scrollRef,
      'data-testid': 'scroll-container',
      style: { height: '500px', overflow: 'auto' },
    },
    // Inner content taller than container to enable scrolling
    React.createElement('div', { style: { height: '2000px' } }),
    React.createElement('div', { ref: result.bottomRef })
  );
}

/**
 * Helper: sets scrollTop on the container and dispatches scroll event.
 * Uses Object.defineProperty because JSDOM doesn't properly
 * implement scrollable containers.
 */
function simulateScroll(container: HTMLElement, scrollTop: number) {
  Object.defineProperty(container, 'scrollTop', {
    value: scrollTop,
    configurable: true,
    writable: true,
  });
  container.dispatchEvent(new Event('scroll'));
}

function makeScrollable(container: HTMLElement) {
  Object.defineProperty(container, 'scrollHeight', {
    value: 2000,
    configurable: true,
  });
  Object.defineProperty(container, 'clientHeight', {
    value: 500,
    configurable: true,
  });
  // Start at bottom
  Object.defineProperty(container, 'scrollTop', {
    value: 1450,
    configurable: true,
    writable: true,
  });
}

describe('useSmartScroll', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    Element.prototype.scrollIntoView = jest.fn();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should expose isUserScrolledUp as false initially', () => {
    render(React.createElement(TestComponent));
    expect(hookResult.isUserScrolledUp).toBe(false);
  });

  it('should set isUserScrolledUp=true immediately when user scrolls up', () => {
    const { getByTestId } = render(React.createElement(TestComponent));
    const container = getByTestId('scroll-container');
    makeScrollable(container);

    // Fire rAF for initial state
    act(() => {
      jest.runAllTimers();
    });

    // User scrolls UP (away from bottom)
    act(() => {
      simulateScroll(container, 200);
    });

    // Instant disengage — no debounce needed
    expect(hookResult.isUserScrolledUp).toBe(true);
  });

  it('should not auto-scroll when user has scrolled up during streaming', () => {
    const { getByTestId } = render(React.createElement(TestComponent));
    const container = getByTestId('scroll-container');
    makeScrollable(container);

    act(() => {
      jest.runAllTimers();
    });

    // User scrolls up
    act(() => {
      simulateScroll(container, 200);
    });

    // Reset scrollIntoView mock
    (Element.prototype.scrollIntoView as jest.Mock).mockClear();

    // Non-forced scrollToBottom (what streaming content updates use)
    act(() => {
      hookResult.scrollToBottom(false);
    });

    // Should NOT scroll since user has scrolled up
    expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled();
  });

  it('should re-engage auto-scroll when user scrolls back to bottom', () => {
    const { getByTestId } = render(React.createElement(TestComponent));
    const container = getByTestId('scroll-container');
    makeScrollable(container);

    act(() => {
      jest.runAllTimers();
    });

    // User scrolls up first
    act(() => {
      simulateScroll(container, 200);
    });
    expect(hookResult.isUserScrolledUp).toBe(true);

    // User scrolls back to bottom
    act(() => {
      simulateScroll(container, 1500);
      // Re-engage uses 150ms debounce
      jest.advanceTimersByTime(200);
    });

    expect(hookResult.isUserScrolledUp).toBe(false);
  });

  it('should always scroll when force=true even if user scrolled up', () => {
    const { getByTestId } = render(React.createElement(TestComponent));
    const container = getByTestId('scroll-container');
    makeScrollable(container);

    act(() => {
      jest.runAllTimers();
    });

    // User scrolls up
    act(() => {
      simulateScroll(container, 200);
    });

    (Element.prototype.scrollIntoView as jest.Mock).mockClear();

    // Force scroll should work regardless
    act(() => {
      hookResult.scrollToBottom(true);
    });

    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });

  it('should show scroll-to-bottom button when user scrolled up and content is scrollable', () => {
    const { getByTestId } = render(React.createElement(TestComponent));
    const container = getByTestId('scroll-container');
    makeScrollable(container);

    act(() => {
      jest.runAllTimers();
    });

    // User scrolls up
    act(() => {
      simulateScroll(container, 200);
    });

    expect(hookResult.showScrollToBottom).toBe(true);
  });

  it('should clear isUserScrolledUp when scrollToBottom(true) is called', () => {
    const { getByTestId } = render(React.createElement(TestComponent));
    const container = getByTestId('scroll-container');
    makeScrollable(container);

    act(() => {
      jest.runAllTimers();
    });

    // User scrolls up
    act(() => {
      simulateScroll(container, 200);
    });
    expect(hookResult.isUserScrolledUp).toBe(true);

    // Force scroll to bottom (clicking the button)
    act(() => {
      hookResult.scrollToBottom(true);
    });

    expect(hookResult.isUserScrolledUp).toBe(false);
  });

  it('should not disengage during programmatic scrolls', () => {
    const { getByTestId } = render(React.createElement(TestComponent));
    const container = getByTestId('scroll-container');
    makeScrollable(container);

    act(() => {
      jest.runAllTimers();
    });

    // Trigger a programmatic scroll (which sets isScrollingProgrammatically)
    act(() => {
      hookResult.scrollToBottom(false);
    });

    // Now simulate a scroll event while the programmatic flag is still set
    act(() => {
      simulateScroll(container, 200);
    });

    // Should NOT disengage because the scroll was programmatic
    expect(hookResult.isUserScrolledUp).toBe(false);
  });
});
