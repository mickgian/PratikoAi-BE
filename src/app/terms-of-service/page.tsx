'use client'

import React, { useEffect } from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Brain, FileText, Scale, AlertTriangle, Users, CreditCard, Gavel } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'

export default function TermsOfServicePage() {
  // Ensure page starts at top
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [])

  const sections = [
    {
      id: 'accettazione',
      title: 'Accettazione dei Termini',
      icon: FileText,
      priority: 'high',
      content: `Utilizzando PratikoAI, accetti integralmente questi Termini di Servizio. Se non accetti questi termini, non utilizzare il servizio.

**Capacità Legale:**
Dichiari di avere la capacità legale per stipulare questo accordo e di agire per conto di un'organizzazione autorizzata se applicabile.

**Aggiornamenti:**
Ci riserviamo il diritto di modificare questi termini. Gli utenti saranno notificati via email almeno 30 giorni prima dell'entrata in vigore delle modifiche.`
    },
    {
      id: 'servizio',
      title: 'Descrizione del Servizio',
      icon: Brain,
      priority: 'high',
      content: `PratikoAI è un assistente AI specializzato per professionisti legali italiani che fornisce:

**Servizi Principali:**
- Assistenza su normativa fiscale, del lavoro e societaria
- Aggiornamenti normativi in tempo reale
- Ricerca intelligente nella giurisprudenza italiana
- Generazione di documenti legali standard

**Limitazioni:**
- Il servizio NON fornisce consulenza legale personalizzata
- Le risposte sono di carattere informativo generale
- È necessaria sempre la valutazione professionale di un avvocato
- Non sostituisce la consulenza legale professionale`
    },
    {
      id: 'account',
      title: 'Registrazione e Account',
      icon: Users,
      priority: 'medium',
      content: `**Requisiti di Registrazione:**
- Informazioni accurate e complete
- Utilizzo professionale del servizio
- Un account per persona/organizzazione

**Responsabilità dell'Account:**
- Mantenere sicure le credenziali di accesso
- Notificare immediatamente accessi non autorizzati
- Rispondere delle attività svolte con il proprio account
- Aggiornare tempestivamente le informazioni di contatto

**Sospensione Account:**
Possiamo sospendere o terminare account per violazioni dei termini, attività fraudolente o utilizzo inappropriato del servizio.`
    },
    {
      id: 'utilizzo',
      title: 'Utilizzo Accettabile',
      icon: Scale,
      priority: 'high',
      content: `**Utilizzi Consentiti:**
- Ricerca di informazioni normative per scopi professionali
- Supporto nella preparazione di documenti legali
- Aggiornamento professionale continuo
- Formazione e studio del diritto italiano

**Utilizzi Vietati:**
- Attività illegali o fraudolente
- Violazione di diritti di proprietà intellettuale
- Diffusione di malware o contenuti dannosi
- Utilizzo per spam o comunicazioni massive non autorizzate
- Reverse engineering del sistema AI
- Condivisione delle credenziali di accesso

**Responsabilità Professionale:**
L'utente rimane pienamente responsabile delle decisioni professionali prese utilizzando le informazioni fornite dal servizio.`
    },
    {
      id: 'pagamenti',
      title: 'Pagamenti e Fatturazione',
      icon: CreditCard,
      priority: 'medium',
      content: `**Piani di Abbonamento:**
- Fatturazione mensile o annuale anticipata
- Prezzi espressi in Euro, IVA inclusa
- Rinnovo automatico salvo disdetta

**Modalità di Pagamento:**
- Carta di credito/debito
- Bonifico bancario (solo piani annuali)
- Fatturazione B2B disponibile

**Politica di Rimborso:**
- Rimborso proporzionale per i primi 30 giorni
- Nessun rimborso per violazioni dei termini
- Diritto di recesso per consumatori secondo normativa italiana

**Modifiche Tariffarie:**
Preavviso di almeno 60 giorni per aumenti tariffari. Gli utenti possono disdire prima dell'applicazione delle nuove tariffe.`
    },
    {
      id: 'proprieta',
      title: 'Proprietà Intellettuale',
      icon: Gavel,
      priority: 'medium',
      content: `**Diritti di PratikoAI:**
- Proprietà esclusiva del software e dell'AI
- Diritti sui database normativi elaborati
- Marchi registrati e brand identity
- Metodologie e algoritmi proprietari

**Diritti dell'Utente:**
- Proprietà dei contenuti caricati dall'utente
- Licenza d'uso del servizio secondo i termini
- Diritto di portabilità dei propri dati

**Licenze di Terzi:**
Il servizio utilizza database normativi ufficiali e fonti pubbliche, rispettando tutti i diritti di proprietà intellettuale applicabili.`
    },
    {
      id: 'limitazioni',
      title: 'Limitazioni di Responsabilità',
      icon: AlertTriangle,
      priority: 'high',
      content: `**Esclusioni di Garanzia:**
Il servizio è fornito "così com'è" senza garanzie esplicite o implicite riguardo a:
- Accuratezza completa delle informazioni
- Disponibilità continua del servizio
- Assenza di errori o interruzioni

**Limiti di Responsabilità:**
La responsabilità di PratikoAI è limitata al valore dell'abbonamento pagato nell'ultimo anno.

**Responsabilità dell'Utente:**
L'utente è pienamente responsabile per:
- Decisioni professionali basate sulle informazioni ricevute
- Verifica indipendente delle informazioni normative
- Rispetto degli obblighi deontologici professionali

**Forza Maggiore:**
Non siamo responsabili per ritardi o impossibilità di prestazione dovuti a cause di forza maggiore.`
    }
  ]

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'destructive'
      case 'medium': return 'default'
      default: return 'secondary'
    }
  }

  const getPriorityLabel = (priority: string) => {
    switch (priority) {
      case 'high': return 'Priorità Alta'
      case 'medium': return 'Priorità Media'
      default: return 'Priorità Bassa'
    }
  }

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
            <Scale className="w-8 h-8 text-white" />
          </motion.div>
          
          <motion.h1
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-4xl font-bold text-[#2A5D67] mb-4"
          >
            Termini di Servizio
          </motion.h1>
          
          <motion.p
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-xl text-[#1E293B] max-w-2xl mx-auto mb-6"
          >
            Condizioni generali per l&apos;utilizzo di PratikoAI
          </motion.p>

          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-sm text-[#C4BDB4] space-y-1"
          >
            <p><strong>Ultimo aggiornamento:</strong> 12 agosto 2025</p>
            <p><strong>Versione:</strong> 3.2</p>
            <p><strong>Giurisdizione:</strong> Repubblica Italiana</p>
          </motion.div>
        </div>

        {/* Important Notice */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="bg-[#FEF3C7] border border-[#F59E0B] rounded-lg p-4 mb-8"
        >
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-[#F59E0B] flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-[#92400E] mb-1">Importante</h3>
              <p className="text-sm text-[#92400E]">
                PratikoAI fornisce supporto informativo ma non consulenza legale. 
                È sempre necessaria la validazione di un professionista qualificato per decisioni legali.
              </p>
            </div>
          </div>
        </motion.div>

        {/* Content Sections */}
        <div className="space-y-8">
          {sections.map((section, index) => (
            <motion.div
              key={section.id}
              initial={{ y: 30, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.6 + index * 0.1 }}
            >
              <div className="bg-white border border-[#C4BDB4]/20 rounded-xl p-8 shadow-sm">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-3 text-[#2A5D67]">
                    <div className="w-10 h-10 bg-[#F8F5F1] rounded-lg flex items-center justify-center">
                      <section.icon className="w-5 h-5 text-[#2A5D67]" />
                    </div>
                    <h2 className="text-2xl font-bold">{section.title}</h2>
                  </div>
                  <Badge variant={getPriorityColor(section.priority)} className="text-xs">
                    {getPriorityLabel(section.priority)}
                  </Badge>
                </div>
                <div className="whitespace-pre-line text-[#1E293B] leading-relaxed">
                  {section.content}
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="border-t border-[#C4BDB4]/20 my-12"></div>

        {/* Contact and Legal */}
        <motion.div
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 1.3 }}
          className="grid md:grid-cols-2 gap-6"
        >
          {/* Contact */}
          <div className="bg-[#F8F5F1] rounded-xl p-6">
            <h3 className="text-xl font-bold text-[#2A5D67] mb-4">
              Contatti Legali
            </h3>
            <div className="space-y-2 text-[#1E293B]">
              <p><strong>PratikoAI S.r.l.</strong></p>
              <p>Via Roma 123, 96017 Pachino (SR)</p>
              <p>P.IVA: 12345678901</p>
              <p>Email: legal@pratikoai.it</p>
              <p>PEC: pratikoai@pec.it</p>
            </div>
          </div>

          {/* Dispute Resolution */}
          <div className="bg-[#F8F5F1] rounded-xl p-6">
            <h3 className="text-xl font-bold text-[#2A5D67] mb-4">
              Risoluzione Controversie
            </h3>
            <div className="text-[#1E293B] space-y-2">
              <p><strong>Foro Competente:</strong> Tribunale di Siracusa</p>
              <p><strong>Legge Applicabile:</strong> Diritto Italiano</p>
              <p><strong>Mediazione:</strong> Tentativo obbligatorio presso Camera di Commercio</p>
              <p><strong>Consumatori:</strong> Diritti garantiti dal Codice del Consumo</p>
            </div>
          </div>
        </motion.div>

        {/* Legal Footer */}
        <motion.div
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 1.5 }}
          className="mt-12 text-center text-sm text-[#C4BDB4]"
        >
          <p>
            © 2025 PratikoAI S.r.l. - Tutti i diritti riservati<br />
            Documento redatto secondo la normativa italiana e comunitaria
          </p>
        </motion.div>
      </motion.div>
    </div>
  )
}