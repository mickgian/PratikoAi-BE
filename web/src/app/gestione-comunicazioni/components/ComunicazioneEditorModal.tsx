'use client';

import { motion, AnimatePresence } from 'motion/react';
import { X, Mail, MessageCircle, Check, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { Communication, CommunicationChannel } from '../types';

const TEMPLATES = [
  { id: 'normativa_update', name: 'Aggiornamento Normativo' },
  { id: 'scadenza_reminder', name: 'Promemoria Scadenza' },
  { id: 'opportunita_fiscale', name: 'Opportunità Fiscale' },
  { id: 'richiesta_documenti', name: 'Richiesta Documenti' },
  { id: 'custom', name: 'Personalizzata' },
];

interface EditorState {
  subject: string;
  body: string;
  client: string;
  template: string;
  channel: CommunicationChannel;
}

interface ClientOption {
  id: number;
  name: string;
}

interface ComunicazioneEditorModalProps {
  isOpen: boolean;
  editingCommunication: Communication | null;
  editorState: EditorState;
  clients: ClientOption[];
  isSaving: boolean;
  onClose: () => void;
  onSave: () => void;
  onSubjectChange: (value: string) => void;
  onBodyChange: (value: string) => void;
  onClientChange: (value: string) => void;
  onTemplateChange: (value: string) => void;
  onChannelChange: (value: CommunicationChannel) => void;
}

export function ComunicazioneEditorModal({
  isOpen,
  editingCommunication,
  editorState,
  clients,
  isSaving,
  onClose,
  onSave,
  onSubjectChange,
  onBodyChange,
  onClientChange,
  onTemplateChange,
  onChannelChange,
}: ComunicazioneEditorModalProps) {
  const canSave = editorState.client && editorState.subject && editorState.body;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="fixed inset-4 md:inset-auto md:top-1/2 md:left-1/2 md:transform md:-translate-x-1/2 md:-translate-y-1/2 bg-white rounded-lg shadow-2xl z-50 md:w-full md:max-w-3xl max-h-[90vh] overflow-hidden flex flex-col"
          >
            <div className="flex items-center justify-between p-6 border-b border-[#C4BDB4]/20">
              <h2 className="text-2xl font-bold text-[#2A5D67]">
                {editingCommunication
                  ? 'Modifica Comunicazione'
                  : 'Nuova Comunicazione'}
              </h2>
              <button
                onClick={onClose}
                className="text-[#C4BDB4] hover:text-[#2A5D67] transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div>
                <label className="block text-sm font-medium text-[#1E293B] mb-2">
                  Cliente *
                </label>
                <Select
                  value={editorState.client}
                  onValueChange={onClientChange}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleziona un cliente" />
                  </SelectTrigger>
                  <SelectContent>
                    {clients.map(client => (
                      <SelectItem key={client.id} value={String(client.id)}>
                        {client.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#1E293B] mb-2">
                  Template
                </label>
                <Select
                  value={editorState.template}
                  onValueChange={onTemplateChange}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleziona un template (opzionale)" />
                  </SelectTrigger>
                  <SelectContent>
                    {TEMPLATES.map(template => (
                      <SelectItem key={template.id} value={template.id}>
                        {template.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#1E293B] mb-2">
                  Canale *
                </label>
                <div className="flex space-x-4">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => onChannelChange('email')}
                    className={`flex-1 flex items-center justify-center space-x-2 p-4 rounded-lg border-2 transition-all ${
                      editorState.channel === 'email'
                        ? 'border-[#2A5D67] bg-[#F8F5F1]'
                        : 'border-[#C4BDB4]/20 hover:border-[#C4BDB4]'
                    }`}
                  >
                    <Mail className="w-5 h-5" />
                    <span className="font-medium">Email</span>
                  </motion.button>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => onChannelChange('whatsapp')}
                    className={`flex-1 flex items-center justify-center space-x-2 p-4 rounded-lg border-2 transition-all ${
                      editorState.channel === 'whatsapp'
                        ? 'border-[#2A5D67] bg-[#F8F5F1]'
                        : 'border-[#C4BDB4]/20 hover:border-[#C4BDB4]'
                    }`}
                  >
                    <MessageCircle className="w-5 h-5" />
                    <span className="font-medium">WhatsApp</span>
                  </motion.button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#1E293B] mb-2">
                  Oggetto *
                </label>
                <Input
                  type="text"
                  value={editorState.subject}
                  onChange={e => onSubjectChange(e.target.value)}
                  placeholder="Inserisci l'oggetto della comunicazione"
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[#1E293B] mb-2">
                  Contenuto *
                </label>
                <Textarea
                  value={editorState.body}
                  onChange={e => onBodyChange(e.target.value)}
                  placeholder="Scrivi il contenuto della comunicazione..."
                  className="w-full min-h-[300px] resize-none"
                />
                <p className="text-xs text-[#C4BDB4] mt-2">
                  {editorState.body.length} caratteri
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-3 p-6 border-t border-[#C4BDB4]/20 bg-[#F8F5F1]">
              <Button
                onClick={onClose}
                variant="outline"
                className="text-[#1E293B]"
              >
                Annulla
              </Button>
              <Button
                onClick={onSave}
                disabled={!canSave || isSaving}
                className={`${
                  canSave && !isSaving
                    ? 'bg-[#2A5D67] hover:bg-[#1E293B] text-white'
                    : 'bg-[#C4BDB4] text-white cursor-not-allowed'
                }`}
              >
                {isSaving ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Check className="w-4 h-4 mr-2" />
                )}
                <span className="font-bold">
                  {isSaving ? 'Salvataggio...' : 'Salva Bozza'}
                </span>
              </Button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
