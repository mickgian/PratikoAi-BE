'use client';

import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Inbox, FileText, Clock, CheckCircle, Send, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import type { FilterTab, ComunicazioniStats } from '../types';

interface ComunicazioniFilterTabsProps {
  activeTab: FilterTab;
  onTabChange: (tab: FilterTab) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  selectedCount: number;
  filteredCount: number;
  stats: ComunicazioniStats;
  onSelectAll: () => void;
  onBulkApprove: () => void;
  onBulkSend: () => void;
}

const tabs: {
  id: FilterTab;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  { id: 'tutte', label: 'Tutte', icon: Inbox },
  { id: 'bozze', label: 'Bozze', icon: FileText },
  { id: 'in_revisione', label: 'In Revisione', icon: Clock },
  { id: 'approvate', label: 'Approvate', icon: CheckCircle },
  { id: 'inviate', label: 'Inviate', icon: Send },
];

export function ComunicazioniFilterTabs({
  activeTab,
  onTabChange,
  searchQuery,
  onSearchChange,
  selectedCount,
  filteredCount,
  stats,
  onSelectAll,
  onBulkApprove,
  onBulkSend,
}: ComunicazioniFilterTabsProps) {
  return (
    <div className="mb-6 space-y-4">
      <div className="bg-white rounded-lg shadow-sm border border-[#C4BDB4]/20 p-2">
        <div className="flex flex-wrap gap-2">
          {tabs.map(tab => {
            const Icon = tab.icon;
            const count =
              tab.id !== 'tutte'
                ? stats[tab.id as keyof ComunicazioniStats]
                : undefined;
            return (
              <motion.button
                key={tab.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => onTabChange(tab.id)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all ${
                  activeTab === tab.id
                    ? 'bg-[#2A5D67] text-white shadow-md'
                    : 'bg-white text-[#1E293B] hover:bg-[#F8F5F1]'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="font-medium">{tab.label}</span>
                {count !== undefined && (
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      activeTab === tab.id
                        ? 'bg-white/20 text-white'
                        : 'bg-[#F8F5F1] text-[#2A5D67]'
                    }`}
                  >
                    {count}
                  </span>
                )}
              </motion.button>
            );
          })}
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1">
          <Input
            type="text"
            placeholder="Cerca per oggetto o cliente..."
            value={searchQuery}
            onChange={e => onSearchChange(e.target.value)}
            className="w-full"
          />
        </div>

        <AnimatePresence>
          {selectedCount > 0 && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="flex items-center space-x-2"
            >
              <span className="text-sm text-[#2A5D67] font-medium">
                {selectedCount} selezionate
              </span>
              <Button
                onClick={onBulkApprove}
                size="sm"
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                <Check className="w-4 h-4 mr-1" />
                Approva
              </Button>
              <Button
                onClick={onBulkSend}
                size="sm"
                className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
              >
                <Send className="w-4 h-4 mr-1" />
                Invia
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {filteredCount > 0 && (
        <div className="flex items-center space-x-2">
          <Checkbox
            checked={selectedCount === filteredCount}
            onCheckedChange={onSelectAll}
            className="border-[#C4BDB4]"
          />
          <span className="text-sm text-[#1E293B]">
            Seleziona tutte le comunicazioni visibili
          </span>
        </div>
      )}
    </div>
  );
}
