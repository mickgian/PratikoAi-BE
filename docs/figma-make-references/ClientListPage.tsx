"use client";

import React, { useState } from "react";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Search,
  Filter,
  Plus,
  Eye,
  Pencil,
  Trash2,
  Download,
  Mail,
  ChevronDown,
  X,
} from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Badge } from "./ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";
import { Checkbox } from "./ui/checkbox";
import { toast } from "sonner@2.0.3";

interface ClientListPageProps {
  onBackToHome: () => void;
  onNavigateToClientDetail: (clientId: string) => void;
  onNavigateToImport: () => void;
}

type TipoSoggetto =
  | "persona_fisica"
  | "ditta_individuale"
  | "societa_persone"
  | "societa_capitali"
  | "ente_no_profit";
type RegimeFiscale = "ordinario" | "semplificato" | "forfettario";
type StatoTab = "attivi" | "prospect" | "tutti";

interface Cliente {
  id: string;
  denominazione: string;
  codiceFiscale: string;
  tipoSoggetto: TipoSoggetto;
  regimeFiscale: RegimeFiscale;
  codiceAteco: string;
  nDipendenti: number;
  tags: string[];
  statoCliente: "attivo" | "prospect";
}

const mockClienti: Cliente[] = [
  {
    id: "1",
    denominazione: "Studio Legale Associato Rossi",
    codiceFiscale: "RSSMRA70A01F205X",
    tipoSoggetto: "societa_persone",
    regimeFiscale: "ordinario",
    codiceAteco: "69.10.10",
    nDipendenti: 8,
    tags: ["Priorità Alta", "Fiscale"],
    statoCliente: "attivo",
  },
  {
    id: "2",
    denominazione: "Bianchi Maria",
    codiceFiscale: "BNCMRA85B45H501Y",
    tipoSoggetto: "persona_fisica",
    regimeFiscale: "forfettario",
    codiceAteco: "62.01.00",
    nDipendenti: 0,
    tags: ["IT", "Startup"],
    statoCliente: "attivo",
  },
  {
    id: "3",
    denominazione: "Verdi S.r.l.",
    codiceFiscale: "12345678901",
    tipoSoggetto: "societa_capitali",
    regimeFiscale: "ordinario",
    codiceAteco: "47.11.30",
    nDipendenti: 24,
    tags: ["Retail", "Grande Cliente"],
    statoCliente: "attivo",
  },
  {
    id: "4",
    denominazione: "Neri Giuseppe",
    codiceFiscale: "NREGPP78C12D612Z",
    tipoSoggetto: "ditta_individuale",
    regimeFiscale: "semplificato",
    codiceAteco: "43.21.01",
    nDipendenti: 3,
    tags: ["Edilizia"],
    statoCliente: "attivo",
  },
  {
    id: "5",
    denominazione: "Fondazione Cultura e Arte",
    codiceFiscale: "98765432109",
    tipoSoggetto: "ente_no_profit",
    regimeFiscale: "ordinario",
    codiceAteco: "90.03.09",
    nDipendenti: 12,
    tags: ["Non Profit", "Cultura"],
    statoCliente: "attivo",
  },
  {
    id: "6",
    denominazione: "Gialli Consulting S.a.s.",
    codiceFiscale: "11223344556",
    tipoSoggetto: "societa_persone",
    regimeFiscale: "ordinario",
    codiceAteco: "70.22.09",
    nDipendenti: 5,
    tags: ["Consulting"],
    statoCliente: "prospect",
  },
  {
    id: "7",
    denominazione: "Azzurri Tech Solutions",
    codiceFiscale: "22334455667",
    tipoSoggetto: "societa_capitali",
    regimeFiscale: "ordinario",
    codiceAteco: "62.02.00",
    nDipendenti: 45,
    tags: ["IT", "Software", "Grande Cliente"],
    statoCliente: "prospect",
  },
];

const tipoSoggettoLabels: Record<TipoSoggetto, string> = {
  persona_fisica: "Persona Fisica",
  ditta_individuale: "Ditta Individuale",
  societa_persone: "Società di Persone",
  societa_capitali: "Società di Capitali",
  ente_no_profit: "Ente No Profit",
};

const regimeFiscaleLabels: Record<RegimeFiscale, string> = {
  ordinario: "Ordinario",
  semplificato: "Semplificato",
  forfettario: "Forfettario",
};

