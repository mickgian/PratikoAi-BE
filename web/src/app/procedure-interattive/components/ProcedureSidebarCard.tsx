'use client';

import { motion } from 'motion/react';
import { Badge } from '@/components/ui/badge';
import type { Procedura } from '../types';

interface ProcedureSidebarCardProps {
  procedura: Procedura;
  index: number;
  isSelected: boolean;
  onSelect: () => void;
}

const getCategoryColor = (category: string): string => {
  const colors: Record<string, string> = {
    Fiscale: 'bg-blue-100 text-blue-700 border-blue-300',
    Lavoro: 'bg-purple-100 text-purple-700 border-purple-300',
    Contabilità: 'bg-green-100 text-green-700 border-green-300',
    Previdenziale: 'bg-orange-100 text-orange-700 border-orange-300',
  };
  return colors[category] || 'bg-gray-100 text-gray-700 border-gray-300';
};

const getProgressColor = (progress: number): string => {
  if (progress === 100) return 'bg-green-500';
  if (progress >= 50) return 'bg-blue-500';
  if (progress > 0) return 'bg-yellow-500';
  return 'bg-gray-300';
};

export function ProcedureSidebarCard({
  procedura,
  index,
  isSelected,
  onSelect,
}: ProcedureSidebarCardProps) {
  return (
    <motion.button
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      onClick={onSelect}
      className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
        isSelected
          ? 'border-[#2A5D67] bg-[#F8F5F1] shadow-md'
          : 'border-[#C4BDB4]/20 hover:border-[#C4BDB4] hover:bg-[#F8F5F1]/50'
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-semibold text-[#2A5D67] text-sm leading-tight pr-2">
          {procedura.title}
        </h3>
        <Badge
          className={`${getCategoryColor(procedura.category)} border text-xs flex-shrink-0`}
        >
          {procedura.category}
        </Badge>
      </div>

      <p className="text-xs text-[#1E293B] mb-3 line-clamp-2">
        {procedura.description}
      </p>

      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs text-[#1E293B]">
          <span>
            {procedura.completedSteps} di {procedura.totalSteps} passi
          </span>
          <span className="font-semibold">{procedura.progress}%</span>
        </div>
        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${procedura.progress}%` }}
            transition={{ duration: 0.5, delay: index * 0.05 }}
            className={`h-full ${getProgressColor(procedura.progress)} rounded-full`}
          />
        </div>
      </div>
    </motion.button>
  );
}
