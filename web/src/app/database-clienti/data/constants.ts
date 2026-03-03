import type { ClientFormData, TipoSoggetto, RegimeFiscale } from '../types';

export const tipoSoggettoLabels: Record<TipoSoggetto, string> = {
  persona_fisica: 'Persona Fisica',
  ditta_individuale: 'Ditta Individuale',
  societa_persone: 'Società di Persone',
  societa_capitali: 'Società di Capitali',
  ente_no_profit: 'Ente No Profit',
};

export const regimeFiscaleLabels: Record<RegimeFiscale, string> = {
  ordinario: 'Ordinario',
  semplificato: 'Semplificato',
  forfettario: 'Forfettario',
};

export const initialFormData: ClientFormData = {
  denominazione: '',
  codiceFiscale: '',
  partitaIva: '',
  tipoSoggetto: '',
  indirizzo: '',
  cap: '',
  comune: '',
  provincia: '',
  regimeFiscale: '',
  codiceAteco: '',
  dataInizioAttivita: '',
  posizioneAgenziaEntrate: '',
  haCartelleEsattoriali: false,
  numeroDipendenti: '0',
  ccnlApplicato: '',
  haApprendisti: false,
  haLavoratoriStagionali: false,
  immobili: [],
  tags: [],
  note: '',
};

export const ourFields = [
  {
    value: 'denominazione',
    label: 'Denominazione / Ragione Sociale',
    required: true,
  },
  { value: 'codiceFiscale', label: 'Codice Fiscale', required: true },
  { value: 'partitaIva', label: 'Partita IVA', required: false },
  { value: 'tipoSoggetto', label: 'Tipo Soggetto', required: true },
  { value: 'regimeFiscale', label: 'Regime Fiscale', required: true },
  { value: 'codiceAteco', label: 'Codice ATECO', required: true },
  { value: 'indirizzo', label: 'Indirizzo', required: false },
  { value: 'cap', label: 'CAP', required: false },
  { value: 'comune', label: 'Comune', required: false },
  { value: 'provincia', label: 'Provincia', required: false },
  { value: 'numeroDipendenti', label: 'Numero Dipendenti', required: false },
  { value: 'ccnlApplicato', label: 'CCNL Applicato', required: false },
];
