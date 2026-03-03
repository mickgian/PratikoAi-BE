'use client';

import { Download, Mail, X } from 'lucide-react';
import { motion } from 'motion/react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

interface ClientListBulkActionsProps {
  selectedCount: number;
  onDeselect: () => void;
}

export function ClientListBulkActions({
  selectedCount,
  onDeselect,
}: ClientListBulkActionsProps) {
  const handleBulkExport = () => {
    toast.success(`Esportati ${selectedCount} clienti in formato Excel`);
    onDeselect();
  };

  const handleBulkCommunication = () => {
    toast.success(`Preparata comunicazione per ${selectedCount} clienti`);
    onDeselect();
  };

  return (
    <motion.div
      initial={{ y: -10, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="bg-[#D4A574] rounded-lg p-4 mb-6 flex items-center justify-between"
    >
      <div className="flex items-center gap-4">
        <span className="text-[#1E293B]">
          {selectedCount} clienti selezionati
        </span>
        <Button
          onClick={onDeselect}
          variant="ghost"
          size="sm"
          className="text-[#1E293B] hover:bg-white/20"
        >
          <X className="w-4 h-4 mr-1" />
          Deseleziona
        </Button>
      </div>
      <div className="flex gap-2">
        <Button
          onClick={handleBulkExport}
          variant="outline"
          size="sm"
          className="bg-white border-[#1E293B] text-[#1E293B] hover:bg-[#F8F5F1]"
        >
          <Download className="w-4 h-4 mr-2" />
          Esporta
        </Button>
        <Button
          onClick={handleBulkCommunication}
          variant="outline"
          size="sm"
          className="bg-white border-[#1E293B] text-[#1E293B] hover:bg-[#F8F5F1]"
        >
          <Mail className="w-4 h-4 mr-2" />
          Crea comunicazione
        </Button>
      </div>
    </motion.div>
  );
}
