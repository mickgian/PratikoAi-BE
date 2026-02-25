"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Search,
  Building2,
  User,
  FileText,
  X,
  Database,
  Users,
} from "lucide-react";
import { Card } from "./ui/card";

export interface Client {
  id: string;
  name: string;
  codiceFiscale: string;
  regimeFiscale: "Forfettario" | "Ordinario" | "Semplificato";
  ateco: string;
  atecoDescription: string;
  posizione: string;
  activeProcedures?: string[];
  suggestedProcedures?: string[];
}

// Mock client data
export const mockClients: Client[] = [
  {
    id: "1",
    name: "Rossi S.r.l.",
    codiceFiscale: "RSSSRL85H01H501Z",
    regimeFiscale: "Ordinario",
    ateco: "47.91.10",
    atecoDescription: "Commercio al dettaglio per corrispondenza",
    posizione: "Milano, MI",
    activeProcedures: [
      "Dichiarazione IVA Trimestrale",
      "Bilancio Annuale S.r.l.",
    ],
    suggestedProcedures: ["Assunzione Dipendente"],
  },
  {
    id: "2",
    name: "Mario Rossi",
    codiceFiscale: "RSSMRA80A01H501X",
    regimeFiscale: "Forfettario",
    ateco: "62.01.00",
    atecoDescription: "Produzione di software non connesso all'edizione",
    posizione: "Roma, RM",
    activeProcedures: [],
    suggestedProcedures: [
      "Dichiarazione IVA Trimestrale",
      "Apertura S.r.l. Semplificata",
    ],
  },
  {
    id: "3",
    name: "Bianchi & Partners S.r.l.",
    codiceFiscale: "BNCPRT92L01F205W",
    regimeFiscale: "Ordinario",
    ateco: "69.20.11",
    atecoDescription:
      "Servizi forniti da revisori contabili, periti, consulenti",
    posizione: "Torino, TO",
    activeProcedures: ["Bilancio Annuale S.r.l."],
    suggestedProcedures: [],
  },
  {
    id: "4",
    name: "Verdi S.p.A.",
    codiceFiscale: "VRDSPA78C01L219Y",
    regimeFiscale: "Ordinario",
    ateco: "25.11.00",
    atecoDescription: "Fabbricazione di strutture metalliche",
    posizione: "Bologna, BO",
    activeProcedures: ["Dichiarazione IVA Trimestrale"],
    suggestedProcedures: ["Assunzione Dipendente", "Bilancio Annuale S.r.l."],
  },
  {
    id: "5",
    name: "Neri & Associati",
    codiceFiscale: "NRIASC85M01A944V",
    regimeFiscale: "Semplificato",
    ateco: "69.20.30",
    atecoDescription: "Servizi degli studi commerciali",
    posizione: "Napoli, NA",
    activeProcedures: ["Cessazione Attività Ditta Individuale"],
    suggestedProcedures: [],
  },
  {
    id: "6",
    name: "Ferrari S.r.l.",
    codiceFiscale: "FRRSRL90H01F839Z",
    regimeFiscale: "Ordinario",
    ateco: "56.10.11",
    atecoDescription: "Ristorazione con somministrazione",
    posizione: "Firenze, FI",
    activeProcedures: [],
    suggestedProcedures: [
      "Assunzione Dipendente",
      "Dichiarazione IVA Trimestrale",
    ],
  },
  {
    id: "7",
    name: "Mario Rossi",
    codiceFiscale: "RSSMRA75B15H501K",
    regimeFiscale: "Semplificato",
    ateco: "43.21.01",
    atecoDescription: "Installazione di impianti elettrici",
    posizione: "Genova, GE",
    activeProcedures: [],
    suggestedProcedures: ["Trasformazione da Ditta a S.r.l."],
  },
  {
    id: "8",
    name: "Colombo Consulting",
    codiceFiscale: "CLMCNS88D01L736P",
    regimeFiscale: "Forfettario",
    ateco: "70.22.09",
    atecoDescription:
      "Consulenza imprenditoriale e altra consulenza amministrativo-gestionale",
    posizione: "Padova, PD",
    activeProcedures: [],
    suggestedProcedures: [],
  },
];

const regimeConfig = {
  Forfettario: {
    color: "text-green-700",
    bg: "bg-green-50",
    border: "border-green-200",
  },
  Ordinario: {
    color: "text-blue-700",
    bg: "bg-blue-50",
    border: "border-blue-200",
  },
  Semplificato: {
    color: "text-orange-700",
    bg: "bg-orange-50",
    border: "border-orange-200",
  },
};

interface ClientMentionAutocompleteProps {
  searchQuery: string;
  onSelectClient: (client: Client) => void;
  onClose: () => void;
  isOpen: boolean;
}

