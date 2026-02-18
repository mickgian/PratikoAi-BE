'use client'

import React from 'react'
import { AlertCircle, Wifi, Clock, FileText } from 'lucide-react'

// Empty Response Handler
interface EmptyResponseProps {
  show: boolean
  onRetry?: () => void
}

export function EmptyResponseHandler({ show, onRetry }: EmptyResponseProps) {
  if (!show) return null

  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 my-4">
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-yellow-800 mb-1">
            Risposta Vuota
          </h4>
          <p className="text-sm text-yellow-700 mb-3">
            Il server non ha fornito alcuna risposta. Questo può accadere per domande molto specifiche 
            o problemi temporanei del servizio.
          </p>
          <div className="flex flex-col sm:flex-row gap-2">
            <button
              onClick={onRetry}
              className="
                px-3 py-1.5 text-sm font-medium
                bg-yellow-600 text-white rounded
                hover:bg-yellow-700 transition-colors
              "
            >
              Riprova la domanda
            </button>
            <span className="text-xs text-yellow-600 py-1.5">
              Oppure prova a riformulare la domanda
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

// Long Message Handler
interface LongMessageProps {
  contentLength: number
  showWarning?: boolean
  estimatedReadTime?: number
}

export function LongMessageIndicator({ 
  contentLength, 
  showWarning = true,
  estimatedReadTime 
}: LongMessageProps) {
  const isLong = contentLength > 3000
  const isVeryLong = contentLength > 8000
  
  if (!isLong || !showWarning) return null

  const readTime = estimatedReadTime || Math.ceil(contentLength / 1000) // ~1000 chars per minute

  return (
    <div className={`
      ${isVeryLong ? 'bg-orange-50 border-orange-200' : 'bg-blue-50 border-blue-200'}
      border rounded-lg p-3 mb-4
    `}>
      <div className="flex items-center gap-2">
        <FileText className={`w-4 h-4 ${isVeryLong ? 'text-orange-600' : 'text-blue-600'}`} />
        <span className={`text-sm font-medium ${isVeryLong ? 'text-orange-800' : 'text-blue-800'}`}>
          {isVeryLong ? 'Risposta molto dettagliata' : 'Risposta dettagliata'}
        </span>
        <span className={`text-xs ${isVeryLong ? 'text-orange-600' : 'text-blue-600'}`}>
          ~{readTime} min di lettura
        </span>
      </div>
    </div>
  )
}

// Network Issue Handler
interface NetworkIssueProps {
  type: 'slow' | 'disconnected' | 'timeout' | 'error'
  message?: string
  onRetry?: () => void
  onCancel?: () => void
}

export function NetworkIssueHandler({ 
  type, 
  message, 
  onRetry, 
  onCancel 
}: NetworkIssueProps) {
  const getConfig = () => {
    switch (type) {
      case 'slow':
        return {
          icon: Clock,
          color: 'yellow',
          title: 'Connessione Lenta',
          description: 'La risposta sta richiedendo più tempo del previsto. La connessione potrebbe essere lenta.',
          actionText: 'Continua ad attendere'
        }
      case 'disconnected':
        return {
          icon: Wifi,
          color: 'red',
          title: 'Connessione Persa',
          description: 'La connessione internet è stata interrotta durante la comunicazione.',
          actionText: 'Riconnetti'
        }
      case 'timeout':
        return {
          icon: Clock,
          color: 'orange',
          title: 'Timeout',
          description: 'Il server non ha risposto entro il tempo limite. Riprova tra qualche momento.',
          actionText: 'Riprova'
        }
      case 'error':
      default:
        return {
          icon: AlertCircle,
          color: 'red',
          title: 'Errore di Rete',
          description: message || 'Si è verificato un errore durante la comunicazione con il server.',
          actionText: 'Riprova'
        }
    }
  }

  const config = getConfig()
  const Icon = config.icon
  const colorClass = config.color

  return (
    <div className={`
      bg-${colorClass}-50 border border-${colorClass}-200 rounded-lg p-4 my-4
    `}>
      <div className="flex items-start gap-3">
        <Icon className={`w-5 h-5 text-${colorClass}-600 mt-0.5 flex-shrink-0`} />
        <div className="flex-1 min-w-0">
          <h4 className={`text-sm font-medium text-${colorClass}-800 mb-1`}>
            {config.title}
          </h4>
          <p className={`text-sm text-${colorClass}-700 mb-3`}>
            {config.description}
          </p>
          <div className="flex flex-col sm:flex-row gap-2">
            {onRetry && (
              <button
                onClick={onRetry}
                className={`
                  px-3 py-1.5 text-sm font-medium
                  bg-${colorClass}-600 text-white rounded
                  hover:bg-${colorClass}-700 transition-colors
                `}
              >
                {config.actionText}
              </button>
            )}
            {onCancel && (
              <button
                onClick={onCancel}
                className="
                  px-3 py-1.5 text-sm font-medium
                  border border-gray-300 text-gray-700 rounded
                  hover:bg-gray-50 transition-colors
                "
              >
                Annulla
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// Streaming Status Indicator
interface StreamingStatusProps {
  isStreaming: boolean
  contentLength: number
  estimatedTimeRemaining?: number
  canCancel?: boolean
  onCancel?: () => void
}

export function StreamingStatusIndicator({ 
  isStreaming,
  contentLength,
  estimatedTimeRemaining,
  canCancel = false,
  onCancel
}: StreamingStatusProps) {
  if (!isStreaming) return null

  const charsPerSecond = 40 // As per requirements
  const estimatedRemaining = estimatedTimeRemaining || 
    Math.max(1, Math.ceil((5000 - contentLength) / charsPerSecond))

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="animate-pulse w-2 h-2 bg-blue-600 rounded-full" />
          <span className="text-sm font-medium text-blue-800">
            PratikoAI sta scrivendo...
          </span>
          <span className="text-xs text-blue-600">
            {contentLength} caratteri
          </span>
        </div>
        
        {canCancel && onCancel && (
          <button
            onClick={onCancel}
            className="
              text-xs text-blue-600 hover:text-blue-800
              px-2 py-1 rounded hover:bg-blue-100
              transition-colors
            "
          >
            Interrompi
          </button>
        )}
      </div>
      
      {estimatedRemaining > 0 && (
        <div className="mt-2 text-xs text-blue-600">
          Tempo stimato: ~{estimatedRemaining}s
        </div>
      )}
    </div>
  )
}

// Rate Limit Handler
interface RateLimitProps {
  show: boolean
  resetTime?: number
  onClose?: () => void
}

export function RateLimitHandler({ show, resetTime, onClose }: RateLimitProps) {
  if (!show) return null

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds} secondi`
    return `${Math.ceil(seconds / 60)} minuti`
  }

  return (
    <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 my-4">
      <div className="flex items-start gap-3">
        <Clock className="w-5 h-5 text-orange-600 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-orange-800 mb-1">
            Limite di Utilizzo Raggiunto
          </h4>
          <p className="text-sm text-orange-700 mb-3">
            Hai raggiunto il limite di messaggi per questo periodo. 
            {resetTime && ` Potrai inviare nuovi messaggi tra ${formatTime(resetTime)}.`}
          </p>
          {onClose && (
            <button
              onClick={onClose}
              className="
                px-3 py-1.5 text-sm font-medium
                border border-orange-300 text-orange-700 rounded
                hover:bg-orange-100 transition-colors
              "
            >
              Ho capito
            </button>
          )}
        </div>
      </div>
    </div>
  )
}