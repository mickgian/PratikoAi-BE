'use client'

import React from 'react'
import { formatTimestamp, formatDateForScreenReader } from '../utils/formatters'

interface MessageTimestampProps {
  timestamp: string
  messageType?: 'user' | 'ai' | 'system'
}

/**
 * MessageTimestamp component for displaying message timestamps
 * Implements CHAT_REQUIREMENTS.md Section 2 timestamp specifications
 * 
 * Features:
 * - Italian time format (HH:MM, 24-hour)
 * - Automatic timezone conversion to Europe/Rome
 * - Color: #C4BDB4 (Grigio Tortora)
 * - Font size: 12px
 * - Accessibility support with screen reader formatting
 * - Alignment based on message type
 */
export function MessageTimestamp({ timestamp, messageType = 'ai' }: MessageTimestampProps) {
  const formattedTime = formatTimestamp(timestamp)
  const screenReaderText = formatDateForScreenReader(timestamp)
  
  // Determine alignment based on message type
  const alignmentClass = messageType === 'user' ? 'text-right' : 'text-left'

  return (
    <time
      data-testid="message-timestamp"
      dateTime={timestamp}
      aria-label={screenReaderText}
      className={`
        text-xs 
        text-[#C4BDB4] 
        mt-1 
        opacity-80
        ${alignmentClass}
      `}
    >
      {formattedTime}
    </time>
  )
}