'use client';

import { motion, AnimatePresence } from 'motion/react';
import { Filter, Search } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { FilterType, FilterUrgency, FilterStatus } from '../types';
import { getUrgencyLabel } from '../utils/matching-helpers';

interface MatchingSearchFilterProps {
  searchQuery: string;
  filterType: FilterType;
  filterUrgency: FilterUrgency;
  filterStatus: FilterStatus;
  showFilters: boolean;
  onSearchChange: (value: string) => void;
  onTypeChange: (value: FilterType) => void;
  onUrgencyChange: (value: FilterUrgency) => void;
  onStatusChange: (value: FilterStatus) => void;
  onToggleFilters: () => void;
}

const STATUS_LABELS: Record<string, string> = {
  all: 'Tutti',
  new: 'Nuovo',
  reviewed: 'Revisionato',
  handled: 'Gestito',
  ignored: 'Ignorato',
};

export function MatchingSearchFilter({
  searchQuery,
  filterType,
  filterUrgency,
  filterStatus,
  showFilters,
  onSearchChange,
  onTypeChange,
  onUrgencyChange,
  onStatusChange,
  onToggleFilters,
}: MatchingSearchFilterProps) {
  const activeFilterCount = [filterType, filterUrgency, filterStatus].filter(
    f => f !== 'all'
  ).length;

  return (
    <Card className="border-[#C4BDB4]/20 mb-6">
      <CardContent className="pt-6">
        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-[#C4BDB4]" />
            <Input
              placeholder="Cerca normativa per titolo..."
              value={searchQuery}
              onChange={e => onSearchChange(e.target.value)}
              className="pl-10 border-[#C4BDB4]/20"
            />
          </div>

          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={onToggleFilters}
              className="border-[#C4BDB4]/20"
            >
              <Filter className="w-4 h-4 mr-2" />
              {showFilters ? 'Nascondi Filtri' : 'Mostra Filtri'}
            </Button>

            {activeFilterCount > 0 && (
              <Badge
                variant="outline"
                className="border-[#2A5D67] text-[#2A5D67]"
              >
                {activeFilterCount} filtri attivi
              </Badge>
            )}
          </div>

          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-[#C4BDB4]/20"
              >
                <div>
                  <Label className="text-sm font-medium text-[#1E293B] mb-2 block">
                    Tipo Match
                  </Label>
                  <div className="space-y-2">
                    {(
                      ['all', 'NORMATIVA', 'SCADENZA', 'OPPORTUNITA'] as const
                    ).map(type => (
                      <div key={type} className="flex items-center">
                        <input
                          type="radio"
                          id={`type-${type}`}
                          name="type"
                          checked={filterType === type}
                          onChange={() => onTypeChange(type)}
                          className="w-4 h-4 text-[#2A5D67] focus:ring-[#2A5D67]"
                        />
                        <label
                          htmlFor={`type-${type}`}
                          className="ml-2 text-sm text-[#1E293B]"
                        >
                          {type === 'all' ? 'Tutti' : type}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <Label className="text-sm font-medium text-[#1E293B] mb-2 block">
                    Livello Urgenza
                  </Label>
                  <div className="space-y-2">
                    {(
                      [
                        'all',
                        'critical',
                        'high',
                        'medium',
                        'informational',
                      ] as const
                    ).map(urgency => (
                      <div key={urgency} className="flex items-center">
                        <input
                          type="radio"
                          id={`urgency-${urgency}`}
                          name="urgency"
                          checked={filterUrgency === urgency}
                          onChange={() => onUrgencyChange(urgency)}
                          className="w-4 h-4 text-[#2A5D67] focus:ring-[#2A5D67]"
                        />
                        <label
                          htmlFor={`urgency-${urgency}`}
                          className="ml-2 text-sm text-[#1E293B]"
                        >
                          {urgency === 'all'
                            ? 'Tutti'
                            : getUrgencyLabel(urgency)}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <Label className="text-sm font-medium text-[#1E293B] mb-2 block">
                    Stato
                  </Label>
                  <div className="space-y-2">
                    {(
                      ['all', 'new', 'reviewed', 'handled', 'ignored'] as const
                    ).map(status => (
                      <div key={status} className="flex items-center">
                        <input
                          type="radio"
                          id={`status-${status}`}
                          name="status"
                          checked={filterStatus === status}
                          onChange={() => onStatusChange(status)}
                          className="w-4 h-4 text-[#2A5D67] focus:ring-[#2A5D67]"
                        />
                        <label
                          htmlFor={`status-${status}`}
                          className="ml-2 text-sm text-[#1E293B] capitalize"
                        >
                          {STATUS_LABELS[status]}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </CardContent>
    </Card>
  );
}
