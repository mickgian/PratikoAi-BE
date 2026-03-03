'use client';

import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { useMatching } from '@/lib/hooks/useMatching';
import { MatchingNormativoView } from './components/MatchingNormativoView';

export default function MatchingNormativoPage() {
  const router = useRouter();
  const { suggestions, isLoading, error, refresh, markAsRead, dismiss } =
    useMatching();

  const handleGenerateCommunication = (matchIds: string[]) => {
    toast.success(
      `Generazione comunicazione per ${matchIds.length} match in corso...`
    );
  };

  const handleIgnore = async (matchIds: string[]) => {
    try {
      await dismiss(matchIds);
      toast.success(
        `${matchIds.length} match ignorat${matchIds.length === 1 ? 'o' : 'i'}`
      );
    } catch {
      toast.error('Errore durante il rifiuto dei suggerimenti');
    }
  };

  const handleMarkAsHandled = async (matchIds: string[]) => {
    try {
      await markAsRead(matchIds);
      toast.success(
        `${matchIds.length} match segnat${matchIds.length === 1 ? 'o' : 'i'} come gestit${matchIds.length === 1 ? 'o' : 'i'}`
      );
    } catch {
      toast.error('Errore durante la segnatura come gestito');
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      <div className="bg-white border-b border-[#C4BDB4]/20 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <Button
            variant="ghost"
            onClick={() => router.push('/chat')}
            className="text-[#2A5D67] hover:bg-[#F8F5F1] mb-3 -ml-2"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Indietro
          </Button>
        </div>
      </div>
      <MatchingNormativoView
        suggestions={suggestions}
        isLoading={isLoading}
        error={error}
        onRetry={refresh}
        onGenerateCommunication={handleGenerateCommunication}
        onIgnore={handleIgnore}
        onMarkAsHandled={handleMarkAsHandled}
      />
    </div>
  );
}
