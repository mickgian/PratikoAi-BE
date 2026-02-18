/**
 * Italian Localization for PratikoAI Chat
 * Complete localization including formatting, messages, and error handling
 */

// Main interface strings
export const STRINGS = {
  // Welcome and empty states
  WELCOME: {
    TITLE: 'Benvenuto in PratikoAI',
    SUBTITLE: 'Inizia una conversazione per ricevere assistenza fiscale',
    EMPTY_SESSION_TITLE: 'Sessione Vuota',
    EMPTY_SESSION_SUBTITLE: 'Inizia scrivendo il tuo primo messaggio in questa sessione',
    START_CONVERSATION: 'Inizia conversazione'
  },
  
  // Input area
  INPUT: {
    PLACEHOLDER_SIMPLE: 'Scrivi la tua domanda fiscale...',
    PLACEHOLDER_COMPLEX: 'Descrivi la tua situazione fiscale in dettaglio...',
    PLACEHOLDER_INTERACTIVE: 'Fammi una domanda specifica...',
    PLACEHOLDER_DOCUMENT: 'Carica un documento o descrivi il problema...',
    SEND_BUTTON: 'Invia',
    SENDING: 'Invio...',
    DISABLED_STREAMING: 'Attendere la risposta...'
  },
  
  // Messages and streaming
  MESSAGES: {
    USER_LABEL: 'Il tuo messaggio',
    AI_LABEL: 'Risposta di PratikoAI',
    AI_LABEL_PROCESSING: 'Risposta di PratikoAI (in elaborazione)',
    TYPING_INDICATOR: 'PratikoAI sta scrivendo...',
    TIMESTAMP_ARIA: 'Inviato alle',
    MESSAGE_ARIA: 'Messaggio da'
  },
  
  // Loading states
  LOADING: {
    HISTORY: 'Caricamento conversazione...',
    SESSION: 'Caricamento sessione...',
    SENDING: 'Invio messaggio...',
    AI_THINKING: 'PratikoAI sta elaborando...',
    CONNECTING: 'Connessione in corso...'
  },
  
  // Errors
  ERRORS: {
    NETWORK: 'Errore di connessione. Controlla la tua connessione internet.',
    TIMEOUT: 'Il server non ha risposto entro il tempo limite.',
    SERVER_ERROR: 'Errore del server. Riprova tra qualche momento.',
    RATE_LIMIT: 'Hai raggiunto il limite di messaggi. Riprova più tardi.',
    EMPTY_RESPONSE: 'Il server non ha fornito alcuna risposta.',
    MALFORMED_RESPONSE: 'Risposta del server non valida.',
    SESSION_ERROR: 'Errore nel caricamento della sessione.',
    HISTORY_ERROR: 'Errore nel caricamento della conversazione',
    GENERIC_ERROR: 'Si è verificato un errore imprevisto.',
    STREAMING_ERROR: 'Errore durante la ricezione della risposta.',
    CONNECTION_LOST: 'Connessione persa durante la comunicazione.'
  },
  
  // Actions
  ACTIONS: {
    RETRY: 'Riprova',
    RELOAD: 'Ricarica la pagina',
    CANCEL: 'Annulla',
    CONTINUE: 'Continua',
    CLOSE: 'Chiudi',
    UNDERSTAND: 'Ho capito',
    RECONNECT: 'Riconnetti',
    INTERRUPT: 'Interrompi',
    TRY_AGAIN: 'Riprova la domanda'
  },
  
  // Status messages
  STATUS: {
    ONLINE: 'Online',
    OFFLINE: 'Offline',
    CONNECTING: 'Connessione...',
    CONNECTED: 'Connesso',
    DISCONNECTED: 'Disconnesso',
    CONNECTION_RESTORED: 'Connessione ripristinata',
    CONNECTION_LOST: 'Connessione assente'
  },
  
  // Time and dates
  TIME: {
    JUST_NOW: 'Ora',
    MINUTES_AGO: (n: number) => `${n} minut${n === 1 ? 'o' : 'i'} fa`,
    HOURS_AGO: (n: number) => `${n} or${n === 1 ? 'a' : 'e'} fa`,
    DAYS_AGO: (n: number) => `${n} giorn${n === 1 ? 'o' : 'i'} fa`,
    ESTIMATED_TIME: (seconds: number) => 
      seconds < 60 ? `~${seconds} secondi` : `~${Math.ceil(seconds / 60)} minuti`,
    READING_TIME: (minutes: number) => `${minutes} min di lettura`
  },
  
  // Content indicators
  CONTENT: {
    DETAILED_RESPONSE: 'Risposta dettagliata',
    VERY_DETAILED_RESPONSE: 'Risposta molto dettagliata',
    LONG_CONTENT_WARNING: 'Contenuto lungo',
    CHARACTERS_COUNT: (count: number) => `${count} caratteri`,
    WORDS_COUNT: (count: number) => `${count} parole`
  },
  
  // Sidebar and navigation
  SIDEBAR: {
    NEW_CHAT: 'Nuova Chat',
    RECENT_CHATS: 'Chat Recenti',
    SETTINGS: 'Impostazioni',
    HELP: 'Aiuto',
    SESSION_NAME: 'Nome Sessione'
  },
  
  // Input modes
  INPUT_MODES: {
    SIMPLE: 'Semplice',
    COMPLEX: 'Complessa',
    INTERACTIVE: 'Interattiva',
    DOCUMENT: 'Documento'
  }
} as const

