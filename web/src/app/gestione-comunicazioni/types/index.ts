export type CommunicationStatus =
  | 'bozza'
  | 'in_revisione'
  | 'approvata'
  | 'inviata';

export type CommunicationChannel = 'email' | 'whatsapp';

export type FilterTab =
  | 'tutte'
  | 'bozze'
  | 'in_revisione'
  | 'approvate'
  | 'inviate';

export interface Communication {
  id: string;
  subject: string;
  clientName: string;
  clientId: string;
  channel: CommunicationChannel;
  status: CommunicationStatus;
  normativaReference: string;
  createdDate: string;
  body: string;
  template?: string;
}

export interface Client {
  id: string;
  name: string;
}

export interface Template {
  id: string;
  name: string;
}

export interface ComunicazioniStats {
  bozze: number;
  in_revisione: number;
  approvate: number;
  inviate: number;
}
