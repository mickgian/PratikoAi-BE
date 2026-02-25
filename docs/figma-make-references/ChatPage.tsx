import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { Button } from './ui/button'
import {
  Send,
  Circle,
  LogOut,
  Settings,
  User,
  BookOpen,
  MessageSquare,

  Menu,
  X,
  Brain,
  FileText,
  Clock,
  AlertCircle,
  Construction,
  ThumbsUp,
  ThumbsDown,
  AlertTriangle,
  Check,
  ChevronDown,
  Upload,
  FileCheck,
  Zap,
  HelpCircle,
  Paperclip,
  Search,
  Database,
  Mail,
  ListChecks,
  BarChart3,
  Target,
  Bell
} from 'lucide-react'
import { NotificationsDropdown } from './NotificationsDropdown'
import { ProcedureSelector, CommandPopover } from './ProcedureSelector'
import { ClientMentionAutocomplete, ClientMentionPill, ClientContextCard, type Client } from './ClientMentionAutocomplete'
import { ClientActionPicker, ClientProfileCard } from './ClientActionPicker'


interface Message {
  id: string
  type: 'user' | 'ai'
  content: string
  timestamp: string
  sources?: string[]
  feedback?: MessageFeedback
  isInteractiveQuestion?: boolean
  mentionedClients?: Client[]
}

interface MessageFeedback {
  type: 'correct' | 'incomplete' | 'wrong'
  category?: string
  details?: string
  timestamp: string
}

type FeedbackType = 'correct' | 'incomplete' | 'wrong'

type InputMode = 'simple' | 'complex' | 'interactive' | 'document'

interface InputModeConfig {
  id: InputMode
  label: string
  icon: React.ComponentType<{ className?: string }>
  placeholder: string
  description: string
}

interface ChatPageProps {
  onLogout: () => void
  onNavigateToModelli: () => void
  onNavigateToFonte: (sourceTitle: string) => void
  onNavigateToScadenze: () => void
  onNavigateToNormative: () => void
  onNavigateToAggiornamenti: () => void
  onNavigateToNormativeFAQ: () => void
  onNavigateToDomandePronte: () => void
  onNavigateToClients: () => void
  onNavigateToComunicazioni: () => void
  onNavigateToProcedure: () => void
  onNavigateToDashboard: () => void
  onNavigateToMatching: () => void
}

const quickActions = [
  { icon: FileText, label: "Modelli e Formulari", count: 245, action: 'modelli' },
  { icon: Clock, label: "Scadenze Fiscali", count: 12, action: 'scadenze' },
  { icon: AlertCircle, label: "Aggiornamenti Urgenti", count: 3, action: 'aggiornamenti' },
  { icon: BookOpen, label: "Normative Recenti", count: 28, action: 'normative' },
  { icon: MessageSquare, label: "Domande Pronte", count: 89, action: 'domande-pronte' },
  { icon: HelpCircle, label: "Domande Frequenti", count: 127, action: 'normative-faq' }
]

// Input modes configuration - Updated with Interactive mode
const inputModes: InputModeConfig[] = [
  {
    id: 'simple',
    label: 'Domanda Semplice',
    icon: MessageSquare,
    placeholder: 'Fai una domanda rapida sulla normativa italiana...',
    description: 'Perfetto per quesiti diretti e chiarimenti normativi'
  },
  {
    id: 'complex',
    label: 'Domanda Complessa',
    icon: Brain,
    placeholder: 'Descrivi il tuo caso complesso per analisi approfondita...',
    description: 'Analisi dettagliata con casistica, precedenti e strategie'
  },
  {
    id: 'interactive',
    label: 'Domanda Interattiva',
    icon: Search,
    placeholder: 'Inizia con il tuo quesito e lascia che ti guidi verso la soluzione...',
    description: 'PratikoAI ti farà domande specifiche per individuare la soluzione ottimale'
  },
  {
    id: 'document',
    label: 'Analisi Documento',
    icon: FileCheck,
    placeholder: 'Carica un documento per analisi automatica (PDF, DOC, IMG)...',
    description: 'Riconoscimento automatico, estrazione dati e controllo conformità'
  }
]

