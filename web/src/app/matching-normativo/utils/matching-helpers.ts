import { Clock, FileText, TrendingUp } from 'lucide-react';
import { UrgencyLevel, MatchType } from '../types';

export interface UrgencyColors {
  bg: string;
  border: string;
  text: string;
  badge: string;
  icon: string;
}

export function getUrgencyColor(urgency: UrgencyLevel): UrgencyColors {
  switch (urgency) {
    case 'critical':
      return {
        bg: 'bg-red-50',
        border: 'border-red-300',
        text: 'text-red-700',
        badge: 'bg-red-100 text-red-700 border-red-300',
        icon: 'text-red-600',
      };
    case 'high':
      return {
        bg: 'bg-orange-50',
        border: 'border-orange-300',
        text: 'text-orange-700',
        badge: 'bg-orange-100 text-orange-700 border-orange-300',
        icon: 'text-orange-600',
      };
    case 'medium':
      return {
        bg: 'bg-yellow-50',
        border: 'border-yellow-300',
        text: 'text-yellow-700',
        badge: 'bg-yellow-100 text-yellow-700 border-yellow-300',
        icon: 'text-yellow-600',
      };
    case 'informational':
      return {
        bg: 'bg-green-50',
        border: 'border-green-300',
        text: 'text-green-700',
        badge: 'bg-green-100 text-green-700 border-green-300',
        icon: 'text-green-600',
      };
  }
}

export function getUrgencyLabel(urgency: UrgencyLevel): string {
  switch (urgency) {
    case 'critical':
      return 'Critica';
    case 'high':
      return 'Alta';
    case 'medium':
      return 'Media';
    case 'informational':
      return 'Informativa';
  }
}

export function getTypeIcon(type: MatchType) {
  switch (type) {
    case 'NORMATIVA':
      return FileText;
    case 'SCADENZA':
      return Clock;
    case 'OPPORTUNITA':
      return TrendingUp;
  }
}

export function getTypeColor(type: MatchType): string {
  switch (type) {
    case 'NORMATIVA':
      return 'bg-blue-100 text-blue-700 border-blue-300';
    case 'SCADENZA':
      return 'bg-purple-100 text-purple-700 border-purple-300';
    case 'OPPORTUNITA':
      return 'bg-green-100 text-green-700 border-green-300';
  }
}

export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('it-IT', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

export function getDaysUntil(dateString: string): number {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  return Math.ceil(diffMs / 86400000);
}
