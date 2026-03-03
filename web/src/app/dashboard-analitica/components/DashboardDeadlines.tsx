'use client';

import { Calendar, Users } from 'lucide-react';
import { motion } from 'motion/react';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Deadline } from '../types';
import { getDaysUntil, getPriorityColor } from '../utils/formatters';

interface DashboardDeadlinesProps {
  deadlines: Deadline[];
}

export function DashboardDeadlines({ deadlines }: DashboardDeadlinesProps) {
  if (deadlines.length === 0) {
    return (
      <Card className="border-[#C4BDB4]/20">
        <CardHeader>
          <CardTitle className="text-xl text-[#2A5D67] flex items-center">
            <Calendar className="w-5 h-5 mr-2" />
            Scadenze Imminenti
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[#94A3B8] text-center py-8">
            Nessuna scadenza imminente
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-[#C4BDB4]/20">
      <CardHeader>
        <CardTitle className="text-xl text-[#2A5D67] flex items-center">
          <Calendar className="w-5 h-5 mr-2" />
          Scadenze Imminenti
        </CardTitle>
        <CardDescription>Prossimi 7 giorni</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {deadlines.map((deadline, index) => {
            const daysUntil = getDaysUntil(deadline.date);
            return (
              <motion.div
                key={deadline.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.7 + index * 0.05 }}
                className="bg-white border border-[#C4BDB4]/20 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-2">
                  <h4 className="font-semibold text-[#2A5D67] text-sm">
                    {deadline.title}
                  </h4>
                  <Badge
                    className={`${getPriorityColor(deadline.priority)} border text-xs`}
                  >
                    {deadline.priority === 'high' ? 'Urgente' : 'Normale'}
                  </Badge>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center text-[#1E293B]">
                    <Calendar className="w-4 h-4 mr-1" />
                    {new Date(deadline.date).toLocaleDateString('it-IT', {
                      day: 'numeric',
                      month: 'short',
                    })}
                    <span className="mx-2">•</span>
                    <span className="text-[#94A3B8]">
                      {daysUntil === 0
                        ? 'Oggi'
                        : daysUntil === 1
                          ? 'Domani'
                          : `Tra ${daysUntil} giorni`}
                    </span>
                  </div>
                  <div className="flex items-center text-[#2A5D67]">
                    <Users className="w-4 h-4 mr-1" />
                    {deadline.clientCount}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
