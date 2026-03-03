'use client';

import { Activity } from 'lucide-react';
import { motion } from 'motion/react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { ActivityItem } from '../types';
import { formatRelativeTime } from '../utils/formatters';

interface DashboardActivityTimelineProps {
  activities: ActivityItem[];
}

export function DashboardActivityTimeline({
  activities,
}: DashboardActivityTimelineProps) {
  if (activities.length === 0) {
    return (
      <Card className="border-[#C4BDB4]/20">
        <CardHeader>
          <CardTitle className="text-xl text-[#2A5D67] flex items-center">
            <Activity className="w-5 h-5 mr-2" />
            Attività Recenti
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[#94A3B8] text-center py-8">
            Nessuna attività recente
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-[#C4BDB4]/20">
      <CardHeader>
        <CardTitle className="text-xl text-[#2A5D67] flex items-center">
          <Activity className="w-5 h-5 mr-2" />
          Attività Recenti
        </CardTitle>
        <CardDescription>Timeline delle ultime azioni</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4 max-h-96 overflow-y-auto">
          {activities.map((activity, index) => {
            const IconComponent = activity.icon;
            return (
              <motion.div
                key={activity.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.6 + index * 0.05 }}
                className="flex items-start space-x-3 pb-4 border-b border-[#C4BDB4]/20 last:border-0"
              >
                <div
                  className={`w-10 h-10 rounded-lg ${activity.color} flex items-center justify-center flex-shrink-0`}
                >
                  <IconComponent className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-[#2A5D67] text-sm">
                    {activity.title}
                  </p>
                  <p className="text-sm text-[#1E293B] mt-1">
                    {activity.description}
                  </p>
                  <p className="text-xs text-[#94A3B8] mt-1">
                    {formatRelativeTime(activity.timestamp)}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
