'use client';

import { useEffect, useState } from 'react';
import {
  ArrowLeft,
  Save,
  X,
  Building2,
  FileText,
  Users,
  Home,
  Tag,
  Loader2,
  AlertCircle,
  Trash2,
} from 'lucide-react';
import { motion } from 'motion/react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useClient } from '@/lib/hooks/useClients';
import type { ClientResponse } from '@/lib/api/clients';
import type { ClientFormData } from '../types';
import { initialFormData } from '../data/constants';
import { ClientDetailTabAnagrafica } from './ClientDetailTabAnagrafica';
import { ClientDetailTabFiscali } from './ClientDetailTabFiscali';
import { ClientDetailTabLavoro } from './ClientDetailTabLavoro';
import { ClientDetailTabImmobili } from './ClientDetailTabImmobili';
import { ClientDetailTabTags } from './ClientDetailTabTags';

interface ClientDetailViewProps {
  clientId: string;
}

/** Map a backend ClientResponse into the form's ClientFormData. */
function mapResponseToFormData(c: ClientResponse): ClientFormData {
  return {
    denominazione: c.nome || '',
    codiceFiscale: c.codice_fiscale || '',
    partitaIva: c.partita_iva || '',
    tipoSoggetto: c.tipo_cliente || '',
    indirizzo: c.indirizzo || '',
    cap: c.cap || '',
    comune: c.comune || '',
    provincia: c.provincia || '',
    regimeFiscale: '',
    codiceAteco: '',
    dataInizioAttivita: '',
    posizioneAgenziaEntrate: '',
    haCartelleEsattoriali: false,
    numeroDipendenti: '0',
    ccnlApplicato: '',
    haApprendisti: false,
    haLavoratoriStagionali: false,
    immobili: [],
    tags: [],
    note: c.note_studio || '',
  };
}

