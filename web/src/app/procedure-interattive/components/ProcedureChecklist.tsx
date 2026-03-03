'use client';

import { motion } from 'motion/react';
import { Check, CheckCircle } from 'lucide-react';
import type { ChecklistItem } from '../types';

interface ProcedureChecklistProps {
  items: ChecklistItem[];
  isClientMode: boolean;
  onToggle: (itemId: string) => void;
}

export function ProcedureChecklist({
  items,
  isClientMode,
  onToggle,
}: ProcedureChecklistProps) {
  return (
    <div>
      <h3 className="text-lg font-semibold text-[#2A5D67] mb-3 flex items-center">
        <CheckCircle className="w-5 h-5 mr-2" />
        Checklist
      </h3>
      <div className="space-y-2">
        {items.map(item => (
          <motion.div
            key={item.id}
            whileHover={{ x: 4 }}
            className={`flex items-center space-x-3 p-3 rounded-lg border transition-all ${
              item.completed
                ? 'bg-green-50 border-green-200'
                : 'bg-white border-[#C4BDB4]/20 hover:border-[#C4BDB4]'
            }`}
          >
            <input
              type="checkbox"
              checked={item.completed}
              onChange={() => onToggle(item.id)}
              disabled={!isClientMode}
              className="w-5 h-5 text-[#2A5D67] border-[#C4BDB4] rounded focus:ring-[#2A5D67] disabled:opacity-50"
            />
            <span
              className={`flex-1 ${
                item.completed
                  ? 'text-green-700 line-through'
                  : 'text-[#1E293B]'
              }`}
            >
              {item.text}
            </span>
            {item.completed && <Check className="w-5 h-5 text-green-600" />}
          </motion.div>
        ))}
      </div>
    </div>
  );
}
