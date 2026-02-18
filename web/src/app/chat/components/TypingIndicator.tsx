'use client';

import React from 'react';
import { PratikoLogo } from './PratikoLogo';

interface TypingIndicatorProps {
  show: boolean;
}

/**
 * TypingIndicator component for showing AI writing status
 *
 * Features:
 * - Italian text: "PratikoAI sta scrivendo..."
 * - 3 animated dots with staggered timing
 * - Smooth fade in/out
 * - Accessibility support
 * - Matches chat message styling
 */
export function TypingIndicator({ show }: TypingIndicatorProps) {
  if (!show) {
    return null;
  }

  return (
    <div
      data-testid="typing-indicator"
      role="status"
      aria-label="PratikoAI sta scrivendo la risposta"
      aria-live="polite"
      className="
        flex
        items-center
        space-x-2
        text-[#C4BDB4]
        text-sm
        font-medium
        py-3
        px-4
        mb-4
        max-w-4xl
        w-full
        justify-start
        animate-fade-in
        opacity-100
        transition-opacity
        duration-300
      "
    >
      {/* Screen reader text */}
      <span data-testid="sr-only-text" className="sr-only">
        PratikoAI sta scrivendo una risposta
      </span>

      {/* Animated logo */}
      <PratikoLogo animated={true} className="mr-1" />

      {/* Visible text */}
      <span className="text-[#C4BDB4]">Sto pensando...</span>

      {/* Enhanced animated dots with better timing */}
      <div data-testid="typing-dots-container" className="flex space-x-1 ml-1">
        <div
          data-testid="typing-dot-1"
          className="
            w-1.5
            h-1.5
            bg-[#2A5D67]
            rounded-full
            animate-pulse
          "
          style={{
            animationDelay: '0ms',
            animationDuration: '1.5s',
          }}
        />
        <div
          data-testid="typing-dot-2"
          className="
            w-1.5
            h-1.5
            bg-[#2A5D67]
            rounded-full
            animate-pulse
          "
          style={{
            animationDelay: '500ms',
            animationDuration: '1.5s',
          }}
        />
        <div
          data-testid="typing-dot-3"
          className="
            w-1.5
            h-1.5
            bg-[#2A5D67]
            rounded-full
            animate-pulse
          "
          style={{
            animationDelay: '1000ms',
            animationDuration: '1.5s',
          }}
        />
      </div>
    </div>
  );
}