// Mock conversations for history sidebar - expanded with more examples
const mockConversations: Record<string, { id: string; title: string; preview: string; timestamp: string; type: 'simple' | 'complex' | 'interactive' | 'document'; messages: Message[] }> = {
  'analisi_fattura': {
    id: 'analisi_fattura',
    title: 'Analisi Documenti',
    preview: 'Analizza questa fattura elettronica per verificarne la conformità',
    timestamp: '2024-01-15T14:30:00',
    type: 'document',
    messages: [
      {
        id: 'user_1',
        type: 'user',
        content: 'Analizza questa fattura elettronica per verificarne la conformità\n\n📄 **Documento caricato**: Fattura_Elettronica_2024_001.xml\n**Modalità**: Analisi automatica documento',
        timestamp: '14:30',
      },
      {
        id: 'ai_1',
        type: 'ai',
        content: '📄 **Analisi Documento Completata** - Fattura_Elettronica_2024_001.xml\n\n**🔍 Riconoscimento Automatico:**\n• **Tipo documento**: Fattura Elettronica\n• **Data emissione**: 12 gennaio 2024\n• **Partita IVA**: Validata e attiva\n\n**DOCUMENT_ANALYSIS_UI**\n\n**💡 Suggerimenti:**\n• Considera l\'utilizzo del reverse charge per questa categoria\n• Verifica la detraibilità IVA per questo fornitore\n\n**📊 Riepilogo Conformità:**\nIl documento presenta principalmente conformità alle normative vigenti con alcune raccomandazioni per ottimizzare la gestione fiscale.',
        timestamp: '14:31',
        sources: ['D.Lgs 127/2015', 'DM 55/2013', 'Circolare AgID 2024']
      }
    ]
  },
  'consulenza_interattiva': {
    id: 'consulenza_interattiva',
    title: 'Consulenza Fiscale Interattiva',
    preview: 'Ho un problema con la dichiarazione dei redditi e non so da dove iniziare',
    timestamp: '2024-01-15T10:15:00',
    type: 'interactive',
    messages: [
      {
        id: 'user_int_1',
        type: 'user',
        content: 'Ho un problema con la dichiarazione dei redditi e non so da dove iniziare\n\n🔍 **Modalità**: Domanda interattiva richiesta',
        timestamp: '10:15'
      },
      {
        id: 'ai_int_1',
        type: 'ai',
        content: '🔍 **Modalità Consulenza Interattiva Attivata**\n\nPerfetto! Ti aiuterò a risolvere il problema con la dichiarazione dei redditi attraverso alcune domande mirate.\n\n**Prima domanda di approfondimento:**\n\n1️⃣ **Qual è la tua situazione lavorativa attuale?**\n   • Dipendente con un solo datore di lavoro\n   • Dipendente con più datori di lavoro\n   • Lavoratore autonomo con Partita IVA\n   • Pensionato\n   • Altro (specifica)\n\n**Perché è importante:** La tipologia di reddito determina quale modello dichiarativo utilizzare (730 vs Redditi PF) e quali documenti sono necessari.\n\nRispondi con il numero dell\'opzione più adatta alla tua situazione.',
        timestamp: '10:16',
        isInteractiveQuestion: true,
        sources: ['Istruzioni 730/2024', 'Istruzioni Redditi PF/2024']
      },
      {
        id: 'user_int_2',
        type: 'user',
        content: 'Sono un lavoratore autonomo con Partita IVA',
        timestamp: '10:17'
      },
      {
        id: 'ai_int_2',
        type: 'ai',
        content: '✅ **Situazione identificata: Lavoratore autonomo con P.IVA**\n\n**Seconda domanda di approfondimento:**\n\n2️⃣ **Quale regime fiscale utilizzi per la tua Partita IVA?**\n   • Regime forfettario (fatturato fino a €85.000)\n   • Regime semplificato\n   • Regime ordinario\n   • Non sono sicuro\n\n**Perché è importante:** Il regime fiscale determina:\n• Il modello da utilizzare (Redditi PF con o senza dichiarazione IVA)\n• Le deduzioni e detrazioni applicabili\n• Gli obblighi contabili e documentali\n\nInoltre, hai sostenuto **spese deducibili** nel 2023? (es. spese per ufficio, auto, formazione, consulenze)',
        timestamp: '10:18',
        isInteractiveQuestion: true,
        sources: ['L. 190/2014', 'DPR 917/86']
      },
      {
        id: 'user_int_3',
        type: 'user',
        content: 'Regime forfettario e sì, ho sostenuto spese per ufficio e auto',
        timestamp: '10:19'
      },
      {
        id: 'ai_int_3',
        type: 'ai',
        content: '🎯 **Soluzione Identificata!**\n\n**La tua situazione:**\n• Lavoratore autonomo in regime forfettario\n• Con spese deducibili (ufficio + auto)\n\n**⚠️ Attenzione importante:**\nNel **regime forfettario NON puoi dedurre le spese** sostenute, poiché il calcolo dell\'imposta avviene su base forfettaria con coefficienti di redditività prestabiliti.\n\n**📋 Quello che devi fare:**\n\n1️⃣ **Compilare il Modello Redditi PF** (non il 730)\n2️⃣ **Sezioni da completare:**\n   • Quadro RH: Redditi di lavoro autonomo\n   • Dichiarazione IVA (se fatturato > €5.000)\n3️⃣ **Calcolo semplificato:** Solo il 78% dei ricavi sarà tassato\n4️⃣ **Imposta sostitutiva:** 15% (o 5% se primo quinquennio)\n\n**💡 Ottimizzazione possibile:**\nSe le tue spese superano il 22% dei ricavi, potresti valutare il passaggio al regime ordinario per il 2024.\n\n**Documenti necessari:**\n• Registro dei corrispettivi 2023\n• Fatture emesse\n• Eventuale dichiarazione IVA\n\nVuoi che ti spieghi come compilare una sezione specifica?',
        timestamp: '10:22',
        sources: ['L. 190/2014 Art. 1', 'Vademecum AdE 2024', 'Istruzioni Redditi PF/2024']
      }
    ]
  },
  'contratto_lavoro': {
    id: 'contratto_lavoro',
    title: 'Contratto di lavoro part-time',
    preview: 'Quali sono gli obblighi del datore di lavoro per i contratti part-time secondo il D.Lgs 81/2015?',
    timestamp: '2024-01-14T16:45:00',
    type: 'simple',
    messages: [
      {
        id: 'q1-1',
        type: 'user',
        content: 'Quali sono gli obblighi del datore di lavoro per i contratti part-time secondo il D.Lgs 81/2015?',
        timestamp: '16:45'
      },
      {
        id: 'a1-1',
        type: 'ai',
        content: `Per i contratti part-time, il D.Lgs 81/2015 stabilisce specifici obblighi per il datore di lavoro:\n\n• **Forma scritta**: Il contratto deve essere in forma scritta e contenere la indicazione della durata della prestazione lavorativa e della collocazione temporale dell orario\n• **Parità di trattamento**: Garantire parità di trattamento rispetto ai lavoratori a tempo pieno comparabili\n• **Proporzionalità**: Retribuzione e ferie proporzionali allo orario svolto\n• **Diritto di precedenza**: Informare i lavoratori part-time delle opportunità di lavoro a tempo pieno\n• **Clausole elastiche**: Se previste, devono essere specificamente accettate per iscritto\n\nIl mancato rispetto di questi obblighi può comportare sanzioni amministrative.`,
        timestamp: '16:47',
        sources: ['D.Lgs 81/2015 - Art. 4-12', 'Circolare Min. Lavoro 17/2015']
      }
    ]
  },
  'f24_compilazione': {
    id: 'f24_compilazione',
    title: 'F24 compilazione IMU',
    preview: 'Come compilare correttamente il modello F24 per il versamento della IMU?',
    timestamp: '2024-01-14T11:20:00',
    type: 'simple',
    messages: [
      {
        id: 'q2-1',
        type: 'user',
        content: 'Come compilare correttamente il modello F24 per il versamento della IMU?',
        timestamp: '11:20'
      },
      {
        id: 'a2-1',
        type: 'ai',
        content: `Per compilare correttamente il F24 per la IMU, segui questi passaggi nella sezione IMU ed altri tributi locali:\n\n• **Codice tributo**: 3918 per IMU su altri fabbricati, 3925 per terreni agricoli\n• **Anno di riferimento**: Inserire lo anno per cui si versa la imposta (es. 2024)\n• **Codice catastale**: Codice del comune dove è ubicato lo immobile (reperibile su AgID)\n• **Detrazione**: Eventuale importo della detrazione spettante\n• **Importo a debito**: Somma dovuta per lo immobile`,
        timestamp: '11:22',
        sources: ['Istruzioni F24 2024', 'D.Lgs 504/1992', 'Provv. AgE 22/E/2024']
      }
    ]
  },
  'superbonus_2024': {
    id: 'superbonus_2024',
    title: 'Superbonus e detrazioni 2024',
    preview: 'Come funziona il Superbonus 110% nel 2024? Ci sono state modifiche?',
    timestamp: '2024-01-13T09:22:00',
    type: 'complex',
    messages: [
      {
        id: 'user_3',
        type: 'user',
        content: 'Come funziona il Superbonus 110% nel 2024? Ci sono state modifiche?',
        timestamp: '09:22',
      },
      {
        id: 'ai_3',
        type: 'ai',
        content: '**Superbonus 110% - Aggiornamenti 2024:**\n\n**🏠 Edifici Unifamiliari:**\n• **Scadenza**: 31 dicembre 2024\n• **Requisito ISEE**: €15.000 per lavori iniziati dal 2024\n• **SAL**: 30% al 30 giugno 2024 obbligatorio\n\n**🏢 Condomini:**\n• **Detrazione**: Ridotta al 70% dal 2024\n• **Scadenza**: 31 dicembre 2025\n• **CILAS**: Obbligatoria entro 31/12/2023\n\n**⚠️ Modifiche principali:**\n• Stop cessione crediti e sconto in fattura\n• Solo detrazione diretta in dichiarazione\n• Nuovi limiti di spesa per alcune categorie\n• Controlli rafforzati sulle asseverazioni',
        timestamp: '09:24',
        sources: ['L. Bilancio 2024', 'D.L. 39/2024', 'Circolare 13/E/2024']
      }
    ]
  },
  'iva_reverse_charge': {
    id: 'iva_reverse_charge',
    title: 'IVA Reverse Charge 2024',
    preview: 'Quando si applica il meccanismo del reverse charge e come funziona la registrazione?',
    timestamp: '2024-01-12T15:18:00',
    type: 'complex',
    messages: [
      {
        id: 'user_4',
        type: 'user',
        content: 'Quando si applica il meccanismo del reverse charge e come funziona la registrazione?',
        timestamp: '15:18',
      },
      {
        id: 'ai_4',
        type: 'ai',
        content: '**Reverse Charge IVA - Applicazione:**\n\n**📋 Operazioni soggette:**\n• Cessioni di materiali da demolizione, rottami metallici\n• Servizi di pulizia, demolizione, installazione\n• Prestazioni nel settore edile\n• Cessioni di oro e argento\n• Energia elettrica e gas\n\n**📝 Registrazione:**\n• **Registro IVA vendite**: Annotazione con IVA a zero\n• **Registro IVA acquisti**: Annotazione dell\'IVA dovuta\n• **Liquidazione**: IVA a debito = IVA a credito (se detraibile)\n\n**⚠️ Adempimenti:**\n• Dicitura "Inversione contabile" in fattura\n• Codice natura operazione\n• Comunicazione dati fatture se applicabile',
        timestamp: '15:20',
        sources: ['DPR 633/1972 Art. 17', 'L. 190/2014', 'Circolare 37/E/2013']
      }
    ]
  },
  'regime_forfettario': {
    id: 'regime_forfettario',
    title: 'Regime Forfettario 2024',
    preview: 'Quali sono i requisiti e i vantaggi del regime forfettario per il 2024?',
    timestamp: '2024-01-11T10:30:00',
    type: 'simple',
    messages: [
      {
        id: 'user_5',
        type: 'user',
        content: 'Quali sono i requisiti e i vantaggi del regime forfettario per il 2024?',
        timestamp: '10:30',
      },
      {
        id: 'ai_5',
        type: 'ai',
        content: '**Regime Forfettario 2024:**\n\n**💰 Soglie di accesso:**\n• **Ricavi/compensi**: Massimo €85.000 annui\n• **Beni strumentali**: Non superiori a €20.000\n• **Lavoro accessorio**: Massimo €5.000 per collaboratori\n\n**🎯 Vantaggi:**\n• **Imposta sostitutiva**: 15% sui ricavi (5% primi 5 anni)\n• **IVA**: Nessun versamento né detrazione\n• **IRAP**: Esenzione totale\n• **Contributi INPS**: Riduzione del 35%\n\n**📋 Obblighi semplificati:**\n• Numerazione e conservazione fatture\n• Registro dei corrispettivi\n• Dichiarazione dei redditi semplificata\n\n**⚠️ Incompatibilità:**\n• Partecipazioni in SRL/SpA\n• Attività prevalentemente commerciali con volume > €25.000',
        timestamp: '10:33',
        sources: ['L. 190/2014 Art. 1', 'DL 34/2019', 'Vademecum AdE 2024']
      }
    ]
  },
  'dichiarazione_precompilata': {
    id: 'dichiarazione_precompilata',
    title: 'Dichiarazione Precompilata 2024',
    preview: 'Come funziona la dichiarazione precompilata e quando conviene modificarla?',
    timestamp: '2024-01-10T14:55:00',
    type: 'simple',
    messages: [
      {
        id: 'user_6',
        type: 'user',
        content: 'Come funziona la dichiarazione precompilata e quando conviene modificarla?',
        timestamp: '14:55',
      },
      {
        id: 'ai_6',
        type: 'ai',
        content: '**Dichiarazione Precompilata 2024:**\n\n**📊 Dati già inseriti:**\n• **Redditi da lavoro**: CU di dipendenti e pensionati\n• **Altri redditi**: Locazioni, dividendi, interessi\n• **Oneri detraibili**: Spese sanitarie, mutui, ristrutturazioni\n• **Crediti**: Ritenute, acconti, crediti precedenti\n\n**✏️ Quando modificare:**\n• Redditi non presenti (es. lavoro autonomo)\n• Oneri detraibili aggiuntivi\n• Deduzioni non rilevate automaticamente\n• Correzione errori nei dati precompilati\n\n**⏰ Scadenze 2024:**\n• **Disponibilità**: 15 aprile 2024\n• **Invio telematico**: 31 ottobre 2024\n• **Modello Redditi**: 30 novembre 2024\n\n**💡 Vantaggi:**\n• Controlli preventivi integrati\n• Liquidazione automatica\n• Rimborsi accelerati (max 4 mesi)',
        timestamp: '14:58',
        sources: ['DL 175/2014', 'Provv. AdE 89775/2024', 'Istruzioni 730/2024']
      }
    ]
  },
  'bonus_casa_2024': {
    id: 'bonus_casa_2024',
    title: 'Bonus Casa 2024',
    preview: 'Quali detrazioni per la casa sono ancora attive nel 2024?',
    timestamp: '2024-01-09T16:12:00',
    type: 'complex',
    messages: [
      {
        id: 'user_7',
        type: 'user',
        content: 'Quali detrazioni per la casa sono ancora attive nel 2024?',
        timestamp: '16:12',
      },
      {
        id: 'ai_7',
        type: 'ai',
        content: '**Bonus Casa 2024 - Panoramica:**\n\n**🏠 Detrazioni attive:**\n• **Ristrutturazioni**: 50% fino a €96.000 (scade 31/12/2024)\n• **Bonus mobili**: 50% fino a €5.000 (solo con ristrutturazione)\n• **Bonus verde**: 36% fino a €5.000 (giardini e terrazzi)\n• **Bonus barriere**: 75% senza limiti di spesa\n\n**⚡ Efficienza energetica:**\n• **Ecobonus**: 50-65% per interventi specifici\n• **Superbonus**: 70% per condomini (scade 31/12/2025)\n• **Bonus facciate**: Sospeso per il 2024\n\n**💡 Novità 2024:**\n• **Tetto ISEE**: €15.000 per Superbonus unifamiliari\n• **Comunicazioni**: Obbligo ENEA per tutti i bonus\n• **Controlli**: Verifiche rafforzate su SAL e asseverazioni\n\n**📋 Documenti necessari:**\n• Comunicazione inizio lavori\n• Fatture e bonifici "parlanti"\n• Asseverazioni tecniche (dove richieste)',
        timestamp: '16:15',
        sources: ['L. Bilancio 2024', 'DL 39/2024', 'Vademecum ENEA 2024']
      }
    ]
  },
  'partita_iva_apertura': {
    id: 'partita_iva_apertura',
    title: 'Aperture Partita IVA 2024',
    preview: 'Come aprire una partita IVA nel 2024? Procedure e regimi fiscali disponibili.',
    timestamp: '2024-01-08T11:40:00',
    type: 'simple',
    messages: [
      {
        id: 'user_8',
        type: 'user',
        content: 'Come aprire una partita IVA nel 2024? Procedure e regimi fiscali disponibili.',
        timestamp: '11:40',
      },
      {
        id: 'ai_8',
        type: 'ai',
        content: '**Apertura Partita IVA 2024:**\n\n**📝 Procedura:**\n• **Termine**: Entro 30 giorni dall\'inizio attività\n• **Modalità**: Telematica (Fisconline/Entratel) o tramite intermediario\n• **Costi**: Gratuita se telematica\n• **Documenti**: Documento identità, codice fiscale, dati attività\n\n**🎯 Regimi fiscali disponibili:**\n• **Forfettario**: Fino a €85.000, imposta 15% (5% primi 5 anni)\n• **Semplificato**: Fino a €400.000 (beni) / €700.000 (servizi)\n• **Ordinario**: Senza limiti, contabilità completa\n\n**📊 Codici ATECO più comuni:**\n• **74.90.93**: Attività di consulenza\n• **62.01.00**: Programmazione informatica\n• **69.20.30**: Consulenza fiscale\n• **85.59.20**: Corsi di formazione\n\n**⚠️ Adempimenti immediati:**\n• Comunicazione inizio attività (se necessaria)\n• Iscrizione gestione INPS\n• Apertura conto corrente dedicato (consigliato)\n• Prima dichiarazione IVA (trimestrale o annuale)',
        timestamp: '11:44',
        sources: ['DPR 633/1972', 'DM 294/1999', 'Circolare 22/E/2024']
      }
    ]
  }
}

