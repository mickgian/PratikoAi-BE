'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Brain, Cookie, Settings, Shield, BarChart3, Eye, Check } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import Link from 'next/link'

interface CookieCategory {
  id: string
  name: string
  icon: React.ComponentType<{ className?: string }>
  essential: boolean
  description: string
  enabled: boolean
  cookies: {
    name: string
    purpose: string
    duration: string
    provider: string
  }[]
}

export default function CookiePolicyPage() {
  // Ensure page starts at top
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [])

  const [cookiePreferences, setCookiePreferences] = useState({
    essential: true,
    functional: true,
    analytics: false,
    marketing: false
  })

  const updatePreference = (category: string, enabled: boolean) => {
    if (category === 'essential') return // Essential cookies cannot be disabled
    setCookiePreferences(prev => ({
      ...prev,
      [category]: enabled
    }))
  }

  const cookieCategories: CookieCategory[] = [
    {
      id: 'essential',
      name: 'Cookie Essenziali',
      icon: Shield,
      essential: true,
      description: 'Cookie necessari per il funzionamento basilare del sito web. Non possono essere disabilitati.',
      enabled: cookiePreferences.essential,
      cookies: [
        {
          name: 'pratikoai_session',
          purpose: 'Mantiene la sessione utente attiva',
          duration: '24 ore',
          provider: 'PratikoAI'
        },
        {
          name: 'auth_token',
          purpose: 'Gestisce l\'autenticazione sicura',
          duration: '30 giorni',
          provider: 'PratikoAI'
        },
        {
          name: 'csrf_token',
          purpose: 'Protezione da attacchi CSRF',
          duration: 'Sessione',
          provider: 'PratikoAI'
        }
      ]
    },
    {
      id: 'functional',
      name: 'Cookie Funzionali',
      icon: Settings,
      essential: false,
      description: 'Cookie che migliorano la funzionalità e personalizzazione del sito.',
      enabled: cookiePreferences.functional,
      cookies: [
        {
          name: 'user_preferences',
          purpose: 'Salva le preferenze utente (tema, lingua, layout)',
          duration: '1 anno',
          provider: 'PratikoAI'
        },
        {
          name: 'search_history',
          purpose: 'Memorizza la cronologia ricerche recenti',
          duration: '90 giorni',
          provider: 'PratikoAI'
        },
        {
          name: 'dashboard_layout',
          purpose: 'Ricorda la personalizzazione della dashboard',
          duration: '6 mesi',
          provider: 'PratikoAI'
        }
      ]
    },
    {
      id: 'analytics',
      name: 'Cookie Analytics',
      icon: BarChart3,
      essential: false,
      description: 'Cookie che ci aiutano a comprendere come gli utenti interagiscono con il sito.',
      enabled: cookiePreferences.analytics,
      cookies: [
        {
          name: '_ga',
          purpose: 'Identifica utenti unici per Google Analytics',
          duration: '2 anni',
          provider: 'Google Analytics'
        },
        {
          name: '_ga_*',
          purpose: 'Mantiene lo stato della sessione per Google Analytics',
          duration: '2 anni',
          provider: 'Google Analytics'
        },
        {
          name: 'hotjar_session',
          purpose: 'Tracciamento comportamento utente (anonimizzato)',
          duration: '30 minuti',
          provider: 'Hotjar'
        }
      ]
    },
    {
      id: 'marketing',
      name: 'Cookie Marketing',
      icon: Eye,
      essential: false,
      description: 'Cookie utilizzati per tracciare i visitatori attraverso i siti web.',
      enabled: cookiePreferences.marketing,
      cookies: [
        {
          name: 'facebook_pixel',
          purpose: 'Tracciamento conversioni per Facebook Ads',
          duration: '90 giorni',
          provider: 'Facebook'
        },
        {
          name: 'linkedin_insight',
          purpose: 'Tracciamento performance campagne LinkedIn',
          duration: '180 giorni',
          provider: 'LinkedIn'
        }
      ]
    }
  ]

  const generalInfo = `I cookie sono piccoli file di testo che i siti web possono utilizzare per rendere più efficiente l'esperienza per l'utente.

La legge afferma che possiamo memorizzare i cookie sul tuo dispositivo se sono strettamente necessari per il funzionamento di questo sito. Per tutti gli altri tipi di cookie ci serve il tuo permesso.

Questo sito utilizza diversi tipi di cookie. Alcuni cookie sono posti da servizi di terzi che compaiono sulle nostre pagine.

Puoi in qualsiasi momento modificare o revocare il tuo consenso dalla Dichiarazione dei cookie sul nostro sito web.`

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="bg-white border-b border-[#C4BDB4]/20 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Link href="/">
              <Button
                variant="ghost"
                className="flex items-center space-x-2 text-[#2A5D67] hover:bg-[#F8F5F1] transition-all duration-200"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Torna alla Home</span>
              </Button>
            </Link>
            
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

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12"
      >
        {/* Page Header */}
        <div className="text-center mb-12">
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="w-16 h-16 bg-[#D4A574] rounded-full flex items-center justify-center mx-auto mb-6"
          >
            <Cookie className="w-8 h-8 text-white" />
          </motion.div>
          
          <motion.h1
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-4xl font-bold text-[#2A5D67] mb-4"
          >
            Cookie Policy
          </motion.h1>
          
          <motion.p
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-xl text-[#1E293B] max-w-2xl mx-auto mb-6"
          >
            Come utilizziamo i cookie per migliorare la tua esperienza
          </motion.p>

          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-sm text-[#C4BDB4] space-y-1"
          >
            <p><strong>Ultimo aggiornamento:</strong> 12 agosto 2025</p>
            <p><strong>Versione:</strong> 1.3</p>
          </motion.div>
        </div>

        {/* General Information */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="bg-[#F8F5F1] rounded-xl p-8 mb-8"
        >
          <h2 className="text-2xl font-bold text-[#2A5D67] mb-4">
            Cosa sono i Cookie?
          </h2>
          <div className="whitespace-pre-line text-[#1E293B] leading-relaxed">
            {generalInfo}
          </div>
        </motion.div>

        {/* Cookie Categories */}
        <div className="space-y-6">
          <motion.h2
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="text-2xl font-bold text-[#2A5D67] mb-6"
          >
            Gestisci le tue Preferenze Cookie
          </motion.h2>

          {cookieCategories.map((category, index) => (
            <motion.div
              key={category.id}
              initial={{ y: 30, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.7 + index * 0.1 }}
            >
              <div className="bg-white border border-[#C4BDB4]/20 rounded-xl shadow-sm">
                <div className="p-6 border-b border-[#C4BDB4]/20">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3 text-[#2A5D67]">
                      <div className="w-10 h-10 bg-[#F8F5F1] rounded-lg flex items-center justify-center">
                        <category.icon className="w-5 h-5 text-[#2A5D67]" />
                      </div>
                      <h3 className="text-xl font-bold">{category.name}</h3>
                      {category.essential && (
                        <Badge variant="secondary" className="ml-2">
                          Sempre Attivi
                        </Badge>
                      )}
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      {category.essential ? (
                        <Check className="w-5 h-5 text-green-600" />
                      ) : (
                        <Switch
                          checked={category.enabled}
                          onCheckedChange={(enabled) => updatePreference(category.id, enabled)}
                        />
                      )}
                    </div>
                  </div>
                  
                  <p className="text-[#1E293B] mt-3">
                    {category.description}
                  </p>
                </div>

                <div className="p-6">
                  <div className="space-y-4">
                    {category.cookies.map((cookie, cookieIndex) => (
                      <div
                        key={cookieIndex}
                        className="border border-[#C4BDB4]/20 rounded-lg p-4 bg-[#F8F5F1]"
                      >
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <p className="font-semibold text-[#2A5D67] mb-1">
                              {cookie.name}
                            </p>
                            <p className="text-sm text-[#1E293B]">
                              {cookie.purpose}
                            </p>
                          </div>
                          <div className="text-sm text-[#1E293B] space-y-1">
                            <p><strong>Durata:</strong> {cookie.duration}</p>
                            <p><strong>Provider:</strong> {cookie.provider}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="border-t border-[#C4BDB4]/20 my-12"></div>

        {/* Cookie Management */}
        <motion.div
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 1.2 }}
          className="bg-[#F8F5F1] rounded-xl p-8"
        >
          <h3 className="text-2xl font-bold text-[#2A5D67] mb-6">
            Gestione Cookie del Browser
          </h3>
          
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-semibold text-[#2A5D67] mb-3">
                Come disabilitare i cookie
              </h4>
              <ul className="text-[#1E293B] space-y-2 text-sm">
                <li>• <strong>Chrome:</strong> Settings &gt; Privacy &gt; Cookies</li>
                <li>• <strong>Firefox:</strong> Options &gt; Privacy &gt; Cookies</li>
                <li>• <strong>Safari:</strong> Preferences &gt; Privacy &gt; Cookies</li>
                <li>• <strong>Edge:</strong> Settings &gt; Privacy &gt; Cookies</li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold text-[#2A5D67] mb-3">
                Strumenti di Opt-out
              </h4>
              <div className="text-[#1E293B] space-y-2 text-sm">
                <p>• <a href="https://tools.google.com/dlpage/gaoptout" className="text-[#2A5D67] underline">Google Analytics Opt-out</a></p>
                <p>• <a href="https://www.facebook.com/privacy/explanation" className="text-[#2A5D67] underline">Facebook Pixel Settings</a></p>
                <p>• <a href="https://www.linkedin.com/psettings/guest-controls" className="text-[#2A5D67] underline">LinkedIn Controls</a></p>
                <p>• <a href="https://www.hotjar.com/privacy/do-not-track/" className="text-[#2A5D67] underline">Hotjar Opt-out</a></p>
              </div>
            </div>
          </div>

          <div className="mt-6 p-4 bg-white rounded-lg border border-[#C4BDB4]/20">
            <p className="text-sm text-[#1E293B]">
              <strong>Nota:</strong> Disabilitando alcuni cookie, alcune funzionalità del sito potrebbero non funzionare correttamente.
            </p>
          </div>
        </motion.div>

        {/* Save Preferences */}
        <motion.div
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 1.4 }}
          className="mt-8 text-center"
        >
          <Button
            className="bg-[#2A5D67] hover:bg-[#1E293B] text-white px-8 py-3"
            onClick={() => {
              // In a real implementation, this would save preferences
              alert('Preferenze cookie salvate!')
            }}
          >
            <strong>Salva Preferenze Cookie</strong>
          </Button>
          
          <p className="text-sm text-[#C4BDB4] mt-4">
            Le tue preferenze saranno memorizzate per 1 anno o fino alla prossima modifica
          </p>
        </motion.div>

        {/* Legal Footer */}
        <motion.div
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 1.6 }}
          className="mt-12 text-center text-sm text-[#C4BDB4]"
        >
          <p>
            © 2025 PratikoAI S.r.l. - P.IVA: 12345678901<br />
            Cookie Policy conforme al GDPR e alla normativa italiana sui cookie
          </p>
        </motion.div>
      </motion.div>
    </div>
  )
}