// Number formatting for Italian locale
export const formatNumber = (num: number, options?: Intl.NumberFormatOptions): string => {
  return new Intl.NumberFormat('it-IT', options).format(num)
}

// Currency formatting
export const formatCurrency = (amount: number, currency: string = 'EUR'): string => {
  return new Intl.NumberFormat('it-IT', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount)
}

// Percentage formatting  
export const formatPercentage = (value: number): string => {
  return new Intl.NumberFormat('it-IT', {
    style: 'percent',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(value / 100)
}

// Time formatting
export const formatTime = (date: Date): string => {
  return new Intl.DateTimeFormat('it-IT', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date)
}

// Date formatting
export const formatDate = (date: Date): string => {
  return new Intl.DateTimeFormat('it-IT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  }).format(date)
}

// Relative time formatting
export const formatRelativeTime = (date: Date): string => {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMinutes = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)
  
  if (diffMinutes < 1) {
    return STRINGS.TIME.JUST_NOW
  } else if (diffMinutes < 60) {
    return STRINGS.TIME.MINUTES_AGO(diffMinutes)
  } else if (diffHours < 24) {
    return STRINGS.TIME.HOURS_AGO(diffHours)
  } else {
    return STRINGS.TIME.DAYS_AGO(diffDays)
  }
}

// Pluralization helper
export const pluralize = (count: number, singular: string, plural: string): string => {
  return count === 1 ? singular : plural
}

// Tax calculation formatting (specific to Italian tax system)
export const TAX_STRINGS = {
  IRPEF: 'IRPEF',
  IRES: 'IRES', 
  IVA: 'IVA',
  IRAP: 'IRAP',
  TAX_BRACKETS: 'Scaglioni Fiscali',
  TAX_RATE: 'Aliquota',
  TAXABLE_INCOME: 'Reddito Imponibile',
  GROSS_INCOME: 'Reddito Lordo',
  NET_INCOME: 'Reddito Netto',
  DEDUCTIONS: 'Detrazioni',
  CALCULATION: 'Calcolo',
  RESULT: 'Risultato',
  TOTAL: 'Totale'
} as const

// Legal references formatting
export const LEGAL_STRINGS = {
  LAW: 'Legge',
  DECREE: 'Decreto',
  ARTICLE: 'Articolo',
  PARAGRAPH: 'Comma',
  LETTER: 'Lettera',
  REFERENCE: 'Riferimento',
  REGULATION: 'Regolamento',
  CIRCULAR: 'Circolare',
  RESOLUTION: 'Risoluzione'
} as const

// Error message details for better user experience
export const ERROR_DETAILS = {
  NETWORK_ERROR: {
    title: 'Errore di Rete',
    description: 'Impossibile connettersi al server. Controlla la tua connessione internet e riprova.',
    suggestions: [
      'Verifica la connessione internet',
      'Prova a ricaricare la pagina',
      'Controlla le impostazioni del firewall'
    ]
  },
  TIMEOUT_ERROR: {
    title: 'Timeout',
    description: 'Il server non ha risposto entro il tempo limite.',
    suggestions: [
      'Riprova con una domanda più semplice',
      'Attendi qualche momento e riprova',
      'Controlla la stabilità della connessione'
    ]
  },
  RATE_LIMIT_ERROR: {
    title: 'Limite Raggiunto',
    description: 'Hai raggiunto il limite di messaggi per questo periodo.',
    suggestions: [
      'Attendi prima di inviare altri messaggi',
      'Prova a unire più domande in un unico messaggio',
      'Contatta il supporto per aumentare i limiti'
    ]
  }
} as const

// Accessibility strings
export const A11Y_STRINGS = {
  CHAT_AREA: 'Area messaggi della chat',
  USER_MESSAGE: 'Il tuo messaggio',
  AI_MESSAGE: 'Risposta di PratikoAI',
  TYPING_INDICATOR: 'PratikoAI sta scrivendo una risposta',
  SEND_BUTTON: 'Invia messaggio',
  INPUT_FIELD: 'Campo di testo per scrivere il messaggio',
  SCROLL_TO_BOTTOM: 'Scorri fino in fondo',
  MESSAGE_OPTIONS: 'Opzioni messaggio',
  TIMESTAMP: 'Orario di invio'
} as const