// Italian tax-specific feedback categories
const feedbackCategories = {
  wrong: [
    { id: 'normativa_obsoleta', label: 'Normativa obsoleta', description: 'La risposta fa riferimento a leggi o regolamenti non più in vigore' },
    { id: 'calcolo_sbagliato', label: 'Calcolo errato', description: 'Errori numerici o di applicazione delle aliquote fiscali' },
    { id: 'interpretazione_errata', label: 'Interpretazione errata', description: 'Interpretazione non corretta della normativa vigente' },
    { id: 'procedura_sbagliata', label: 'Procedura errata', description: 'Steps procedurali non corretti o fuorvianti' },
    { id: 'giurisprudenza_errata', label: 'Giurisprudenza non aggiornata', description: 'Riferimenti a orientamenti giurisprudenziali superati' }
  ],
  incomplete: [
    { id: 'info_mancanti', label: 'Informazioni mancanti', description: 'La risposta non copre aspetti importanti del quesito' },
    { id: 'fonti_insufficienti', label: 'Fonti insufficienti', description: 'Mancano riferimenti normativi o giurisprudenziali rilevanti' },
    { id: 'dettagli_procedurali', label: 'Dettagli procedurali mancanti', description: 'Passi operativi o tempistiche non specificate' },
    { id: 'eccezioni_non_citate', label: 'Eccezioni non citate', description: 'Non sono state menzionate eccezioni o casi particolari' },
    { id: 'aggiornamenti_recenti', label: 'Aggiornamenti recenti', description: 'Mancano le ultime modifiche normative o orientamenti' }
  ],
  correct: [
    { id: 'completa_accurata', label: 'Completa e accurata', description: 'La risposta è precisa e completa in tutti gli aspetti' },
    { id: 'fonti_corrette', label: 'Fonti aggiornate', description: 'Tutti i riferimenti normativi e giurisprudenziali sono corretti' },
    { id: 'pratica_utile', label: 'Praticamente utile', description: 'La risposta fornisce indicazioni operative chiare e utilizzabili' }
  ]
}

// Interactive question templates for different scenarios
const interactiveQuestionTemplates = [
  {
    id: 'tax_situation',
    initialQuestions: [
      'Qual è la tua situazione fiscale attuale?',
      'Hai una Partita IVA attiva?',
      'Che tipo di attività svolgi?',
      'Qual è il tuo regime fiscale?',
      'Hai dipendenti o collaboratori?'
    ],
    followUpQuestions: [
      'Da quanto tempo sei in questa situazione?',
      'Hai cambiato regime fiscale di recente?',
      'Ci sono stati cambiamenti significativi nell\'ultimo anno?',
      'Prevedi modifiche per il prossimo anno fiscale?'
    ]
  },
  {
    id: 'compliance_issue',
    initialQuestions: [
      'Quale normativa ti sta creando difficoltà?',
      'Quando è stata introdotta questa normativa?',
      'Hai già ricevuto comunicazioni dall\'Agenzia delle Entrate?',
      'Ci sono scadenze imminenti da rispettare?',
      'Hai documentazione specifica sul caso?'
    ],
    followUpQuestions: [
      'Hai già consultato altri professionisti?',
      'Qual è il rischio percepito se non risolvi?',
      'Ci sono precedenti simili nella tua attività?',
      'Preferisci una soluzione conservativa o ottimizzata?'
    ]
  },
  {
    id: 'planning_optimization',
    initialQuestions: [
      'Quale aspetto fiscale vorresti ottimizzare?',
      'Qual è il tuo orizzonte temporale di pianificazione?',
      'Ci sono investimenti o acquisizioni in programma?',
      'Quale regime fiscale utilizzi attualmente?',
      'Qual è il volume d\'affari approssimativo?'
    ],
    followUpQuestions: [
      'Sei disposto a modificare la struttura societaria?',
      'Ci sono vincoli familiari o personali?',
      'Qual è la priorità: risparmio fiscale o semplicità?',
      'Hai un commercialista di riferimento?'
    ]
  }
]

