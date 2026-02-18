'use client'

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Button } from '../../components/ui/button'
import { ArrowLeft, Mail, Lock, Eye, EyeOff, Clock, Shield, Zap, Brain, MessageSquare, Search, FileCheck } from 'lucide-react'
import Link from 'next/link'
import { GoogleAccountSelector } from '../../components/GoogleAccountSelector'
import { LinkedInAccountSelector } from '../../components/LinkedInAccountSelector'
import { apiClient } from '../../lib/api'

export default function SignInPage() {
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [showGoogleSelector, setShowGoogleSelector] = useState(false)
  const [showLinkedInSelector, setShowLinkedInSelector] = useState(false)
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false
  })

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
  }

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    
    try {
      // Call real backend API
      const result = await apiClient.login(formData.email, formData.password)
      
      console.log('Sign in successful:', result)
      
      // Redirect to chat page silently
      window.location.href = '/chat'
      
    } catch (error) {
      console.error('Sign in error:', error)
      alert(`Errore durante l'accesso: ${error instanceof Error ? error.message : 'Errore sconosciuto'}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleGoogleAccountSelect = async (account: { id: string; name: string; email: string; avatar: string }) => {
    console.log('Selected Google account:', account)
    setIsLoading(true)
    
    try {
      // Use the real Google OAuth API endpoint
      const result = await apiClient.loginWithGoogle()
      console.log('Google OAuth login successful:', result)
      
      // Redirect to chat page silently
      window.location.href = '/chat'
      
    } catch (error) {
      console.error('Google sign in error:', error)
      alert(`Errore durante l'accesso con Google: ${error instanceof Error ? error.message : 'Errore sconosciuto'}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleLinkedInAccountSelect = async (account: { id: string; name: string; email: string; title: string; company: string; avatar: string; connections: number }) => {
    console.log('Selected LinkedIn account:', account)
    setIsLoading(true)
    
    try {
      // Use the real LinkedIn OAuth API endpoint
      const result = await apiClient.loginWithLinkedIn()
      console.log('LinkedIn OAuth login successful:', result)
      
      // Redirect to chat page silently
      window.location.href = '/chat'
      
    } catch (error) {
      console.error('LinkedIn sign in error:', error)
      alert(`Errore durante l'accesso con LinkedIn: ${error instanceof Error ? error.message : 'Errore sconosciuto'}`)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="relative bg-white border-b border-[#C4BDB4]/20 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <Button
              onClick={() => window.location.href = '/'}
              variant="ghost"
              className="flex items-center space-x-2 text-[#2A5D67] hover:bg-[#F8F5F1] transition-all duration-200"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Torna alla Home</span>
            </Button>
            
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center space-x-2"
            >
              <div className="w-8 h-8 bg-[#2A5D67] rounded-lg flex items-center justify-center">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-[#2A5D67]">PratikoAI</span>
            </motion.div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid lg:grid-cols-2 gap-12 items-start">
          {/* Left Column - Value Proposition */}
          <div className="lg:pr-8">
            <div>
              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="text-4xl lg:text-5xl font-bold text-[#2A5D67] mb-4"
              >
                Bentornato su PratikoAI
              </motion.h1>
              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="text-xl text-[#1E293B] leading-relaxed mb-8"
              >
                Accedi al tuo account per continuare a lavorare con il nostro assistente AI.
              </motion.p>
            </div>

            {/* Key Benefits */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8"
            >
              {[
                {
                  icon: Clock,
                  title: 'Risparmia 10+ ore a settimana',
                  description: 'Automatizza la ricerca normativa e l\'analisi documenti'
                },
                {
                  icon: Shield,
                  title: 'Sempre aggiornato e compliant',
                  description: 'Monitoraggio in tempo reale di Agenzia Entrate, INPS, MEF e molte altre fonti'
                }
              ].map((benefit, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 + index * 0.1 }}
                  className="flex items-start space-x-3 p-4 rounded-lg bg-[#F8F5F1] border border-[#C4BDB4]/20"
                >
                  <div className="flex-shrink-0 w-10 h-10 bg-[#2A5D67] rounded-lg flex items-center justify-center">
                    <benefit.icon className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-[#2A5D67] mb-1">
                      {benefit.title}
                    </h4>
                    <p className="text-[#1E293B] text-base">
                      {benefit.description}
                    </p>
                  </div>
                </motion.div>
              ))}
            </motion.div>

            {/* Types of Questions */}
            <div className="mb-8">
              <motion.h3
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 }}
                className="text-2xl font-semibold text-[#2A5D67] mb-6"
              >
                Che tipo di domande puoi fare?
              </motion.h3>
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8 }}
                className="grid grid-cols-1 sm:grid-cols-2 gap-4"
              >
                {[
                  {
                    icon: MessageSquare,
                    title: 'Domanda Semplice',
                    description: 'Perfetto per quesiti diretti e chiarimenti normativi'
                  },
                  {
                    icon: Brain,
                    title: 'Domanda Complessa',
                    description: 'Analisi dettagliata con casistica, precedenti e strategie'
                  },
                  {
                    icon: Search,
                    title: 'Domanda Interattiva',
                    description: 'PratikoAI ti farà domande specifiche per individuare la soluzione ottimale',
                    isNew: true
                  },
                  {
                    icon: FileCheck,
                    title: 'Analisi Documento',
                    description: 'Riconoscimento automatico, estrazione dati e controllo conformità'
                  }
                ].map((questionType, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.9 + index * 0.1 }}
                    className="flex items-start space-x-3 p-4 rounded-lg bg-[#F8F5F1] border border-[#C4BDB4]/20 hover:border-[#2A5D67]/30 transition-all duration-200"
                  >
                    <div className="flex-shrink-0 w-10 h-10 bg-[#2A5D67] rounded-lg flex items-center justify-center">
                      <questionType.icon className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-[#2A5D67] mb-1">
                        {questionType.title}
                        {questionType.isNew && (
                          <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[#D4A574] text-white">
                            Nuovo
                          </span>
                        )}
                      </h4>
                      <p className="text-[#1E293B] text-sm leading-relaxed">
                        {questionType.description}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            </div>
          </div>

          {/* Right Column - Sign In Form */}
          <div className="lg:pl-8">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="bg-white border border-[#C4BDB4]/20 rounded-xl p-8 shadow-2xl sticky top-8"
            >
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-[#2A5D67] mb-2">
                  Accedi al tuo account
                </h2>
                <p className="text-[#1E293B] text-lg">
                  Entra e continua a lavorare con PratikoAI
                </p>
              </div>

              {/* Social Sign In Buttons */}
              <div className="space-y-3 mb-6">
                <Button
                  onClick={() => setShowGoogleSelector(true)}
                  variant="outline"
                  className="w-full py-3 border-[#C4BDB4] hover:bg-[#F8F5F1] transition-all duration-200 flex items-center justify-center space-x-3"
                >
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  <span className="text-[#1E293B] font-medium">Accedi con Google</span>
                </Button>
                
                <Button
                  onClick={() => setShowLinkedInSelector(true)}
                  variant="outline"
                  className="w-full py-3 border-[#C4BDB4] hover:bg-[#F8F5F1] transition-all duration-200 flex items-center justify-center space-x-3"
                >
                  <svg className="w-5 h-5" fill="#0A66C2" viewBox="0 0 24 24">
                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                  </svg>
                  <span className="text-[#1E293B] font-medium">Accedi con LinkedIn</span>
                </Button>
              </div>

              <div className="relative mb-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-[#C4BDB4]"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-white text-[#1E293B]">oppure</span>
                </div>
              </div>

              {/* Sign In Form */}
              <form onSubmit={handleSignIn} className="space-y-6">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-[#1E293B] mb-2">
                    Email
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[#C4BDB4] w-5 h-5" />
                    <input
                      type="email"
                      id="email"
                      name="email"
                      value={formData.email}
                      onChange={handleInputChange}
                      className="w-full pl-10 pr-4 py-3 border border-[#C4BDB4] rounded-lg focus:ring-2 focus:ring-[#2A5D67] focus:border-transparent transition-all duration-200 bg-white text-[#1E293B]"
                      placeholder="mario.rossi@studio.it"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-[#1E293B] mb-2">
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[#C4BDB4] w-5 h-5" />
                    <input
                      type={showPassword ? "text" : "password"}
                      id="password"
                      name="password"
                      value={formData.password}
                      onChange={handleInputChange}
                      className="w-full pl-10 pr-12 py-3 border border-[#C4BDB4] rounded-lg focus:ring-2 focus:ring-[#2A5D67] focus:border-transparent transition-all duration-200 bg-white text-[#1E293B]"
                      placeholder="••••••••"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-[#C4BDB4] hover:text-[#2A5D67] transition-colors duration-200"
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      name="rememberMe"
                      checked={formData.rememberMe}
                      onChange={handleInputChange}
                      className="w-4 h-4 text-[#2A5D67] focus:ring-[#2A5D67] border-[#C4BDB4] rounded"
                    />
                    <label className="text-[#1E293B] text-sm">
                      Ricordami
                    </label>
                  </div>
                  <button type="button" className="text-[#2A5D67] text-sm hover:underline">
                    Password dimenticata?
                  </button>
                </div>

                <Button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-[#2A5D67] hover:bg-[#1E293B] text-white py-3 text-lg font-semibold transition-all duration-200 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                >
                  {isLoading ? (
                    <div className="flex items-center justify-center space-x-2">
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                        className="w-4 h-4 border-2 border-white border-t-transparent rounded-full"
                      />
                      <span>Accesso in corso...</span>
                    </div>
                  ) : (
                    <strong>Accedi</strong>
                  )}
                </Button>
              </form>

              <div className="mt-6 text-center">
                <p className="text-[#1E293B]">
                  Non hai ancora un account?{' '}
                  <Link href="/signup" className="text-[#2A5D67] font-semibold hover:underline">
                    Registrati ora
                  </Link>
                </p>
              </div>

              {/* Trust Signals */}
              <div className="mt-8 pt-6 border-t border-[#C4BDB4]/20">
                <div className="flex items-center justify-center text-sm text-[#1E293B]">
                  <div className="flex items-center space-x-2">
                    <Shield className="w-4 h-4 text-[#2A5D67]" />
                    <span>Sicuro e protetto</span>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Google Account Selector Modal */}
      <GoogleAccountSelector
        isOpen={showGoogleSelector}
        onClose={() => setShowGoogleSelector(false)}
        onSelectAccount={handleGoogleAccountSelect}
      />

      {/* LinkedIn Account Selector Modal */}
      <LinkedInAccountSelector
        isOpen={showLinkedInSelector}
        onClose={() => setShowLinkedInSelector(false)}
        onSelectAccount={handleLinkedInAccountSelect}
      />
    </div>
  )
}