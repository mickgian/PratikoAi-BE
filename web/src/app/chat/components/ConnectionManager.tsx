'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Wifi, WifiOff, RefreshCw, AlertCircle } from 'lucide-react'

interface ConnectionStatus {
  isOnline: boolean
  isConnected: boolean
  lastError?: string
  retryCount: number
}

interface ConnectionManagerProps {
  onRetry?: () => void
  showOfflineIndicator?: boolean
}

/**
 * Connection manager with Italian localization
 * 
 * Features:
 * - Network status monitoring
 * - Connection retry logic
 * - User-friendly error messages in Italian
 * - Professional appearance
 * - Non-intrusive notifications
 */
export function ConnectionManager({ 
  onRetry, 
  showOfflineIndicator = true 
}: ConnectionManagerProps) {
  const [status, setStatus] = useState<ConnectionStatus>({
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
    isConnected: true,
    retryCount: 0
  })

  const [showRetryButton, setShowRetryButton] = useState(false)

  // Monitor network status
  useEffect(() => {
    const handleOnline = () => {
      setStatus(prev => ({ ...prev, isOnline: true }))
      setShowRetryButton(false)
    }

    const handleOffline = () => {
      setStatus(prev => ({ ...prev, isOnline: false, isConnected: false }))
      setShowRetryButton(true)
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  const handleRetry = useCallback(async () => {
    setStatus(prev => ({ 
      ...prev, 
      retryCount: prev.retryCount + 1,
      lastError: undefined 
    }))

    try {
      if (onRetry) {
        await onRetry()
      }
      
      setStatus(prev => ({ ...prev, isConnected: true }))
      setShowRetryButton(false)
    } catch (error) {
      setStatus(prev => ({ 
        ...prev, 
        isConnected: false,
        lastError: error instanceof Error ? error.message : 'Errore di connessione'
      }))
    }
  }, [onRetry])

  // Auto-retry logic
  useEffect(() => {
    if (!status.isOnline || status.isConnected || status.retryCount >= 3) return

    const retryDelay = Math.min(1000 * Math.pow(2, status.retryCount), 10000) // Exponential backoff
    const timer = setTimeout(handleRetry, retryDelay)

    return () => clearTimeout(timer)
  }, [status, handleRetry])

  // Don't show anything if everything is fine
  if (status.isOnline && status.isConnected && !status.lastError) {
    return null
  }

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm">
      {!status.isOnline && showOfflineIndicator && (
        <div className="bg-orange-500 text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 mb-2">
          <WifiOff className="w-5 h-5 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium">Connessione assente</p>
            <p className="text-xs opacity-90">
              Controlla la tua connessione internet
            </p>
          </div>
        </div>
      )}

      {status.isOnline && !status.isConnected && (
        <div className="bg-red-500 text-white px-4 py-3 rounded-lg shadow-lg">
          <div className="flex items-center gap-3 mb-2">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">Errore di connessione</p>
              <p className="text-xs opacity-90">
                {status.lastError || 'Impossibile connettersi al server'}
              </p>
            </div>
          </div>

          {showRetryButton && (
            <div className="flex items-center justify-between">
              <span className="text-xs opacity-75">
                Tentativo {status.retryCount}/3
              </span>
              <button
                onClick={handleRetry}
                disabled={status.retryCount >= 3}
                className="
                  flex items-center gap-1.5 px-3 py-1.5
                  bg-white/20 text-white text-xs font-medium
                  rounded border border-white/30
                  hover:bg-white/30 transition-colors
                  disabled:opacity-50 disabled:cursor-not-allowed
                "
              >
                <RefreshCw className="w-3 h-3" />
                Riprova
              </button>
            </div>
          )}
        </div>
      )}

      {status.isConnected && status.retryCount > 0 && (
        <div className="bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-3">
          <Wifi className="w-4 h-4 flex-shrink-0" />
          <p className="text-sm font-medium">Connessione ripristinata</p>
        </div>
      )}
    </div>
  )
}