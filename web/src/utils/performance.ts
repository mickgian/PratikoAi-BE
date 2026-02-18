/**
 * Production Performance Utilities
 * 
 * Provides performance monitoring and optimization utilities
 * for the chat application.
 */

import { logger } from './logger'

// Performance thresholds (in milliseconds)
const THRESHOLDS = {
  RENDER_SLOW: 100,
  API_SLOW: 2000,
  STORAGE_SLOW: 50,
  STREAMING_CHUNK_SLOW: 16, // 60fps target
  MEMORY_WARNING_MB: 50,
  MEMORY_CRITICAL_MB: 100
}

// Performance monitoring utilities
export class PerformanceMonitor {
  private static instance: PerformanceMonitor
  private observers: PerformanceObserver[] = []
  private timers: Map<string, number> = new Map()
  private metrics: Map<string, number[]> = new Map()
  
  static getInstance(): PerformanceMonitor {
    if (!this.instance) {
      this.instance = new PerformanceMonitor()
    }
    return this.instance
  }
  
  constructor() {
    if (typeof window !== 'undefined') {
      this.setupObservers()
      this.startMemoryMonitoring()
    }
  }
  
  private setupObservers() {
    try {
      // Long Task Observer
      if ('PerformanceObserver' in window) {
        const longTaskObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.duration > THRESHOLDS.RENDER_SLOW) {
              logger.warn('Long task detected', {
                component: 'PerformanceMonitor',
                action: 'long_task',
                metadata: {
                  duration: `${entry.duration.toFixed(2)}ms`,
                  startTime: entry.startTime,
                  name: entry.name
                }
              })
            }
          }
        })
        
        longTaskObserver.observe({ entryTypes: ['longtask'] })
        this.observers.push(longTaskObserver)
      }
      
      // Layout Shift Observer
      if ('PerformanceObserver' in window) {
        const layoutShiftObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if ((entry as any).value > 0.1) { // CLS threshold
              logger.info('Layout shift detected', {
                component: 'PerformanceMonitor',
                action: 'layout_shift',
                metadata: {
                  value: (entry as any).value,
                  hadRecentInput: (entry as any).hadRecentInput
                }
              })
            }
          }
        })
        
        try {
          layoutShiftObserver.observe({ entryTypes: ['layout-shift'] })
          this.observers.push(layoutShiftObserver)
        } catch (error) {
          // layout-shift not supported in all browsers
        }
      }
    } catch (error) {
      logger.warn('Failed to setup performance observers', {
        component: 'PerformanceMonitor',
        action: 'observer_setup_failed',
        metadata: { error: (error as Error).message }
      })
    }
  }
  
  private startMemoryMonitoring() {
    if (typeof window === 'undefined' || !(window as any).performance?.memory) {
      return
    }
    
    setInterval(() => {
      const memory = (window as any).performance.memory
      const usedMB = memory.usedJSHeapSize / 1024 / 1024
      const totalMB = memory.totalJSHeapSize / 1024 / 1024
      
      if (usedMB > THRESHOLDS.MEMORY_CRITICAL_MB) {
        logger.error('Critical memory usage', new Error('Memory usage exceeded threshold'), {
          component: 'PerformanceMonitor',
          action: 'memory_critical',
          metadata: { usedMB: usedMB.toFixed(2), totalMB: totalMB.toFixed(2) }
        })
      } else if (usedMB > THRESHOLDS.MEMORY_WARNING_MB) {
        logger.warn('High memory usage', {
          component: 'PerformanceMonitor',
          action: 'memory_warning',
          metadata: { usedMB: usedMB.toFixed(2), totalMB: totalMB.toFixed(2) }
        })
      }
    }, 30000) // Check every 30 seconds
  }
  
  // High-level timing utilities
  startTiming(operation: string): string {
    const timerId = `${operation}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    this.timers.set(timerId, performance.now())
    return timerId
  }
  
  endTiming(timerId: string, operation?: string): number {
    const startTime = this.timers.get(timerId)
    if (!startTime) return 0
    
    const duration = performance.now() - startTime
    this.timers.delete(timerId)
    
    // Store metric
    const op = operation || timerId.split('-')[0]
    if (!this.metrics.has(op)) {
      this.metrics.set(op, [])
    }
    this.metrics.get(op)!.push(duration)
    
    // Check thresholds
    this.checkThresholds(op, duration)
    
    return duration
  }
  
  private checkThresholds(operation: string, duration: number) {
    let threshold = THRESHOLDS.RENDER_SLOW
    
    if (operation.includes('api') || operation.includes('fetch')) {
      threshold = THRESHOLDS.API_SLOW
    } else if (operation.includes('storage')) {
      threshold = THRESHOLDS.STORAGE_SLOW
    } else if (operation.includes('stream') || operation.includes('chunk')) {
      threshold = THRESHOLDS.STREAMING_CHUNK_SLOW
    }
    
    if (duration > threshold) {
      logger.warn(`Slow ${operation} detected`, {
        component: 'PerformanceMonitor',
        action: 'slow_operation',
        metadata: {
          operation,
          duration: `${duration.toFixed(2)}ms`,
          threshold: `${threshold}ms`
        }
      })
    }
  }
  
  // Get performance statistics
  getStats(operation?: string): Record<string, { avg: number, min: number, max: number, count: number }> {
    const stats: Record<string, { avg: number, min: number, max: number, count: number }> = {}
    
    const operations = operation ? [operation] : Array.from(this.metrics.keys())
    
    for (const op of operations) {
      const values = this.metrics.get(op) || []
      if (values.length === 0) continue
      
      stats[op] = {
        avg: values.reduce((sum, val) => sum + val, 0) / values.length,
        min: Math.min(...values),
        max: Math.max(...values),
        count: values.length
      }
    }
    
    return stats
  }
  
  // Clear metrics (for memory management)
  clearMetrics(operation?: string) {
    if (operation) {
      this.metrics.delete(operation)
    } else {
      this.metrics.clear()
    }
  }
  
  // Cleanup
  destroy() {
    this.observers.forEach(observer => observer.disconnect())
    this.observers = []
    this.timers.clear()
    this.metrics.clear()
  }
}

// React performance utilities
export function measureComponentRender<T extends Record<string, any>>(
  componentName: string,
  props: T
): T {
  if (process.env.NODE_ENV === 'development') {
    const timer = PerformanceMonitor.getInstance().startTiming(`render-${componentName}`)
    
    // Use useEffect equivalent in function components to end timing
    setTimeout(() => {
      PerformanceMonitor.getInstance().endTiming(timer, `render-${componentName}`)
    }, 0)
  }
  
  return props
}

// Storage performance utilities
export async function measureStorageOperation<T>(
  operation: string,
  fn: () => Promise<T> | T
): Promise<T> {
  const timer = PerformanceMonitor.getInstance().startTiming(`storage-${operation}`)
  
  try {
    const result = await fn()
    PerformanceMonitor.getInstance().endTiming(timer, `storage-${operation}`)
    return result
  } catch (error) {
    PerformanceMonitor.getInstance().endTiming(timer, `storage-${operation}`)
    throw error
  }
}

// API performance utilities
export async function measureApiCall<T>(
  endpoint: string,
  fn: () => Promise<T>
): Promise<T> {
  const timer = PerformanceMonitor.getInstance().startTiming(`api-${endpoint.replace(/[^a-zA-Z0-9]/g, '-')}`)
  
  try {
    const result = await fn()
    PerformanceMonitor.getInstance().endTiming(timer, `api-${endpoint}`)
    return result
  } catch (error) {
    PerformanceMonitor.getInstance().endTiming(timer, `api-${endpoint}`)
    throw error
  }
}

// Stream performance utilities
export function measureStreamingChunk(chunkSize: number, processingFn: () => void) {
  const timer = PerformanceMonitor.getInstance().startTiming('streaming-chunk')
  
  try {
    processingFn()
  } finally {
    const duration = PerformanceMonitor.getInstance().endTiming(timer, 'streaming-chunk')
    
    // Log if processing is too slow for 60fps
    if (duration > THRESHOLDS.STREAMING_CHUNK_SLOW) {
      logger.debug('Slow streaming chunk processing', {
        component: 'StreamingPerformance',
        action: 'slow_chunk',
        metadata: {
          chunkSize,
          duration: `${duration.toFixed(2)}ms`,
          fps: `${(1000 / duration).toFixed(1)} fps`
        }
      })
    }
  }
}

// Memory management utilities
export function requestIdleCallback(callback: () => void, options?: { timeout?: number }) {
  if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
    return window.requestIdleCallback(callback, options)
  } else {
    // Fallback for browsers without requestIdleCallback
    return setTimeout(callback, 0)
  }
}

export function scheduleCleanupTask(task: () => void) {
  requestIdleCallback(() => {
    try {
      task()
    } catch (error) {
      logger.warn('Cleanup task failed', {
        component: 'PerformanceUtils',
        action: 'cleanup_failed',
        metadata: { error: (error as Error).message }
      })
    }
  }, { timeout: 5000 })
}

// Bundle size optimization utilities
export function lazyImport<T = any>(importFn: () => Promise<{ default: T }>): Promise<T> {
  return importFn().then(module => module.default)
}

// Web Vitals integration
export function reportWebVitals(metric: any) {
  // This would typically send to your analytics service
  logger.info('Web Vitals metric', {
    component: 'WebVitals',
    action: 'metric_reported',
    metadata: {
      name: metric.name,
      value: metric.value,
      rating: metric.rating
    }
  })
}

// Export singleton
export const performanceMonitor = PerformanceMonitor.getInstance()

// Cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    performanceMonitor.destroy()
  })
}