export function ClientListPage({
  onBackToHome,
  onNavigateToClientDetail,
  onNavigateToImport,
}: ClientListPageProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [tipoSoggettoFilter, setTipoSoggettoFilter] = useState<string>("tutti");
  const [regimeFiscaleFilter, setRegimeFiscaleFilter] =
    useState<string>("tutti");
  const [statoTab, setStatoTab] = useState<StatoTab>("tutti");
  const [selectedClients, setSelectedClients] = useState<Set<string>>(
    new Set(),
  );
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Filter clients
  const filteredClients = mockClienti.filter((cliente) => {
    const matchesSearch =
      cliente.denominazione.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cliente.codiceFiscale.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesTipo =
      tipoSoggettoFilter === "tutti" ||
      cliente.tipoSoggetto === tipoSoggettoFilter;
    const matchesRegime =
      regimeFiscaleFilter === "tutti" ||
      cliente.regimeFiscale === regimeFiscaleFilter;
    const matchesStato =
      statoTab === "tutti" ||
      cliente.statoCliente === statoTab.replace("i", "o");

    return matchesSearch && matchesTipo && matchesRegime && matchesStato;
  });

  const totalClients = filteredClients.length;
  const paginatedClients = filteredClients.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage,
  );

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedClients(new Set(paginatedClients.map((c) => c.id)));
    } else {
      setSelectedClients(new Set());
    }
  };

  const handleSelectClient = (clientId: string, checked: boolean) => {
    const newSelected = new Set(selectedClients);
    if (checked) {
      newSelected.add(clientId);
    } else {
      newSelected.delete(clientId);
    }
    setSelectedClients(newSelected);
  };

  const handleBulkExport = () => {
    toast.success(`Esportati ${selectedClients.size} clienti in formato Excel`);
    setSelectedClients(new Set());
  };

  const handleBulkCommunication = () => {
    toast.success(
      `Preparata comunicazione per ${selectedClients.size} clienti`,
    );
    setSelectedClients(new Set());
  };

  const handleDeleteClient = (clientId: string, denominazione: string) => {
    toast.success(`Cliente "${denominazione}" eliminato`);
  };

  const maskCodiceFiscale = (cf: string) => {
    if (cf.length <= 4) return cf;
    return "***" + cf.slice(-4);
  };

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      {/* Header */}
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
                onClick={onBackToHome}
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
              onClick={onNavigateToImport}
              variant="outline"
              className="border-[#2A5D67] text-[#2A5D67] hover:bg-[#2A5D67] hover:text-white"
            >
              <Download className="w-4 h-4 mr-2" />
              Importa da Excel
            </Button>
          </div>
        </div>
      </motion.header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search and Filters */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-lg shadow-sm border border-[#C4BDB4] p-6 mb-6"
        >
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <div className="md:col-span-2 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-[#C4BDB4]" />
              <Input
                type="text"
                placeholder="Cerca per nome o codice fiscale..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-[#F8F5F1] border-[#C4BDB4]"
              />
            </div>

            {/* Tipo Soggetto Filter */}
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

            {/* Regime Fiscale Filter */}
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

          {/* Stato Tabs */}
          <div className="flex gap-2 mt-4 border-t border-[#C4BDB4] pt-4">
            {(["tutti", "attivi", "prospect"] as StatoTab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setStatoTab(tab)}
                className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                  statoTab === tab
                    ? "bg-[#2A5D67] text-white"
                    : "bg-[#F8F5F1] text-[#1E293B] hover:bg-[#C4BDB4]"
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Bulk Actions Bar */}
        {selectedClients.size > 0 && (
          <motion.div
            initial={{ y: -10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="bg-[#D4A574] rounded-lg p-4 mb-6 flex items-center justify-between"
          >
            <div className="flex items-center gap-4">
              <span className="text-[#1E293B]">
                {selectedClients.size} clienti selezionati
              </span>
              <Button
                onClick={() => setSelectedClients(new Set())}
                variant="ghost"
                size="sm"
                className="text-[#1E293B] hover:bg-white/20"
              >
                <X className="w-4 h-4 mr-1" />
                Deseleziona
              </Button>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={handleBulkExport}
                variant="outline"
                size="sm"
                className="bg-white border-[#1E293B] text-[#1E293B] hover:bg-[#F8F5F1]"
              >
                <Download className="w-4 h-4 mr-2" />
                Esporta
              </Button>
              <Button
                onClick={handleBulkCommunication}
                variant="outline"
                size="sm"
                className="bg-white border-[#1E293B] text-[#1E293B] hover:bg-[#F8F5F1]"
              >
                <Mail className="w-4 h-4 mr-2" />
                Crea comunicazione
              </Button>
            </div>
          </motion.div>
        )}

        {/* Table */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-lg shadow-sm border border-[#C4BDB4] overflow-hidden"
        >
          {paginatedClients.length > 0 ? (
            <>
              <Table>
                <TableHeader>
                  <TableRow className="bg-[#F8F5F1] hover:bg-[#F8F5F1]">
                    <TableHead className="w-12">
                      <Checkbox
                        checked={
                          paginatedClients.length > 0 &&
                          paginatedClients.every((c) =>
                            selectedClients.has(c.id),
                          )
                        }
                        onCheckedChange={handleSelectAll}
                      />
                    </TableHead>
                    <TableHead className="text-[#2A5D67]">
                      Nome/Ragione Sociale
                    </TableHead>
                    <TableHead className="text-[#2A5D67]">
                      Codice Fiscale
                    </TableHead>
                    <TableHead className="text-[#2A5D67]">Tipo</TableHead>
                    <TableHead className="text-[#2A5D67]">Regime</TableHead>
                    <TableHead className="text-[#2A5D67]">ATECO</TableHead>
                    <TableHead className="text-[#2A5D67]">Dipendenti</TableHead>
                    <TableHead className="text-[#2A5D67]">Tags</TableHead>
                    <TableHead className="text-[#2A5D67] text-right">
                      Azioni
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedClients.map((cliente, index) => (
                    <motion.tr
                      key={cliente.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="border-b border-[#C4BDB4] hover:bg-[#F8F5F1] transition-colors"
                    >
                      <TableCell>
                        <Checkbox
                          checked={selectedClients.has(cliente.id)}
                          onCheckedChange={(checked) =>
                            handleSelectClient(cliente.id, checked as boolean)
                          }
                        />
                      </TableCell>
                      <TableCell className="text-[#1E293B]">
                        {cliente.denominazione}
                      </TableCell>
                      <TableCell className="text-[#1E293B] font-mono text-sm">
                        {maskCodiceFiscale(cliente.codiceFiscale)}
                      </TableCell>
                      <TableCell>
                        <span className="text-xs text-[#1E293B]">
                          {tipoSoggettoLabels[cliente.tipoSoggetto]}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className="border-[#2A5D67] text-[#2A5D67] bg-[#2A5D67]/5"
                        >
                          {regimeFiscaleLabels[cliente.regimeFiscale]}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-[#1E293B] font-mono text-sm">
                        {cliente.codiceAteco}
                      </TableCell>
                      <TableCell className="text-[#1E293B]">
                        {cliente.nDipendenti}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {cliente.tags.map((tag) => (
                            <Badge
                              key={tag}
                              variant="secondary"
                              className="bg-[#D4A574]/20 text-[#1E293B] border-none text-xs"
                            >
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onNavigateToClientDetail(cliente.id)}
                            className="hover:bg-[#2A5D67]/10"
                          >
                            <Pencil className="w-4 h-4 text-[#2A5D67]" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              handleDeleteClient(
                                cliente.id,
                                cliente.denominazione,
                              )
                            }
                            className="hover:bg-red-50"
                          >
                            <Trash2 className="w-4 h-4 text-red-600" />
                          </Button>
                        </div>
                      </TableCell>
                    </motion.tr>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              <div className="px-6 py-4 border-t border-[#C4BDB4] flex items-center justify-between">
                <p className="text-sm text-[#1E293B]">
                  Mostrando {(currentPage - 1) * itemsPerPage + 1}-
                  {Math.min(currentPage * itemsPerPage, totalClients)} di{" "}
                  {totalClients} clienti
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="border-[#C4BDB4]"
                  >
                    Precedente
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage((p) => p + 1)}
                    disabled={currentPage * itemsPerPage >= totalClients}
                    className="border-[#C4BDB4]"
                  >
                    Successivo
                  </Button>
                </div>
              </div>
            </>
          ) : (
            /* Empty State */
            <div className="py-16 px-4 text-center">
              <div className="w-24 h-24 mx-auto mb-4 rounded-full bg-[#F8F5F1] flex items-center justify-center">
                <Search className="w-12 h-12 text-[#C4BDB4]" />
              </div>
              <h3 className="text-[#1E293B] mb-2">Nessun cliente trovato</h3>
              <p className="text-[#1E293B] opacity-70 mb-6">
                Importa da Excel o aggiungi manualmente il tuo primo cliente
              </p>
              <div className="flex gap-3 justify-center">
                <Button
                  onClick={onNavigateToImport}
                  className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Importa da Excel
                </Button>
                <Button
                  onClick={() => onNavigateToClientDetail("new")}
                  variant="outline"
                  className="border-[#2A5D67] text-[#2A5D67] hover:bg-[#F8F5F1]"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Aggiungi Manualmente
                </Button>
              </div>
            </div>
          )}
        </motion.div>
      </div>

      {/* FAB - Add Client */}
      <motion.button
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.5, type: "spring", stiffness: 200 }}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => onNavigateToClientDetail("new")}
        className="fixed bottom-8 right-8 w-14 h-14 bg-[#2A5D67] text-white rounded-full shadow-2xl hover:bg-[#1E293B] transition-colors flex items-center justify-center z-40"
      >
        <Plus className="w-6 h-6" />
      </motion.button>
    </div>
  );
}
