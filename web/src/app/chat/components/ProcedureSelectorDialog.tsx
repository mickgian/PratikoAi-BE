'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  Search,
  Clock,
  FileText,
  ChevronRight,
  X,
  Info,
  Building2,
  Users,
  Calculator,
  UserCheck,
  ArrowRight,
  AlertCircle,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import type { ProceduraResponse } from '@/lib/api/procedure';

const categoryConfig: Record<
  string,
  {
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    color: string;
    bg: string;
  }
> = {
  apertura: {
    label: 'Apertura',
    icon: Building2,
    color: 'text-green-600',
    bg: 'bg-green-50',
  },
  chiusura: {
    label: 'Chiusura',
    icon: X,
    color: 'text-red-600',
    bg: 'bg-red-50',
  },
  lavoro: {
    label: 'Lavoro',
    icon: Users,
    color: 'text-blue-600',
    bg: 'bg-blue-50',
  },
  fiscale: {
    label: 'Fiscale',
    icon: Calculator,
    color: 'text-purple-600',
    bg: 'bg-purple-50',
  },
};

function formatEstimatedTime(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rem = minutes % 60;
  return rem > 0 ? `${hours}h ${rem}min` : `${hours}h`;
}

interface ProcedureSelectorDialogProps {
  procedures: ProceduraResponse[];
  error: string | null;
  initialQuery?: string;
  onClose: () => void;
}

