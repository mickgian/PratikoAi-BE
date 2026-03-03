'use client';

import { motion, AnimatePresence } from 'motion/react';
import { AlertTriangle, Calendar, ChevronDown, ChevronUp } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardHeader } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { NormativeMatch } from '../types';
import {
  getUrgencyColor,
  getUrgencyLabel,
  getTypeColor,
  getTypeIcon,
  getDaysUntil,
} from '../utils/matching-helpers';
import { MatchingRelevanceScore } from './MatchingRelevanceScore';
import { MatchingCardDetails } from './MatchingCardDetails';

interface MatchingCardProps {
  match: NormativeMatch;
  index: number;
  isExpanded: boolean;
  isSelected: boolean;
  onToggleExpanded: (id: string) => void;
  onToggleSelected: (id: string) => void;
  onGenerateCommunication?: (matchIds: string[]) => void;
  onMarkAsHandled?: (matchIds: string[]) => void;
  onIgnore?: (matchIds: string[]) => void;
}

export function MatchingCard({
  match,
  index,
  isExpanded,
  isSelected,
  onToggleExpanded,
  onToggleSelected,
  onGenerateCommunication,
  onMarkAsHandled,
  onIgnore,
}: MatchingCardProps) {
  const urgencyColors = getUrgencyColor(match.urgency);
  const TypeIcon = getTypeIcon(match.type);
  const daysUntil = match.deadline ? getDaysUntil(match.deadline) : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      <Card
        className={`border-2 ${isSelected ? 'border-[#2A5D67] shadow-lg' : urgencyColors.border} ${urgencyColors.bg} transition-all`}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start space-x-3">
            <Checkbox
              id={`match-${match.id}`}
              checked={isSelected}
              onCheckedChange={() => onToggleSelected(match.id)}
              className="mt-1"
            />

            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <Badge className={`${getTypeColor(match.type)} border`}>
                      <TypeIcon className="w-3 h-3 mr-1" />
                      {match.type}
                    </Badge>
                    <Badge className={`${urgencyColors.badge} border`}>
                      <AlertTriangle className="w-3 h-3 mr-1" />
                      {getUrgencyLabel(match.urgency)}
                    </Badge>
                    {match.deadline && daysUntil !== null && daysUntil <= 7 && (
                      <Badge className="bg-red-100 text-red-700 border-red-300 border">
                        <Calendar className="w-3 h-3 mr-1" />
                        {daysUntil === 0
                          ? 'Oggi!'
                          : daysUntil === 1
                            ? 'Domani'
                            : `${daysUntil} giorni`}
                      </Badge>
                    )}
                  </div>
                  <h3 className="font-bold text-[#2A5D67] text-lg mb-1">
                    {match.title}
                  </h3>
                  <p className="text-sm text-[#1E293B] mb-2">
                    {match.matchReason}
                  </p>
                </div>

                <div className="ml-4">
                  <MatchingRelevanceScore score={match.relevanceScore} />
                </div>
              </div>

              <AnimatePresence>
                {isExpanded && (
                  <MatchingCardDetails
                    match={match}
                    onGenerateCommunication={onGenerateCommunication}
                    onMarkAsHandled={onMarkAsHandled}
                    onIgnore={onIgnore}
                  />
                )}
              </AnimatePresence>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => onToggleExpanded(match.id)}
                className="w-full mt-3 text-[#2A5D67] hover:bg-white/50"
              >
                {isExpanded ? (
                  <>
                    <ChevronUp className="w-4 h-4 mr-2" />
                    Mostra Meno
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-4 h-4 mr-2" />
                    Mostra Dettagli
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>
    </motion.div>
  );
}
