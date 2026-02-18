'use client'

import React, { useState } from 'react'
import { motion } from 'motion/react'
import { Button } from '../../components/ui/button'
import { ArrowLeft, Mail, Lock, Eye, EyeOff, Shield, Users, CheckCircle } from 'lucide-react'
import Link from 'next/link'
import { GoogleAccountSelector } from '../../components/GoogleAccountSelector'
import { LinkedInAccountSelector } from '../../components/LinkedInAccountSelector'
import { PasswordStrengthIndicator } from '../../components/PasswordStrengthIndicator'
import { apiClient } from '../../lib/api'
import { validatePassword, validateEmail } from '../../lib/validation'

export default function SignUpPage() {
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [showGoogleSelector, setShowGoogleSelector] = useState(false)
  const [showLinkedInSelector, setShowLinkedInSelector] = useState(false)
  const [validationErrors, setValidationErrors] = useState<{[key: string]: string}>({})
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    acceptTerms: false,
    acceptMarketing: false
  })

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
  }

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Clear previous validation errors
    setValidationErrors({})
    
    // Client-side validation
    const emailValidation = validateEmail(formData.email)
    if (!emailValidation.isValid) {
      setValidationErrors({ email: emailValidation.error || 'Email non valida' })
      return
    }
    
    const passwordValidation = validatePassword(formData.password)
    if (!passwordValidation.isValid) {
      setValidationErrors({ password: passwordValidation.errors[0] })
      return
    }
    
    if (formData.password !== formData.confirmPassword) {
      setValidationErrors({ confirmPassword: 'Le password non corrispondono' })
      return
    }
    
    if (!formData.acceptTerms) {
      setValidationErrors({ terms: 'Devi accettare i termini di servizio' })
      return
    }
    
    setIsLoading(true)
    
    try {
      // Call real backend API
      const result = await apiClient.register({
        email: formData.email,
        password: formData.password
      })
      
      console.log('Registration successful:', result)
      
      // Redirect to chat page silently since user is now logged in
      window.location.href = '/chat'
      
    } catch (error) {
      console.error('Registration error:', error)
      setValidationErrors({ 
        general: error instanceof Error ? error.message : 'Errore sconosciuto durante la registrazione' 
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleGoogleAccountSelect = async (account: { id: string; name: string; email: string; avatar: string }) => {
    console.log('Selected Google account for signup:', account)
    setIsLoading(true)
    
    try {
      // Use the real Google OAuth API endpoint
      const result = await apiClient.loginWithGoogle()
      console.log('Google OAuth registration/login successful:', result)
      
      // Redirect to chat page silently since user is now logged in
      window.location.href = '/chat'
      
    } catch (error) {
      console.error('Google OAuth error:', error)
      setValidationErrors({ 
        general: error instanceof Error ? error.message : 'Errore durante l\'autenticazione con Google' 
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleLinkedInAccountSelect = async (account: { id: string; name: string; email: string; title: string; company: string; avatar: string; connections: number }) => {
    console.log('Selected LinkedIn account for signup:', account)
    setIsLoading(true)
    
    try {
      // Use the real LinkedIn OAuth API endpoint
      const result = await apiClient.loginWithLinkedIn()
      console.log('LinkedIn OAuth registration/login successful:', result)
      
      // Redirect to chat page silently since user is now logged in
      window.location.href = '/chat'
      
    } catch (error) {
      console.error('LinkedIn OAuth error:', error)
      setValidationErrors({ 
        general: error instanceof Error ? error.message : 'Errore durante l\'autenticazione con LinkedIn' 
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Button
              onClick={() => window.location.href = '/'}
              variant="ghost"
              className="flex items-center space-x-2 text-[#2A5D67] hover:bg-[#F8F5F1] transition-all duration-200"
            >
              <ArrowLeft className="w-5 h-5" />
              <span className="font-medium">Torna alla Home</span>
            </Button>
            
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-[#2A5D67] rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">P</span>
              </div>
              <span className="text-[#2A5D67] text-xl font-bold">PratikoAI</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
          
          {/* Left Side - Benefits & Content */}
          <div className="lg:sticky lg:top-8">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6 }}
              className="space-y-8"
            >
              {/* Main Value Proposition */}
              <div>
                <motion.h1
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="text-4xl lg:text-5xl font-bold text-[#2A5D67] mb-4"
                >
                  Inizia a risparmiare tempo oggi stesso con PratikoAI
                </motion.h1>
                <motion.p
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="text-xl text-[#1E293B] leading-relaxed"
                >
                  Unisciti a centinaia di professionisti che hanno già trasformato 
                  il loro modo di lavorare con il nostro assistente AI.
                </motion.p>
              </div>

              {/* Key Benefits */}
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="space-y-6"
              >
                <h3 className="text-2xl font-bold text-[#2A5D67]">
                  Perché scegliere PratikoAI?
                </h3>
                
                <div className="space-y-4">
                  {[
                    {
                      icon: (
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      ),
                      title: 'Risparmia 10+ ore a settimana',
                      description: 'Automatizza la ricerca normativa e l\'analisi documenti'
                    },
                    {
                      icon: <Shield className="w-6 h-6 text-white" />,
                      title: 'Sempre aggiornato e compliant',
                      description: 'Monitoraggio in tempo reale di Agenzia Entrate, INPS, MEF e molte altre fonti'
                    },
                    {
                      icon: (
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                      ),
                      title: 'Setup istantaneo',
                      description: 'Nessuna configurazione complicata, inizia subito'
                    },
                    {
                      icon: <Users className="w-6 h-6 text-white" />,
                      title: 'Supporto dedicato',
                      description: 'Team di esperti pronti ad aiutarti quando serve'
                    }
                  ].map((benefit, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.5 + index * 0.1 }}
                      className="flex items-start space-x-4"
                    >
                      <div className="flex-shrink-0 w-12 h-12 bg-[#2A5D67] rounded-lg flex items-center justify-center">
                        {benefit.icon}
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
                </div>
              </motion.div>

              {/* Social Proof */}
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.9 }}
                className="bg-white rounded-xl p-6 shadow-lg border border-[#C4BDB4]/20"
              >
                <div className="flex items-center space-x-2 mb-4">
                  <div className="flex text-yellow-400">
                    {[...Array(5)].map((_, i) => (
                      <svg key={i} className="w-5 h-5 fill-current" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                    ))}
                  </div>
                  <span className="text-[#2A5D67] font-semibold">4.9/5</span>
                </div>
                <blockquote className="text-[#1E293B] italic mb-3">
                  &ldquo;PratikoAI ha rivoluzionato il mio studio. Quello che prima richiedeva ore 
                  di ricerca ora lo faccio in minuti. Incredibile!&rdquo;
                </blockquote>
                <cite className="text-[#2A5D67] font-medium text-sm">
                  — Dott.ssa Maria Rossi, Commercialista
                </cite>
              </motion.div>

              {/* Trust Signals */}
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.0 }}
                className="grid grid-cols-2 gap-4"
              >
                <div className="bg-white rounded-lg p-4 shadow-sm border border-[#C4BDB4]/20 text-center">
                  <div className="text-2xl font-bold text-[#2A5D67]">1000+</div>
                  <div className="text-sm text-[#1E293B]">Professionisti</div>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm border border-[#C4BDB4]/20 text-center">
                  <div className="text-2xl font-bold text-[#2A5D67]">50k+</div>
                  <div className="text-sm text-[#1E293B]">Documenti analizzati</div>
                </div>
              </motion.div>
            </motion.div>
          </div>

          {/* Right Side - Signup Form */}
          <div>
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="bg-white rounded-2xl shadow-xl p-8"
            >
              {/* Header */}
              <div className="text-center mb-8">
                <motion.h2
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.4 }}
                  className="text-2xl font-bold text-[#2A5D67] mb-2"
                >
                  Inizia in 30 secondi
                </motion.h2>
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.5 }}
                  className="text-[#1E293B]"
                >
                  7 giorni gratuiti, setup istantaneo
                </motion.p>
              </div>

              {/* Social Login Buttons */}
              <div className="space-y-3 mb-6">
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.6 }}
                >
                  <Button
                    type="button"
                    onClick={() => setShowGoogleSelector(true)}
                    className="w-full bg-white border-2 border-[#C4BDB4]/30 text-[#1E293B] hover:bg-gray-50 hover:border-[#D4A574] py-3 h-auto rounded-xl transition-all duration-300 group flex items-center justify-center space-x-3"
                  >
                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                    <span className="font-medium">Continua con Google</span>
                  </Button>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.7 }}
                >
                  <Button
                    type="button"
                    onClick={() => setShowLinkedInSelector(true)}
                    className="w-full bg-white border-2 border-[#C4BDB4]/30 text-[#1E293B] hover:bg-gray-50 hover:border-[#D4A574] py-3 h-auto rounded-xl transition-all duration-300 group flex items-center justify-center space-x-3"
                  >
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="#0A66C2">
                      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                    </svg>
                    <span className="font-medium">Continua con LinkedIn</span>
                  </Button>
                </motion.div>
              </div>

              {/* Divider */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
                className="relative my-6"
              >
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-[#C4BDB4]/30"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-[#C4BDB4]">oppure con email</span>
                </div>
              </motion.div>

              {/* Email/Password Form */}
              <form onSubmit={handleSignUp} className="space-y-5">
                {/* Email */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.9 }}
                >
                  <label className="block text-[#2A5D67] font-medium mb-2">
                    Email *
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-[#C4BDB4]" />
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleInputChange}
                      required
                      className={`w-full pl-10 pr-4 py-3 border rounded-lg focus:ring-2 focus:ring-[#2A5D67]/20 focus:border-[#2A5D67] transition-all ${
                        validationErrors.email ? 'border-red-400 bg-red-50' : 'border-[#C4BDB4]/30'
                      }`}
                      placeholder="tuo.nome@email.it"
                    />
                  </div>
                  {validationErrors.email && (
                    <p className="mt-1 text-sm text-red-600">{validationErrors.email}</p>
                  )}
                </motion.div>

                {/* Password */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.0 }}
                >
                  <label className="block text-[#2A5D67] font-medium mb-2">
                    Password *
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-[#C4BDB4]" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      name="password"
                      value={formData.password}
                      onChange={handleInputChange}
                      required
                      className={`w-full pl-10 pr-12 py-3 border rounded-lg focus:ring-2 focus:ring-[#2A5D67]/20 focus:border-[#2A5D67] transition-all ${
                        validationErrors.password ? 'border-red-400 bg-red-50' : 'border-[#C4BDB4]/30'
                      }`}
                      placeholder="Minimo 8 caratteri, maiuscola, minuscola, numero, carattere speciale"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-[#C4BDB4] hover:text-[#2A5D67] transition-colors"
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                  
                  {/* Password Strength Indicator */}
                  {formData.password && (
                    <PasswordStrengthIndicator password={formData.password} />
                  )}
                  
                  {validationErrors.password && (
                    <p className="mt-1 text-sm text-red-600">{validationErrors.password}</p>
                  )}
                </motion.div>

                {/* Confirm Password */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.1 }}
                >
                  <label className="block text-[#2A5D67] font-medium mb-2">
                    Conferma Password *
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-[#C4BDB4]" />
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      name="confirmPassword"
                      value={formData.confirmPassword}
                      onChange={handleInputChange}
                      required
                      className={`w-full pl-10 pr-12 py-3 border rounded-lg focus:ring-2 focus:ring-[#2A5D67]/20 focus:border-[#2A5D67] transition-all ${
                        validationErrors.confirmPassword ? 'border-red-400 bg-red-50' : 'border-[#C4BDB4]/30'
                      }`}
                      placeholder="Ripeti la password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-[#C4BDB4] hover:text-[#2A5D67] transition-colors"
                    >
                      {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                  {validationErrors.confirmPassword && (
                    <p className="mt-1 text-sm text-red-600">{validationErrors.confirmPassword}</p>
                  )}
                </motion.div>

                {/* Terms and Marketing */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.2 }}
                  className="space-y-4"
                >
                  <div className="flex items-start space-x-3">
                    <input
                      type="checkbox"
                      name="acceptTerms"
                      checked={formData.acceptTerms}
                      onChange={handleInputChange}
                      required
                      className="mt-1 w-4 h-4 text-[#2A5D67] focus:ring-[#2A5D67] border-[#C4BDB4] rounded"
                    />
                    <label className="text-[#1E293B] text-sm">
                      Accetto i <a href="/terms" className="text-[#2A5D67] hover:underline">Termini di Servizio</a> e 
                      la <a href="/privacy" className="text-[#2A5D67] hover:underline">Privacy Policy</a> *
                    </label>
                  </div>
                </motion.div>

                {/* General Error Message */}
                {validationErrors.general && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-red-50 border border-red-200 rounded-lg p-3"
                  >
                    <p className="text-sm text-red-600">{validationErrors.general}</p>
                  </motion.div>
                )}

                {validationErrors.terms && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-yellow-50 border border-yellow-200 rounded-lg p-3"
                  >
                    <p className="text-sm text-yellow-600">{validationErrors.terms}</p>
                  </motion.div>
                )}

                {/* Submit Button */}
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.3 }}
                  className="pt-4"
                >
                  <Button
                    type="submit"
                    disabled={isLoading}
                    className="w-full bg-[#2A5D67] hover:bg-[#1E293B] text-white py-4 h-auto rounded-xl shadow-xl hover:shadow-2xl transition-all duration-300 group relative overflow-hidden"
                  >
                    {isLoading ? (
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                        <span>Creazione account in corso...</span>
                      </div>
                    ) : (
                      <span className="flex items-center justify-center space-x-2 font-bold">
                        <CheckCircle className="w-5 h-5" />
                        <span>Inizia la Prova Gratuita di 7 Giorni</span>
                      </span>
                    )}
                  </Button>
                </motion.div>
              </form>

              {/* Sign-In Link */}
              <div className="mt-6 text-center">
                <p className="text-[#1E293B]">
                  Hai già un account?{' '}
                  <Link href="/signin" className="text-[#2A5D67] font-semibold hover:underline">
                    Accedi ora
                  </Link>
                </p>
              </div>

              {/* Security Badge */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.5 }}
                className="mt-6 text-center"
              >
                <div className="inline-flex items-center space-x-2 text-[#C4BDB4] text-sm">
                  <CheckCircle className="w-4 h-4" />
                  <span>Dati protetti con crittografia SSL</span>
                </div>
              </motion.div>

              {/* Quick Benefits */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.6 }}
                className="mt-4 bg-[#F8F5F1] rounded-lg p-4"
              >
                <div className="text-center space-y-2">
                  <p className="text-[#2A5D67] font-medium text-sm">
                    ✅ Attivazione immediata • ✅ Nessuna carta di credito • ✅ Cancellazione facile
                  </p>
                </div>
              </motion.div>
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