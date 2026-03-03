'use client';

import { useState, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'motion/react';
import { ArrowLeft, Plus, AlertCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { ComunicazioniStatsBar } from './ComunicazioniStatsBar';
import { ComunicazioniFilterTabs } from './ComunicazioniFilterTabs';
import { ComunicazioneCard } from './ComunicazioneCard';
import { ComunicazioneEditorModal } from './ComunicazioneEditorModal';
import {
  useCommunications,
  useCommunicationActions,
} from '@/lib/hooks/useCommunications';
import type { CommunicationResponse } from '@/lib/api/communications';
import type {
  Communication,
  CommunicationChannel,
  CommunicationStatus,
  FilterTab,
} from '../types';

interface EditorState {
  subject: string;
  body: string;
  client: string;
  template: string;
  channel: CommunicationChannel;
}

const DEFAULT_EDITOR_STATE: EditorState = {
  subject: '',
  body: '',
  client: '',
  template: '',
  channel: 'email',
};

const STATUS_API_MAP: Record<string, CommunicationStatus> = {
  DRAFT: 'bozza',
  PENDING_REVIEW: 'in_revisione',
  APPROVED: 'approvata',
  SENT: 'inviata',
};

function mapToCommunication(
  c: CommunicationResponse,
  getClientName: (id: number | null) => string
): Communication {
  return {
    id: c.id,
    subject: c.subject,
    body: c.content,
    clientId: String(c.client_id ?? ''),
    clientName: getClientName(c.client_id),
    channel: (c.channel?.toLowerCase() ?? 'email') as CommunicationChannel,
    status: STATUS_API_MAP[c.status] ?? 'bozza',
    normativaReference: c.normativa_riferimento ?? '',
    createdDate: c.created_at,
  };
}

export function ComunicazioniView() {
  const router = useRouter();
  const {
    communications: rawCommunications,
    clients,
    stats,
    isLoading,
    error,
    refresh,
    getClientName,
  } = useCommunications();

  const { create, submit, approve, send, remove } =
    useCommunicationActions(refresh);

  const [activeTab, setActiveTab] = useState<FilterTab>('tutte');
  const [selectedCommunications, setSelectedCommunications] = useState<
    Set<string>
  >(new Set());
  const [showEditor, setShowEditor] = useState(false);
  const [editingCommunication, setEditingCommunication] =
    useState<Communication | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [editorState, setEditorState] =
    useState<EditorState>(DEFAULT_EDITOR_STATE);
  const [isSaving, setIsSaving] = useState(false);

  const communications = useMemo(
    () => rawCommunications.map(c => mapToCommunication(c, getClientName)),
    [rawCommunications, getClientName]
  );

  const filteredCommunications = useMemo(() => {
    let filtered = communications;
    if (activeTab !== 'tutte') {
      const statusMap: Record<FilterTab, string | null> = {
        tutte: null,
        bozze: 'bozza',
        in_revisione: 'in_revisione',
        approvate: 'approvata',
        inviate: 'inviata',
      };
      const targetStatus = statusMap[activeTab];
      if (targetStatus) {
        filtered = filtered.filter(c => c.status === targetStatus);
      }
    }
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        c =>
          c.subject.toLowerCase().includes(query) ||
          c.clientName.toLowerCase().includes(query)
      );
    }
    return filtered;
  }, [communications, activeTab, searchQuery]);

  const toggleSelect = (id: string) => {
    const next = new Set(selectedCommunications);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedCommunications(next);
  };

  const toggleSelectAll = () => {
    if (selectedCommunications.size === filteredCommunications.length) {
      setSelectedCommunications(new Set());
    } else {
      setSelectedCommunications(new Set(filteredCommunications.map(c => c.id)));
    }
  };

  const openEditor = (communication?: Communication) => {
    if (communication) {
      setEditingCommunication(communication);
      setEditorState({
        subject: communication.subject,
        body: communication.body,
        client: communication.clientId,
        template: communication.template ?? '',
        channel: communication.channel,
      });
    } else {
      setEditingCommunication(null);
      setEditorState(DEFAULT_EDITOR_STATE);
    }
    setShowEditor(true);
  };

  const closeEditor = () => {
    setShowEditor(false);
    setEditingCommunication(null);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await create({
        subject: editorState.subject,
        content: editorState.body,
        channel: editorState.channel,
        client_id: editorState.client
          ? parseInt(editorState.client, 10)
          : undefined,
      });
      toast.success('Comunicazione salvata con successo');
      closeEditor();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : 'Errore nel salvataggio'
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleSubmitForReview = useCallback(
    async (id: string) => {
      try {
        await submit(id);
        toast.success('Comunicazione inviata per revisione');
      } catch (err) {
        toast.error(
          err instanceof Error ? err.message : "Errore nell'invio per revisione"
        );
      }
    },
    [submit]
  );

  const handleApprove = useCallback(
    async (id: string) => {
      try {
        await approve(id);
        toast.success('Comunicazione approvata');
      } catch (err) {
        toast.error(
          err instanceof Error ? err.message : "Errore nell'approvazione"
        );
      }
    },
    [approve]
  );

  const handleSend = useCallback(
    async (id: string) => {
      try {
        await send(id);
        toast.success('Comunicazione inviata con successo');
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Errore nell'invio");
      }
    },
    [send]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await remove(id);
        toast.success('Comunicazione eliminata');
      } catch (err) {
        toast.error(
          err instanceof Error ? err.message : "Errore nell'eliminazione"
        );
      }
    },
    [remove]
  );

  const handleBulkApprove = useCallback(async () => {
    const ids = Array.from(selectedCommunications);
    try {
      await Promise.all(ids.map(id => approve(id)));
      toast.success(`${ids.length} comunicazioni approvate`);
      setSelectedCommunications(new Set());
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Errore nell'approvazione"
      );
    }
  }, [selectedCommunications, approve]);

  const handleBulkSend = useCallback(async () => {
    const ids = Array.from(selectedCommunications);
    try {
      await Promise.all(ids.map(id => send(id)));
      toast.success(`${ids.length} comunicazioni inviate`);
      setSelectedCommunications(new Set());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Errore nell'invio");
    }
  }, [selectedCommunications, send]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F8F5F1] flex flex-col items-center justify-center">
        <Loader2 className="w-10 h-10 text-[#2A5D67] animate-spin mb-4" />
        <p className="text-[#1E293B] text-lg">Caricamento comunicazioni...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#F8F5F1] flex flex-col items-center justify-center">
        <AlertCircle className="w-10 h-10 text-red-500 mb-4" />
        <p className="text-[#1E293B] text-lg mb-4">{error}</p>
        <Button
          onClick={refresh}
          className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
        >
          Riprova
        </Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      <div className="bg-white shadow-sm border-b border-[#C4BDB4]/20 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                onClick={() => router.push('/chat')}
                className="text-[#2A5D67] hover:bg-[#F8F5F1]"
              >
                <ArrowLeft className="w-5 h-5 mr-2" />
                Indietro
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-[#2A5D67]">
                  Gestione Comunicazioni
                </h1>
                <p className="text-sm text-[#1E293B]">
                  Gestisci e invia comunicazioni ai tuoi clienti
                </p>
              </div>
            </div>
            <Button
              onClick={() => openEditor()}
              className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
            >
              <Plus className="w-4 h-4 mr-2" />
              <span className="font-bold">Nuova Comunicazione</span>
            </Button>
          </div>
        </div>
      </div>

      <ComunicazioniStatsBar stats={stats} />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ComunicazioniFilterTabs
          activeTab={activeTab}
          onTabChange={setActiveTab}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          selectedCount={selectedCommunications.size}
          filteredCount={filteredCommunications.length}
          stats={stats}
          onSelectAll={toggleSelectAll}
          onBulkApprove={handleBulkApprove}
          onBulkSend={handleBulkSend}
        />

        <div className="space-y-4">
          <AnimatePresence mode="popLayout">
            {filteredCommunications.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="bg-white rounded-lg shadow-sm border border-[#C4BDB4]/20 p-12 text-center"
              >
                <AlertCircle className="w-12 h-12 text-[#C4BDB4] mx-auto mb-4" />
                <p className="text-lg text-[#1E293B] mb-2">
                  Nessuna comunicazione trovata
                </p>
                <p className="text-sm text-[#C4BDB4]">
                  {searchQuery
                    ? 'Prova a modificare i filtri di ricerca'
                    : 'Inizia creando una nuova comunicazione'}
                </p>
              </motion.div>
            ) : (
              filteredCommunications.map((communication, index) => (
                <ComunicazioneCard
                  key={communication.id}
                  communication={communication}
                  isSelected={selectedCommunications.has(communication.id)}
                  animationDelay={index * 0.05}
                  onSelect={toggleSelect}
                  onEdit={openEditor}
                  onSubmitForReview={handleSubmitForReview}
                  onApprove={handleApprove}
                  onSend={handleSend}
                  onDelete={handleDelete}
                />
              ))
            )}
          </AnimatePresence>
        </div>
      </div>

      <ComunicazioneEditorModal
        isOpen={showEditor}
        editingCommunication={editingCommunication}
        editorState={editorState}
        clients={clients}
        isSaving={isSaving}
        onClose={closeEditor}
        onSave={handleSave}
        onSubjectChange={v => setEditorState(s => ({ ...s, subject: v }))}
        onBodyChange={v => setEditorState(s => ({ ...s, body: v }))}
        onClientChange={v => setEditorState(s => ({ ...s, client: v }))}
        onTemplateChange={v => setEditorState(s => ({ ...s, template: v }))}
        onChannelChange={v => setEditorState(s => ({ ...s, channel: v }))}
      />
    </div>
  );
}
