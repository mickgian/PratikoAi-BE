'use client'

import { useEffect, useRef, useCallback, useState } from 'react'

interface PerformanceMetrics {
  // Typing performance
  typingSpeed: number // chars per second
  typingLatency: number // ms
  typingFrameRate: number // fps
  
  // Rendering performance  
  renderTime: number // ms
  componentUpdates: number
  reRenders: number
  
  // Memory usage
  memoryUsage: number // MB
  memoryPeak: number // MB
  
  // Network performance
  apiLatency: number // ms
  streamingLatency: number // ms
  
  // User experience
  timeToFirstMessage: number // ms
  timeToResponse: number // ms
  
  // Browser performance
  fps: number
  frameDrops: number
}

interface UsePerformanceMonitoringOptions {
  enabled?: boolean
  logToConsole?: boolean
  trackMemory?: boolean
  trackFPS?: boolean
  sampleInterval?: number
}

interface UsePerformanceMonitoringReturn {
  metrics: PerformanceMetrics
  startTypingMeasurement: () => void
  endTypingMeasurement: (charsTyped: number) => void
  recordRender: (componentName: string) => void
  recordAPICall: (duration: number) => void
  getPerformanceReport: () => string
  resetMetrics: () => void
}

/**
 * Performance monitoring hook for chat optimization
 * 
 * Features:
 * - Typing speed and latency measurement
 * - Memory usage tracking
 * - Frame rate monitoring
 * - API latency measurement
 * - User experience metrics
 * - Performance reporting
 */
