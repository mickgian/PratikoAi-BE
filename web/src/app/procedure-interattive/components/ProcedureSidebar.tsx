'use client';

import { useRouter } from 'next/navigation';
import { ArrowLeft, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ProcedureSidebarCard } from './ProcedureSidebarCard';
import type { Procedura } from '../types';

interface ProcedureSidebarProps {
  procedures: Procedura[];
  selectedId: string;
  onSelect: (id: string, stepIndex: number) => void;
}

export function ProcedureSidebar({
  procedures,
  selectedId,
  onSelect,
}: ProcedureSidebarProps) {
  const router = useRouter();

  return (
    <div className="w-80 bg-white border-r border-[#C4BDB4]/20 flex flex-col overflow-hidden">
      <div className="p-4 border-b border-[#C4BDB4]/20 bg-[#2A5D67] text-white">
        <Button
          variant="ghost"
          onClick={() => router.push('/chat')}
          className="text-white hover:bg-white/10 mb-3 -ml-2"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Indietro
        </Button>
        <h2 className="text-xl font-bold flex items-center">
          <BookOpen className="w-5 h-5 mr-2" />
          Procedure
        </h2>
        <p className="text-sm text-white/80 mt-1">
          Guide passo-passo interattive
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {procedures.map((procedura, index) => (
          <ProcedureSidebarCard
            key={procedura.id}
            procedura={procedura}
            index={index}
            isSelected={selectedId === procedura.id}
            onSelect={() => {
              const stepIndex =
                procedura.completedSteps < procedura.totalSteps
                  ? procedura.completedSteps
                  : 0;
              onSelect(procedura.id, stepIndex);
            }}
          />
        ))}
      </div>
    </div>
  );
}
