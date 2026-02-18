/**
 * Production-Ready Logger
 * 
 * Provides configurable logging with performance monitoring
 * and analytics integration for the chat system.
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error'

export interface LogContext {
  component?: string
  action?: string
  sessionId?: string
  userId?: string
  metadata?: Record<string, any>
}

export interface PerformanceMetrics {
  startTime: number
  endTime?: number
  duration?: number
  memoryUsage?: number
  operation: string
}

type DebugFlags = {
  SSE_RAW?: boolean  // ultra-verbose transport logs (raw reader.read chunks)
  SSE_PROC?: boolean // mid-level processSSEData logs
}

function readDebugFlags(): DebugFlags {
  try {
    if (typeof window === 'undefined') return {}
    const v = localStorage.getItem('DEBUG_FLAGS')
    return v ? JSON.parse(v) as DebugFlags : {}
  } catch {
    return {}
  }
}

function writeDebugFlags(flags: DebugFlags) {
  try {
    if (typeof window === 'undefined') return
    localStorage.setItem('DEBUG_FLAGS', JSON.stringify(flags))
  } catch {}
}


class ProductionLogger {
  private isDevelopment = process.env.NODE_ENV === 'development'
  private enabledLevels: Set<LogLevel> = new Set(['error', 'warn'])
  private analyticsQueue: any[] = []
  private performanceMetrics: Map<string, PerformanceMetrics> = new Map()
  private debugFlags: DebugFlags = {}
  
  constructor() {
    if (this.isDevelopment) {
      this.enabledLevels.add('info')
      this.enabledLevels.add('debug')
      this.debugFlags = readDebugFlags()

      // expose runtime toggle for the console
      if (typeof window !== 'undefined') {
        (window as any).__logger__ = {
          setFlag: (key: keyof DebugFlags, value: boolean) => {
            this.debugFlags[key] = value
            writeDebugFlags(this.debugFlags)
            console.info('[LOGGER] Debug flag set:', key, value)
          },
          getFlags: () => ({ ...this.debugFlags }),
          clearFlags: () => {
            this.debugFlags = {}
            writeDebugFlags(this.debugFlags)
            console.info('[LOGGER] Debug flags cleared')
          }
        }
      }
    }
    
    // Enable performance monitoring in production
    if (typeof window !== 'undefined' && !this.isDevelopment) {
      this.setupPerformanceObserver()
    }
  }

  /** Log only if a debug flag is ON */
  debugIf(flag: keyof DebugFlags, message: string, context?: LogContext) {
    if (this.debugFlags[flag]) this.debug(message, context)
  }

  /** Convenience SSE channel (pretty label & style) */
  sse(tag: string, payload?: any, flag: keyof DebugFlags = 'SSE_RAW') {
    if (!this.debugFlags[flag]) return
    if (this.isDevelopment) {
      console.debug(
          `%c[SSE][${tag}]`,
          'color:#2A5D67;font-weight:600;',
          payload ?? ''
      )
    } else {
      this.debug(`[SSE][${tag}]`, { metadata: payload })
    }
  }
  
  private setupPerformanceObserver() {
    if ('PerformanceObserver' in window) {
      try {
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.name.includes('chat') || entry.name.includes('stream')) {
              this.recordPerformanceMetric(entry.name, {
                startTime: entry.startTime,
                endTime: entry.startTime + entry.duration,
                duration: entry.duration,
                operation: entry.name
              })
            }
          }
        })
        
        observer.observe({ entryTypes: ['measure', 'navigation'] })
      } catch (error) {
        // Performance observer not supported
      }
    }
  }
  
  debug(message: string, context?: LogContext) {
    this.log('debug', message, context)
  }
  
  info(message: string, context?: LogContext) {
    this.log('info', message, context)
  }
  
  warn(message: string, context?: LogContext) {
    this.log('warn', message, context)
  }
  
  error(message: string, error?: Error, context?: LogContext) {
    const errorContext = {
      ...context,
      error: error ? {
        name: error.name,
        message: error.message,
        stack: error.stack
      } : undefined
    }
    
    this.log('error', message, errorContext)
    
    // Send critical errors to analytics in production
    if (!this.isDevelopment && error) {
      this.trackError(message, error, context)
    }
  }
  
  private log(level: LogLevel, message: string, context?: LogContext) {
    if (!this.enabledLevels.has(level)) {
      return
    }
    
    const timestamp = new Date().toISOString()
    const logEntry = {
      timestamp,
      level,
      message,
      ...context
    }
    
    if (this.isDevelopment) {
      // Development: use console with colors
      const prefix = this.getColorPrefix(level)
      console.log(prefix, message, context || '')
    } else {
      // Production: structured logging
      console.log(JSON.stringify(logEntry))
    }
  }
  
  private getColorPrefix(level: LogLevel): string {
    const prefixes = {
      debug: '🐛 [DEBUG]',
      info: 'ℹ️ [INFO]',
      warn: '⚠️ [WARN]',
      error: '❌ [ERROR]'
    }
    return prefixes[level]
  }
  
  // Performance monitoring
  startPerformanceTimer(operation: string, context?: LogContext): string {
    const timerId = `${operation}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    
    this.performanceMetrics.set(timerId, {
      startTime: performance.now(),
      operation,
      ...context
    })
    
    if (typeof window !== 'undefined' && window.performance?.mark) {
      window.performance.mark(`${operation}-start`)
    }
    
    return timerId
  }

  endPerformanceTimer(timerId: string, additionalContext?: LogContext) {
    const metric = this.performanceMetrics.get(timerId)
    if (!metric) return

    const endTime = performance.now()
    const duration = endTime - metric.startTime

    const finalMetric: PerformanceMetrics = {
      ...metric,
      endTime,
      duration,
      memoryUsage: this.getMemoryUsage()
    }

    this.recordPerformanceMetric(timerId, finalMetric)

    if (typeof window !== 'undefined' && window.performance?.mark) {
      window.performance.mark(`${metric.operation}-end`)
      window.performance.measure(metric.operation, `${metric.operation}-start`, `${metric.operation}-end`)
    }

    // Log slow operations
    if (duration > 1000) {
      this.warn(`Slow operation detected: ${metric.operation}`, {
        ...additionalContext,
        metadata: {
          ...(additionalContext?.metadata || {}),
          durationMs: duration.toFixed(2)
        }
      })
    }

    this.performanceMetrics.delete(timerId)
  }

  
  private recordPerformanceMetric(id: string, metric: PerformanceMetrics) {
    if (!this.isDevelopment) {
      // In production, queue metrics for analytics
      this.analyticsQueue.push({
        type: 'performance',
        id,
        ...metric,
        timestamp: new Date().toISOString()
      })
      
      // Process queue if it gets large
      if (this.analyticsQueue.length > 50) {
        this.flushAnalytics()
      }
    }
  }
  
  private getMemoryUsage(): number {
    if (typeof window !== 'undefined' && (window as any).performance?.memory) {
      return (window as any).performance.memory.usedJSHeapSize
    }
    return 0
  }
  
  // Chat-specific logging methods
  logStreamingStart(streamId: string, messageCount: number) {
    this.info('Stream started', {
      component: 'StreamingHandler',
      action: 'start_stream',
      metadata: { streamId, messageCount }
    })
  }
  
  logStreamingComplete(streamId: string, duration: number, chunkCount: number) {
    this.info('Stream completed', {
      component: 'StreamingHandler',
      action: 'complete_stream',
      metadata: { streamId, duration: `${duration.toFixed(2)}ms`, chunkCount }
    })
  }
  
  logStreamingError(streamId: string, error: Error) {
    this.error('Stream failed', error, {
      component: 'StreamingHandler',
      action: 'stream_error',
      metadata: { streamId }
    })
  }
  
  logStorageOperation(operation: string, success: boolean, size?: number) {
    this.info(`Storage ${operation}`, {
      component: 'ChatStorage',
      action: operation,
      metadata: { success, size: size ? `${size} bytes` : undefined }
    })
  }
  
  logStorageQuotaWarning(percentUsed: number, available: number) {
    this.warn('Storage quota warning', {
      component: 'ChatStorage',
      action: 'quota_warning',
      metadata: { percentUsed: `${(percentUsed * 100).toFixed(1)}%`, available }
    })
  }
  
  // Analytics integration (production only)
  private trackError(message: string, error: Error, context?: LogContext) {
    this.analyticsQueue.push({
      type: 'error',
      message,
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack?.substring(0, 1000) // Limit stack trace size
      },
      context,
      timestamp: new Date().toISOString(),
      url: typeof window !== 'undefined' ? window.location.href : undefined,
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined
    })
    
    // Immediately flush critical errors
    this.flushAnalytics()
  }
  
  private async flushAnalytics() {
    if (this.analyticsQueue.length === 0) return
    
    const batch = [...this.analyticsQueue]
    this.analyticsQueue.length = 0
    
    try {
      // In a real application, send to your analytics service
      // await this.sendToAnalyticsService(batch)
      
      // For now, just log the count in production
      if (!this.isDevelopment) {
        console.log(`Analytics batch sent: ${batch.length} events`)
      }
    } catch (error) {
      // Failed to send analytics, put back in queue
      this.analyticsQueue.unshift(...batch.slice(-10)) // Keep last 10 events
    }
  }
  
  // Cleanup
  destroy() {
    this.flushAnalytics()
    this.performanceMetrics.clear()
  }
}

// Export singleton instance
export const logger = new ProductionLogger()

// Cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    logger.destroy()
  })
}