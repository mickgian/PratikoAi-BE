/**
 * Centralized log prefixes for consistent debugging and filtering
 * Use these prefixes to easily filter logs in the browser console
 * Example: In Chrome DevTools Console, filter by typing: STREAM_SESSION
 */
export class LogPrefix {
  // Session and streaming related
  static readonly STREAM_SESSION = '[STREAM_SESSION]'
  static readonly STREAM_PERSIST = '[STREAM_PERSIST]'
  static readonly STREAM_HANDLER = '[STREAM_HANDLER]'
  static readonly STREAM_CONTENT = '[STREAM_CONTENT]'
  
  // Session management
  static readonly SESSION_LOAD = '[SESSION_LOAD]'
  static readonly SESSION_SWITCH = '[SESSION_SWITCH]'
  static readonly SESSION_CREATE = '[SESSION_CREATE]'
  static readonly SESSION_DELETE = '[SESSION_DELETE]'
  
  // Message handling
  static readonly MSG_SAVE = '[MSG_SAVE]'
  static readonly MSG_LOAD = '[MSG_LOAD]'
  static readonly MSG_DISPLAY = '[MSG_DISPLAY]'
  static readonly MSG_DEDUP = '[MSG_DEDUP]'
  
  // State management
  static readonly STATE_REDUCER = '[STATE_REDUCER]'
  static readonly STATE_UPDATE = '[STATE_UPDATE]'
  static readonly STATE_SYNC = '[STATE_SYNC]'
  
  // API and network
  static readonly API_REQUEST = '[API_REQUEST]'
  static readonly API_RESPONSE = '[API_RESPONSE]'
  static readonly API_ERROR = '[API_ERROR]'
  static readonly API_SSE = '[API_SSE]'
  
  // UI components
  static readonly UI_SIDEBAR = '[UI_SIDEBAR]'
  static readonly UI_INPUT = '[UI_INPUT]'
  static readonly UI_MESSAGE = '[UI_MESSAGE]'
  static readonly UI_RENDER = '[UI_RENDER]'
  
  // Performance and debugging
  static readonly PERF = '[PERF]'
  static readonly DEBUG = '[DEBUG]'
  static readonly ERROR = '[ERROR]'
  static readonly WARN = '[WARN]'
  
  /**
   * Helper method to create consistent log messages
   * @param prefix - The log prefix to use
   * @param message - The log message
   * @param data - Optional data to log
   * @returns Formatted log string
   */
  static format(prefix: string, message: string, data?: any): string {
    if (data !== undefined) {
      return `${prefix} ${message}:`
    }
    return `${prefix} ${message}`
  }
  
  /**
   * Log with prefix and optional data
   * @param prefix - The log prefix to use
   * @param message - The log message
   * @param data - Optional data to log
   */
  static log(prefix: string, message: string, data?: any): void {
    if (data !== undefined) {
      console.log(LogPrefix.format(prefix, message, data), data)
    } else {
      console.log(LogPrefix.format(prefix, message))
    }
  }
  
  /**
   * Warn with prefix and optional data
   * @param prefix - The log prefix to use
   * @param message - The log message
   * @param data - Optional data to log
   */
  static warn(prefix: string, message: string, data?: any): void {
    if (data !== undefined) {
      console.warn(LogPrefix.format(prefix, message, data), data)
    } else {
      console.warn(LogPrefix.format(prefix, message))
    }
  }
  
  /**
   * Error with prefix and optional data
   * @param prefix - The log prefix to use
   * @param message - The log message
   * @param data - Optional data to log
   */
  static error(prefix: string, message: string, data?: any): void {
    if (data !== undefined) {
      console.error(LogPrefix.format(prefix, message, data), data)
    } else {
      console.error(LogPrefix.format(prefix, message))
    }
  }
}