'use client'

import { useState, useEffect, useCallback } from 'react'

interface MobileState {
  isMobile: boolean
  isTablet: boolean
  isDesktop: boolean
  screenSize: 'sm' | 'md' | 'lg' | 'xl' | '2xl'
  orientation: 'portrait' | 'landscape'
  hasTouch: boolean
  isKeyboardVisible: boolean
  viewportHeight: number
  safeAreaInsets: {
    top: number
    right: number
    bottom: number
    left: number
  }
}

interface UseMobileOptimizationReturn {
  mobileState: MobileState
  isKeyboardOpen: boolean
  adjustForKeyboard: boolean
  mobileClasses: string
  containerClasses: string
}

/**
 * Mobile optimization hook for chat interface
 * 
 * Features:
 * - Device detection and responsive behavior
 * - Virtual keyboard handling for iOS/Android
 * - Safe area support for notched devices
 * - Touch interaction optimization
 * - Performance optimization for mobile
 */
export function useMobileOptimization(): UseMobileOptimizationReturn {
  const [mobileState, setMobileState] = useState<MobileState>({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    screenSize: 'lg',
    orientation: 'landscape',
    hasTouch: false,
    isKeyboardVisible: false,
    viewportHeight: typeof window !== 'undefined' ? window.innerHeight : 800,
    safeAreaInsets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  })

  const [initialViewportHeight, setInitialViewportHeight] = useState(0)

  // Detect device capabilities
  const detectDeviceCapabilities = useCallback(() => {
    if (typeof window === 'undefined') return

    const userAgent = navigator.userAgent.toLowerCase()
    const isMobile = /android|iphone|ipad|ipod|blackberry|iemobile|opera mini/.test(userAgent)
    const isTablet = /ipad|android(?!.*mobile)/.test(userAgent)
    const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0

    // Get screen size category
    const width = window.innerWidth
    let screenSize: MobileState['screenSize'] = 'sm'
    if (width >= 1536) screenSize = '2xl'
    else if (width >= 1280) screenSize = 'xl'  
    else if (width >= 1024) screenSize = 'lg'
    else if (width >= 768) screenSize = 'md'
    else screenSize = 'sm'

    const orientation = window.innerHeight > window.innerWidth ? 'portrait' : 'landscape'

    return {
      isMobile,
      isTablet,
      isDesktop: !isMobile && !isTablet,
      screenSize,
      orientation,
      hasTouch
    }
  }, [])

  // Detect safe area insets (for iOS notch, etc.)
  const detectSafeAreaInsets = useCallback(() => {
    if (typeof window === 'undefined') return { top: 0, right: 0, bottom: 0, left: 0 }

    const styles = getComputedStyle(document.documentElement)
    
    return {
      top: parseInt(styles.getPropertyValue('--sat') || '0', 10),
      right: parseInt(styles.getPropertyValue('--sar') || '0', 10),
      bottom: parseInt(styles.getPropertyValue('--sab') || '0', 10),
      left: parseInt(styles.getPropertyValue('--sal') || '0', 10)
    }
  }, [])

  // Handle viewport changes (including keyboard)
  const handleViewportChange = useCallback(() => {
    if (typeof window === 'undefined') return

    const currentHeight = window.innerHeight
    const capabilities = detectDeviceCapabilities()
    const safeAreaInsets = detectSafeAreaInsets()
    
    // Initialize height on first run
    if (initialViewportHeight === 0) {
      setInitialViewportHeight(currentHeight)
    }

    // Detect keyboard on mobile (iOS/Android behavior)
    const heightDifference = initialViewportHeight - currentHeight
    const isKeyboardVisible = capabilities?.isMobile && heightDifference > 150

    if (capabilities) {
      setMobileState(prev => ({
        ...prev,
        ...capabilities,
        orientation: capabilities.orientation as 'portrait' | 'landscape',
        viewportHeight: currentHeight,
        isKeyboardVisible: Boolean(isKeyboardVisible),
        safeAreaInsets
      }))
    }
  }, [detectDeviceCapabilities, detectSafeAreaInsets, initialViewportHeight])

  // Setup event listeners
  useEffect(() => {
    if (typeof window === 'undefined') return

    // Initial setup
    handleViewportChange()

    // Listen for viewport changes
    const handleResize = () => {
      // Debounce resize events
      setTimeout(handleViewportChange, 100)
    }

    const handleOrientationChange = () => {
      // Wait for orientation change to complete
      setTimeout(handleViewportChange, 300)
    }

    window.addEventListener('resize', handleResize)
    window.addEventListener('orientationchange', handleOrientationChange)

    // CSS environment variables for safe area insets
    const updateSafeAreaVars = () => {
      const root = document.documentElement
      root.style.setProperty('--sat', 'env(safe-area-inset-top)')
      root.style.setProperty('--sar', 'env(safe-area-inset-right)')
      root.style.setProperty('--sab', 'env(safe-area-inset-bottom)')
      root.style.setProperty('--sal', 'env(safe-area-inset-left)')
    }

    updateSafeAreaVars()

    return () => {
      window.removeEventListener('resize', handleResize)
      window.removeEventListener('orientationchange', handleOrientationChange)
    }
  }, [handleViewportChange])

  // Derived state
  const isKeyboardOpen = mobileState.isKeyboardVisible
  const adjustForKeyboard = mobileState.isMobile && isKeyboardOpen

  // Generate responsive classes
  const mobileClasses = [
    mobileState.isMobile ? 'mobile-device' : '',
    mobileState.isTablet ? 'tablet-device' : '',
    mobileState.hasTouch ? 'touch-device' : '',
    `screen-${mobileState.screenSize}`,
    `orientation-${mobileState.orientation}`,
    isKeyboardOpen ? 'keyboard-visible' : 'keyboard-hidden'
  ].filter(Boolean).join(' ')

  // Container classes for proper mobile layout
  const containerClasses = [
    'w-full h-full',
    mobileState.isMobile ? 'mobile-container' : 'desktop-container',
    adjustForKeyboard ? 'keyboard-adjusted' : '',
    mobileState.orientation === 'portrait' ? 'portrait-layout' : 'landscape-layout'
  ].filter(Boolean).join(' ')

  return {
    mobileState,
    isKeyboardOpen,
    adjustForKeyboard,
    mobileClasses,
    containerClasses
  }
}

