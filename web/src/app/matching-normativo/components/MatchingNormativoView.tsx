'use client';

import { useMemo, useState } from 'react';
import { AlertCircle, Loader2, Target, User } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Info } from 'lucide-react';
import { SuggestionResponse } from '@/lib/api/matching';
import {
  NormativeMatch,
  FilterType,
  FilterUrgency,
  FilterStatus,
  mapSuggestionToMatch,
} from '../types';
import { MatchingSearchFilter } from './MatchingSearchFilter';
import { MatchingBulkActions } from './MatchingBulkActions';
import { MatchingCard } from './MatchingCard';

interface MatchingNormativoViewProps {
  suggestions: SuggestionResponse[];
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  onGenerateCommunication?: (matchIds: string[]) => void;
  onIgnore?: (matchIds: string[]) => void;
  onMarkAsHandled?: (matchIds: string[]) => void;
}

export function MatchingNormativoView({
  suggestions,
  isLoading,
  error,
  onRetry,
  onGenerateCommunication,
  onIgnore,
  onMarkAsHandled,
}: MatchingNormativoViewProps) {
  const [expandedMatches, setExpandedMatches] = useState<Set<string>>(
    new Set()
  );
  const [selectedMatches, setSelectedMatches] = useState<Set<string>>(
    new Set()
  );
  const [filterType, setFilterType] = useState<FilterType>('all');
  const [filterUrgency, setFilterUrgency] = useState<FilterUrgency>('all');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const matches: NormativeMatch[] = useMemo(
    () => suggestions.map(mapSuggestionToMatch),
    [suggestions]
  );

  const filteredMatches = matches.filter(match => {
    if (filterType !== 'all' && match.type !== filterType) return false;
    if (filterUrgency !== 'all' && match.urgency !== filterUrgency)
      return false;
    if (filterStatus !== 'all' && match.status !== filterStatus) return false;
    if (
      searchQuery &&
      !match.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !match.matchReason.toLowerCase().includes(searchQuery.toLowerCase())
    )
      return false;
    return true;
  });

  const toggleExpanded = (matchId: string) => {
    const next = new Set(expandedMatches);
    if (next.has(matchId)) next.delete(matchId);
    else next.add(matchId);
    setExpandedMatches(next);
  };

  const toggleSelected = (matchId: string) => {
    const next = new Set(selectedMatches);
    if (next.has(matchId)) next.delete(matchId);
    else next.add(matchId);
    setSelectedMatches(next);
  };

  const selectAll = () => {
    if (selectedMatches.size === filteredMatches.length) {
      setSelectedMatches(new Set());
    } else {
      setSelectedMatches(new Set(filteredMatches.map(m => m.id)));
    }
  };

  const handleBulkAction = (action: 'communicate' | 'ignore' | 'handled') => {
    const selectedIds = Array.from(selectedMatches);
    if (action === 'communicate') onGenerateCommunication?.(selectedIds);
    if (action === 'ignore') onIgnore?.(selectedIds);
    if (action === 'handled') onMarkAsHandled?.(selectedIds);
    setSelectedMatches(new Set());
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F8F5F1] p-6">
        <div className="max-w-6xl mx-auto flex flex-col items-center justify-center py-24">
          <Loader2 className="w-12 h-12 text-[#2A5D67] animate-spin mb-4" />
          <p className="text-[#1E293B] text-lg">
            Caricamento suggerimenti in corso...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#F8F5F1] p-6">
        <div className="max-w-6xl mx-auto flex flex-col items-center justify-center py-24">
          <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
          <p className="text-[#1E293B] text-lg mb-4">{error}</p>
          <Button
            onClick={onRetry}
            className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
          >
            Riprova
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8F5F1] p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h2 className="text-2xl font-bold text-[#2A5D67] flex items-center">
                <Target className="w-6 h-6 mr-2" />
                Risultati Matching Normativo
              </h2>
            </div>
            <Badge className="bg-[#2A5D67] text-white border-[#2A5D67] px-4 py-2 text-base">
              {filteredMatches.length} Match Trovati
            </Badge>
          </div>
        </div>

        <MatchingSearchFilter
          searchQuery={searchQuery}
          filterType={filterType}
          filterUrgency={filterUrgency}
          filterStatus={filterStatus}
          showFilters={showFilters}
          onSearchChange={setSearchQuery}
          onTypeChange={setFilterType}
          onUrgencyChange={setFilterUrgency}
          onStatusChange={setFilterStatus}
          onToggleFilters={() => setShowFilters(prev => !prev)}
        />

        <MatchingBulkActions
          selectedCount={selectedMatches.size}
          onCommunicate={() => handleBulkAction('communicate')}
          onMarkHandled={() => handleBulkAction('handled')}
          onIgnore={() => handleBulkAction('ignore')}
        />

        {filteredMatches.length > 0 && (
          <div className="mb-4 flex items-center space-x-2">
            <Checkbox
              id="select-all"
              checked={
                selectedMatches.size === filteredMatches.length &&
                filteredMatches.length > 0
              }
              onCheckedChange={selectAll}
            />
            <label
              htmlFor="select-all"
              className="text-sm font-medium text-[#1E293B] cursor-pointer"
            >
              Seleziona tutti ({filteredMatches.length})
            </label>
          </div>
        )}

        <div className="space-y-4">
          {filteredMatches.length === 0 ? (
            <Card className="border-[#C4BDB4]/20">
              <CardContent className="py-12 text-center">
                <Info className="w-12 h-12 text-[#C4BDB4] mx-auto mb-4" />
                <p className="text-[#1E293B] text-lg">
                  Nessun match trovato con i filtri selezionati
                </p>
              </CardContent>
            </Card>
          ) : (
            filteredMatches.map((match, index) => (
              <MatchingCard
                key={match.id}
                match={match}
                index={index}
                isExpanded={expandedMatches.has(match.id)}
                isSelected={selectedMatches.has(match.id)}
                onToggleExpanded={toggleExpanded}
                onToggleSelected={toggleSelected}
                onGenerateCommunication={onGenerateCommunication}
                onMarkAsHandled={onMarkAsHandled}
                onIgnore={onIgnore}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