export function usePerformanceMonitoring(
  options: UsePerformanceMonitoringOptions = {}
): UsePerformanceMonitoringReturn {
  const {
    enabled = process.env.NODE_ENV === 'development',
    logToConsole = false,
    trackMemory = true,
    trackFPS = true,
    sampleInterval = 5000 // 5 seconds
  } = options

  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    typingSpeed: 0,
    typingLatency: 0,
    typingFrameRate: 60,
    renderTime: 0,
    componentUpdates: 0,
    reRenders: 0,
    memoryUsage: 0,
    memoryPeak: 0,
    apiLatency: 0,
    streamingLatency: 0,
    timeToFirstMessage: 0,
    timeToResponse: 0,
    fps: 60,
    frameDrops: 0
  })

  const typingStartTime = useRef<number>(0)
  const renderTimes = useRef<number[]>([])
  const componentCounts = useRef<Map<string, number>>(new Map())
  const fpsCounter = useRef<{
    frames: number[]
    lastTime: number
  }>({ frames: [], lastTime: 0 })

  // Memory tracking
  const trackMemoryUsage = useCallback(() => {
    if (!trackMemory || !enabled) return

    try {
      const memInfo = (performance as any).memory
      if (memInfo) {
        const currentUsage = Math.round(memInfo.usedJSHeapSize / 1048576) // Convert to MB
        
        setMetrics(prev => {
          const newMetrics = {
            ...prev,
            memoryUsage: currentUsage,
            memoryPeak: Math.max(prev.memoryPeak, currentUsage)
          }
          
          if (logToConsole && currentUsage > prev.memoryPeak) {
            console.log(`📊 New memory peak: ${currentUsage}MB`)
          }
          
          return newMetrics
        })
      }
    } catch (error) {
      // Memory API not available
    }
  }, [trackMemory, enabled, logToConsole])

  // FPS tracking
  const trackFrameRate = useCallback(() => {
    if (!trackFPS || !enabled) return

    const now = performance.now()
    fpsCounter.current.frames.push(now)

    // Keep only frames from last second
    fpsCounter.current.frames = fpsCounter.current.frames.filter(
      time => now - time <= 1000
    )

    const currentFPS = fpsCounter.current.frames.length
    const expectedFrames = 60
    const frameDrops = Math.max(0, expectedFrames - currentFPS)

    setMetrics(prev => ({
      ...prev,
      fps: currentFPS,
      frameDrops: prev.frameDrops + frameDrops
    }))

    requestAnimationFrame(trackFrameRate)
  }, [trackFPS, enabled])

  // Start typing measurement
  const startTypingMeasurement = useCallback(() => {
    if (!enabled) return
    typingStartTime.current = performance.now()
  }, [enabled])

  // End typing measurement
  const endTypingMeasurement = useCallback((charsTyped: number) => {
    if (!enabled || typingStartTime.current === 0) return

    const endTime = performance.now()
    const duration = endTime - typingStartTime.current
    const speed = duration > 0 ? (charsTyped / duration) * 1000 : 0 // chars per second

    setMetrics(prev => ({
      ...prev,
      typingSpeed: speed,
      typingLatency: duration
    }))

    if (logToConsole) {
      console.log(`⌨️ Typing: ${speed.toFixed(1)} chars/sec, ${duration.toFixed(1)}ms latency`)
    }

    typingStartTime.current = 0
  }, [enabled, logToConsole])

  // Record render performance
  const recordRender = useCallback((componentName: string) => {
    if (!enabled) return

    const renderStart = performance.now()
    
    // Use setTimeout to measure after render
    setTimeout(() => {
      const renderEnd = performance.now()
      const renderTime = renderEnd - renderStart

      renderTimes.current.push(renderTime)
      if (renderTimes.current.length > 100) {
        renderTimes.current.shift()
      }

      const avgRenderTime = renderTimes.current.reduce((a, b) => a + b, 0) / renderTimes.current.length

      const count = componentCounts.current.get(componentName) || 0
      componentCounts.current.set(componentName, count + 1)

      setMetrics(prev => ({
        ...prev,
        renderTime: avgRenderTime,
        componentUpdates: prev.componentUpdates + 1,
        reRenders: componentName === 'ChatMessagesArea' ? prev.reRenders + 1 : prev.reRenders
      }))
    }, 0)
  }, [enabled])

  // Record API call performance
  const recordAPICall = useCallback((duration: number) => {
    if (!enabled) return

    setMetrics(prev => ({
      ...prev,
      apiLatency: duration,
      streamingLatency: duration // For now, same as API latency
    }))

    if (logToConsole) {
      console.log(`🌐 API call: ${duration.toFixed(1)}ms`)
    }
  }, [enabled, logToConsole])

  // Generate performance report
  const getPerformanceReport = useCallback(() => {
    const report = `
🚀 PratikoAI Performance Report
================================

⌨️ Typing Performance:
  Speed: ${metrics.typingSpeed.toFixed(1)} chars/sec (target: 30-50)
  Latency: ${metrics.typingLatency.toFixed(1)}ms

🎨 Rendering Performance:
  Avg Render Time: ${metrics.renderTime.toFixed(1)}ms
  Component Updates: ${metrics.componentUpdates}
  Re-renders: ${metrics.reRenders}

💾 Memory Usage:
  Current: ${metrics.memoryUsage}MB
  Peak: ${metrics.memoryPeak}MB

🌐 Network Performance:
  API Latency: ${metrics.apiLatency.toFixed(1)}ms
  Streaming Latency: ${metrics.streamingLatency.toFixed(1)}ms

📱 Browser Performance:
  FPS: ${metrics.fps} (target: 60)
  Frame Drops: ${metrics.frameDrops}

⏱️ User Experience:
  Time to First Message: ${metrics.timeToFirstMessage.toFixed(1)}ms
  Time to Response: ${metrics.timeToResponse.toFixed(1)}ms

Component Render Counts:
${Array.from(componentCounts.current.entries())
  .map(([name, count]) => `  ${name}: ${count}`)
  .join('\n')}
`

    return report.trim()
  }, [metrics])

  // Reset metrics
  const resetMetrics = useCallback(() => {
    setMetrics({
      typingSpeed: 0,
      typingLatency: 0,
      typingFrameRate: 60,
      renderTime: 0,
      componentUpdates: 0,
      reRenders: 0,
      memoryUsage: 0,
      memoryPeak: 0,
      apiLatency: 0,
      streamingLatency: 0,
      timeToFirstMessage: 0,
      timeToResponse: 0,
      fps: 60,
      frameDrops: 0
    })

    renderTimes.current = []
    componentCounts.current.clear()
    fpsCounter.current = { frames: [], lastTime: 0 }
  }, [])

  // Setup monitoring intervals
  useEffect(() => {
    if (!enabled) return

    // Memory monitoring
    const memoryInterval = setInterval(trackMemoryUsage, sampleInterval)

    // FPS monitoring
    if (trackFPS) {
      trackFrameRate()
    }

    // Performance logging
    if (logToConsole) {
      const logInterval = setInterval(() => {
        console.group('📊 Performance Metrics')
        console.log(getPerformanceReport())
        console.groupEnd()
      }, sampleInterval * 2) // Log every 10 seconds

      return () => {
        clearInterval(memoryInterval)
        clearInterval(logInterval)
      }
    }

    return () => {
      clearInterval(memoryInterval)
    }
  }, [enabled, sampleInterval, trackMemoryUsage, trackFPS, trackFrameRate, logToConsole, getPerformanceReport])

  // Performance warnings
  useEffect(() => {
    if (!enabled || !logToConsole) return

    // Warn about performance issues
    if (metrics.typingSpeed > 0 && (metrics.typingSpeed < 30 || metrics.typingSpeed > 60)) {
      console.warn(`⚠️ Typing speed out of range: ${metrics.typingSpeed.toFixed(1)} chars/sec`)
    }

    if (metrics.fps < 55) {
      console.warn(`⚠️ Low FPS detected: ${metrics.fps}`)
    }

    if (metrics.memoryUsage > 100) {
      console.warn(`⚠️ High memory usage: ${metrics.memoryUsage}MB`)
    }

    if (metrics.renderTime > 16) { // 60fps = 16.67ms per frame
      console.warn(`⚠️ Slow render time: ${metrics.renderTime.toFixed(1)}ms`)
    }
  }, [enabled, logToConsole, metrics])

  return {
    metrics,
    startTypingMeasurement,
    endTypingMeasurement,
    recordRender,
    recordAPICall,
    getPerformanceReport,
    resetMetrics
  }
}

