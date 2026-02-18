'use client'

import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: ErrorInfo
}

/**
 * Chat-specific error boundary with Italian localization
 * 
 * Features:
 * - Catches JavaScript errors in chat components
 * - Shows user-friendly error message in Italian
 * - Provides recovery options
 * - Maintains professional appearance
 * - Logs errors for debugging
 */
export class ChatErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Chat Error Boundary caught an error:', error, errorInfo)
    
    this.setState({
      error,
      errorInfo
    })

    // In production, send to error reporting service
    if (process.env.NODE_ENV === 'production') {
      // TODO: Send to error reporting service
      console.error('Production error in chat:', {
        error: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack
      })
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="flex flex-col items-center justify-center h-64 p-6 bg-[#F8F5F1] rounded-lg">
          <div className="flex flex-col items-center max-w-md text-center">
            <div className="w-16 h-16 mb-4 flex items-center justify-center bg-red-50 rounded-full">
              <AlertTriangle className="w-8 h-8 text-red-500" />
            </div>
            
            <h3 className="text-lg font-semibold text-[#1E293B] mb-2">
              Si è verificato un errore
            </h3>
            
            <p className="text-sm text-[#64748B] mb-6 leading-relaxed">
              Qualcosa è andato storto durante l&apos;utilizzo della chat. 
              Prova a ricaricare la pagina o riprova più tardi.
            </p>

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={this.handleRetry}
                className="
                  flex items-center gap-2 px-4 py-2 
                  bg-[#2A5D67] text-white 
                  rounded-lg font-medium 
                  hover:bg-[#2A5D67]/90 
                  transition-colors
                "
              >
                <RefreshCw className="w-4 h-4" />
                Riprova
              </button>
              
              <button
                onClick={() => window.location.reload()}
                className="
                  px-4 py-2 
                  border border-[#E2E8F0] text-[#64748B] 
                  rounded-lg font-medium 
                  hover:bg-gray-50 
                  transition-colors
                "
              >
                Ricarica la pagina
              </button>
            </div>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mt-6 w-full">
                <summary className="cursor-pointer text-xs text-gray-500 mb-2">
                  Dettagli errore (solo sviluppo)
                </summary>
                <div className="text-left text-xs bg-gray-100 p-3 rounded border overflow-auto max-h-32">
                  <div className="font-mono text-red-600">
                    {this.state.error.message}
                  </div>
                  <div className="font-mono text-gray-600 mt-2 text-xs">
                    {this.state.error.stack}
                  </div>
                </div>
              </details>
            )}
          </div>
        </div>
      )
    }

    return this.props.children
  }
}