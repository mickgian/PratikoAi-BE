'use client'

import React from 'react'

interface TypingCursorProps {
  show: boolean
}

/**
 * TypingCursor component for square block cursor during typing
 * 
 * Features:
 * - Square block cursor (not vertical line)
 * - Half character width (0.5ch)
 * - Line height (1em)
 * - 1 second blink cycle (0.5s visible, 0.5s hidden)
 * - Inline positioning after text with no line breaks
 * - Accessible (hidden from screen readers)  
 * - Professional appearance matching modern editors
 * - Proper baseline alignment
 */
export function TypingCursor({ show }: TypingCursorProps) {
  if (!show) {
    return null
  }

  return (
    <span
      data-testid="typing-cursor"
      aria-hidden="true"
      className="
        select-none
        pointer-events-none
        animate-blink
      "
      style={{
        // Square block cursor specifications
        display: 'inline-block',
        width: '0.5ch', // Half character width
        height: '1em', // Line height
        backgroundColor: 'currentColor',
        verticalAlign: 'baseline',
        // Ensure no spacing issues
        margin: 0,
        padding: 0,
        // Inherit font properties
        fontFamily: 'inherit',
        fontSize: 'inherit',
        lineHeight: 'inherit'
      }}
    />
  )
}