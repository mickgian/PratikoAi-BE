import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Custom render function that includes providers
const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
  return <>{children}</>;
};

const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllTheProviders, ...options });

// Re-export everything
export * from '@testing-library/react';

// Override render method
export { customRender as render };

// Create user event instance
export const user = userEvent.setup();

// Custom matchers and utilities for testing
export const waitForStreamingComplete = async (timeout = 5000) => {
  return new Promise<void>(resolve => {
    const startTime = Date.now();
    const checkComplete = () => {
      if (Date.now() - startTime > timeout) {
        resolve();
        return;
      }

      // Check if streaming indicator is gone
      const streamingIndicator = document.querySelector(
        '[data-streaming="true"]'
      );
      if (!streamingIndicator) {
        resolve();
      } else {
        setTimeout(checkComplete, 100);
      }
    };
    checkComplete();
  });
};

export const createMockDispatch = () => {
  const dispatch = jest.fn();
  dispatch.mockName('mockDispatch');
  return dispatch;
};

export const createMockSessionToken = () => 'mock-session-token-12345';