/**
 * Hook to benchmark specific operations
 */
export function useBenchmark() {
  const [benchmarks, setBenchmarks] = useState<Map<string, number[]>>(new Map())

  const benchmark = useCallback((name: string, operation: () => void | Promise<void>) => {
    const start = performance.now()
    
    const finish = () => {
      const end = performance.now()
      const duration = end - start
      
      setBenchmarks(prev => {
        const newMap = new Map(prev)
        const existing = newMap.get(name) || []
        existing.push(duration)
        // Keep only last 100 measurements
        if (existing.length > 100) {
          existing.shift()
        }
        newMap.set(name, existing)
        return newMap
      })

      return duration
    }

    const result = operation()
    
    if (result instanceof Promise) {
      return result.then(() => finish())
    } else {
      return finish()
    }
  }, [])

  const getBenchmarkStats = useCallback((name: string) => {
    const times = benchmarks.get(name) || []
    if (times.length === 0) return null

    const sorted = [...times].sort((a, b) => a - b)
    const avg = times.reduce((a, b) => a + b, 0) / times.length
    const min = sorted[0]
    const max = sorted[sorted.length - 1]
    const median = sorted[Math.floor(sorted.length / 2)]
    const p95 = sorted[Math.floor(sorted.length * 0.95)]

    return {
      count: times.length,
      avg: avg.toFixed(2),
      min: min.toFixed(2),
      max: max.toFixed(2),
      median: median.toFixed(2),
      p95: p95.toFixed(2)
    }
  }, [benchmarks])

  return {
    benchmark,
    getBenchmarkStats,
    getAllBenchmarks: () => Array.from(benchmarks.keys()),
    clearBenchmarks: () => setBenchmarks(new Map())
  }
}