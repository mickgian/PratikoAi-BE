'use client';

import { useMemo, useState } from 'react';
import {
  ArrowLeft,
  Search,
  Filter,
  Plus,
  Download,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { motion } from 'motion/react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useClients } from '@/lib/hooks/useClients';
import type { ClientResponse } from '@/lib/api/clients';
import type { Cliente, StatoTab, TipoSoggetto, RegimeFiscale } from '../types';
import { ClientListTable } from './ClientListTable';
import { ClientListBulkActions } from './ClientListBulkActions';

const ITEMS_PER_PAGE = 10;

/** Map backend stato tab values to API enum values. */
function mapStatoToApi(tab: StatoTab): string | undefined {
  if (tab === 'attivi') return 'ATTIVO';
  if (tab === 'prospect') return 'PROSPECT';
  return undefined;
}

/** Map a backend ClientResponse to the display Cliente type. */
function toCliente(c: ClientResponse): Cliente {
  return {
    id: String(c.id),
    denominazione: c.nome,
    codiceFiscale: c.codice_fiscale,
    tipoSoggetto: (c.tipo_cliente || 'persona_fisica') as TipoSoggetto,
    regimeFiscale: 'ordinario' as RegimeFiscale,
    codiceAteco: '',
    nDipendenti: 0,
    tags: [],
    statoCliente:
      c.stato_cliente?.toLowerCase() === 'prospect' ? 'prospect' : 'attivo',
  };
}

export function ClientListView() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [tipoSoggettoFilter, setTipoSoggettoFilter] = useState<string>('tutti');
  const [regimeFiscaleFilter, setRegimeFiscaleFilter] =
    useState<string>('tutti');
  const [statoTab, setStatoTab] = useState<StatoTab>('tutti');
  const [selectedClients, setSelectedClients] = useState<Set<string>>(
    new Set()
  );
  const [currentPage, setCurrentPage] = useState(1);

  const apiParams = useMemo(
    () => ({
      offset: (currentPage - 1) * ITEMS_PER_PAGE,
      limit: ITEMS_PER_PAGE,
      stato: mapStatoToApi(statoTab),
    }),
    [currentPage, statoTab]
  );

  const {
    clients: rawClients,
    total,
    isLoading,
    error,
    refresh,
  } = useClients(apiParams);

  const allClients = useMemo(() => rawClients.map(toCliente), [rawClients]);

  /** Client-side filtering for search and tipo/regime (not supported by API). */
  const filteredClients = useMemo(() => {
    return allClients.filter(cliente => {
      const matchesSearch =
        !searchQuery ||
        cliente.denominazione
          .toLowerCase()
          .includes(searchQuery.toLowerCase()) ||
        cliente.codiceFiscale.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesTipo =
        tipoSoggettoFilter === 'tutti' ||
        cliente.tipoSoggetto === tipoSoggettoFilter;
      const matchesRegime =
        regimeFiscaleFilter === 'tutti' ||
        cliente.regimeFiscale === regimeFiscaleFilter;
      return matchesSearch && matchesTipo && matchesRegime;
    });
  }, [allClients, searchQuery, tipoSoggettoFilter, regimeFiscaleFilter]);

  const totalClients =
    searchQuery ||
    tipoSoggettoFilter !== 'tutti' ||
    regimeFiscaleFilter !== 'tutti'
      ? filteredClients.length
      : total;

  const handleSelectAll = (checked: boolean) => {
    setSelectedClients(
      checked ? new Set(filteredClients.map(c => c.id)) : new Set()
    );
  };

  const handleSelectClient = (clientId: string, checked: boolean) => {
    const next = new Set(selectedClients);
    if (checked) next.add(clientId);
    else next.delete(clientId);
    setSelectedClients(next);
  };

  const handleTabChange = (tab: StatoTab) => {
    setStatoTab(tab);
    setCurrentPage(1);
    setSelectedClients(new Set());
  };

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
                onClick={() => router.push('/chat')}
                className="text-[#2A5D67] hover:bg-[#F8F5F1]"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Indietro
              </Button>
              <div>
                <h1 className="text-2xl text-[#2A5D67]">Database Clienti</h1>
                <p className="text-sm text-[#1E293B] opacity-70">
                  Gestisci i tuoi clienti e i loro dati fiscali
                </p>
              </div>
            </div>
            <Button
              onClick={() => router.push('/database-clienti/import')}
              variant="outline"
              className="border-[#2A5D67] text-[#2A5D67] hover:bg-[#2A5D67] hover:text-white"
            >
              <Download className="w-4 h-4 mr-2" />
              Importa Clienti
            </Button>
          </div>
        </div>
      </motion.header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-lg shadow-sm border border-[#C4BDB4] p-6 mb-6"
        >
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="md:col-span-2 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-[#C4BDB4]" />
              <Input
                type="text"
                placeholder="Cerca per nome o codice fiscale..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-10 bg-[#F8F5F1] border-[#C4BDB4]"
              />
            </div>
            <Select
              value={tipoSoggettoFilter}
              onValueChange={setTipoSoggettoFilter}
            >
              <SelectTrigger className="bg-[#F8F5F1] border-[#C4BDB4]">
                <Filter className="w-4 h-4 mr-2 text-[#2A5D67]" />
                <SelectValue placeholder="Tipo Soggetto" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tutti">Tutti i Tipi</SelectItem>
                <SelectItem value="persona_fisica">Persona Fisica</SelectItem>
                <SelectItem value="ditta_individuale">
                  Ditta Individuale
                </SelectItem>
                <SelectItem value="societa_persone">
                  Società di Persone
                </SelectItem>
                <SelectItem value="societa_capitali">
                  Società di Capitali
                </SelectItem>
                <SelectItem value="ente_no_profit">Ente No Profit</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={regimeFiscaleFilter}
              onValueChange={setRegimeFiscaleFilter}
            >
              <SelectTrigger className="bg-[#F8F5F1] border-[#C4BDB4]">
                <Filter className="w-4 h-4 mr-2 text-[#2A5D67]" />
                <SelectValue placeholder="Regime Fiscale" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tutti">Tutti i Regimi</SelectItem>
                <SelectItem value="ordinario">Ordinario</SelectItem>
                <SelectItem value="semplificato">Semplificato</SelectItem>
                <SelectItem value="forfettario">Forfettario</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex gap-2 mt-4 border-t border-[#C4BDB4] pt-4">
            {(['tutti', 'attivi', 'prospect'] as StatoTab[]).map(tab => (
              <button
                key={tab}
                onClick={() => handleTabChange(tab)}
                className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                  statoTab === tab
                    ? 'bg-[#2A5D67] text-white'
                    : 'bg-[#F8F5F1] text-[#1E293B] hover:bg-[#C4BDB4]'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
        </motion.div>

        {selectedClients.size > 0 && (
          <ClientListBulkActions
            selectedCount={selectedClients.size}
            onDeselect={() => setSelectedClients(new Set())}
          />
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-[#2A5D67] animate-spin mb-4" />
            <p className="text-[#1E293B] opacity-70">
              Caricamento clienti in corso...
            </p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-20">
            <AlertCircle className="w-8 h-8 text-red-500 mb-4" />
            <p className="text-[#1E293B] mb-4">{error}</p>
            <Button
              onClick={refresh}
              className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
            >
              Riprova
            </Button>
          </div>
        ) : (
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="bg-white rounded-lg shadow-sm border border-[#C4BDB4] overflow-hidden"
          >
            <ClientListTable
              clients={filteredClients}
              selectedClients={selectedClients}
              currentPage={currentPage}
              itemsPerPage={ITEMS_PER_PAGE}
              totalClients={totalClients}
              onSelectAll={handleSelectAll}
              onSelectClient={handleSelectClient}
              onNavigateToDetail={id => router.push(`/database-clienti/${id}`)}
              onNavigateToImport={() => router.push('/database-clienti/import')}
              onPageChange={setCurrentPage}
            />
          </motion.div>
        )}
      </div>

      <motion.button
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.5, type: 'spring', stiffness: 200 }}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => router.push('/database-clienti/new')}
        className="fixed bottom-8 right-8 w-14 h-14 bg-[#2A5D67] text-white rounded-full shadow-2xl hover:bg-[#1E293B] transition-colors flex items-center justify-center z-40"
      >
        <Plus className="w-6 h-6" />
      </motion.button>
    </div>
  );
}
