'use client'

import React, { useEffect } from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Brain, Shield, Eye, Lock, FileText, Clock, Mail } from 'lucide-react'
import Link from 'next/link'

export default function PrivacyPolicyPage() {
  // Ensure page starts at top
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [])

  const sections = [
    {
      id: 'introduzione',
      title: 'Introduzione',
      icon: Shield,
      content: `PratikoAI S.r.l. ("noi", "nostro" o "PratikoAI") si impegna a proteggere la privacy e la sicurezza dei dati personali degli utenti. Questa Privacy Policy descrive come raccogliamo, utilizziamo, conserviamo e proteggiamo le informazioni personali quando utilizzi i nostri servizi di assistente AI per professionisti legali.`
    },
    {
      id: 'raccolta',
      title: 'Raccolta dei Dati',
      icon: Eye,
      content: `Raccogliamo i seguenti tipi di dati personali:

**Dati di Registrazione:**
- Nome e cognome
- Indirizzo email professionale
- Informazioni di contatto
- Dati di fatturazione

**Dati di Utilizzo:**
- Query di ricerca normativa
- Cronologia delle conversazioni con l'AI
- Preferenze e impostazioni utente
- Dati di accesso e utilizzo del servizio

**Dati Tecnici:**
- Indirizzo IP
- Informazioni sul dispositivo e browser
- Cookie e tecnologie simili
- Log di sistema per sicurezza e manutenzione`
    },
    {
      id: 'utilizzo',
      title: 'Utilizzo dei Dati',
      icon: FileText,
      content: `Utilizziamo i tuoi dati personali per:

**Fornitura del Servizio:**
- Erogare servizi di assistente AI specializzato
- Fornire aggiornamenti normativi personalizzati
- Mantenere e migliorare le funzionalità

**Comunicazioni:**
- Inviare aggiornamenti importanti sul servizio
- Fornire supporto tecnico
- Comunicare modifiche normative rilevanti

**Sicurezza e Compliance:**
- Prevenire frodi e abusi
- Garantire la sicurezza dei dati
- Rispettare obblighi legali e normativi

**Miglioramento del Servizio:**
- Analizzare l'utilizzo per miglioramenti
- Sviluppare nuove funzionalità
- Personalizzare l'esperienza utente`
    },
    {
      id: 'conservazione',
      title: 'Conservazione dei Dati',
      icon: Clock,
      content: `Conserviamo i tuoi dati personali per il tempo necessario a:
- Fornire i servizi richiesti
- Rispettare obblighi legali (es. conservazione fiscale)
- Gestire contenziosi o reclami
- Mantenere la sicurezza del sistema

**Periodi di Conservazione:**
- Dati di account: per la durata del rapporto contrattuale + 10 anni
- Cronologia conversazioni: 24 mesi dall'ultimo accesso
- Dati di fatturazione: 10 anni come richiesto dalla legge italiana
- Log di sistema: 12 mesi per sicurezza`
    },
    {
      id: 'sicurezza',
      title: 'Sicurezza dei Dati',
      icon: Lock,
      content: `Implementiamo misure tecniche e organizzative avanzate:

**Misure Tecniche:**
- Crittografia end-to-end per dati sensibili
- Autenticazione a due fattori
- Backup sicuri e ridondanti
- Monitoraggio continuo della sicurezza

**Misure Organizzative:**
- Formazione del personale sulla privacy
- Controlli di accesso rigorosi
- Procedure di incident response
- Audit regolari della sicurezza

**Certificazioni:**
- Conformità GDPR completa
- Standard di sicurezza ISO 27001
- Hosting in data center certificati in Italia`
    },
    {
      id: 'diritti',
      title: 'Diritti degli Utenti',
      icon: Shield,
      content: `Ai sensi del GDPR, hai i seguenti diritti:

**Diritto di Accesso:** Ottenere informazioni sui tuoi dati personali

**Diritto di Rettifica:** Correggere dati inesatti o incompleti

**Diritto alla Cancellazione:** Richiedere la cancellazione dei tuoi dati ("diritto all'oblio")

**Diritto di Limitazione:** Limitare il trattamento in specifiche circostanze

**Diritto alla Portabilità:** Ricevere i tuoi dati in formato strutturato

**Diritto di Opposizione:** Opporti al trattamento per motivi legittimi

**Diritto di Reclamo:** Presentare reclamo all'Autorità Garante`
    }
  ]

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
            className="w-16 h-16 bg-[#2A5D67] rounded-full flex items-center justify-center mx-auto mb-6"
          >
            <Shield className="w-8 h-8 text-white" />
          </motion.div>
          
          <motion.h1
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-4xl font-bold text-[#2A5D67] mb-4"
          >
            Privacy Policy
          </motion.h1>
          
          <motion.p
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-xl text-[#1E293B] max-w-2xl mx-auto mb-6"
          >
            Come PratikoAI protegge e gestisce i tuoi dati personali
          </motion.p>

          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-sm text-[#C4BDB4] space-y-1"
          >
            <p><strong>Ultimo aggiornamento:</strong> 12 agosto 2025</p>
            <p><strong>Versione:</strong> 2.1</p>
          </motion.div>
        </div>

        {/* Content Sections */}
        <div className="space-y-8">
          {sections.map((section, index) => (
            <motion.div
              key={section.id}
              initial={{ y: 30, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.5 + index * 0.1 }}
            >
              <div className="bg-white border border-[#C4BDB4]/20 rounded-xl p-8 shadow-sm">
                <div className="flex items-center space-x-3 text-[#2A5D67] mb-6">
                  <div className="w-10 h-10 bg-[#F8F5F1] rounded-lg flex items-center justify-center">
                    <section.icon className="w-5 h-5 text-[#2A5D67]" />
                  </div>
                  <h2 className="text-2xl font-bold">{section.title}</h2>
                </div>
                <div className="whitespace-pre-line text-[#1E293B] leading-relaxed">
                  {section.content}
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="border-t border-[#C4BDB4]/20 my-12"></div>

        {/* Contact Section */}
        <motion.div
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 1.2 }}
          className="bg-[#F8F5F1] rounded-xl p-8 text-center"
        >
          <div className="w-12 h-12 bg-[#2A5D67] rounded-full flex items-center justify-center mx-auto mb-4">
            <Mail className="w-6 h-6 text-white" />
          </div>
          
          <h3 className="text-2xl font-bold text-[#2A5D67] mb-4">
            Hai Domande sulla Privacy?
          </h3>
          
          <p className="text-[#1E293B] mb-6 max-w-2xl mx-auto">
            Per qualsiasi domanda riguardante questa Privacy Policy o il trattamento dei tuoi dati personali, 
            contatta il nostro Data Protection Officer.
          </p>

          <div className="space-y-2 text-[#2A5D67]">
            <p><strong>Email:</strong> privacy@pratikoai.it</p>
            <p><strong>Indirizzo:</strong> Via Roma 123, 96017 Pachino (SR), Italia</p>
            <p><strong>PEC:</strong> pratikoai@pec.it</p>
          </div>

          <div className="mt-8 p-4 bg-white rounded-lg border border-[#C4BDB4]/20">
            <p className="text-sm text-[#1E293B]">
              <strong>Data Protection Officer:</strong><br />
              Dott.ssa Maria Rossi - dpo@pratikoai.it
            </p>
          </div>
        </motion.div>

        {/* Legal Footer */}
        <motion.div
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 1.4 }}
          className="mt-12 text-center text-sm text-[#C4BDB4]"
        >
          <p>
            © 2025 PratikoAI S.r.l. - P.IVA: 12345678901<br />
            Tutti i diritti riservati. Documento conforme al GDPR (Regolamento UE 2016/679)
          </p>
        </motion.div>
      </motion.div>
    </div>
  )
}