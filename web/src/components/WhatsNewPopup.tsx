'use client';

import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Sparkles } from 'lucide-react';

interface ReleaseNoteData {
  version: string;
  released_at: string | null;
  user_notes: string;
  technical_notes: string;
}

interface WhatsNewPopupProps {
  releaseNote: ReleaseNoteData | null;
  onDismiss: (version: string) => void;
}

export function WhatsNewPopup({ releaseNote, onDismiss }: WhatsNewPopupProps) {
  if (!releaseNote) return null;

  const noteLines = releaseNote.user_notes
    .split('\n')
    .filter(line => line.trim());

  return (
    <Dialog open={true} onOpenChange={() => onDismiss(releaseNote.version)}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2 text-[#2A5D67]">
            <Sparkles className="w-5 h-5 text-[#D4A574]" />
            <span>Novità v{releaseNote.version}</span>
          </DialogTitle>
          <DialogDescription className="text-sm text-gray-500">
            Ecco le ultime novità di PratikoAI
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 py-4">
          {noteLines.map((line, index) => {
            if (line.startsWith('- ')) {
              return (
                <div key={index} className="flex items-start space-x-2 ml-2">
                  <span className="text-[#D4A574] mt-1">•</span>
                  <span className="text-sm text-gray-700">{line.slice(2)}</span>
                </div>
              );
            }
            if (line.endsWith(':')) {
              return (
                <h4
                  key={index}
                  className="text-sm font-semibold text-[#2A5D67] pt-2"
                >
                  {line}
                </h4>
              );
            }
            return (
              <p key={index} className="text-sm text-gray-700">
                {line}
              </p>
            );
          })}
        </div>

        <div className="flex justify-end">
          <Button
            onClick={() => onDismiss(releaseNote.version)}
            className="bg-[#2A5D67] hover:bg-[#1E4A52] text-white"
            aria-label="Ho capito!"
          >
            Ho capito!
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