// Helper function to highlight matching text
function highlightMatch(text: string, query: string) {
  if (!query.trim()) return <span>{text}</span>;

  const index = text.toLowerCase().indexOf(query.toLowerCase());
  if (index === -1) return <span>{text}</span>;

  return (
    <span>
      {text.substring(0, index)}
      <span className="bg-[#D4A574]/20 text-[#2A5D67] font-semibold">
        {text.substring(index, index + query.length)}
      </span>
      {text.substring(index + query.length)}
    </span>
  );
}

export function ClientMentionAutocomplete({
  searchQuery,
  onSelectClient,
  onClose,
  isOpen,
}: ClientMentionAutocompleteProps) {
  const [filteredClients, setFilteredClients] = useState<Client[]>(mockClients);

  useEffect(() => {
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      const filtered = mockClients.filter(
        (client) =>
          client.name.toLowerCase().includes(query) ||
          client.codiceFiscale.toLowerCase().includes(query),
      );
      setFilteredClients(filtered);
    } else {
      setFilteredClients(mockClients);
    }
  }, [searchQuery]);

  // Check for duplicate names to add CF disambiguation
  const getDuplicateNames = () => {
    const nameCount: { [key: string]: number } = {};
    mockClients.forEach((client) => {
      nameCount[client.name] = (nameCount[client.name] || 0) + 1;
    });
    return nameCount;
  };

  const duplicateNames = getDuplicateNames();

  const getDisplayName = (client: Client) => {
    if (duplicateNames[client.name] > 1) {
      const cfSuffix = client.codiceFiscale.substring(0, 10);
      return `${client.name} (${cfSuffix}...)`;
    }
    return client.name;
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 10, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 10, scale: 0.95 }}
        className="absolute bottom-full left-0 mb-2 w-full max-w-md z-50"
      >
        <Card className="shadow-2xl border-[#C4BDB4]/30 overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-[#F8F5F1] to-white px-4 py-3 border-b border-[#C4BDB4]/20 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Users className="w-4 h-4 text-[#2A5D67]" />
              <h4 className="text-sm font-semibold text-[#2A5D67]">
                Seleziona Cliente
                {searchQuery && (
                  <span className="ml-2 text-xs font-normal text-[#1E293B]/60">
                    "{searchQuery}"
                  </span>
                )}
              </h4>
            </div>
            <button
              onClick={onClose}
              className="text-[#1E293B]/60 hover:text-[#1E293B] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Client List */}
          <div className="max-h-[300px] overflow-y-auto">
            {filteredClients.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <Database className="w-10 h-10 mx-auto text-[#C4BDB4] mb-2" />
                <p className="text-sm text-[#1E293B]/60 mb-1">
                  {searchQuery
                    ? "Nessun cliente trovato"
                    : "Nessun cliente disponibile"}
                </p>
                <p className="text-xs text-[#1E293B]/40">
                  Importa i tuoi clienti per usare le menzioni @
                </p>
              </div>
            ) : (
              <div className="p-2 space-y-1">
                {filteredClients.map((client) => {
                  const regime = regimeConfig[client.regimeFiscale];
                  const displayName = getDisplayName(client);

                  return (
                    <button
                      key={client.id}
                      onClick={() => onSelectClient(client)}
                      className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg hover:bg-[#F8F5F1] transition-colors group text-left"
                    >
                      {/* Icon */}
                      <div className="flex-shrink-0 w-9 h-9 bg-[#2A5D67]/10 rounded-lg flex items-center justify-center group-hover:bg-[#2A5D67] transition-colors">
                        {client.name.includes("S.r.l.") ||
                        client.name.includes("S.p.A.") ? (
                          <Building2 className="w-4 h-4 text-[#2A5D67] group-hover:text-white transition-colors" />
                        ) : (
                          <User className="w-4 h-4 text-[#2A5D67] group-hover:text-white transition-colors" />
                        )}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <p className="font-semibold text-[#1E293B] text-sm truncate group-hover:text-[#2A5D67] transition-colors">
                            {highlightMatch(displayName, searchQuery)}
                          </p>
                        </div>
                        <div className="flex items-center space-x-2">
                          <p className="text-xs text-[#1E293B]/50 font-mono truncate">
                            {highlightMatch(client.codiceFiscale, searchQuery)}
                          </p>
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${regime.bg} ${regime.color} ${regime.border}`}
                          >
                            {client.regimeFiscale}
                          </span>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer hint */}
          {filteredClients.length > 0 && (
            <div className="px-4 py-2 bg-[#F8F5F1]/50 border-t border-[#C4BDB4]/20">
              <p className="text-xs text-[#1E293B]/50 text-center">
                <span className="font-mono bg-white px-1.5 py-0.5 rounded">
                  ↑↓
                </span>{" "}
                per navigare,
                <span className="font-mono bg-white px-1.5 py-0.5 rounded ml-1">
                  Enter
                </span>{" "}
                per selezionare
              </p>
            </div>
          )}
        </Card>
      </motion.div>
    </AnimatePresence>
  );
}

// Client Mention Pill Component (for input display)
interface ClientMentionPillProps {
  client: Client;
  onRemove: () => void;
}

export function ClientMentionPill({
  client,
  onRemove,
}: ClientMentionPillProps) {
  const duplicateNames =
    mockClients.filter((c) => c.name === client.name).length > 1;
  const displayName = duplicateNames
    ? `${client.name} (${client.codiceFiscale.substring(0, 10)}...)`
    : client.name;

  return (
    <motion.span
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0.8, opacity: 0 }}
      className="inline-flex items-center space-x-1 bg-[#2A5D67] text-white px-2.5 py-1 rounded-full text-sm font-medium mx-1"
    >
      <span>@{displayName}</span>
      <button
        onClick={onRemove}
        className="hover:bg-white/20 rounded-full p-0.5 transition-colors"
      >
        <X className="w-3 h-3" />
      </button>
    </motion.span>
  );
}

// Client Context Card Component (for AI responses)
interface ClientContextCardProps {
  client: Client;
}

export function ClientContextCard({ client }: ClientContextCardProps) {
  const regime = regimeConfig[client.regimeFiscale];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-4 mb-2"
    >
      <Card className="border-[#2A5D67]/30 bg-gradient-to-br from-[#F8F5F1] to-white overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#2A5D67] to-[#1E293B] px-4 py-3">
          <div className="flex items-center space-x-2">
            {client.name.includes("S.r.l.") ||
            client.name.includes("S.p.A.") ? (
              <Building2 className="w-5 h-5 text-white" />
            ) : (
              <User className="w-5 h-5 text-white" />
            )}
            <div className="flex-1">
              <h4 className="font-semibold text-white">{client.name}</h4>
              <p className="text-xs text-white/80 font-mono">
                {client.codiceFiscale}
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-3">
          {/* Info Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white rounded-lg p-3 border border-[#C4BDB4]/20">
              <p className="text-xs text-[#1E293B]/60 mb-1">Regime Fiscale</p>
              <span
                className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${regime.bg} ${regime.color} ${regime.border}`}
              >
                {client.regimeFiscale}
              </span>
            </div>
            <div className="bg-white rounded-lg p-3 border border-[#C4BDB4]/20">
              <p className="text-xs text-[#1E293B]/60 mb-1">Posizione</p>
              <p className="text-sm font-medium text-[#1E293B]">
                {client.posizione}
              </p>
            </div>
          </div>

          {/* ATECO */}
          <div className="bg-white rounded-lg p-3 border border-[#C4BDB4]/20">
            <p className="text-xs text-[#1E293B]/60 mb-1">Codice ATECO</p>
            <p className="text-sm font-medium text-[#2A5D67]">{client.ateco}</p>
            <p className="text-xs text-[#1E293B]/70 mt-1">
              {client.atecoDescription}
            </p>
          </div>

          {/* Active Procedures */}
          {client.activeProcedures && client.activeProcedures.length > 0 && (
            <div>
              <div className="flex items-center space-x-2 mb-2">
                <FileText className="w-4 h-4 text-[#2A5D67]" />
                <h5 className="text-sm font-semibold text-[#2A5D67]">
                  Procedure Attive
                </h5>
              </div>
              <div className="space-y-1.5">
                {client.activeProcedures.map((procedure, index) => (
                  <div
                    key={index}
                    className="flex items-center space-x-2 bg-white rounded-lg px-3 py-2 border border-[#C4BDB4]/20"
                  >
                    <div className="w-2 h-2 bg-green-500 rounded-full flex-shrink-0" />
                    <span className="text-sm text-[#1E293B]">{procedure}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Suggested Procedures */}
          {client.suggestedProcedures &&
            client.suggestedProcedures.length > 0 && (
              <div>
                <div className="flex items-center space-x-2 mb-2">
                  <FileText className="w-4 h-4 text-[#D4A574]" />
                  <h5 className="text-sm font-semibold text-[#D4A574]">
                    Procedure Suggerite
                  </h5>
                </div>
                <div className="space-y-1.5">
                  {client.suggestedProcedures.map((procedure, index) => (
                    <div
                      key={index}
                      className="flex items-center space-x-2 bg-white rounded-lg px-3 py-2 border border-[#D4A574]/20"
                    >
                      <div className="w-2 h-2 bg-[#D4A574] rounded-full flex-shrink-0" />
                      <span className="text-sm text-[#1E293B]">
                        {procedure}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

          {/* No Procedures */}
          {(!client.activeProcedures || client.activeProcedures.length === 0) &&
            (!client.suggestedProcedures ||
              client.suggestedProcedures.length === 0) && (
              <div className="bg-white rounded-lg p-3 border border-[#C4BDB4]/20 text-center">
                <p className="text-sm text-[#1E293B]/60">
                  Nessuna procedura attiva o suggerita
                </p>
              </div>
            )}
        </div>
      </Card>
    </motion.div>
  );
}
