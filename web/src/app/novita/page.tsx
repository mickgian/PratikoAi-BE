'use client';

import React, { useState, useEffect } from 'react';
import { Sparkles, ArrowLeft, Calendar } from 'lucide-react';
import Link from 'next/link';
import { getReleaseNotes } from '@/lib/api/release-notes';
import type { ReleaseNotePublic } from '@/lib/api/release-notes';

export default function NovitaPage() {
  const [notes, setNotes] = useState<ReleaseNotePublic[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getReleaseNotes(1, 50)
      .then(data => {
        setNotes(data.items);
      })
      .catch(() => {
        setNotes([]);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="mb-8">
          <Link
            href="/"
            className="inline-flex items-center space-x-1 text-sm text-[#2A5D67] hover:text-[#1E4A52] transition-colors mb-6"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Torna alla home</span>
          </Link>
          <div className="flex items-center space-x-3">
            <Sparkles className="w-8 h-8 text-[#D4A574]" />
            <h1 className="text-3xl font-bold text-[#2A5D67]">Novità</h1>
          </div>
          <p className="text-gray-600 mt-2">
            Tutte le novità e gli aggiornamenti di PratikoAI
          </p>
        </div>

        {loading && (
          <div className="text-center py-12 text-gray-500">Caricamento...</div>
        )}

        {!loading && notes.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            Nessuna nota di rilascio disponibile.
          </div>
        )}

        <div className="space-y-8">
          {notes.map(note => (
            <article
              key={note.version}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-6"
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-[#2A5D67]">
                  v{note.version}
                </h2>
                {note.released_at && (
                  <div className="flex items-center space-x-1 text-sm text-gray-400">
                    <Calendar className="w-3.5 h-3.5" />
                    <time dateTime={note.released_at}>
                      {new Date(note.released_at).toLocaleDateString('it-IT', {
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric',
                      })}
                    </time>
                  </div>
                )}
              </div>
              <div className="space-y-1.5">
                {note.user_notes
                  .split('\n')
                  .filter(line => line.trim())
                  .map((line, i) => {
                    if (line.startsWith('- ')) {
                      return (
                        <div
                          key={i}
                          className="flex items-start space-x-2 ml-2"
                        >
                          <span className="text-[#D4A574] mt-0.5">•</span>
                          <span className="text-gray-700">{line.slice(2)}</span>
                        </div>
                      );
                    }
                    if (line.endsWith(':')) {
                      return (
                        <h3
                          key={i}
                          className="text-sm font-semibold text-[#2A5D67] pt-2"
                        >
                          {line}
                        </h3>
                      );
                    }
                    return (
                      <p key={i} className="text-gray-700">
                        {line}
                      </p>
                    );
                  })}
              </div>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}