export function ChatPage({ onLogout, onNavigateToModelli, onNavigateToFonte, onNavigateToScadenze, onNavigateToNormative, onNavigateToAggiornamenti, onNavigateToNormativeFAQ, onNavigateToDomandePronte, onNavigateToClients, onNavigateToComunicazioni, onNavigateToProcedure, onNavigateToDashboard, onNavigateToMatching }: ChatPageProps) {
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [showMobileNav, setShowMobileNav] = useState(false)
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)
  const [showFeedbackModal, setShowFeedbackModal] = useState(false)
  const [feedbackMessageId, setFeedbackMessageId] = useState<string | null>(null)
  const [selectedFeedbackType, setSelectedFeedbackType] = useState<FeedbackType | null>(null)
  const [showFeedbackConfirmation, setShowFeedbackConfirmation] = useState<string | null>(null)
  const [inputMode, setInputMode] = useState<InputMode>('simple')
  const [isDragOver, setIsDragOver] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [interactiveQuestionCount, setInteractiveQuestionCount] = useState(0)
  const [showNotifications, setShowNotifications] = useState(false)
  const [showCommandPopover, setShowCommandPopover] = useState(false)
  const [showProcedureSelector, setShowProcedureSelector] = useState(false)
  const [showClientMention, setShowClientMention] = useState(false)
  const [mentionSearchQuery, setMentionSearchQuery] = useState('')
  const [mentionedClients, setMentionedClients] = useState<Client[]>([])
  const [mentionTimeout, setMentionTimeout] = useState<NodeJS.Timeout | null>(null)
  const [showClientActionPicker, setShowClientActionPicker] = useState(false)
  const [selectedClientForAction, setSelectedClientForAction] = useState<Client | null>(null)
  const [showClientProfile, setShowClientProfile] = useState(false)
  const [activeClientContext, setActiveClientContext] = useState<Client | null>(null)

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      type: 'ai',
      content: 'Benvenuto su PratikoAI! Sono il tuo assistente specializzato in normativa italiana. Come posso aiutarti oggi?',
      timestamp: new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
    }
  ])

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Cleanup mention timeout on unmount
  useEffect(() => {
    return () => {
      if (mentionTimeout) {
        clearTimeout(mentionTimeout)
      }
    }
  }, [mentionTimeout])

  const handleQuickAction = (action: string) => {
    if (action === 'domande-pronte') {
      onNavigateToDomandePronte()
    } else if (action === 'modelli') {
      onNavigateToModelli()
    } else if (action === 'scadenze') {
      onNavigateToScadenze()
    } else if (action === 'aggiornamenti') {
      onNavigateToAggiornamenti()
    } else if (action === 'normative') {
      onNavigateToNormative()
    } else if (action === 'normative-faq') {
      onNavigateToNormativeFAQ()
    }
  }

  const generateInteractiveResponse = (userMessage: string, questionCount: number): string => {
    const randomTemplate = interactiveQuestionTemplates[Math.floor(Math.random() * interactiveQuestionTemplates.length)]

    if (questionCount === 0) {
      // First interactive question
      const question = randomTemplate.initialQuestions[Math.floor(Math.random() * randomTemplate.initialQuestions.length)]
      return `🔍 **Modalità Consulenza Interattiva Attivata**\n\nPerfetto! Ti aiuterò a trovare la soluzione ottimale attraverso alcune domande mirate.\n\n**Prima domanda di approfondimento:**\n\n❓ **${question}**\n\n**Perché è importante:** Questa informazione mi permetterà di personalizzare la consulenza e fornirti la soluzione più adatta alla tua situazione specifica.\n\nRispondi con i dettagli che ritieni rilevanti.`
    } else if (questionCount === 1) {
      // Second interactive question
      const followUp = randomTemplate.followUpQuestions[Math.floor(Math.random() * randomTemplate.followUpQuestions.length)]
      return `✅ **Informazione acquisita**\n\nGrazie per la risposta! Ora ho bisogno di un altro dettaglio per completare il quadro.\n\n**Seconda domanda:**\n\n❓ **${followUp}**\n\n**Perché è rilevante:** Questo mi aiuterà a valutare le opzioni migliori e identificare eventuali rischi o opportunità che potresti non aver considerato.`
    } else {
      // Final solution after questions
      return `🎯 **Analisi Completata - Soluzione Personalizzata**\n\nBene! Basandomi sulle informazioni che mi hai fornito, ecco la **strategia ottimale** per la tua situazione:\n\n**📊 Quadro della Situazione:**\n• Le tue risposte indicano una situazione che richiede un approccio [specifico/conservativo/ottimizzato]\n• Ci sono [opportunità/rischi/adempimenti] da considerare\n\n**🎯 Soluzione Raccomandata:**\n\n1️⃣ **Azione Immediata:**\n   • [Azione specifica basata sul caso]\n   • Verifica documentazione necessaria\n   • Controllo scadenze imminenti\n\n2️⃣ **Strategia a Medio Termine:**\n   • [Pianificazione fiscale ottimale]\n   • Possibili ottimizzazioni da valutare\n   • Monitoraggio normative rilevanti\n\n3️⃣ **Prevenzione Futura:**\n   • Setup di controlli periodici\n   • Aggiornamenti normativi automatici\n   • Revisione annuale della strategia\n\n**⚠️ Punti di Attenzione:**\n• [Rischi specifici da monitorare]\n• Scadenze fiscali rilevanti\n• Modifiche normative in arrivo\n\n**📋 Prossimi Passi:**\n1. Implementa la soluzione immediata\n2. Pianifica le azioni a medio termine\n3. Programma controlli periodici\n\n**💡 Vuoi approfondire** un aspetto specifico della soluzione proposta?`
    }
  }

  const handleSend = (question?: string) => {
    const messageText = question || inputValue
    if (!messageText.trim() && !uploadedFile) return

    // If we're in a historical conversation, start a new conversation
    if (selectedConversationId) {
      setSelectedConversationId(null)
      setMessages([{
        id: 'welcome',
        type: 'ai',
        content: 'Benvenuto su PratikoAI! Sono il tuo assistente specializzato in normativa italiana. Come posso aiutarti oggi?',
        timestamp: new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
      }])
      setInteractiveQuestionCount(0)
    }

    let finalMessage = messageText

    // Handle file attachments based on mode
    if (uploadedFile) {
      if (inputMode === 'document') {
        finalMessage = `${messageText}\\n\\n📄 **Documento caricato**: ${uploadedFile.name}\\n**Modalità**: Analisi automatica documento`
      } else if (inputMode === 'complex') {
        finalMessage = `${messageText}\\n\\n🧠 **Modalità**: Analisi complessa richiesta\\n📎 **File allegato**: ${uploadedFile.name}`
      } else if (inputMode === 'interactive') {
        finalMessage = `${messageText}\\n\\n🔍 **Modalità**: Domanda interattiva richiesta\\n📎 **File allegato**: ${uploadedFile.name}`
      } else if (inputMode === 'simple') {
        finalMessage = `${messageText}\\n\\n📎 **File allegato**: ${uploadedFile.name}`
      }
    } else {
      // No file attached
      if (inputMode === 'complex') {
        finalMessage = `${messageText}\\n\\n🧠 **Modalità**: Analisi complessa richiesta`
      } else if (inputMode === 'interactive') {
        finalMessage = `${messageText}\\n\\n🔍 **Modalità**: Domanda interattiva richiesta`
      }
    }

    const newMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: finalMessage,
      timestamp: new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
    }

    setMessages(prev => [...prev, newMessage])
    setInputValue('')
    setUploadedFile(null)
    setIsTyping(true)

    // Store mentioned clients for this message
    const messageMentionedClients = [...mentionedClients]
    // Clear mentioned clients for next message
    setMentionedClients([])

    // Simulate AI response with realistic legal content
    setTimeout(() => {
      setIsTyping(false)

      let responses = []

      if (inputMode === 'interactive') {
        // Interactive mode - generate questions to guide the user
        const interactiveResponse = generateInteractiveResponse(messageText, interactiveQuestionCount)
        responses = [{
          content: interactiveResponse,
          sources: interactiveQuestionCount === 2 ? ['DPR 917/86', 'L. 212/2000', 'Prassi AdE 2024'] : ['Sistema PratikoAI'],
          isInteractiveQuestion: interactiveQuestionCount < 2
        }]

        setInteractiveQuestionCount(prev => prev + 1)
      } else if (inputMode === 'document') {
        responses = [
          {
            content: `📄 **Analisi Documento Completata** - ${uploadedFile?.name || 'Documento caricato'}\\n\\n**🔍 Riconoscimento Automatico:**\\n• **Tipo documento**: Contratto di locazione commerciale\\n• **Data**: 15 gennaio 2024\\n• **Soggetti**: Locatore/Conduttore identificati\\n\\n**📊 Dati Fiscalmente Rilevanti:**\\n• **Canone mensile**: €2.500,00\\n• **Durata contratto**: 6+6 anni\\n• **Regime IVA**: Ordinario (22%)\\n• **Cedolare secca**: Non applicabile (uso commerciale)\\n\\n**✅ Controllo Conformità:**\\n• **Registrazione obbligatoria**: Entro 30 giorni (Art. 5 DPR 131/86)\\n• **Imposta di registro**: 2% del canone annuo\\n• **Clausole conformi**: L. 392/1978 rispettata\\n\\n**💡 Suggerimenti Ottimizzazione:**\\n• Valutare regime forfettario per il locatore\\n• Clausola di adeguamento ISTAT raccomandata\\n• Verificare detraibilità spese per il conduttore`,
            sources: ['DPR 131/1986', 'L. 392/1978', 'Circolare 6/E/2024']
          },
          {
            content: `📄 **Analisi Fattura Completata** - ${uploadedFile?.name || 'Documento caricato'}\\n\\n**🔍 Riconoscimento Automatico:**\\n• **Tipo documento**: Fattura elettronica B2B\\n• **Numero**: FT001/2024\\n• **Data emissione**: 12 gennaio 2024\\n• **Partita IVA**: Validata e attiva\\n\\n**📊 Estrazione Dati:**\\n• **Imponibile**: €1.000,00\\n• **IVA 22%**: €220,00\\n• **Totale**: €1.220,00\\n• **Codice destinatario**: Presente e corretto\\n\\n**✅ Controllo Conformità:**\\n• **Formato XML**: Conforme alle specifiche AgID\\n• **Campi obbligatori**: Tutti presenti\\n• **Codici articolo**: Conformi alla normativa\\n• **Scadenza pagamento**: 60 giorni (D.Lgs 231/2002)\\n\\n**💡 Suggerimenti:**\\n• Fattura conforme per detrazione IVA\\n• Registrazione immediata consigliata\\n• Pagamento tracciabile obbligatorio sopra €5.000`,
            sources: ['D.Lgs 127/2015', 'DM 55/2013', 'D.Lgs 231/2002']
          }
        ]
      } else if (inputMode === 'complex') {
        responses = [
          {
            content: `🧠 **Analisi Complessa Avviata**\\n\\n${uploadedFile ? `📎 **Documento allegato considerato**: ${uploadedFile.name}\\n\\n` : ''}**📋 Quadro Normativo Completo:**\\nPer il caso descritto, è necessario considerare molteplici aspetti normativi intersecanti:\\n\\n**🏛️ Principi Fondamentali:**\\n• **Art. 53 Costituzione**: Principio di capacità contributiva\\n• **Statuto del Contribuente**: Principi di chiarezza e non retroattività\\n• **Giurisprudenza consolidata**: Orientamenti Cassazione e CTR\\n\\n**📚 Normativa Specifica:**\\n• **TUIR (DPR 917/86)**: Disciplina delle imposte sui redditi\\n• **Codice Civile**: Principi contrattuali e societari\\n• **Normativa UE**: Direttive IVA e aiuti di Stato\\n\\n**⚖️ Casistica Rilevante:**\\n• **Precedenti giurisprudenziali**: 15 casi simili analizzati\\n• **Prassi amministrativa**: Circolari e risoluzioni recenti\\n• **Orientamenti dottrinali**: Commenti esperti del settore\\n\\n**🎯 Strategia Consigliata:**\\n1. **Istanza di interpello**: Art. 11 L. 212/2000\\n2. **Documentazione defensionale**: Raccolta prove\\n3. **Timeline procedurale**: Scadenze da rispettare\\n4. **Risk assessment**: Valutazione probabilità successo${uploadedFile ? '\\n\\n💡 **Nota**: Il documento allegato è stato considerato nel contesto della analisi per fornire raccomandazioni più precise.' : ''}`,
            sources: ['Cost. Art. 53', 'L. 212/2000', 'Giurispr. Cass. 2023-24']
          }
        ]
      } else {
        // Simple mode responses with file attachment awareness
        responses = uploadedFile ? [
          // Responses with file attachment context
          {
            content: `📎 **File allegato considerato**: ${uploadedFile.name}\\n\\nEcco le principali novità fiscali per il 2024 (considerate nel contesto del documento allegato):\\n\\n• **Superbonus 110%**: Prorogato con modifiche fino al 31 dicembre 2024 per edifici unifamiliari\\n• **Bonus mobili**: Confermato al 50% fino a €5.000 per le spese sostenute nel 2024\\n• **Detrazione spese mediche**: Soglia minima aumentata a €129,11\\n• **IRPEF**: Mantenute le quattro aliquote (23%, 25%, 35%, 43%)\\n• **Contributi previdenziali**: Incremento del 0,2% per dipendenti privati\\n\\n💡 **Applicazione al tuo caso**: Sulla base del documento allegato, ti consiglio di verificare la applicabilità specifica di queste normative.\\n\\nUltimo aggiornamento: ${new Date().toLocaleDateString('it-IT')}`,
            sources: ['Legge di Bilancio 2024', 'Circolare 15/E/2024', 'D.L. 39/2024']
          },
          {
            content: `📎 **File allegato considerato**: ${uploadedFile.name}\\n\\nPer la compilazione del modello F24 (con riferimento al documento allegato):\\n\\n• **Sezione Erario**: Inserire codici tributo e importi dovuti\\n• **Sezione INPS**: Contributi previdenziali con codici sede\\n• **Sezione Regioni**: Tributi regionali (IRAP, addizionale IRPEF)\\n• **Sezione IMU**: Codici catastali e importi per ogni immobile\\n\\n⚠️ **Attenzione**: Verificare sempre i codici tributo aggiornati sul sito delle Entrate.\\n\\n💡 **Suggerimento specifico**: Dal documento allegato, sembra necessario prestare particolare attenzione alla sezione [X] del modello F24.\\n\\nLa compilazione telematica è obbligatoria per importi superiori a €1.000.`,
            sources: ['Provvedimento 22/E/2024', 'Istruzioni F24', 'Agenzia Entrate']
          }
        ] : [
          // Standard responses without file attachment
          {
            content: `Ecco le principali novità fiscali per il 2024:\\n\\n• **Superbonus 110%**: Prorogato con modifiche fino al 31 dicembre 2024 per edifici unifamiliari\\n• **Bonus mobili**: Confermato al 50% fino a €5.000 per le spese sostenute nel 2024\\n• **Detrazione spese mediche**: Soglia minima aumentata a €129,11\\n• **IRPEF**: Mantenute le quattro aliquote (23%, 25%, 35%, 43%)\\n• **Contributi previdenziali**: Incremento del 0,2% per dipendenti privati\\n\\nUltimo aggiornamento: ${new Date().toLocaleDateString('it-IT')}`,
            sources: ['Legge di Bilancio 2024', 'Circolare 15/E/2024', 'D.L. 39/2024']
          },
          {
            content: `Per la compilazione del modello F24, ecco i passaggi principali:\\n\\n• **Sezione Erario**: Inserire codici tributo e importi dovuti\\n• **Sezione INPS**: Contributi previdenziali con codici sede\\n• **Sezione Regioni**: Tributi regionali (IRAP, addizionale IRPEF)\\n• **Sezione IMU**: Codici catastali e importi per ogni immobile\\n\\n⚠️ **Attenzione**: Verificare sempre i codici tributo aggiornati sul sito delle Entrate.\\n\\nLa compilazione telematica è obbligatoria per importi superiori a €1.000.`,
            sources: ['Provvedimento 22/E/2024', 'Istruzioni F24', 'Agenzia Entrate']
          }
        ]
      }

      const randomResponse = responses[Math.floor(Math.random() * responses.length)]

      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: randomResponse.content,
        timestamp: new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' }),
        sources: randomResponse.sources,
        isInteractiveQuestion: randomResponse.isInteractiveQuestion,
        mentionedClients: messageMentionedClients.length > 0 ? messageMentionedClients : undefined
      }
      setMessages(prev => [...prev, aiResponse])
    }, 1500 + Math.random() * 1000)
  }

  const clearChat = () => {
    setSelectedConversationId(null)
    setInteractiveQuestionCount(0)
    setMessages([{
      id: 'welcome',
      type: 'ai',
      content: 'Benvenuto su PratikoAI! Sono il tuo assistente specializzato in normativa italiana. Come posso aiutarti oggi?',
      timestamp: new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
    }])
  }

  const handleQuickActionClick = (action: string) => {
    switch (action) {
      case 'modelli':
        onNavigateToModelli()
        break
      case 'scadenze':
        onNavigateToScadenze()
        break
      case 'aggiornamenti':
        onNavigateToAggiornamenti()
        break
      case 'normative':
        onNavigateToNormative()
        break
      case 'domande-pronte':
        onNavigateToDomandePronte()
        break
      case 'normative-faq':
        onNavigateToNormativeFAQ()
        break
      default:
        console.log('Unknown action:', action)
    }
  }

  const handleConversationSelect = (conversationId: string) => {
    const conversation = mockConversations[conversationId]
    if (conversation) {
      setSelectedConversationId(conversationId)
      setMessages(conversation.messages)
      setInteractiveQuestionCount(0) // Reset interactive counter
      setIsSidebarOpen(false) // Close sidebar on mobile
    }
  }

  const handleFeedbackClick = (messageId: string, feedbackType: FeedbackType) => {
    setFeedbackMessageId(messageId)
    setSelectedFeedbackType(feedbackType)

    if (feedbackType === 'correct') {
      // For correct feedback, show quick confirmation
      handleFeedbackSubmit(messageId, feedbackType, 'completa_accurata', '')
    } else {
      // For incomplete/wrong, show detailed modal
      setShowFeedbackModal(true)
    }
  }

  const handleFeedbackSubmit = (messageId: string, feedbackType: FeedbackType, category: string, details: string) => {
    const feedback: MessageFeedback = {
      type: feedbackType,
      category,
      details,
      timestamp: new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
    }

    // Update the message with feedback
    setMessages(prev => prev.map(msg =>
      msg.id === messageId
        ? { ...msg, feedback }
        : msg
    ))

    // Show confirmation
    setShowFeedbackConfirmation(messageId)
    setTimeout(() => setShowFeedbackConfirmation(null), 3000)

    // Close modal and reset state
    setShowFeedbackModal(false)
    setFeedbackMessageId(null)
    setSelectedFeedbackType(null)

    // Here you would typically send the feedback to your backend
    console.log('Feedback submitted:', { messageId, feedback })
  }

  const handleFileUpload = (file: File) => {
    // Validate file type
    const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/jpeg', 'image/png', 'image/gif']

    if (!allowedTypes.includes(file.type)) {
      alert('Formato file non supportato. Carica PDF, DOC, DOCX o immagini.')
      return
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      alert('File troppo grande. Dimensione massima: 10MB.')
      return
    }

    setUploadedFile(file)

    // Update input value based on mode
    if (inputMode === 'document') {
      setInputValue(`📄 ${file.name} - Pronto per la analisi automatica`)
    } else {
      // For simple, complex, and interactive mode, don't auto-fill the input
      // User should still write their question
      if (!inputValue.trim()) {
        setInputValue('')
      }
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)

    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0])
    }
  }

  const getCurrentPlaceholder = () => {
    if (activeClientContext) {
      return `Domanda con contesto di ${activeClientContext.name}...`
    }
    const mode = inputModes.find(m => m.id === inputMode)
    if (selectedConversationId) {
      return "Scrivi qui per iniziare una nuova conversazione..."
    }
    return mode?.placeholder || "Fai una domanda sulla normativa italiana..."
  }

  const FeedbackButtons = ({ messageId, feedback }: { messageId: string, feedback?: MessageFeedback }) => {
    if (feedback) {
      return (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center space-x-2 mt-3 pt-2 border-t border-[#C4BDB4]/20"
        >
          <div className={`flex items-center space-x-1 px-2 py-1 rounded-md text-xs ${
            feedback.type === 'correct'
              ? 'bg-green-100 text-green-800 border border-green-200'
              : feedback.type === 'incomplete'
              ? 'bg-yellow-100 text-yellow-800 border border-yellow-200'
              : 'bg-red-100 text-red-800 border border-red-200'
          }`}>
            {feedback.type === 'correct' && <ThumbsUp className="w-3 h-3" />}
            {feedback.type === 'incomplete' && <AlertTriangle className="w-3 h-3" />}
            {feedback.type === 'wrong' && <ThumbsDown className="w-3 h-3" />}
            <span className="capitalize">
              {feedback.type === 'correct' ? 'Confermata' :
               feedback.type === 'incomplete' ? 'Incompleta' : 'Segnalata'}
            </span>
          </div>
          {showFeedbackConfirmation === messageId && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="flex items-center space-x-1 text-green-600"
            >
              <Check className="w-3 h-3" />
              <span className="text-xs">Grazie per il feedback!</span>
            </motion.div>
          )}
        </motion.div>
      )
    }

    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center space-x-2 mt-3 pt-2 border-t border-[#C4BDB4]/20"
      >
        <span className="text-xs text-[#C4BDB4] mr-2">Questa risposta è:</span>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => handleFeedbackClick(messageId, 'correct')}
          className="flex items-center space-x-1 px-2 py-1 rounded-md text-xs bg-green-50 text-green-700 hover:bg-green-100 transition-colors border border-green-200"
        >
          <ThumbsUp className="w-3 h-3" />
          <span>Corretta</span>
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => handleFeedbackClick(messageId, 'incomplete')}
          className="flex items-center space-x-1 px-2 py-1 rounded-md text-xs bg-yellow-50 text-yellow-700 hover:bg-yellow-100 transition-colors border border-yellow-200"
        >
          <AlertTriangle className="w-3 h-3" />
          <span>Incompleta</span>
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => handleFeedbackClick(messageId, 'wrong')}
          className="flex items-center space-x-1 px-2 py-1 rounded-md text-xs bg-red-50 text-red-700 hover:bg-red-100 transition-colors border border-red-200"
        >
          <ThumbsDown className="w-3 h-3" />
          <span>Errata</span>
        </motion.button>
        {showFeedbackConfirmation === messageId && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="flex items-center space-x-1 text-green-600"
          >
            <Check className="w-3 h-3" />
            <span className="text-xs">Grazie!</span>
          </motion.div>
        )}
      </motion.div>
    )
  }

  const TypingIndicator = () => (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      className="flex items-center space-x-3 p-4 mb-4"
    >
      <div className="w-8 h-8 bg-[#2A5D67] rounded-full flex items-center justify-center">
        <Brain className="w-4 h-4 text-white" />
      </div>
      <div className="flex items-center space-x-1">
        <div className="flex space-x-1">
          <motion.div
            className="w-2 h-2 bg-[#2A5D67] rounded-full"
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.4, repeat: Infinity, delay: 0 }}
          />
          <motion.div
            className="w-2 h-2 bg-[#2A5D67] rounded-full"
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.4, repeat: Infinity, delay: 0.2 }}
          />
          <motion.div
            className="w-2 h-2 bg-[#2A5D67] rounded-full"
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.4, repeat: Infinity, delay: 0.4 }}
          />
        </div>
        <span className="text-sm text-[#C4BDB4] ml-2">
          {inputMode === 'interactive' ? 'PratikoAI sta preparando la prossima domanda...' : 'PratikoAI sta analizzando...'}
        </span>
      </div>
    </motion.div>
  )

  const InputModeSelector = () => (
    <div className="flex items-center space-x-2 mb-4 overflow-x-auto pb-2">
      {inputModes.map((mode) => {
        const Icon = mode.icon
        const isActive = inputMode === mode.id

        return (
          <motion.button
            key={mode.id}
            onClick={() => {
              setInputMode(mode.id)
              setUploadedFile(null)
              setInputValue('')
              setInteractiveQuestionCount(0) // Reset interactive counter when switching modes
            }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className={`flex items-center space-x-2 px-3 py-2 rounded-lg border transition-all flex-shrink-0 ${
              isActive
                ? 'bg-[#2A5D67] text-white border-[#2A5D67] shadow-md'
                : 'bg-white text-[#1E293B] border-[#C4BDB4]/20 hover:border-[#2A5D67] hover:bg-[#F8F5F1]'
            }`}
            title={mode.description}
          >
            <Icon className="w-4 h-4" />
            <span className="text-sm font-medium whitespace-nowrap">{mode.label}</span>
            {mode.id === 'interactive' && (
              <div className="w-2 h-2 bg-[#D4A574] rounded-full animate-pulse" title="Modalità Innovativa" />
            )}
          </motion.button>
        )
      })}
    </div>
  )

  const DocumentAnalysisUI = () => {
    const [progress, setProgress] = useState(0)

    useEffect(() => {
      const timer = setTimeout(() => setProgress(100), 500)
      return () => clearTimeout(timer)
    }, [])

    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white border border-[#C4BDB4]/20 rounded-xl p-6 my-4 max-w-md mx-auto"
      >
        {/* Document Icon and Title */}
        <div className="text-center mb-4">
          <div className="w-12 h-12 bg-[#F8F5F1] rounded-lg flex items-center justify-center mx-auto mb-3">
            <FileText className="w-6 h-6 text-[#2A5D67]" />
          </div>
          <h3 className="font-semibold text-[#1E293B] mb-1">
            Fattura_Elettronica_2024_001.xml
          </h3>
          <p className="text-sm text-[#C4BDB4]">Fattura Elettronica</p>
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="w-full bg-[#C4BDB4]/20 rounded-full h-2">
            <motion.div
              className="bg-[#2A5D67] h-2 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 1.5, ease: "easeOut" }}
            />
          </div>
        </div>

        {/* Analysis Results */}
        <div className="space-y-3">
          {/* IVA Check - Blue */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5 }}
            className="flex items-start space-x-3 p-3 bg-blue-50 border-l-4 border-blue-400 rounded-r-lg"
          >
            <div className="w-2 h-2 bg-blue-400 rounded-full mt-2 flex-shrink-0" />
            <span className="text-sm text-blue-800">
              IVA al 22% applicata correttamente
            </span>
          </motion.div>

          {/* Warning - Yellow */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.7 }}
            className="flex items-start space-x-3 p-3 bg-yellow-50 border-l-4 border-yellow-400 rounded-r-lg"
          >
            <div className="w-2 h-2 bg-yellow-400 rounded-full mt-2 flex-shrink-0" />
            <span className="text-sm text-yellow-800">
              Codice destinatario mancante - può causare ritardi
            </span>
          </motion.div>

          {/* Success - Green */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.9 }}
            className="flex items-start space-x-3 p-3 bg-green-50 border-l-4 border-green-400 rounded-r-lg"
          >
            <div className="w-2 h-2 bg-green-400 rounded-full mt-2 flex-shrink-0" />
            <span className="text-sm text-green-800">
              Formato XML conforme alle specifiche
            </span>
          </motion.div>
        </div>

        {/* Suggestions Section */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.1 }}
          className="mt-6 pt-4 border-t border-[#C4BDB4]/20"
        >
          <h4 className="font-semibold text-[#1E293B] mb-3">
            Suggerimenti:
          </h4>
          <ul className="space-y-2 text-sm text-[#1E293B]">
            <li className="flex items-start space-x-2">
              <span className="text-[#D4A574] mt-1">•</span>
              <span>Considera l'utilizzo del reverse charge per questa categoria</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-[#D4A574] mt-1">•</span>
              <span>Verifica la detraibilità IVA per questo fornitore</span>
            </li>
          </ul>
        </motion.div>
      </motion.div>
    )
  }

  const FileUploadArea = () => {
    return (
      <AnimatePresence>
        {uploadedFile && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-3"
          >
            <div className="flex items-center justify-between bg-[#F8F5F1] border border-[#C4BDB4]/20 rounded-lg p-3">
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-lg ${
                  inputMode === 'document'
                    ? 'bg-[#2A5D67] text-white'
                    : inputMode === 'interactive'
                    ? 'bg-[#D4A574] text-white'
                    : 'bg-[#D4A574] text-white'
                }`}>
                  {inputMode === 'document' ? (
                    <FileCheck className="w-4 h-4" />
                  ) : inputMode === 'interactive' ? (
                    <Search className="w-4 h-4" />
                  ) : (
                    <Paperclip className="w-4 h-4" />
                  )}
                </div>
                <div>
                  <p className="text-sm font-medium text-[#1E293B] truncate max-w-xs">
                    {uploadedFile.name}
                  </p>
                  <p className="text-xs text-[#C4BDB4]">
                    {inputMode === 'document'
                      ? 'Analisi automatica'
                      : inputMode === 'interactive'
                      ? 'Consulenza interattiva'
                      : 'File allegato'
                    }
                  </p>
                </div>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setUploadedFile(null)
                  if (inputMode === 'document') {
                    setInputValue('')
                  }
                }}
                className="text-[#C4BDB4] hover:text-red-600 hover:bg-red-50 h-8 w-8 p-0"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    )
  }

  const FeedbackModal = () => {
    const [selectedCategory, setSelectedCategory] = useState<string>('')
    const [feedbackDetails, setFeedbackDetails] = useState('')

    if (!showFeedbackModal || !selectedFeedbackType || !feedbackMessageId) return null

    const categories = feedbackCategories[selectedFeedbackType] || []

    const handleSubmit = () => {
      if (selectedCategory) {
        handleFeedbackSubmit(feedbackMessageId, selectedFeedbackType, selectedCategory, feedbackDetails)
      }
    }

    return (
      <>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
          onClick={() => setShowFeedbackModal(false)}
        />
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 20 }}
          className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg shadow-2xl p-6 w-full max-w-md z-50"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-[#2A5D67]">
              Dettagli feedback
            </h3>
            <button
              onClick={() => setShowFeedbackModal(false)}
              className="text-[#C4BDB4] hover:text-[#2A5D67] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="mb-4">
            <p className="text-sm text-[#1E293B] mb-3">
              Hai segnalato questa risposta come{' '}
              <strong>
                {selectedFeedbackType === 'incomplete' ? 'incompleta' : 'errata'}
              </strong>
              . Aiutaci a migliorare selezionando la categoria più appropriata:
            </p>

            <div className="space-y-2">
              {categories.map((category) => (
                <motion.label
                  key={category.id}
                  whileHover={{ scale: 1.02 }}
                  className={`block p-3 rounded-lg border cursor-pointer transition-all ${
                    selectedCategory === category.id
                      ? 'border-[#2A5D67] bg-[#F8F5F1] shadow-sm'
                      : 'border-[#C4BDB4]/20 hover:border-[#C4BDB4] hover:bg-[#F8F5F1]/50'
                  }`}
                >
                  <input
                    type="radio"
                    name="category"
                    value={category.id}
                    checked={selectedCategory === category.id}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="sr-only"
                  />
                  <div className="flex items-start space-x-3">
                    <div className={`w-4 h-4 rounded-full border-2 mt-0.5 flex items-center justify-center ${
                      selectedCategory === category.id
                        ? 'border-[#2A5D67] bg-[#2A5D67]'
                        : 'border-[#C4BDB4]'
                    }`}>
                      {selectedCategory === category.id && (
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          className="w-2 h-2 bg-white rounded-full"
                        />
                      )}
                    </div>
                    <div>
                      <p className="font-medium text-[#1E293B]">{category.label}</p>
                      <p className="text-xs text-[#C4BDB4] mt-1">{category.description}</p>
                    </div>
                  </div>
                </motion.label>
              ))}
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-[#1E293B] mb-2">
              Dettagli aggiuntivi (opzionale)
            </label>
            <textarea
              value={feedbackDetails}
              onChange={(e) => setFeedbackDetails(e.target.value)}
              placeholder="Fornisci ulteriori dettagli per aiutarci a migliorare..."
              className="w-full p-3 border border-[#C4BDB4]/20 rounded-lg focus:ring-2 focus:ring-[#2A5D67]/20 focus:border-[#2A5D67] transition-all resize-none"
              rows={3}
            />
          </div>

          <div className="flex space-x-3">
            <Button
              onClick={() => setShowFeedbackModal(false)}
              variant="outline"
              className="flex-1"
            >
              Annulla
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={!selectedCategory}
              className={`flex-1 ${
                selectedCategory
                  ? 'bg-[#2A5D67] hover:bg-[#1E293B] text-white'
                  : 'bg-[#C4BDB4] text-white cursor-not-allowed'
              }`}
            >
              Invia Feedback
            </Button>
          </div>
        </motion.div>
      </>
    )
  }

  return (
    <div className="h-screen bg-[#F8F5F1] flex relative">
      {/* Sidebar */}
      <AnimatePresence>
        {isSidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden"
              onClick={() => setIsSidebarOpen(false)}
            />
            <motion.div
              initial={{ x: -300 }}
              animate={{ x: 0 }}
              exit={{ x: -300 }}
              transition={{ type: 'spring', damping: 30 }}
              className="fixed left-0 top-0 h-full w-80 bg-white shadow-2xl z-50 lg:relative lg:translate-x-0"
            >
              <SidebarContent
                onLogout={onLogout}
                onCloseSidebar={() => setIsSidebarOpen(false)}
                selectedConversationId={selectedConversationId}
                onConversationSelect={handleConversationSelect}
                onNavigateToClients={onNavigateToClients}
                onNavigateToComunicazioni={onNavigateToComunicazioni}
                onNavigateToProcedure={onNavigateToProcedure}
                onNavigateToDashboard={onNavigateToDashboard}
                onNavigateToMatching={onNavigateToMatching}
              />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Desktop Sidebar */}
      <div className="hidden lg:block w-80 bg-white shadow-lg">
        <SidebarContent
          onLogout={onLogout}
          selectedConversationId={selectedConversationId}
          onConversationSelect={handleConversationSelect}
          onNavigateToClients={onNavigateToClients}
          onNavigateToComunicazioni={onNavigateToComunicazioni}
          onNavigateToProcedure={onNavigateToProcedure}
          onNavigateToDashboard={onNavigateToDashboard}
          onNavigateToMatching={onNavigateToMatching}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white shadow-sm border-b border-[#C4BDB4]/20 p-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsSidebarOpen(true)}
              className="lg:hidden text-[#2A5D67] hover:bg-[#F8F5F1]"
            >
              <Menu className="w-5 h-5" />
            </Button>
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-[#2A5D67] rounded-xl flex items-center justify-center">
                <Brain className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-[#2A5D67]">
                  {selectedConversationId ? mockConversations[selectedConversationId]?.title : 'PratikoAI'}
                </h1>
                <div className="flex items-center space-x-2">
                  <Circle className="w-2 h-2 text-[#A9C1B7] fill-current" />
                  <span className="text-sm text-[#1E293B]">
                    {selectedConversationId
                      ? `Conversazione del ${new Date(mockConversations[selectedConversationId]?.timestamp).toLocaleDateString('it-IT')}`
                      : inputMode === 'interactive'
                      ? 'Modalità Interattiva • Guidato da PratikoAI'
                      : 'Online • Aggiornato in tempo reale'
                    }
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {/* Navigation Buttons - Desktop */}
            <div className="hidden md:flex items-center space-x-1 mr-4">
              <Button
                onClick={onNavigateToModelli}
                variant="ghost"
                size="sm"
                className="text-[#1E293B] hover:bg-[#F8F5F1] relative"
              >
                <FileText className="w-4 h-4 mr-2" />
                Modelli
                <Construction className="w-3 h-3 ml-1 text-[#D4A574]" />
              </Button>
              <Button
                onClick={onNavigateToScadenze}
                variant="ghost"
                size="sm"
                className="text-[#1E293B] hover:bg-[#F8F5F1]"
              >
                <Clock className="w-4 h-4 mr-2" />
                Scadenze
                <Construction className="w-3 h-3 ml-1 text-[#D4A574]" />
              </Button>
              <Button
                onClick={onNavigateToNormative}
                variant="ghost"
                size="sm"
                className="text-[#1E293B] hover:bg-[#F8F5F1]"
              >
                <BookOpen className="w-4 h-4 mr-2" />
                Normative
                <Construction className="w-3 h-3 ml-1 text-[#D4A574]" />
              </Button>
              <Button
                onClick={onNavigateToAggiornamenti}
                variant="ghost"
                size="sm"
                className="text-[#1E293B] hover:bg-[#F8F5F1]"
              >
                <AlertCircle className="w-4 h-4 mr-2" />
                Aggiornamenti
                <Construction className="w-3 h-3 ml-1 text-[#D4A574]" />
              </Button>
              <Button
                onClick={onNavigateToDomandePronte}
                variant="ghost"
                size="sm"
                className="text-[#1E293B] hover:bg-[#F8F5F1]"
              >
                <MessageSquare className="w-4 h-4 mr-2" />
                Domande Pronte
                <Construction className="w-3 h-3 ml-1 text-[#D4A574]" />
              </Button>
            </div>

            {/* Navigation Menu - Mobile */}
            <div className="md:hidden mr-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowMobileNav(!showMobileNav)}
                className="text-[#2A5D67] hover:bg-[#F8F5F1] relative"
              >
                <Settings className="w-4 h-4" />
              </Button>

              <AnimatePresence>
                {showMobileNav && (
                  <>
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40"
                      onClick={() => setShowMobileNav(false)}
                    />
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="absolute right-4 top-14 bg-white border border-[#C4BDB4]/20 rounded-lg shadow-lg z-50 py-2 min-w-48"
                    >
                      <button
                        onClick={() => {
                          onNavigateToModelli()
                          setShowMobileNav(false)
                        }}
                        className="w-full text-left px-4 py-2 text-[#1E293B] hover:bg-[#F8F5F1] flex items-center"
                      >
                        <FileText className="w-4 h-4 mr-3" />
                        Modelli e Formulari
                        <Construction className="w-3 h-3 ml-auto text-[#D4A574]" />
                      </button>
                      <button
                        onClick={() => {
                          onNavigateToScadenze()
                          setShowMobileNav(false)
                        }}
                        className="w-full text-left px-4 py-2 text-[#1E293B] hover:bg-[#F8F5F1] flex items-center"
                      >
                        <Clock className="w-4 h-4 mr-3" />
                        Scadenze Fiscali
                        <Construction className="w-3 h-3 ml-auto text-[#D4A574]" />
                      </button>
                      <button
                        onClick={() => {
                          onNavigateToNormative()
                          setShowMobileNav(false)
                        }}
                        className="w-full text-left px-4 py-2 text-[#1E293B] hover:bg-[#F8F5F1] flex items-center"
                      >
                        <BookOpen className="w-4 h-4 mr-3" />
                        Normative Recenti
                        <Construction className="w-3 h-3 ml-auto text-[#D4A574]" />
                      </button>
                      <button
                        onClick={() => {
                          onNavigateToAggiornamenti()
                          setShowMobileNav(false)
                        }}
                        className="w-full text-left px-4 py-2 text-[#1E293B] hover:bg-[#F8F5F1] flex items-center"
                      >
                        <AlertCircle className="w-4 h-4 mr-3" />
                        Aggiornamenti Urgenti
                        <Construction className="w-3 h-3 ml-auto text-[#D4A574]" />
                      </button>
                      <button
                        onClick={() => {
                          onNavigateToDomandePronte()
                          setShowMobileNav(false)
                        }}
                        className="w-full text-left px-4 py-2 text-[#1E293B] hover:bg-[#F8F5F1] flex items-center"
                      >
                        <MessageSquare className="w-4 h-4 mr-3" />
                        Domande Pronte
                        <Construction className="w-3 h-3 ml-auto text-[#D4A574]" />
                      </button>
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </div>

            {/* Notifications Bell */}
            <div className="relative">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowNotifications(!showNotifications)}
                className="text-[#2A5D67] hover:bg-[#F8F5F1] relative"
              >
                <Bell className="w-5 h-5" />
                {/* Unread badge */}
                <span className="absolute -top-1 -right-1 bg-[#D4A574] text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                  4
                </span>
              </Button>
              <NotificationsDropdown
                isOpen={showNotifications}
                onClose={() => setShowNotifications(false)}
                onViewAll={() => {
                  setShowNotifications(false)
                  // Navigate to notifications page if needed
                }}
              />
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={clearChat}
              className="text-[#2A5D67] border-[#2A5D67] hover:bg-[#2A5D67] hover:text-white"
            >

              {selectedConversationId ? 'Nuova Chat' : ''}
            </Button>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Messages */}
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex items-start space-x-3 max-w-3xl ${message.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                  {/* Avatar */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    message.type === 'user'
                      ? 'bg-[#D4A574]'
                      : message.isInteractiveQuestion
                      ? 'bg-gradient-to-r from-[#2A5D67] to-[#D4A574]'
                      : 'bg-[#2A5D67]'
                  }`}>
                    {message.type === 'user' ? (
                      <User className="w-4 h-4 text-white" />
                    ) : message.isInteractiveQuestion ? (
                      <Search className="w-4 h-4 text-white" />
                    ) : (
                      <Brain className="w-4 h-4 text-white" />
                    )}
                  </div>

                  {/* Message Content */}
                  <div
                    className={`p-4 rounded-2xl ${
                      message.type === 'user'
                        ? 'bg-[#D4A574] text-white rounded-br-sm'
                        : message.isInteractiveQuestion
                        ? 'bg-gradient-to-r from-[#F8F5F1] to-white border border-[#D4A574]/30 text-[#1E293B] rounded-bl-sm shadow-md'
                        : 'bg-white border border-[#C4BDB4]/20 text-[#1E293B] rounded-bl-sm shadow-sm'
                    }`}
                  >
                    <div className="prose prose-sm max-w-none">
                      {message.content.includes('**DOCUMENT_ANALYSIS_UI**') ? (
                        // Special handling for document analysis messages
                        <div>
                          {message.content.split('**DOCUMENT_ANALYSIS_UI**')[0].split('\\n').map((line, index) => (
                            <p key={index} className={`${
                              line.startsWith('•') || line.startsWith('**')
                                ? 'mb-2'
                                : 'mb-1'
                            } ${message.type === 'user' ? 'text-white' : 'text-[#1E293B]'}`}>
                              {line.includes('**') ? (
                                line.split('**').map((part, i) =>
                                  i % 2 === 1 ? <strong key={i}>{part}</strong> : part
                                )
                              ) : line.startsWith('•') ? (
                                <span className="flex items-start space-x-2">
                                  <span className={message.type === 'user' ? 'text-white/80' : 'text-[#D4A574]'}>•</span>
                                  <span>{line.substring(1).trim()}</span>
                                </span>
                              ) : line.startsWith('⚠️') ? (
                                <span className="flex items-start space-x-2 bg-orange-50 p-2 rounded-lg border-l-4 border-orange-200">
                                  <span className="text-orange-500">⚠️</span>
                                  <span className="text-orange-800">{line.substring(2).trim()}</span>
                                </span>
                              ) : (
                                line
                              )}
                            </p>
                          ))}

                          <DocumentAnalysisUI />

                          {message.content.split('**DOCUMENT_ANALYSIS_UI**')[1].split('\\n').map((line, index) => (
                            <p key={index} className={`${
                              line.startsWith('•') || line.startsWith('**')
                                ? 'mb-2'
                                : 'mb-1'
                            } ${message.type === 'user' ? 'text-white' : 'text-[#1E293B]'}`}>
                              {line.includes('**') ? (
                                line.split('**').map((part, i) =>
                                  i % 2 === 1 ? <strong key={i}>{part}</strong> : part
                                )
                              ) : line.startsWith('•') ? (
                                <span className="flex items-start space-x-2">
                                  <span className={message.type === 'user' ? 'text-white/80' : 'text-[#D4A574]'}>•</span>
                                  <span>{line.substring(1).trim()}</span>
                                </span>
                              ) : line.startsWith('⚠️') ? (
                                <span className="flex items-start space-x-2 bg-orange-50 p-2 rounded-lg border-l-4 border-orange-200">
                                  <span className="text-orange-500">⚠️</span>
                                  <span className="text-orange-800">{line.substring(2).trim()}</span>
                                </span>
                              ) : (
                                line
                              )}
                            </p>
                          ))}
                        </div>
                      ) : (
                        // Standard message rendering
                        message.content.split('\\n').map((line, index) => (
                          <p key={index} className={`${
                            line.startsWith('•') || line.startsWith('**')
                              ? 'mb-2'
                              : 'mb-1'
                          } ${message.type === 'user' ? 'text-white' : message.isInteractiveQuestion ? 'text-[#1E293B]' : 'text-[#1E293B]'}`}>
                            {line.includes('**') ? (
                              line.split('**').map((part, i) =>
                                i % 2 === 1 ? <strong key={i}>{part}</strong> : part
                              )
                            ) : line.startsWith('•') ? (
                              <span className="flex items-start space-x-2">
                                <span className={message.type === 'user' ? 'text-white/80' : 'text-[#D4A574]'}>•</span>
                                <span>{line.substring(1).trim()}</span>
                              </span>
                            ) : line.startsWith('⚠️') ? (
                              <span className="flex items-start space-x-2 bg-orange-50 p-2 rounded-lg border-l-4 border-orange-200">
                                <span className="text-orange-500">⚠️</span>
                                <span className="text-orange-800">{line.substring(2).trim()}</span>
                              </span>
                            ) : line.startsWith('🔍') || line.startsWith('❓') ? (
                              <span className={`${message.isInteractiveQuestion ? 'text-[#2A5D67] font-medium' : ''}`}>
                                {line}
                              </span>
                            ) : (
                              line
                            )}
                          </p>
                        ))
                      )}
                    </div>

                    {/* Client Context Cards - Show for AI messages with mentioned clients */}
                    {message.type === 'ai' && message.mentionedClients && message.mentionedClients.length > 0 && (
                      <div className="space-y-3">
                        {message.mentionedClients.map((client) => (
                          <ClientContextCard key={client.id} client={client} />
                        ))}
                      </div>
                    )}

                    {message.sources && message.sources.filter(source => source !== 'Sistema PratikoAI').length > 0 && (
                      <div className="mt-4 pt-3 border-t border-[#C4BDB4]/20">
                        <p className="text-xs font-medium mb-2 text-[#2A5D67]">Fonti normative:</p>
                        <div className="flex flex-wrap gap-2">
                          {message.sources.filter(source => source !== 'Sistema PratikoAI').map((source, i) => (
                            <span
                              key={i}
                              onClick={() => onNavigateToFonte(source)}
                              className="text-xs bg-[#F8F5F1] text-[#2A5D67] px-2 py-1 rounded-md border border-[#C4BDB4]/20 hover:bg-[#2A5D67] hover:text-white transition-colors cursor-pointer"
                            >
                              {source}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <span className={`text-xs mt-2 block ${
                      message.type === 'user' ? 'text-white/70' : 'text-[#C4BDB4]'
                    }`}>
                      {message.timestamp}
                      {message.isInteractiveQuestion && (
                        <span className="ml-2 inline-flex items-center space-x-1 text-[#D4A574]">
                          <Search className="w-3 h-3" />
                          <span>Domanda interattiva</span>
                        </span>
                      )}
                    </span>

                    {/* Feedback Buttons - Only for AI responses (not welcome message or interactive questions) */}
                    {message.type === 'ai' && message.id !== 'welcome' && !message.isInteractiveQuestion && (
                      <FeedbackButtons messageId={message.id} feedback={message.feedback} />
                    )}
                  </div>
                </div>
              </motion.div>
            ))}

            {/* Procedure Selector */}
            {showProcedureSelector && (
              <ProcedureSelector
                onClose={() => setShowProcedureSelector(false)}
                onSelectProcedure={(procedureId) => {
                  // Handle procedure selection - navigate to client selection
                  setShowProcedureSelector(false)
                  // You can add logic here to navigate to procedure page with client selection
                  const procedureMessage = `Ho selezionato la procedura. Ora scelgo il cliente...`
                  setMessages(prev => [...prev, {
                    id: `proc-${Date.now()}`,
                    type: 'user',
                    content: procedureMessage,
                    timestamp: new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
                  }])
                }}
              />
            )}

            {/* Client Action Picker */}
            <AnimatePresence>
              {showClientActionPicker && selectedClientForAction && (
                <ClientActionPicker
                  client={selectedClientForAction}
                  onSelectAction={(action) => {
                    if (action === 'profile') {
                      // Show full client profile
                      setShowClientProfile(true)
                      setShowClientActionPicker(false)
                    } else if (action === 'procedure') {
                      // Open procedure selector for this client
                      setShowProcedureSelector(true)
                      setShowClientActionPicker(false)
                    } else if (action === 'generic' || action === 'specific') {
                      // Set active context and focus input
                      setActiveClientContext(selectedClientForAction)
                      setShowClientActionPicker(false)
                      // Focus would happen here in real implementation
                    }
                  }}
                  onClose={() => {
                    setShowClientActionPicker(false)
                    setSelectedClientForAction(null)
                  }}
                />
              )}
            </AnimatePresence>

            {/* Client Profile Card */}
            <AnimatePresence>
              {showClientProfile && selectedClientForAction && (
                <ClientProfileCard
                  client={selectedClientForAction}
                  onClose={() => {
                    setShowClientProfile(false)
                    setSelectedClientForAction(null)
                  }}
                />
              )}
            </AnimatePresence>

            {isTyping && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className="bg-white border-t border-[#C4BDB4]/20 p-6">
          <div className="max-w-4xl mx-auto">
            {/* Input Mode Selector */}
            <InputModeSelector />

            {/* File Upload Area - now for all modes */}
            <AnimatePresence>
              <FileUploadArea />
            </AnimatePresence>

            {/* Active Client Context Indicator */}
            <AnimatePresence>
              {activeClientContext && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="mb-3 flex items-center justify-between bg-gradient-to-r from-[#2A5D67]/10 to-[#D4A574]/10 rounded-lg p-3 border border-[#2A5D67]/20"
                >
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-[#2A5D67] rounded-full animate-pulse" />
                    <span className="text-sm font-medium text-[#2A5D67]">
                      Contesto attivo: {activeClientContext.name}
                    </span>
                    <span className="text-xs text-[#1E293B]/60">
                      Le tue domande includeranno automaticamente i dati del cliente
                    </span>
                  </div>
                  <button
                    onClick={() => setActiveClientContext(null)}
                    className="text-[#1E293B]/60 hover:text-[#1E293B] transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Mentioned Clients Pills */}
            {mentionedClients.length > 0 && (
              <div className="mb-3 flex flex-wrap items-center gap-2 bg-[#F8F5F1] rounded-lg p-3 border border-[#C4BDB4]/20">
                <span className="text-sm text-[#1E293B]/60">Clienti menzionati:</span>
                <AnimatePresence>
                  {mentionedClients.map((client) => (
                    <ClientMentionPill
                      key={client.id}
                      client={client}
                      onRemove={() => {
                        setMentionedClients(prev => prev.filter(c => c.id !== client.id))
                      }}
                    />
                  ))}
                </AnimatePresence>
              </div>
            )}

            {/* Text Input with File Upload */}
            <div
              className={`relative ${
                isDragOver
                  ? 'ring-2 ring-[#2A5D67] ring-opacity-50 rounded-2xl'
                  : ''
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              {/* Command Popover */}
              <AnimatePresence>
                {showCommandPopover && (
                  <CommandPopover
                    onSelectCommand={(command) => {
                      if (command === 'procedura') {
                        setShowProcedureSelector(true)
                        setInputValue('')
                      }
                    }}
                    onClose={() => setShowCommandPopover(false)}
                  />
                )}
              </AnimatePresence>

              {/* Client Mention Autocomplete */}
              <ClientMentionAutocomplete
                searchQuery={mentionSearchQuery}
                onSelectClient={(client) => {
                  // Add client to mentioned clients
                  if (!mentionedClients.find(c => c.id === client.id)) {
                    setMentionedClients(prev => [...prev, client])
                  }
                  // Remove the @ mention from input
                  const atIndex = inputValue.lastIndexOf('@')
                  setInputValue(inputValue.substring(0, atIndex))
                  setShowClientMention(false)
                  setMentionSearchQuery('')

                  // Show action picker
                  setSelectedClientForAction(client)
                  setShowClientActionPicker(true)
                }}
                onClose={() => {
                  setShowClientMention(false)
                  setMentionSearchQuery('')
                }}
                isOpen={showClientMention}
              />

              <input
                type="text"
                value={inputValue}
                onChange={(e) => {
                  const value = e.target.value
                  setInputValue(value)

                  // Detect "/" command trigger
                  if (value === '/' || value.startsWith('/')) {
                    setShowCommandPopover(true)
                    setShowClientMention(false)
                  } else {
                    setShowCommandPopover(false)
                  }

                  // Detect "@" mention trigger
                  const atIndex = value.lastIndexOf('@')
                  if (atIndex !== -1) {
                    const afterAt = value.substring(atIndex + 1)
                    // Check if @ is at the start or preceded by a space
                    if (atIndex === 0 || value[atIndex - 1] === ' ') {
                      // Update search query immediately for real-time filtering
                      setMentionSearchQuery(afterAt)

                      // If autocomplete isn't shown yet, show it after 300ms delay
                      if (!showClientMention) {
                        // Clear existing timeout
                        if (mentionTimeout) {
                          clearTimeout(mentionTimeout)
                        }

                        // Set new timeout for 300ms
                        const timeout = setTimeout(() => {
                          setShowClientMention(true)
                        }, 300)

                        setMentionTimeout(timeout)
                      }
                    } else {
                      setShowClientMention(false)
                      setMentionSearchQuery('')
                    }
                  } else {
                    setShowClientMention(false)
                    setMentionSearchQuery('')
                    if (mentionTimeout) {
                      clearTimeout(mentionTimeout)
                    }
                  }
                }}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                onBlur={() => {
                  // Close command popover when input loses focus (with delay to allow clicks)
                  setTimeout(() => {
                    setShowCommandPopover(false)
                    setShowClientMention(false)
                  }, 200)
                }}
                placeholder={getCurrentPlaceholder()}
                className={`w-full text-[#1E293B] placeholder-[#C4BDB4] border outline-none rounded-2xl pl-6 pr-24 py-4 text-base focus:ring-2 focus:ring-[#2A5D67]/20 focus:border-[#2A5D67] transition-all ${
                  inputMode === 'interactive'
                    ? 'bg-gradient-to-r from-[#F8F5F1] to-white border-[#D4A574]/30'
                    : 'bg-[#F8F5F1] border-[#C4BDB4]/20'
                }`}
              />

              {/* File Upload Button */}
              <input
                type="file"
                accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.gif"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileUpload(e.target.files[0])
                  }
                }}
                className="hidden"
                id="file-upload"
              />

              <div className="absolute right-14 top-1/2 transform -translate-y-1/2">
                <motion.button
                  type="button"
                  onClick={() => document.getElementById('file-upload')?.click()}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-[#C4BDB4] hover:text-[#2A5D67] hover:bg-[#F8F5F1] transition-all"
                  title="Allega file"
                >
                  <Paperclip className="w-4 h-4" />
                </motion.button>
              </div>

              {/* Send Button */}
              <motion.button
                onClick={() => handleSend()}
                disabled={(!inputValue.trim() && !uploadedFile) || isTyping}
                whileHover={{ scale: (inputValue.trim() || uploadedFile) && !isTyping ? 1.05 : 1 }}
                whileTap={{ scale: (inputValue.trim() || uploadedFile) && !isTyping ? 0.95 : 1 }}
                className={`absolute right-2 top-1/2 transform -translate-y-1/2 w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
                  (inputValue.trim() || uploadedFile) && !isTyping
                    ? inputMode === 'interactive'
                      ? 'bg-gradient-to-r from-[#2A5D67] to-[#D4A574] text-white hover:from-[#1E293B] hover:to-[#C4A060] cursor-pointer shadow-lg'
                      : 'bg-[#2A5D67] text-white hover:bg-[#1E293B] cursor-pointer shadow-lg'
                    : 'bg-[#C4BDB4] text-white cursor-not-allowed'
                }`}
              >
                {inputMode === 'interactive' ? <Search className="w-5 h-5" /> : <Send className="w-5 h-5" />}
              </motion.button>

              {/* Drag Overlay */}
              <AnimatePresence>
                {isDragOver && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="absolute inset-0 bg-[#2A5D67]/5 border-2 border-dashed border-[#2A5D67] rounded-2xl flex items-center justify-center pointer-events-none"
                  >
                    <div className="text-center">
                      <Upload className="w-6 h-6 text-[#2A5D67] mx-auto mb-1" />
                      <p className="text-sm text-[#2A5D67] font-medium">Rilascia qui il file</p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Mode Description */}
            <div className="mt-3 space-y-3">
              <div className="flex items-center space-x-4">
                <p className={`text-sm ${
                  inputMode === 'interactive'
                    ? 'text-[#2A5D67] font-medium'
                    : 'text-[#1E293B]'
                }`}>
                  {inputModes.find(m => m.id === inputMode)?.description}
                  {inputMode === 'interactive' && (
                    <span className="ml-2 inline-flex items-center space-x-1 text-[#D4A574]">
                      <Zap className="w-3 h-3" />
                      <span className="text-xs">Innovativo</span>
                    </span>
                  )}
                </p>
                <div className="flex items-center space-x-1 text-sm text-[#1E293B]">
                  <Paperclip className="w-3 h-3" />
                  <span>Trascina qui i file o clicca l'icona • PDF, DOC, DOCX, JPG, PNG • Max 10MB</span>
                </div>
              </div>
              <p className="text-sm text-[#1E293B]">
                PratikoAI è alimentato dalla IA e potrebbe commettere errori. Verifica sempre le informazioni importanti.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Feedback Modal */}
      <AnimatePresence>
        {showFeedbackModal && <FeedbackModal />}
      </AnimatePresence>
    </div>
  )
}

// Use the conversations defined earlier
const mockChatHistory = Object.values(mockConversations)

// Sidebar Component
function SidebarContent({
  onLogout,
  onCloseSidebar,
  selectedConversationId,
  onConversationSelect,
  onNavigateToClients,
  onNavigateToComunicazioni,
  onNavigateToProcedure,
  onNavigateToDashboard,
  onNavigateToMatching
}: {
  onLogout: () => void,
  onCloseSidebar?: () => void,
  selectedConversationId?: string | null,
  onConversationSelect?: (conversationId: string) => void,
  onNavigateToClients?: () => void,
  onNavigateToComunicazioni?: () => void,
  onNavigateToProcedure?: () => void,
  onNavigateToDashboard?: () => void,
  onNavigateToMatching?: () => void
}) {
  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-[#C4BDB4]/20 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-[#2A5D67] rounded-xl flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-[#2A5D67]">PratikoAI</h2>
            </div>
          </div>
          {onCloseSidebar && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onCloseSidebar}
              className="lg:hidden text-[#C4BDB4] hover:text-[#2A5D67]"
            >
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 p-4 flex flex-col min-h-0 overflow-hidden">
        {/* Profile Section */}
        <div className="space-y-2 mb-6 flex-shrink-0">
          <Button variant="ghost" className="w-full justify-start text-[#1E293B] hover:bg-[#F8F5F1]">
            <User className="w-4 h-4 mr-3" />
            Profilo
          </Button>
          <Button
            variant="ghost"
            className="w-full justify-start text-[#1E293B] hover:bg-[#F8F5F1]"
            onClick={() => {
              if (onNavigateToDashboard) onNavigateToDashboard()
              if (onCloseSidebar) onCloseSidebar()
            }}
          >
            <BarChart3 className="w-4 h-4 mr-3" />
            Dashboard Analitica
          </Button>
          <Button
            variant="ghost"
            className="w-full justify-start text-[#1E293B] hover:bg-[#F8F5F1]"
            onClick={() => {
              if (onNavigateToMatching) onNavigateToMatching()
              if (onCloseSidebar) onCloseSidebar()
            }}
          >
            <Target className="w-4 h-4 mr-3" />
            Matching Normativo
          </Button>
          <Button
            variant="ghost"
            className="w-full justify-start text-[#1E293B] hover:bg-[#F8F5F1]"
            onClick={() => {
              if (onNavigateToClients) onNavigateToClients()
              if (onCloseSidebar) onCloseSidebar()
            }}
          >
            <Database className="w-4 h-4 mr-3" />
            Database Clienti
          </Button>
          <Button
            variant="ghost"
            className="w-full justify-start text-[#1E293B] hover:bg-[#F8F5F1]"
            onClick={() => {
              if (onNavigateToComunicazioni) onNavigateToComunicazioni()
              if (onCloseSidebar) onCloseSidebar()
            }}
          >
            <Mail className="w-4 h-4 mr-3" />
            Gestione Comunicazioni
          </Button>
          <Button
            variant="ghost"
            className="w-full justify-start text-[#1E293B] hover:bg-[#F8F5F1]"
            onClick={() => {
              if (onNavigateToProcedure) onNavigateToProcedure()
              if (onCloseSidebar) onCloseSidebar()
            }}
          >
            <ListChecks className="w-4 h-4 mr-3" />
            Procedure Interattive
          </Button>
          <Button variant="ghost" className="w-full justify-start text-[#1E293B] hover:bg-[#F8F5F1]">
            <Settings className="w-4 h-4 mr-3" />
            Impostazioni
          </Button>
          <Button
            onClick={onLogout}
            variant="ghost"
            className="w-full justify-start text-red-600 hover:bg-red-50 hover:text-red-700"
          >
            <LogOut className="w-4 h-4 mr-3" />
            Esci
          </Button>
        </div>

        {/* Navigation */}
        <nav className="space-y-2 mb-6 flex-shrink-0">
          <Button
            variant="ghost"
            className="w-full justify-start text-[#2A5D67] bg-[#F8F5F1] hover:bg-[#F8F5F1]"
          >
            <MessageSquare className="w-4 h-4 mr-3" />
            Chat Principale
          </Button>
        </nav>

        {/* Chat History Section */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex items-center justify-between mb-3 flex-shrink-0">
            <h3 className="text-sm font-medium text-[#2A5D67]">Cronologia</h3>
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-[#C4BDB4] hover:text-[#2A5D67]">
              <LogOut className="w-3 h-3" />
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 pr-2 min-h-0">
            {mockChatHistory.map((chat, index) => (
              <motion.div
                key={chat.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className={`group p-3 rounded-lg cursor-pointer transition-all hover:bg-[#F8F5F1] ${
                  selectedConversationId === chat.id ? 'bg-[#F8F5F1] border-l-2 border-[#2A5D67]' : ''
                }`}
                onClick={() => {
                  if (onConversationSelect) {
                    onConversationSelect(chat.id)
                  }
                  if (onCloseSidebar) onCloseSidebar()
                }}
              >
                <div className="flex items-start justify-between mb-1">
                  <h4 className={`text-sm font-medium line-clamp-1 group-hover:text-[#1E293B] ${
                    selectedConversationId === chat.id ? 'text-[#1E293B]' : 'text-[#2A5D67]'
                  }`}>
                    {chat.title}
                    {chat.type === 'interactive' && (
                      <span className="ml-2 inline-flex items-center">
                        <Search className="w-3 h-3 text-[#D4A574]" />
                      </span>
                    )}
                    {chat.type === 'complex' && (
                      <span className="ml-2 inline-flex items-center">
                        <Brain className="w-3 h-3 text-[#2A5D67]" />
                      </span>
                    )}
                    {chat.type === 'document' && (
                      <span className="ml-2 inline-flex items-center">
                        <FileCheck className="w-3 h-3 text-[#2A5D67]" />
                      </span>
                    )}
                    {chat.type === 'simple' && (
                      <span className="ml-2 inline-flex items-center">
                        <MessageSquare className="w-3 h-3 text-[#C4BDB4]" />
                      </span>
                    )}
                  </h4>
                  <span className="text-xs text-[#C4BDB4] ml-2 flex-shrink-0">
                    {new Date(chat.timestamp).toLocaleDateString('it-IT', {
                      month: 'short',
                      day: 'numeric'
                    })}
                  </span>
                </div>
                <p className="text-xs text-[#1E293B] opacity-70 line-clamp-2 leading-relaxed">
                  {chat.preview}
                </p>
                <div className="flex items-center mt-2 text-xs text-[#C4BDB4]">
                  <Clock className="w-3 h-3 mr-1" />
                  {new Date(chat.timestamp).toLocaleTimeString('it-IT', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                  {chat.type === 'interactive' && (
                    <span className="ml-2 inline-flex items-center space-x-1 text-[#D4A574]">
                      <span>•</span>
                      <span>Interattiva</span>
                    </span>
                  )}
                  {chat.type === 'complex' && (
                    <span className="ml-2 inline-flex items-center space-x-1 text-[#2A5D67]">
                      <span>•</span>
                      <span>Complessa</span>
                    </span>
                  )}
                  {chat.type === 'document' && (
                    <span className="ml-2 inline-flex items-center space-x-1 text-[#2A5D67]">
                      <span>•</span>
                      <span>Analisi documento</span>
                    </span>
                  )}
                  {chat.type === 'simple' && (
                    <span className="ml-2 inline-flex items-center space-x-1 text-[#C4BDB4]">
                      <span>•</span>
                      <span>Semplice</span>
                    </span>
                  )}
                </div>
              </motion.div>
            ))}
          </div>

          {/* Load More Button - Now at the bottom */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="pt-4 flex-shrink-0"
          >
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-[#C4BDB4] hover:text-[#2A5D67] hover:bg-[#F8F5F1] text-xs"
            >
              Carica altre conversazioni
            </Button>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