/**
 * iOS-specific optimization hook
 * Handles iOS Safari quirks and optimizations
 */
export function useIOSOptimization() {
  const [isIOS, setIsIOS] = useState(false)
  const [isSafari, setIsSafari] = useState(false)
  const [iosVersion, setIOSVersion] = useState<number | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return

    const userAgent = navigator.userAgent
    const isIOSDevice = /iPad|iPhone|iPod/.test(userAgent)
    const isSafariDetected = /Safari/.test(userAgent) && !/Chrome|CriOS|FxiOS/.test(userAgent)
    
    let version: number | null = null
    if (isIOSDevice) {
      const match = userAgent.match(/OS (\d+)_(\d+)/)
      if (match) {
        version = parseInt(match[1], 10)
      }
    }

    setIsIOS(isIOSDevice)
    setIsSafari(isSafariDetected)
    setIOSVersion(version)

    // iOS-specific CSS fixes
    if (isIOSDevice) {
      document.documentElement.classList.add('ios-device')
      
      // Fix iOS Safari bounce scrolling
      document.body.style.overscrollBehavior = 'none'
      
      // Fix iOS Safari viewport unit issues
      const updateIOSHeight = () => {
        document.documentElement.style.setProperty(
          '--ios-vh',
          `${window.innerHeight * 0.01}px`
        )
      }
      
      updateIOSHeight()
      window.addEventListener('resize', updateIOSHeight)
      window.addEventListener('orientationchange', () => {
        setTimeout(updateIOSHeight, 300)
      })

      return () => {
        window.removeEventListener('resize', updateIOSHeight)
      }
    }
  }, [])

  return {
    isIOS,
    isSafari,
    iosVersion,
    isLegacyIOS: iosVersion !== null && iosVersion < 13
  }
}

/**
 * Touch optimization hook
 * Optimizes touch interactions for mobile devices
 */
export function useTouchOptimization() {
  const [touchCapabilities, setTouchCapabilities] = useState({
    hasTouch: false,
    maxTouchPoints: 0,
    supportsPressure: false,
    supportsForce: false
  })

  useEffect(() => {
    if (typeof window === 'undefined') return

    const hasTouch = 'ontouchstart' in window
    const maxTouchPoints = navigator.maxTouchPoints || 0
    
    // Feature detection
    const supportsPressure = 'pressure' in (new Touch({
      identifier: 0,
      target: document.body,
      clientX: 0,
      clientY: 0
    }) as any)

    const supportsForce = 'force' in (new Touch({
      identifier: 0,
      target: document.body,
      clientX: 0,
      clientY: 0
    }) as any)

    setTouchCapabilities({
      hasTouch,
      maxTouchPoints,
      supportsPressure,
      supportsForce
    })

    // Add touch classes to document
    if (hasTouch) {
      document.documentElement.classList.add('touch-enabled')
    }
  }, [])

  return touchCapabilities
}