export function ProcedureSelectorDialog({
  procedures,
  error,
  initialQuery = '',
  onClose,
}: ProcedureSelectorDialogProps) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [selectedCategory, setSelectedCategory] = useState<string>('tutte');
  const [selectedProcedure, setSelectedProcedure] =
    useState<ProceduraResponse | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const filteredProcedures = useMemo(() => {
    return procedures.filter(proc => {
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        !q ||
        proc.title.toLowerCase().includes(q) ||
        (proc.description ?? '').toLowerCase().includes(q);
      const matchesCategory =
        selectedCategory === 'tutte' ||
        proc.category.toLowerCase() === selectedCategory;
      return matchesSearch && matchesCategory;
    });
  }, [procedures, searchQuery, selectedCategory]);

  if (error) {
    return (
      <div
        data-testid="procedura-dialog"
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        onClick={onClose}
        role="dialog"
        aria-modal="true"
        aria-label="Procedure"
      >
        <div
          className="max-w-md bg-white rounded-xl border border-amber-200 p-5 space-y-3"
          onClick={e => e.stopPropagation()}
        >
          <div className="flex items-start gap-2 text-amber-800">
            <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <span className="text-sm">{error}</span>
          </div>
          <p className="text-xs text-gray-400 text-center">
            Premi Esc per chiudere
          </p>
        </div>
      </div>
    );
  }

  if (selectedProcedure) {
    const cat = categoryConfig[selectedProcedure.category.toLowerCase()];
    return (
      <div
        data-testid="procedura-dialog"
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        onClick={onClose}
        role="dialog"
        aria-modal="true"
        aria-label="Dettaglio procedura"
      >
        <div
          className="relative w-full max-w-2xl max-h-[80vh] mx-4 bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden flex flex-col"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-[#F8F5F1] to-white px-6 py-4 border-b border-[#C4BDB4]/20 flex-shrink-0">
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  <button
                    onClick={() => setSelectedProcedure(null)}
                    className="text-[#2A5D67] hover:bg-white rounded-md p-1 -ml-2"
                    aria-label="Torna alla lista"
                  >
                    <ChevronRight className="w-4 h-4 rotate-180" />
                  </button>
                  <h3 className="text-xl font-semibold text-[#1E293B]">
                    {selectedProcedure.title}
                  </h3>
                </div>
                <div className="flex items-center space-x-3 ml-10">
                  {cat && (
                    <span
                      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${cat.bg} ${cat.color}`}
                    >
                      {React.createElement(cat.icon, {
                        className: 'w-3 h-3 mr-1',
                      })}
                      {cat.label}
                    </span>
                  )}
                  <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                    <Info className="w-3 h-3 mr-1" />
                    Modalità consultazione
                  </span>
                </div>
              </div>
              <button
                onClick={onClose}
                className="text-[#1E293B]/60 hover:bg-white rounded-md p-1"
                aria-label="Chiudi"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            {selectedProcedure.description && (
              <p className="text-sm text-[#1E293B]/70 ml-10 mt-2">
                {selectedProcedure.description}
              </p>
            )}
          </div>

          {/* Scrollable content */}
          <div className="overflow-y-auto flex-1 p-6 space-y-6">
            {/* Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-[#F8F5F1] rounded-lg p-4">
                <div className="flex items-center space-x-2 text-[#2A5D67] mb-1">
                  <FileText className="w-4 h-4" />
                  <span className="text-sm font-medium">Passi totali</span>
                </div>
                <p className="text-2xl font-semibold text-[#1E293B]">
                  {selectedProcedure.steps.length}
                </p>
              </div>
              <div className="bg-[#F8F5F1] rounded-lg p-4">
                <div className="flex items-center space-x-2 text-[#2A5D67] mb-1">
                  <Clock className="w-4 h-4" />
                  <span className="text-sm font-medium">Tempo stimato</span>
                </div>
                <p className="text-2xl font-semibold text-[#1E293B]">
                  {formatEstimatedTime(
                    selectedProcedure.estimated_time_minutes
                  )}
                </p>
              </div>
            </div>

            {/* Steps */}
            <div>
              <h4 className="text-sm font-semibold text-[#2A5D67] mb-3 uppercase tracking-wider">
                Passi della procedura
              </h4>
              <div className="space-y-2">
                {selectedProcedure.steps.map((step, index) => (
                  <div
                    key={index}
                    className="bg-white border border-[#C4BDB4]/20 rounded-lg p-4"
                  >
                    <div className="flex items-start space-x-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-[#2A5D67]/10 rounded-full flex items-center justify-center">
                        <span className="text-sm font-semibold text-[#2A5D67]">
                          {index + 1}
                        </span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <h5 className="text-sm font-medium text-[#1E293B] mb-1">
                          {step.title}
                        </h5>
                        {step.notes && (
                          <p className="text-xs text-[#1E293B]/60">
                            {step.notes}
                          </p>
                        )}
                        {step.checklist && step.checklist.length > 0 && (
                          <ul className="mt-1 space-y-0.5">
                            {step.checklist.map((item, ci) => (
                              <li
                                key={ci}
                                className="text-xs text-[#1E293B]/60 flex items-center space-x-1 before:content-none !p-0 !m-0"
                              >
                                <span className="text-[#2A5D67]">•</span>
                                <span>{item}</span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Documents (collected from all steps) */}
            {(() => {
              const allDocs = selectedProcedure.steps.flatMap(
                s => s.documents ?? []
              );
              if (allDocs.length === 0) return null;
              return (
                <div>
                  <h4 className="text-sm font-semibold text-[#2A5D67] mb-3 uppercase tracking-wider">
                    Documenti necessari
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {allDocs.map((doc, i) => (
                      <div
                        key={i}
                        className="flex items-center space-x-2 text-sm text-[#1E293B]/70 bg-[#F8F5F1] rounded-lg px-3 py-2"
                      >
                        <FileText className="w-3.5 h-3.5 text-[#2A5D67] flex-shrink-0" />
                        <span className="truncate">{doc}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 bg-[#F8F5F1] border-t border-[#C4BDB4]/20 flex-shrink-0">
            <button
              onClick={() => {
                onClose();
                router.push('/procedure-interattive');
              }}
              className="w-full flex items-center justify-center bg-gradient-to-r from-[#2A5D67] to-[#1E293B] hover:from-[#1E293B] hover:to-[#2A5D67] text-white font-medium rounded-lg px-4 py-2.5 transition-all"
            >
              <UserCheck className="w-4 h-4 mr-2" />
              Avvia per un cliente
              <ArrowRight className="w-4 h-4 ml-2" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // List view
  return (
    <div
      data-testid="procedura-dialog"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Seleziona procedura"
    >
      <div
        className="relative w-full max-w-2xl max-h-[80vh] mx-4 bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-[#2A5D67] to-[#1E293B] px-6 py-4 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white mb-1">
                Seleziona Procedura
              </h3>
              <p className="text-sm text-white/80">
                Scegli una procedura per consultarla o avviarla per un cliente
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:bg-white/10 rounded-md p-1"
              aria-label="Chiudi"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="p-4 pb-3 bg-white border-b border-[#C4BDB4]/20 flex-shrink-0">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#1E293B]/40" />
            <input
              type="text"
              placeholder="Cerca procedura..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-[#C4BDB4]/30 rounded-lg text-sm focus:border-[#2A5D67] focus:ring-1 focus:ring-[#2A5D67] outline-none"
            />
          </div>
        </div>

        {/* Category Chips */}
        <div className="px-4 py-3 bg-[#F8F5F1]/50 border-b border-[#C4BDB4]/20 flex-shrink-0">
          <div className="flex items-center space-x-2 overflow-x-auto pb-1">
            <button
              onClick={() => setSelectedCategory('tutte')}
              className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                selectedCategory === 'tutte'
                  ? 'bg-[#2A5D67] text-white'
                  : 'bg-white text-[#1E293B] hover:bg-[#F8F5F1]'
              }`}
            >
              Tutte
            </button>
            {Object.entries(categoryConfig).map(([key, config]) => (
              <button
                key={key}
                onClick={() => setSelectedCategory(key)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors flex items-center space-x-1.5 ${
                  selectedCategory === key
                    ? 'bg-[#2A5D67] text-white'
                    : 'bg-white text-[#1E293B] hover:bg-[#F8F5F1]'
                }`}
              >
                {React.createElement(config.icon, {
                  className: 'w-3.5 h-3.5',
                })}
                <span>{config.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Procedure List */}
        <div className="overflow-y-auto flex-1 p-4 space-y-3">
          {filteredProcedures.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="w-12 h-12 mx-auto text-[#C4BDB4] mb-3" />
              <p className="text-[#1E293B]/60">Nessuna procedura trovata</p>
            </div>
          ) : (
            filteredProcedures.map(procedure => {
              const cat = categoryConfig[procedure.category.toLowerCase()];
              return (
                <div
                  key={procedure.id}
                  onClick={() => setSelectedProcedure(procedure)}
                  className="bg-white border border-[#C4BDB4]/20 rounded-lg p-4 cursor-pointer hover:shadow-md hover:border-[#2A5D67]/30 transition-all group"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <h4 className="font-medium text-[#1E293B] group-hover:text-[#2A5D67] transition-colors">
                          {procedure.title}
                        </h4>
                        <ChevronRight className="w-4 h-4 text-[#1E293B]/40 group-hover:text-[#2A5D67] transition-colors" />
                      </div>
                      {cat && (
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cat.bg} ${cat.color}`}
                        >
                          {React.createElement(cat.icon, {
                            className: 'w-3 h-3 mr-1',
                          })}
                          {cat.label}
                        </span>
                      )}
                    </div>
                  </div>
                  {procedure.description && (
                    <p className="text-sm text-[#1E293B]/60 mb-3">
                      {procedure.description}
                    </p>
                  )}
                  <div className="flex items-center space-x-4 text-xs text-[#1E293B]/50">
                    <div className="flex items-center space-x-1">
                      <FileText className="w-3.5 h-3.5" />
                      <span>{procedure.steps.length} passi</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Clock className="w-3.5 h-3.5" />
                      <span>
                        {formatEstimatedTime(procedure.estimated_time_minutes)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-[#C4BDB4]/20 flex-shrink-0">
          <p className="text-xs text-gray-400 text-center">
            Premi Esc per chiudere
          </p>
        </div>
      </div>
    </div>
  );
}
