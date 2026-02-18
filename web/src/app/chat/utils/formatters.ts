/**
 * Utility functions for formatting timestamps and dates
 * Implements Italian locale formatting as per CHAT_REQUIREMENTS.md Section 2
 */

/**
 * Formats a timestamp to Italian time format (HH:MM)
 * Uses Italian timezone (CET/CEST) and 24-hour format
 * 
 * @param timestamp - ISO timestamp string
 * @returns Formatted time string (HH:MM) or fallback "--:--"
 */
export function formatTimestamp(timestamp: string): string {
  try {
    if (!timestamp || !isValidTimestamp(timestamp)) {
      return '--:--'
    }

    const date = new Date(timestamp)
    
    // Use Italian locale and timezone
    const formatter = new Intl.DateTimeFormat('it-IT', {
      timeZone: 'Europe/Rome',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false // 24-hour format
    })

    return formatter.format(date)
  } catch (error) {
    return '--:--'
  }
}

/**
 * Formats a full datetime string for screen readers in Italian
 * Provides complete date and time information for accessibility
 * 
 * @param timestamp - ISO timestamp string
 * @returns Formatted datetime string for screen readers
 */
export function formatDateForScreenReader(timestamp: string): string {
  try {
    if (!timestamp || !isValidTimestamp(timestamp)) {
      return 'Orario non valido'
    }

    const date = new Date(timestamp)
    
    // Format full date in Italian
    const dateFormatter = new Intl.DateTimeFormat('it-IT', {
      timeZone: 'Europe/Rome',
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    })

    // Format time in Italian
    const timeFormatter = new Intl.DateTimeFormat('it-IT', {
      timeZone: 'Europe/Rome',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })

    const formattedDate = dateFormatter.format(date)
    const formattedTime = timeFormatter.format(date)

    return `${formattedDate}, ore ${formattedTime}`
  } catch (error) {
    return 'Orario non valido'
  }
}

/**
 * Validates if a timestamp string is a valid ISO date
 * 
 * @param timestamp - Timestamp string to validate
 * @returns True if valid, false otherwise
 */
export function isValidTimestamp(timestamp: unknown): boolean {
  if (!timestamp || typeof timestamp !== 'string') {
    return false
  }

  try {
    // Check if the timestamp follows basic ISO format
    if (!timestamp.includes('T') || 
        !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(timestamp)) {
      return false
    }

    const date = new Date(timestamp)
    
    // Check if the date is valid
    if (isNaN(date.getTime())) {
      return false
    }

    // Additional validation: check if the parsed date matches the input
    // This catches cases like February 29th in non-leap years
    const isoString = date.toISOString()
    const inputDatePart = timestamp.substring(0, 10) // YYYY-MM-DD
    const parsedDatePart = isoString.substring(0, 10) // YYYY-MM-DD
    
    return inputDatePart === parsedDatePart
  } catch (error) {
    return false
  }
}