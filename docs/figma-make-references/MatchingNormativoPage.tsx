import React from "react";
import { ArrowLeft } from "lucide-react";
import { Button } from "./ui/button";
import { RisultatiMatchingNormativoPanel } from "./RisultatimatchingNormativoPanel";
import { toast } from "sonner@2.0.3";

interface MatchingNormativoPageProps {
  onBackToChat: () => void;
}

export function MatchingNormativoPage({
  onBackToChat,
}: MatchingNormativoPageProps) {
  const handleGenerateCommunication = (matchIds: string[]) => {
    toast.success(
      `Generazione comunicazione per ${matchIds.length} match in corso...`,
    );
    console.log("Generate communication for:", matchIds);
  };

  const handleIgnore = (matchIds: string[]) => {
    toast.success(
      `${matchIds.length} match ignorat${matchIds.length === 1 ? "o" : "i"}`,
    );
    console.log("Ignore matches:", matchIds);
  };

  const handleMarkAsHandled = (matchIds: string[]) => {
    toast.success(
      `${matchIds.length} match segnat${matchIds.length === 1 ? "o" : "i"} come gestit${matchIds.length === 1 ? "o" : "i"}`,
    );
    console.log("Mark as handled:", matchIds);
  };

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      {/* Header */}
      <div className="bg-white border-b border-[#C4BDB4]/20 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <Button
            variant="ghost"
            onClick={onBackToChat}
            className="text-[#2A5D67] hover:bg-[#F8F5F1] mb-3 -ml-2"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Indietro
          </Button>
        </div>
      </div>

      {/* Content */}
      <RisultatiMatchingNormativoPanel
        clientName="Studio Legale Rossi & Associati"
        clientId="client_001"
        onGenerateCommunication={handleGenerateCommunication}
        onIgnore={handleIgnore}
        onMarkAsHandled={handleMarkAsHandled}
        embedded={false}
      />
    </div>
  );
}
