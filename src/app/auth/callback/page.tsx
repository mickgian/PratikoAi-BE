'use client'

import React, { useEffect, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'

function OAuthCallbackContent() {
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing')
  const [message, setMessage] = useState('Elaborazione autenticazione...')
  const searchParams = useSearchParams()

  useEffect(() => {
    const handleOAuthCallback = () => {
      try {
        const code = searchParams.get('code')
        const state = searchParams.get('state')
        const error = searchParams.get('error')
        const errorDescription = searchParams.get('error_description')

        if (error) {
          console.error('OAuth Error:', error, errorDescription)
          setStatus('error')
          setMessage(`Errore OAuth: ${errorDescription || error}`)
          
          // Send error to parent window
          if (window.opener) {
            window.opener.postMessage({
              type: 'OAUTH_ERROR',
              error: errorDescription || error
            }, window.location.origin)
          }
          return
        }

        if (!code) {
          setStatus('error')
          setMessage('Codice di autorizzazione mancante')
          
          if (window.opener) {
            window.opener.postMessage({
              type: 'OAUTH_ERROR',
              error: 'Authorization code missing'
            }, window.location.origin)
          }
          return
        }

        setStatus('success')
        setMessage('Autenticazione completata! Chiusura finestra in corso...')

        // Send success data to parent window
        if (window.opener) {
          window.opener.postMessage({
            type: 'OAUTH_SUCCESS',
            code,
            state
          }, window.location.origin)
        }

        // Close popup after a short delay
        setTimeout(() => {
          window.close()
        }, 1000)

      } catch (error) {
        console.error('Callback processing error:', error)
        setStatus('error')
        setMessage('Errore durante l\'elaborazione dell\'autenticazione')
        
        if (window.opener) {
          window.opener.postMessage({
            type: 'OAUTH_ERROR',
            error: 'Callback processing failed'
          }, window.location.origin)
        }
      }
    }

    // Process the callback when component mounts
    handleOAuthCallback()
  }, [searchParams])

  return (
    <div className="min-h-screen bg-[#F8F5F1] flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full mx-4">
        <div className="text-center">
          <div className="flex items-center justify-center mb-6">
            <div className="w-12 h-12 bg-[#2A5D67] rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">P</span>
            </div>
          </div>
          
          <h1 className="text-2xl font-bold text-[#2A5D67] mb-4">
            {status === 'processing' && 'Elaborazione...'}
            {status === 'success' && 'Autenticazione Completata!'}
            {status === 'error' && 'Errore di Autenticazione'}
          </h1>
          
          <div className="flex items-center justify-center mb-6">
            {status === 'processing' && (
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#2A5D67]"></div>
            )}
            {status === 'success' && (
              <div className="text-green-500">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            )}
            {status === 'error' && (
              <div className="text-red-500">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
            )}
          </div>
          
          <p className="text-[#1E293B] text-center mb-4">
            {message}
          </p>
          
          {status === 'error' && (
            <button
              onClick={() => window.close()}
              className="bg-[#2A5D67] hover:bg-[#1E293B] text-white px-6 py-2 rounded-lg transition-colors"
            >
              Chiudi Finestra
            </button>
          )}
          
          {status === 'success' && (
            <div className="text-sm text-[#C4BDB4]">
              Questa finestra si chiuderà automaticamente...
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function LoadingFallback() {
  return (
    <div className="min-h-screen bg-[#F8F5F1] flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full mx-4">
        <div className="text-center">
          <div className="flex items-center justify-center mb-6">
            <div className="w-12 h-12 bg-[#2A5D67] rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">P</span>
            </div>
          </div>
          
          <h1 className="text-2xl font-bold text-[#2A5D67] mb-4">
            Caricamento...
          </h1>
          
          <div className="flex items-center justify-center mb-6">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#2A5D67]"></div>
          </div>
          
          <p className="text-[#1E293B] text-center">
            Inizializzazione autenticazione...
          </p>
        </div>
      </div>
    </div>
  )
}

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <OAuthCallbackContent />
    </Suspense>
  )
}