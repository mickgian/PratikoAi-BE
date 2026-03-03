'use client';

import { motion } from 'motion/react';
import { Check, CheckCircle, Mail, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface MatchingBulkActionsProps {
  selectedCount: number;
  onCommunicate: () => void;
  onMarkHandled: () => void;
  onIgnore: () => void;
}

export function MatchingBulkActions({
  selectedCount,
  onCommunicate,
  onMarkHandled,
  onIgnore,
}: MatchingBulkActionsProps) {
  if (selectedCount === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-[#2A5D67] text-white rounded-lg p-4 mb-6 shadow-lg"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <CheckCircle className="w-5 h-5" />
          <span className="font-semibold">
            {selectedCount} match selezionat{selectedCount === 1 ? 'o' : 'i'}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            size="sm"
            onClick={onCommunicate}
            className="bg-white text-[#2A5D67] hover:bg-[#F8F5F1]"
          >
            <Mail className="w-4 h-4 mr-2" />
            <span className="font-bold">Genera Comunicazione</span>
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onMarkHandled}
            className="border-white text-white hover:bg-[#1E293B]"
          >
            <Check className="w-4 h-4 mr-2" />
            <span className="font-bold">Segna come Gestito</span>
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onIgnore}
            className="border-white text-white hover:bg-[#1E293B]"
          >
            <XCircle className="w-4 h-4 mr-2" />
            <span className="font-bold">Ignora</span>
          </Button>
        </div>
      </div>
    </motion.div>
  );
}