export function ClientDetailView({ clientId }: ClientDetailViewProps) {
  const router = useRouter();
  const isNew = clientId === 'new';
  const { client, isLoading, error, save, remove } = useClient(clientId);

  const [formData, setFormData] = useState<ClientFormData>(initialFormData);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState('anagrafica');
  const [isSaving, setIsSaving] = useState(false);
  const [formInitialized, setFormInitialized] = useState(isNew);

  /** Populate form when backend data arrives. */
  useEffect(() => {
    if (client && !isNew) {
      setFormData(mapResponseToFormData(client));
      setFormInitialized(true);
    }
  }, [client, isNew]);

  const updateField = (field: keyof ClientFormData, value: unknown) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!formData.denominazione.trim()) {
      newErrors.denominazione = 'Denominazione obbligatoria';
    }
    if (!formData.codiceFiscale.trim()) {
      newErrors.codiceFiscale = 'Codice fiscale obbligatorio';
    } else if (
      !/^[A-Z0-9]{11,16}$/.test(formData.codiceFiscale.toUpperCase())
    ) {
      newErrors.codiceFiscale = 'Formato codice fiscale non valido';
    }
    if (!formData.tipoSoggetto)
      newErrors.tipoSoggetto = 'Seleziona tipo soggetto';
    if (!formData.regimeFiscale)
      newErrors.regimeFiscale = 'Seleziona regime fiscale';
    if (!formData.codiceAteco.trim())
      newErrors.codiceAteco = 'Codice ATECO obbligatorio';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validateForm()) {
      toast.error('Correggi gli errori nel form prima di salvare');
      return;
    }
    setIsSaving(true);
    try {
      await save({
        nome: formData.denominazione,
        codice_fiscale: formData.codiceFiscale,
        tipo_cliente: formData.tipoSoggetto,
        comune: formData.comune,
        provincia: formData.provincia,
        partita_iva: formData.partitaIva || undefined,
        email: undefined,
        phone: undefined,
        indirizzo: formData.indirizzo || undefined,
        cap: formData.cap || undefined,
        note_studio: formData.note || undefined,
      });
      const action = isNew ? 'aggiunto' : 'aggiornato';
      toast.success(
        `Cliente "${formData.denominazione}" ${action} con successo`
      );
      setTimeout(() => router.push('/database-clienti'), 1000);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : 'Errore nel salvataggio'
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      await remove();
      toast.success(
        `Cliente "${formData.denominazione}" eliminato con successo`
      );
      setTimeout(() => router.push('/database-clienti'), 1000);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Errore nell'eliminazione"
      );
    }
  };

  const tabTriggerClass =
    'data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-[#2A5D67] rounded-none py-3 px-6';

  if (!isNew && isLoading) {
    return (
      <div className="min-h-screen bg-[#F8F5F1] flex flex-col items-center justify-center">
        <Loader2 className="w-8 h-8 text-[#2A5D67] animate-spin mb-4" />
        <p className="text-[#1E293B] opacity-70">Caricamento dati cliente...</p>
      </div>
    );
  }

  if (!isNew && error) {
    return (
      <div className="min-h-screen bg-[#F8F5F1] flex flex-col items-center justify-center">
        <AlertCircle className="w-8 h-8 text-red-500 mb-4" />
        <p className="text-[#1E293B] mb-4">{error}</p>
        <Button
          onClick={() => router.push('/database-clienti')}
          className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
        >
          Torna alla lista
        </Button>
      </div>
    );
  }

  if (!formInitialized) {
    return (
      <div className="min-h-screen bg-[#F8F5F1] flex flex-col items-center justify-center">
        <Loader2 className="w-8 h-8 text-[#2A5D67] animate-spin mb-4" />
        <p className="text-[#1E293B] opacity-70">Preparazione form...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="bg-white border-b border-[#C4BDB4] sticky top-0 z-30"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push('/database-clienti')}
                className="text-[#2A5D67] hover:bg-[#F8F5F1]"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Indietro
              </Button>
              <div>
                <h1 className="text-2xl text-[#2A5D67]">
                  {isNew ? 'Nuovo Cliente' : 'Modifica Cliente'}
                </h1>
                <p className="text-sm text-[#1E293B] opacity-70">
                  {isNew
                    ? 'Inserisci i dati del nuovo cliente'
                    : 'Aggiorna le informazioni del cliente'}
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              {!isNew && (
                <Button
                  variant="outline"
                  onClick={handleDelete}
                  className="border-red-300 text-red-600 hover:bg-red-50"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Elimina
                </Button>
              )}
              <Button
                variant="outline"
                onClick={() => router.push('/database-clienti')}
                className="border-[#C4BDB4] text-[#1E293B] hover:bg-[#F8F5F1]"
              >
                <X className="w-4 h-4 mr-2" />
                Annulla
              </Button>
              <Button
                onClick={handleSave}
                disabled={isSaving}
                className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
              >
                {isSaving ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Save className="w-4 h-4 mr-2" />
                )}
                Salva
              </Button>
            </div>
          </div>
        </div>
      </motion.header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-lg shadow-sm border border-[#C4BDB4] overflow-hidden"
        >
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="w-full"
          >
            <TabsList className="w-full justify-start bg-[#F8F5F1] border-b border-[#C4BDB4] rounded-none h-auto p-0">
              <TabsTrigger value="anagrafica" className={tabTriggerClass}>
                <Building2 className="w-4 h-4 mr-2" />
                Anagrafica
              </TabsTrigger>
              <TabsTrigger value="fiscali" className={tabTriggerClass}>
                <FileText className="w-4 h-4 mr-2" />
                Dati Fiscali
              </TabsTrigger>
              <TabsTrigger value="lavoro" className={tabTriggerClass}>
                <Users className="w-4 h-4 mr-2" />
                Lavoro
              </TabsTrigger>
              <TabsTrigger value="immobili" className={tabTriggerClass}>
                <Home className="w-4 h-4 mr-2" />
                Immobili
              </TabsTrigger>
              <TabsTrigger value="tags" className={tabTriggerClass}>
                <Tag className="w-4 h-4 mr-2" />
                Tags &amp; Note
              </TabsTrigger>
            </TabsList>
            <TabsContent value="anagrafica" className="p-6">
              <ClientDetailTabAnagrafica
                formData={formData}
                errors={errors}
                onUpdateField={updateField}
              />
            </TabsContent>
            <TabsContent value="fiscali" className="p-6">
              <ClientDetailTabFiscali
                formData={formData}
                errors={errors}
                onUpdateField={updateField}
              />
            </TabsContent>
            <TabsContent value="lavoro" className="p-6">
              <ClientDetailTabLavoro
                formData={formData}
                onUpdateField={updateField}
              />
            </TabsContent>
            <TabsContent value="immobili" className="p-6">
              <ClientDetailTabImmobili
                immobili={formData.immobili}
                onUpdateField={updateField}
              />
            </TabsContent>
            <TabsContent value="tags" className="p-6">
              <ClientDetailTabTags
                tags={formData.tags}
                note={formData.note}
                onUpdateField={updateField}
              />
            </TabsContent>
          </Tabs>
        </motion.div>
      </div>
    </div>
  );
}
