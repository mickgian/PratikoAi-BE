import { AlertTriangle, CheckCircle, Mail, Target } from 'lucide-react';
import {
  ActivityItem,
  BarChartData,
  Deadline,
  MonthlyValueData,
  PieChartData,
} from '../types';

export const monthlyValueData: MonthlyValueData[] = [
  { month: 'Gen', valore: 4200, manuale: 8500 },
  { month: 'Feb', valore: 4800, manuale: 8700 },
  { month: 'Mar', valore: 5200, manuale: 9200 },
  { month: 'Apr', valore: 5800, manuale: 9800 },
  { month: 'Mag', valore: 6200, manuale: 10200 },
  { month: 'Giu', valore: 6800, manuale: 10800 },
];

export const regimeFiscaleData: PieChartData[] = [
  { name: 'Forfettario', value: 42, color: '#2A5D67' },
  { name: 'Semplificato', value: 28, color: '#D4A574' },
  { name: 'Ordinario', value: 18, color: '#1E293B' },
  { name: 'Altro', value: 12, color: '#94A3B8' },
];

export const atecoSectorData: BarChartData[] = [
  { sector: 'Servizi Prof.', count: 35 },
  { sector: 'Commercio', count: 28 },
  { sector: 'Manifattura', count: 18 },
  { sector: 'Edilizia', count: 15 },
  { sector: 'Altro', count: 12 },
];

export const clientStatusData: PieChartData[] = [
  { name: 'Attivi', value: 82, color: '#10B981' },
  { name: 'In attesa', value: 14, color: '#F59E0B' },
  { name: 'Inattivi', value: 4, color: '#EF4444' },
];

export const activityTimeline: ActivityItem[] = [
  {
    id: 'act_001',
    type: 'match',
    title: 'Nuovo match normativo',
    description: 'D.L. 142/2024 - Bonus Investimenti Sud → 3 clienti',
    timestamp: '2024-02-25T10:30:00',
    icon: Target,
    color: 'text-blue-600 bg-blue-50',
  },
  {
    id: 'act_002',
    type: 'communication',
    title: 'Comunicazione inviata',
    description: 'Aggiornamento IVA 2024 → Studio Legale Rossi',
    timestamp: '2024-02-25T09:15:00',
    icon: Mail,
    color: 'text-green-600 bg-green-50',
  },
  {
    id: 'act_003',
    type: 'procedura',
    title: 'Procedura completata',
    description: 'Apertura P.IVA → Commercialista Ferrari',
    timestamp: '2024-02-25T08:45:00',
    icon: CheckCircle,
    color: 'text-purple-600 bg-purple-50',
  },
  {
    id: 'act_004',
    type: 'deadline',
    title: 'Alert scadenza',
    description: 'Dichiarazione IVA trimestrale - 5 clienti',
    timestamp: '2024-02-25T08:00:00',
    icon: AlertTriangle,
    color: 'text-orange-600 bg-orange-50',
  },
  {
    id: 'act_005',
    type: 'match',
    title: 'Nuovo match normativo',
    description: 'Circolare INPS 23/2024 → 7 clienti',
    timestamp: '2024-02-24T16:20:00',
    icon: Target,
    color: 'text-blue-600 bg-blue-50',
  },
  {
    id: 'act_006',
    type: 'communication',
    title: 'Comunicazione inviata',
    description: 'Scadenza contributi → Immobiliare Milano',
    timestamp: '2024-02-24T15:00:00',
    icon: Mail,
    color: 'text-green-600 bg-green-50',
  },
];

export const upcomingDeadlines: Deadline[] = [
  {
    id: 'dead_001',
    title: 'Versamento IVA mensile',
    date: '2024-02-27',
    clientCount: 12,
    priority: 'high',
  },
  {
    id: 'dead_002',
    title: 'Presentazione F24',
    date: '2024-02-28',
    clientCount: 8,
    priority: 'high',
  },
  {
    id: 'dead_003',
    title: 'Dichiarazione INTRASTAT',
    date: '2024-03-01',
    clientCount: 5,
    priority: 'medium',
  },
  {
    id: 'dead_004',
    title: 'Invio CU dipendenti',
    date: '2024-03-02',
    clientCount: 15,
    priority: 'medium',
  },
];
