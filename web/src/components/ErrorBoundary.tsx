/**
 * Error Boundary Component for Production Error Handling
 * 
 * Provides graceful error recovery and analytics integration
 * for the chat application.
 */

'use client'

import React, { Component, ErrorInfo, ReactNode } from 'react'
import { logger } from '../utils/logger'
import { Button } from './ui/button'
import { AlertCircle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
  retryCount: number
}

export class ErrorBoundary extends Component<Props, State> {
  private maxRetries = 3
  
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0
    }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to production logger
    logger.error('React Error Boundary caught error', error, {
      component: 'ErrorBoundary',
      action: 'component_error',
      metadata: {
        componentStack: errorInfo.componentStack?.slice(0, 1000) || 'Unknown', // Limit size
        retryCount: this.state.retryCount
      }
    })

    this.setState({
      errorInfo
    })

    // Call optional error handler
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }
  }

  handleRetry = () => {
    if (this.state.retryCount >= this.maxRetries) {
      // Max retries reached, reload page
      window.location.reload()
      return
    }

    logger.info('Retrying after error boundary catch', {
      component: 'ErrorBoundary',
      action: 'retry_attempt',
      metadata: { retryCount: this.state.retryCount + 1 }
    })

    this.setState(prevState => ({
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: prevState.retryCount + 1
    }))
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback
      }

      // Default error UI
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
          <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center">
            <div className="flex justify-center mb-4">
              <AlertCircle className="h-12 w-12 text-red-500" />
            </div>
            
            <h1 className="text-xl font-bold text-gray-900 mb-2">
              Si è verificato un errore
            </h1>
            
            <p className="text-gray-600 mb-6">
              {process.env.NODE_ENV === 'development' 
                ? `Errore: ${this.state.error?.message || 'Errore sconosciuto'}`
                : 'Ci scusiamo per l\'inconveniente. L\'errore è stato segnalato al nostro team.'
              }
            </p>

            <div className="space-y-3">
              <Button 
                onClick={this.handleRetry}
                className="w-full"
                disabled={this.state.retryCount >= this.maxRetries}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                {this.state.retryCount >= this.maxRetries ? 'Ricarica Pagina' : 'Riprova'}
              </Button>

              <Button 
                variant="outline" 
                onClick={() => window.location.href = '/'}
                className="w-full"
              >
                Torna alla Home
              </Button>
            </div>

            {/* Development-only error details */}
            {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
              <details className="mt-6 text-left bg-gray-100 p-4 rounded text-xs">
                <summary className="cursor-pointer font-medium">Dettagli Errore</summary>
                <pre className="mt-2 whitespace-pre-wrap break-words">
                  {this.state.error?.stack}
                </pre>
                <pre className="mt-2 whitespace-pre-wrap break-words">
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}

            <p className="text-xs text-gray-400 mt-4">
              Tentativi: {this.state.retryCount}/{this.maxRetries}
            </p>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

// Chat-specific error boundary
export function ChatErrorBoundary({ children }: { children: ReactNode }) {
  const handleChatError = (error: Error, errorInfo: ErrorInfo) => {
    // Chat-specific error handling
    logger.error('Chat component error', error, {
      component: 'ChatErrorBoundary',
      action: 'chat_error',
      metadata: {
        timestamp: new Date().toISOString(),
        url: window.location.href
      }
    })
  }

  return (
    <ErrorBoundary 
      onError={handleChatError}
      fallback={
        <div className="flex items-center justify-center h-96 bg-gray-50 rounded-lg border">
          <div className="text-center">
            <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
            <p className="text-sm text-gray-600">
              Errore nel caricamento della chat
            </p>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => window.location.reload()}
              className="mt-3"
            >
              Ricarica
            </Button>
          </div>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  )
}

// Hook for programmatic error reporting
export function useErrorReporting() {
  const reportError = (error: Error, context?: string) => {
    logger.error('Manual error report', error, {
      component: 'ErrorReporting',
      action: 'manual_report',
      metadata: { context }
    })
  }

  return { reportError }
}