'use client';

import { motion } from 'motion/react';
import { FileText, Clock, CheckCircle, Send } from 'lucide-react';
import type { ComunicazioniStats } from '../types';

interface ComunicazioniStatsBarProps {
  stats: ComunicazioniStats;
}

export function ComunicazioniStatsBar({ stats }: ComunicazioniStatsBarProps) {
  return (
    <div className="bg-white border-b border-[#C4BDB4]/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-gray-50 rounded-lg p-4 border border-gray-200"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Bozze</p>
                <p className="text-3xl font-bold text-gray-700">
                  {stats.bozze}
                </p>
              </div>
              <FileText className="w-8 h-8 text-gray-400" />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-yellow-50 rounded-lg p-4 border border-yellow-200"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-yellow-700">In Revisione</p>
                <p className="text-3xl font-bold text-yellow-700">
                  {stats.in_revisione}
                </p>
              </div>
              <Clock className="w-8 h-8 text-yellow-400" />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-green-50 rounded-lg p-4 border border-green-200"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-green-700">Approvate</p>
                <p className="text-3xl font-bold text-green-700">
                  {stats.approvate}
                </p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-400" />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-blue-50 rounded-lg p-4 border border-blue-200"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-blue-700">Inviate</p>
                <p className="text-3xl font-bold text-blue-700">
                  {stats.inviate}
                </p>
              </div>
              <Send className="w-8 h-8 text-blue-400" />
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
