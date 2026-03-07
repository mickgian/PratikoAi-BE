export type TipoSoggetto =
  | 'persona_fisica'
  | 'ditta_individuale'
  | 'societa_persone'
  | 'societa_capitali'
  | 'ente_no_profit';

export type RegimeFiscale = 'ordinario' | 'semplificato' | 'forfettario';

export type StatoTab = 'attivi' | 'prospect' | 'tutti';

export interface Cliente {
  id: string;
  denominazione: string;
  codiceFiscale: string;
  tipoSoggetto: TipoSoggetto;
  regimeFiscale: RegimeFiscale;
  codiceAteco: string;
  nDipendenti: number;
  tags: string[];
  statoCliente: 'attivo' | 'prospect';
}

export interface Immobile {
  id: string;
  tipologia: string;
  indirizzo: string;
  comune: string;
  renditaCatastale: string;
}

export interface ClientFormData {
  // Tab 1 - Anagrafica
  denominazione: string;
  codiceFiscale: string;
  partitaIva: string;
  tipoSoggetto: string;
  indirizzo: string;
  cap: string;
  comune: string;
  provincia: string;

  // Tab 2 - Dati Fiscali
  regimeFiscale: string;
  codiceAteco: string;
  dataInizioAttivita: string;
  posizioneAgenziaEntrate: string;
  haCartelleEsattoriali: boolean;

  // Tab 3 - Lavoro
  numeroDipendenti: string;
  ccnlApplicato: string;
  haApprendisti: boolean;
  haLavoratoriStagionali: boolean;

  // Tab 4 - Immobili
  immobili: Immobile[];

  // Tab 5 - Tags & Note
  tags: string[];
  note: string;
}

export interface ColumnMapping {
  ourField: string;
  yourColumn: string;
  required: boolean;
  confidence?: number; // 0.0–1.0 from auto-detection
  matchMethod?: 'exact_alias' | 'fuzzy' | 'data_pattern';
}
