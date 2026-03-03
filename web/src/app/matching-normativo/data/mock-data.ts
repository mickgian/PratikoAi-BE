import { NormativeMatch } from '../types';

export const mockMatches: NormativeMatch[] = [
  {
    id: 'match_001',
    title: 'D.L. 142/2024 - Bonus Investimenti Sud 4.0',
    type: 'OPPORTUNITA',
    urgency: 'high',
    relevanceScore: 95,
    matchReason:
      'Cliente con sede operativa in Campania (Zona ZES), ATECO 62.01 (sviluppo software), investimenti pianificati 2024',
    actionRequired:
      "Verificare requisiti di accesso e preparare domanda entro la scadenza. Credito d'imposta fino al 45% per investimenti in beni strumentali.",
    deadline: '2024-03-31',
    sourceLink:
      'https://www.gazzettaufficiale.it/eli/id/2024/02/15/24G00142/sg',
    sourceName: 'Gazzetta Ufficiale Serie Generale n.38',
    publishDate: '2024-02-15',
    matchedAttributes: [
      'Localizzazione: Campania (ZES)',
      'Settore ATECO: 62.01',
      'Investimenti programmati',
    ],
    status: 'new',
  },
  {
    id: 'match_002',
    title: 'Circolare INPS 23/2024 - Nuovi massimali contributivi',
    type: 'NORMATIVA',
    urgency: 'critical',
    relevanceScore: 92,
    matchReason:
      'Cliente con dipendenti a tempo indeterminato, obbligo di adeguamento contributi dal 01/03/2024',
    actionRequired:
      'URGENTE: Aggiornare sistema paghe con i nuovi massimali. Ricalcolare contributi di febbraio. Comunicare ai dipendenti le variazioni in busta paga.',
    deadline: '2024-02-28',
    sourceLink:
      'https://www.inps.it/circolari/circolare-numero-23-del-12-02-2024',
    sourceName: 'INPS - Circolare n.23',
    publishDate: '2024-02-12',
    matchedAttributes: [
      'Dipendenti: 5 a tempo indeterminato',
      'Regime: Ordinario',
      'Obblighi contributivi attivi',
    ],
    status: 'new',
  },
  {
    id: 'match_003',
    title: 'Legge di Bilancio 2024 - Detrazioni ristrutturazioni',
    type: 'OPPORTUNITA',
    urgency: 'medium',
    relevanceScore: 78,
    matchReason:
      'Cliente proprietario immobile commerciale, possibile accesso a superbonus ristrutturazioni per efficientamento energetico',
    actionRequired:
      'Valutare interventi di efficientamento energetico. Nuove aliquote: 70% per spese sostenute nel 2024, scende al 65% nel 2025.',
    deadline: '2024-12-31',
    sourceLink:
      'https://www.agenziaentrate.gov.it/portale/web/guest/legge-bilancio-2024',
    sourceName: 'Agenzia delle Entrate',
    publishDate: '2024-01-01',
    matchedAttributes: [
      'Proprietà immobile commerciale',
      'Categoria catastale C/1',
      'Interesse dichiarato: sostenibilità',
    ],
    status: 'reviewed',
  },
  {
    id: 'match_004',
    title: 'Provvedimento ADE 45782/2024 - Fatturazione elettronica verso PA',
    type: 'SCADENZA',
    urgency: 'high',
    relevanceScore: 88,
    matchReason:
      'Cliente con contratti attivi verso enti pubblici, nuovo obbligo di split payment dal 01/04/2024',
    actionRequired:
      'Verificare tutti i contratti PA attivi. Aggiornare software fatturazione per gestione automatica split payment. Formare personale amministrativo.',
    deadline: '2024-03-25',
    sourceLink:
      'https://www.agenziaentrate.gov.it/portale/provvedimento-45782-2024',
    sourceName: 'Agenzia delle Entrate',
    publishDate: '2024-02-10',
    matchedAttributes: [
      'Clienti PA: 3 attivi',
      'Fatturato PA: 35% del totale',
      'Software: Fatturazione elettronica',
    ],
    status: 'new',
  },
  {
    id: 'match_005',
    title: 'Decreto MEF 18/2024 - Nuove regole compensazione crediti IVA',
    type: 'NORMATIVA',
    urgency: 'medium',
    relevanceScore: 71,
    matchReason:
      'Cliente con credito IVA trimestrale superiore a €5.000, nuove procedure di verifica preventiva',
    actionRequired:
      'Predisporre documentazione aggiuntiva per compensazione crediti IVA. Richiesta visto di conformità per importi superiori a €5.000.',
    deadline: '2024-03-15',
    sourceLink: 'https://www.mef.gov.it/decreti/decreto-18-2024',
    sourceName: 'Ministero Economia e Finanze',
    publishDate: '2024-02-05',
    matchedAttributes: [
      'Credito IVA trimestrale: €7.200',
      'Regime IVA: Ordinario',
      'Trimestrale: Attivo',
    ],
    status: 'new',
  },
  {
    id: 'match_006',
    title: 'Comunicazione Agenzia Entrate - Privacy e GDPR per professionisti',
    type: 'NORMATIVA',
    urgency: 'informational',
    relevanceScore: 65,
    matchReason:
      'Cliente con attività professionale, aggiornamento linee guida trattamento dati clienti',
    actionRequired:
      'Informativa: Revisione delle linee guida sul trattamento dati. Consigliato aggiornamento informativa privacy clienti entro 6 mesi.',
    sourceLink:
      'https://www.agenziaentrate.gov.it/portale/privacy-professionisti',
    sourceName: 'Agenzia delle Entrate',
    publishDate: '2024-01-20',
    matchedAttributes: [
      'Attività: Libero professionista',
      'Gestione dati clienti',
      'Privacy: GDPR compliance',
    ],
    status: 'reviewed',
  },
  {
    id: 'match_007',
    title: 'D.L. 156/2024 - Proroga termini dichiarazione redditi',
    type: 'SCADENZA',
    urgency: 'informational',
    relevanceScore: 82,
    matchReason:
      'Proroga automatica al 15 ottobre 2024 per dichiarazione dei redditi',
    actionRequired:
      'Informare il cliente della proroga. Riprogrammare scadenze interne di studio. Nessuna azione immediata richiesta.',
    deadline: '2024-10-15',
    sourceLink: 'https://www.agenziaentrate.gov.it/portale/decreto-156-2024',
    sourceName: 'Agenzia delle Entrate',
    publishDate: '2024-02-18',
    matchedAttributes: [
      'Soggetto: Persona fisica',
      'Dichiarazione: Modello 730/2024',
      'Scadenza originaria: 30/09',
    ],
    status: 'handled',
  },
];
