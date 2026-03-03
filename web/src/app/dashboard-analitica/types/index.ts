import { LucideIcon } from 'lucide-react';

export interface KPIData {
  clientiAttivi: number;
  oreRisparmiate: number;
  comunicazioniInviate: number;
  normativeMonitorate: number;
}

export interface MatchingStats {
  totalMatches: number;
  conversionRate: number;
  pendingReviews: number;
}

export interface ActivityItem {
  id: string;
  type: 'match' | 'communication' | 'procedura' | 'deadline';
  title: string;
  description: string;
  timestamp: string;
  icon: LucideIcon;
  color: string;
}

export interface Deadline {
  id: string;
  title: string;
  date: string;
  clientCount: number;
  priority: 'high' | 'medium' | 'low';
}

export interface MonthlyValueData {
  month: string;
  valore: number;
  manuale: number;
}

export interface PieChartData {
  name: string;
  value: number;
  color: string;
}

export interface BarChartData {
  sector: string;
  count: number;
}

export type Period = 'week' | 'month' | 'year';
