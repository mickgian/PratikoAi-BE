'use client'

import { useEffect, useRef, useCallback } from 'react'

interface UseMemoryOptimizationOptions {
  /** Maximum number of messages to keep in memory */
  maxMessages?: number
  /** Enable automatic cleanup of event listeners */
  autoCleanup?: boolean
  /** Interval for memory cleanup checks (ms) */
  cleanupInterval?: number
}

interface UseMemoryOptimizationReturn {
  /** Register a cleanup function */
  registerCleanup: (cleanup: () => void) => void
  /** Force memory cleanup */
  forceCleanup: () => void
  /** Check current memory usage (if available) */
  getMemoryInfo: () => any
}

/**
 * Memory optimization hook for chat components
 * 
 * Features:
 * - Automatic cleanup of event listeners and timers
 * - Memory usage monitoring (when available)
 * - Message limit enforcement
 * - Performance optimization
 */
export function useMemoryOptimization(
  options: UseMemoryOptimizationOptions = {}
): UseMemoryOptimizationReturn {
  const {
    maxMessages = 1000,
    autoCleanup = true,
    cleanupInterval = 30000 // 30 seconds
  } = options

  const cleanupFunctions = useRef<(() => void)[]>([])
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  const registerCleanup = useCallback((cleanup: () => void) => {
    cleanupFunctions.current.push(cleanup)
  }, [])

  const forceCleanup = useCallback(() => {
    cleanupFunctions.current.forEach(cleanup => {
      try {
        cleanup()
      } catch (error) {
        console.warn('Memory cleanup error:', error)
      }
    })
    cleanupFunctions.current = []
  }, [])

  const getMemoryInfo = useCallback(() => {
    // Use Performance API if available (Chrome, Edge)
    if ('memory' in performance) {
      return {
        usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
        totalJSHeapSize: (performance as any).memory.totalJSHeapSize,
        jsHeapSizeLimit: (performance as any).memory.jsHeapSizeLimit
      }
    }

    // Fallback to basic info
    return {
      userAgent: navigator.userAgent,
      hardwareConcurrency: navigator.hardwareConcurrency || 'unknown',
      deviceMemory: (navigator as any).deviceMemory || 'unknown'
    }
  }, [])

  const performPeriodicCleanup = useCallback(() => {
    // Log memory info in development
    if (process.env.NODE_ENV === 'development') {
      const memInfo = getMemoryInfo()
      if (memInfo.usedJSHeapSize) {
        const usedMB = Math.round(memInfo.usedJSHeapSize / 1048576)
        const totalMB = Math.round(memInfo.totalJSHeapSize / 1048576)
        console.log(`💾 Memory usage: ${usedMB}MB / ${totalMB}MB`)
      }
    }

    // Force garbage collection if available (development only)
    if (process.env.NODE_ENV === 'development' && (window as any).gc) {
      (window as any).gc()
    }
  }, [getMemoryInfo])

  // Setup periodic cleanup
  useEffect(() => {
    if (autoCleanup) {
      intervalRef.current = setInterval(performPeriodicCleanup, cleanupInterval)
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [autoCleanup, cleanupInterval, performPeriodicCleanup])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      forceCleanup()
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [forceCleanup])

  return {
    registerCleanup,
    forceCleanup,
    getMemoryInfo
  }
}

/**
 * Message history optimization hook
 * Manages message history to prevent memory bloat
 */
export function useMessageHistoryOptimization(messages: any[], maxMessages: number = 500) {
  const optimizedMessages = messages.slice(-maxMessages)
  
  const isOptimized = messages.length > maxMessages
  const removedCount = isOptimized ? messages.length - maxMessages : 0

  return {
    messages: optimizedMessages,
    isOptimized,
    removedCount,
    totalCount: messages.length
  }
}