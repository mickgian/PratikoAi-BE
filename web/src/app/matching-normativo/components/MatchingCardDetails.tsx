'use client';

import { motion } from 'motion/react';
import {
  Calendar,
  CheckCircle,
  Check,
  ExternalLink,
  FileText,
  Mail,
  Target,
  XCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { NormativeMatch } from '../types';
import { formatDate, getDaysUntil } from '../utils/matching-helpers';

interface MatchingCardDetailsProps {
  match: NormativeMatch;
  onGenerateCommunication?: (matchIds: string[]) => void;
  onMarkAsHandled?: (matchIds: string[]) => void;
  onIgnore?: (matchIds: string[]) => void;
}

export function MatchingCardDetails({
  match,
  onGenerateCommunication,
  onMarkAsHandled,
  onIgnore,
}: MatchingCardDetailsProps) {
  const daysUntil = match.deadline ? getDaysUntil(match.deadline) : null;

  const formatDaysLabel = (days: number): string => {
    if (days === 0) return 'Oggi!';
    if (days === 1) return 'Domani';
    if (days > 0) return `Tra ${days} giorni`;
    return `Scaduto da ${Math.abs(days)} giorni`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="border-t border-[#C4BDB4]/30 pt-4 mt-4 space-y-4"
    >
      <div>
        <h4 className="font-semibold text-[#2A5D67] mb-2 flex items-center">
          <CheckCircle className="w-4 h-4 mr-2" />
          Azione Richiesta
        </h4>
        <p className="text-sm text-[#1E293B] bg-white/50 p-3 rounded-lg">
          {match.actionRequired}
        </p>
      </div>

      {match.deadline && daysUntil !== null && (
        <div>
          <h4 className="font-semibold text-[#2A5D67] mb-2 flex items-center">
            <Calendar className="w-4 h-4 mr-2" />
            Scadenza
          </h4>
          <p className="text-sm text-[#1E293B]">
            {formatDate(match.deadline)}
            <span className="ml-2 text-[#94A3B8]">
              ({formatDaysLabel(daysUntil)})
            </span>
          </p>
        </div>
      )}

      {match.matchedAttributes.length > 0 && (
        <div>
          <h4 className="font-semibold text-[#2A5D67] mb-2 flex items-center">
            <Target className="w-4 h-4 mr-2" />
            Attributi Matchati
          </h4>
          <div className="flex flex-wrap gap-2">
            {match.matchedAttributes.map((attr, idx) => (
              <Badge
                key={idx}
                variant="outline"
                className="bg-white/50 border-[#2A5D67] text-[#2A5D67]"
              >
                {attr}
              </Badge>
            ))}
          </div>
        </div>
      )}

      <div>
        <h4 className="font-semibold text-[#2A5D67] mb-2 flex items-center">
          <FileText className="w-4 h-4 mr-2" />
          Fonte
        </h4>
        <div className="flex items-center justify-between bg-white/50 p-3 rounded-lg">
          <div>
            {match.sourceName && (
              <p className="text-sm font-medium text-[#1E293B]">
                {match.sourceName}
              </p>
            )}
            <p className="text-xs text-[#94A3B8]">
              Pubblicato il {formatDate(match.publishDate)}
            </p>
          </div>
          {match.sourceLink && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => window.open(match.sourceLink, '_blank')}
              className="border-[#2A5D67] text-[#2A5D67] hover:bg-[#2A5D67] hover:text-white"
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              Apri Fonte
            </Button>
          )}
        </div>
      </div>

      <div className="flex items-center space-x-2 pt-2">
        <Button
          size="sm"
          className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
          onClick={() => onGenerateCommunication?.([match.id])}
        >
          <Mail className="w-4 h-4 mr-2" />
          <span className="font-bold">Genera Comunicazione</span>
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="border-[#2A5D67] text-[#2A5D67]"
          onClick={() => onMarkAsHandled?.([match.id])}
        >
          <Check className="w-4 h-4 mr-2" />
          <span className="font-bold">Gestito</span>
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="border-[#94A3B8] text-[#94A3B8]"
          onClick={() => onIgnore?.([match.id])}
        >
          <XCircle className="w-4 h-4 mr-2" />
          <span className="font-bold">Ignora</span>
        </Button>
      </div>
    </motion.div>
  );
}
