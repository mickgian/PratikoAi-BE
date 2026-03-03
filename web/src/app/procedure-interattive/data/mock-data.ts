import type { Procedura, Client } from '../types';

export const mockProcedure: Procedura[] = [
  {
    id: 'proc_001',
    title: 'Apertura Partita IVA',
    description: "Procedura completa per l'apertura di una nuova Partita IVA",
    category: 'Fiscale',
    totalSteps: 7,
    completedSteps: 3,
    progress: 42,
    lastUpdated: '2024-02-24T15:30:00',
    steps: [
      {
        id: 'step_001',
        number: 1,
        title: 'Raccolta documenti identificativi',
        description:
          'Raccogliere tutta la documentazione necessaria per identificare il richiedente',
        completed: true,
        checklist: [
          { id: 'cl_001', text: "Carta d'identità valida", completed: true },
          { id: 'cl_002', text: 'Codice fiscale', completed: true },
          { id: 'cl_003', text: 'Certificato di residenza', completed: true },
        ],
        documents: [
          {
            id: 'doc_001',
            name: "Carta d'identità",
            required: true,
            verified: true,
            verifiedDate: '2024-02-20',
            verificationNote: 'Ricevuto via email dal cliente',
          },
          {
            id: 'doc_002',
            name: 'Codice fiscale',
            required: true,
            verified: true,
            verifiedDate: '2024-02-20',
          },
        ],
        notes: [
          {
            id: 'note_001',
            text: 'Documenti ricevuti via email dal cliente',
            date: '2024-02-20T10:00:00',
          },
        ],
      },
      {
        id: 'step_002',
        number: 2,
        title: 'Scelta del regime fiscale',
        description:
          "Determinare il regime fiscale più vantaggioso per l'attività",
        completed: true,
        checklist: [
          { id: 'cl_004', text: 'Analisi fatturato previsto', completed: true },
          {
            id: 'cl_005',
            text: 'Verifica requisiti regime forfettario',
            completed: true,
          },
          {
            id: 'cl_006',
            text: 'Confronto tra regimi disponibili',
            completed: true,
          },
        ],
        documents: [],
        notes: [
          {
            id: 'note_002',
            text: 'Il cliente rientra nei requisiti per il regime forfettario. Fatturato previsto: €35.000',
            date: '2024-02-21T14:00:00',
          },
        ],
      },
      {
        id: 'step_003',
        number: 3,
        title: 'Compilazione modulo AA9/12',
        description:
          'Compilare e verificare il modulo di dichiarazione di inizio attività',
        completed: false,
        checklist: [
          {
            id: 'cl_007',
            text: 'Inserimento dati anagrafici',
            completed: true,
          },
          { id: 'cl_008', text: 'Selezione codice ATECO', completed: true },
          {
            id: 'cl_009',
            text: 'Dichiarazione regime fiscale',
            completed: false,
          },
          { id: 'cl_010', text: 'Firma del modulo', completed: false },
        ],
        documents: [
          {
            id: 'doc_003',
            name: 'Modulo AA9/12 bozza',
            required: true,
            verified: true,
            verifiedDate: '2024-02-23',
          },
          {
            id: 'doc_004',
            name: 'Modulo AA9/12 firmato',
            required: true,
            verified: false,
          },
          {
            id: 'doc_005',
            name: 'Visura camerale',
            required: false,
            verified: false,
          },
          {
            id: 'doc_006',
            name: 'Autocertificazione requisiti',
            required: true,
            verified: false,
          },
          {
            id: 'doc_007',
            name: 'Certificato CCIAA',
            required: false,
            verified: false,
          },
        ],
        notes: [],
      },
      {
        id: 'step_004',
        number: 4,
        title: 'Iscrizione INPS',
        description:
          "Procedere con l'iscrizione alla gestione INPS appropriata",
        completed: false,
        checklist: [
          {
            id: 'cl_011',
            text: 'Verifica gestione INPS di competenza',
            completed: false,
          },
          {
            id: 'cl_012',
            text: 'Compilazione domanda iscrizione',
            completed: false,
          },
          { id: 'cl_013', text: 'Invio documentazione', completed: false },
        ],
        documents: [
          {
            id: 'doc_008',
            name: 'Domanda iscrizione INPS',
            required: true,
            verified: false,
          },
        ],
        notes: [],
      },
      {
        id: 'step_005',
        number: 5,
        title: 'Comunicazione Unica (ComUnica)',
        description:
          "Invio della Comunicazione Unica telematica all'Agenzia delle Entrate",
        completed: false,
        checklist: [
          {
            id: 'cl_014',
            text: 'Preparazione file telematico',
            completed: false,
          },
          {
            id: 'cl_015',
            text: 'Invio tramite Entratel/Fisconline',
            completed: false,
          },
          {
            id: 'cl_016',
            text: 'Ricezione ricevuta di protocollazione',
            completed: false,
          },
        ],
        documents: [],
        notes: [],
      },
      {
        id: 'step_006',
        number: 6,
        title: 'Apertura PEC e firma digitale',
        description: 'Attivazione casella PEC e certificato di firma digitale',
        completed: false,
        checklist: [
          { id: 'cl_017', text: 'Richiesta casella PEC', completed: false },
          { id: 'cl_018', text: 'Richiesta firma digitale', completed: false },
          {
            id: 'cl_019',
            text: 'Test funzionamento servizi',
            completed: false,
          },
        ],
        documents: [],
        notes: [],
      },
      {
        id: 'step_007',
        number: 7,
        title: 'Configurazione fatturazione elettronica',
        description: 'Setup del sistema di fatturazione elettronica',
        completed: false,
        checklist: [
          {
            id: 'cl_020',
            text: 'Scelta software fatturazione',
            completed: false,
          },
          { id: 'cl_021', text: 'Configurazione SdI', completed: false },
          {
            id: 'cl_022',
            text: 'Test invio fattura di prova',
            completed: false,
          },
        ],
        documents: [],
        notes: [],
      },
    ],
  },
  {
    id: 'proc_002',
    title: 'Assunzione Dipendente',
    description: "Procedura completa per l'assunzione di un nuovo dipendente",
    category: 'Lavoro',
    totalSteps: 6,
    completedSteps: 1,
    progress: 16,
    steps: [],
  },
  {
    id: 'proc_003',
    title: 'Chiusura Bilancio',
    description: 'Procedura per la chiusura e deposito del bilancio annuale',
    category: 'Contabilità',
    totalSteps: 8,
    completedSteps: 5,
    progress: 62,
    steps: [],
  },
  {
    id: 'proc_004',
    title: 'Dichiarazione IVA',
    description:
      'Procedura per la compilazione e invio della dichiarazione IVA annuale',
    category: 'Fiscale',
    totalSteps: 5,
    completedSteps: 0,
    progress: 0,
    steps: [],
  },
  {
    id: 'proc_005',
    title: 'Richiesta DURC',
    description:
      'Procedura per la richiesta del Documento Unico di Regolarità Contributiva',
    category: 'Previdenziale',
    totalSteps: 4,
    completedSteps: 4,
    progress: 100,
    steps: [],
  },
  {
    id: 'proc_006',
    title: "Cessione Credito d'Imposta",
    description: "Procedura per la cessione di crediti d'imposta",
    category: 'Fiscale',
    totalSteps: 6,
    completedSteps: 2,
    progress: 33,
    steps: [],
  },
];

export const mockClients: Client[] = [
  { id: 'cli_001', name: 'Studio Legale Rossi & Associati' },
  { id: 'cli_002', name: 'Immobiliare Milano SpA' },
  { id: 'cli_003', name: 'Consulenza Bianchi SRL' },
  { id: 'cli_004', name: 'Costruzioni Verdi Srl' },
  { id: 'cli_005', name: 'Commercialista Ferrari' },
];
