"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Search,
  Clock,
  FileText,
  ChevronRight,
  CheckCircle,
  Users,
  ArrowRight,
  X,
  Info,
  Building2,
  UserCheck,
  TrendingUp,
  Calculator,
} from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Card } from "./ui/card";

interface Procedure {
  id: string;
  name: string;
  category: "apertura" | "chiusura" | "lavoro" | "fiscale";
  stepCount: number;
  estimatedTime: string;
  description: string;
  steps: ProcedureStep[];
  documents: string[];
}

interface ProcedureStep {
  id: string;
  title: string;
  description: string;
  completed?: boolean;
}

const mockProcedures: Procedure[] = [
  {
    id: "1",
    name: "Apertura S.r.l. Semplificata",
    category: "apertura",
    stepCount: 8,
    estimatedTime: "5-7 giorni",
    description:
      "Procedura completa per l'apertura di una società a responsabilità limitata semplificata",
    steps: [
      {
        id: "1",
        title: "Redazione statuto sociale",
        description: "Preparare lo statuto secondo il modello standardizzato",
      },
      {
        id: "2",
        title: "Acquisizione codice fiscale soci",
        description: "Raccogliere i documenti di identità e codici fiscali",
      },
      {
        id: "3",
        title: "Apertura conto corrente dedicato",
        description: "Versamento del capitale sociale minimo",
      },
      {
        id: "4",
        title: "Firma atto costitutivo",
        description: "Sottoscrizione davanti al notaio o con firma digitale",
      },
      {
        id: "5",
        title: "Registrazione presso Registro Imprese",
        description: "Invio pratica ComUnica telematica",
      },
      {
        id: "6",
        title: "Richiesta partita IVA",
        description: "Compilazione modello AA9/12",
      },
      {
        id: "7",
        title: "Iscrizione INPS e INAIL",
        description: "Adempimenti previdenziali e assicurativi",
      },
      {
        id: "8",
        title: "Comunicazione inizio attività",
        description: "SCIA al SUAP competente se necessario",
      },
    ],
    documents: [
      "Statuto sociale (modello standard)",
      "Documento identità soci e amministratori",
      "Codice fiscale soci",
      "Attestazione versamento capitale sociale",
      "Modello AA9/12 per partita IVA",
      "Pratica ComUnica",
    ],
  },
  {
    id: "2",
    name: "Assunzione Dipendente",
    category: "lavoro",
    stepCount: 6,
    estimatedTime: "3-4 giorni",
    description:
      "Procedura per l'assunzione di un nuovo dipendente con contratto a tempo indeterminato",
    steps: [
      {
        id: "1",
        title: "Verifica requisiti e documenti",
        description: "Raccolta documenti del lavoratore",
      },
      {
        id: "2",
        title: "Comunicazione obbligatoria UNILAV",
        description: "Invio entro le 24h precedenti l'inizio",
      },
      {
        id: "3",
        title: "Redazione contratto di lavoro",
        description: "Predisposizione secondo CCNL applicabile",
      },
      {
        id: "4",
        title: "Consegna documentazione al dipendente",
        description: "Lettera di assunzione e informative",
      },
      {
        id: "5",
        title: "Apertura posizione INPS/INAIL",
        description: "Matricola aziendale se primo dipendente",
      },
      {
        id: "6",
        title: "Visita medica di idoneità",
        description: "Richiesta al medico competente",
      },
    ],
    documents: [
      "Documento identità lavoratore",
      "Codice fiscale e tessera sanitaria",
      "Curriculum vitae",
      "Contratto di lavoro firmato",
      "Comunicazione UNILAV",
      "Libro unico del lavoro",
    ],
  },
  {
    id: "3",
    name: "Dichiarazione IVA Trimestrale",
    category: "fiscale",
    stepCount: 5,
    estimatedTime: "2-3 giorni",
    description:
      "Procedura per la compilazione e invio della dichiarazione IVA trimestrale",
    steps: [
      {
        id: "1",
        title: "Raccolta documentazione contabile",
        description: "Fatture attive e passive del trimestre",
      },
      {
        id: "2",
        title: "Compilazione registro IVA",
        description: "Calcolo IVA a debito e a credito",
      },
      {
        id: "3",
        title: "Calcolo saldo IVA trimestrale",
        description: "Determinazione importo da versare o a credito",
      },
      {
        id: "4",
        title: "Compilazione modello F24",
        description: "Se a debito: preparazione per il versamento",
      },
      {
        id: "5",
        title: "Invio telematico dichiarazione",
        description: "Trasmissione entro i termini di legge",
      },
    ],
    documents: [
      "Registro fatture emesse",
      "Registro fatture ricevute",
      "Registro corrispettivi",
      "Modello F24 per versamento",
      "Ricevuta invio telematico",
    ],
  },
  {
    id: "4",
    name: "Cessazione Attività Ditta Individuale",
    category: "chiusura",
    stepCount: 7,
    estimatedTime: "10-15 giorni",
    description:
      "Procedura completa per la cessazione di un'impresa individuale",
    steps: [
      {
        id: "1",
        title: "Comunicazione cessazione attività",
        description: "Pratica ComUnica al Registro Imprese",
      },
      {
        id: "2",
        title: "Chiusura partita IVA",
        description: "Modello AA9/12 con causale cessazione",
      },
      {
        id: "3",
        title: "Dichiarazione IVA finale",
        description: "Presentazione dichiarazione di cessazione",
      },
      {
        id: "4",
        title: "Liquidazione dipendenti",
        description: "TFR e ultime competenze se presenti",
      },
      {
        id: "5",
        title: "Chiusura posizioni INPS/INAIL",
        description: "Comunicazione cessazione e conguagli",
      },
      {
        id: "6",
        title: "Dichiarazione redditi finale",
        description: "Modello Redditi PF per anno di cessazione",
      },
      {
        id: "7",
        title: "Cancellazione dal Registro Imprese",
        description: "Verifica completamento iter",
      },
    ],
    documents: [
      "Pratica ComUnica di cessazione",
      "Modello AA9/12",
      "Dichiarazione IVA finale",
      "Dichiarazione redditi",
      "Quietanze versamenti contributivi",
      "Certificato cancellazione Registro Imprese",
    ],
  },
  {
    id: "5",
    name: "Bilancio Annuale S.r.l.",
    category: "fiscale",
    stepCount: 9,
    estimatedTime: "15-20 giorni",
    description:
      "Procedura per la redazione e approvazione del bilancio d'esercizio annuale",
    steps: [
      {
        id: "1",
        title: "Chiusura contabilità ordinaria",
        description: "Registrazione ultime scritture dell'esercizio",
      },
      {
        id: "2",
        title: "Inventario di magazzino",
        description: "Valorizzazione rimanenze finali",
      },
      {
        id: "3",
        title: "Redazione situazione patrimoniale",
        description: "Stato patrimoniale e conto economico",
      },
      {
        id: "4",
        title: "Redazione nota integrativa",
        description: "Criteri di valutazione e informazioni richieste",
      },
      {
        id: "5",
        title: "Relazione sulla gestione",
        description: "Se obbligatoria secondo dimensioni società",
      },
      {
        id: "6",
        title: "Convocazione assemblea soci",
        description: "Entro 120 giorni dalla chiusura esercizio",
      },
      {
        id: "7",
        title: "Approvazione bilancio",
        description: "Verbale assemblea ordinaria soci",
      },
      {
        id: "8",
        title: "Deposito presso Registro Imprese",
        description: "Entro 30 giorni dall'approvazione",
      },
      {
        id: "9",
        title: "Dichiarazione redditi società",
        description: "Modello Redditi SC entro i termini",
      },
    ],
    documents: [
      "Stato patrimoniale",
      "Conto economico",
      "Nota integrativa",
      "Relazione sulla gestione",
      "Verbale assemblea approvazione",
      "Rendiconto finanziario",
    ],
  },
  {
    id: "6",
    name: "Trasformazione da Ditta a S.r.l.",
    category: "apertura",
    stepCount: 10,
    estimatedTime: "20-30 giorni",
    description:
      "Procedura per la trasformazione di un'impresa individuale in società a responsabilità limitata",
    steps: [
      {
        id: "1",
        title: "Valutazione convenienza fiscale",
        description: "Analisi costi-benefici della trasformazione",
      },
      {
        id: "2",
        title: "Redazione situazione patrimoniale",
        description: "Bilancio di trasformazione",
      },
      {
        id: "3",
        title: "Redazione statuto S.r.l.",
        description: "Preparazione nuovo atto costitutivo",
      },
      {
        id: "4",
        title: "Apertura conto corrente societario",
        description: "Versamento capitale sociale",
      },
      {
        id: "5",
        title: "Atto di trasformazione",
        description: "Firma davanti al notaio",
      },
      {
        id: "6",
        title: "Registrazione atto",
        description: "Imposta di registro e trascrizione",
      },
      {
        id: "7",
        title: "Aggiornamento partita IVA",
        description: "Variazione dati in Anagrafe Tributaria",
      },
      {
        id: "8",
        title: "Iscrizione S.r.l. al Registro Imprese",
        description: "Pratica ComUnica",
      },
      {
        id: "9",
        title: "Cessazione ditta individuale",
        description: "Cancellazione contestuale",
      },
      {
        id: "10",
        title: "Adeguamento adempimenti societari",
        description: "Nomina organi, libri sociali, etc.",
      },
    ],
    documents: [
      "Bilancio di trasformazione",
      "Statuto S.r.l.",
      "Atto di trasformazione",
      "Attestazione versamento capitale",
      "Pratica ComUnica",
      "Visura camerale aggiornata",
    ],
  },
];

const categoryConfig = {
  apertura: {
    label: "Apertura",
    icon: Building2,
    color: "text-green-600",
    bg: "bg-green-50",
  },
  chiusura: {
    label: "Chiusura",
    icon: X,
    color: "text-red-600",
    bg: "bg-red-50",
  },
  lavoro: {
    label: "Lavoro",
    icon: Users,
    color: "text-blue-600",
    bg: "bg-blue-50",
  },
  fiscale: {
    label: "Fiscale",
    icon: Calculator,
    color: "text-purple-600",
    bg: "bg-purple-50",
  },
};

interface ProcedureSelectorProps {
  onClose: () => void;
  onSelectProcedure: (procedureId: string) => void;
}

export function ProcedureSelector({
  onClose,
  onSelectProcedure,
}: ProcedureSelectorProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("tutte");
  const [selectedProcedure, setSelectedProcedure] = useState<Procedure | null>(
    null,
  );

  const filteredProcedures = mockProcedures.filter((proc) => {
    const matchesSearch =
      proc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      proc.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory =
      selectedCategory === "tutte" || proc.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const handleProcedureClick = (procedure: Procedure) => {
    setSelectedProcedure(procedure);
  };

  const handleStartForClient = () => {
    if (selectedProcedure) {
      onSelectProcedure(selectedProcedure.id);
      // This will trigger client selection
    }
  };

  if (selectedProcedure) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="my-4"
      >
        <Card className="border-[#C4BDB4]/30 shadow-lg overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-[#F8F5F1] to-white px-6 py-4 border-b border-[#C4BDB4]/20">
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedProcedure(null)}
                    className="text-[#2A5D67] hover:bg-white -ml-2"
                  >
                    <ChevronRight className="w-4 h-4 rotate-180" />
                  </Button>
                  <h3 className="text-xl font-semibold text-[#1E293B]">
                    {selectedProcedure.name}
                  </h3>
                </div>
                <div className="flex items-center space-x-3 ml-10">
                  <span
                    className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${categoryConfig[selectedProcedure.category].bg} ${categoryConfig[selectedProcedure.category].color}`}
                  >
                    {React.createElement(
                      categoryConfig[selectedProcedure.category].icon,
                      { className: "w-3 h-3 mr-1" },
                    )}
                    {categoryConfig[selectedProcedure.category].label}
                  </span>
                  <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                    <Info className="w-3 h-3 mr-1" />
                    Modalità consultazione
                  </span>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="text-[#1E293B]/60 hover:bg-white"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
            <p className="text-sm text-[#1E293B]/70 ml-10 mt-2">
              {selectedProcedure.description}
            </p>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-[#F8F5F1] rounded-lg p-4">
                <div className="flex items-center space-x-2 text-[#2A5D67] mb-1">
                  <FileText className="w-4 h-4" />
                  <span className="text-sm font-medium">Passi totali</span>
                </div>
                <p className="text-2xl font-semibold text-[#1E293B]">
                  {selectedProcedure.stepCount}
                </p>
              </div>
              <div className="bg-[#F8F5F1] rounded-lg p-4">
                <div className="flex items-center space-x-2 text-[#2A5D67] mb-1">
                  <Clock className="w-4 h-4" />
                  <span className="text-sm font-medium">Tempo stimato</span>
                </div>
                <p className="text-2xl font-semibold text-[#1E293B]">
                  {selectedProcedure.estimatedTime}
                </p>
              </div>
            </div>

            {/* Steps */}
            <div>
              <h4 className="text-sm font-semibold text-[#2A5D67] mb-3 uppercase tracking-wider">
                Passi della procedura
              </h4>
              <div className="space-y-2">
                {selectedProcedure.steps.map((step, index) => (
                  <div
                    key={step.id}
                    className="bg-white border border-[#C4BDB4]/20 rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start space-x-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-[#2A5D67]/10 rounded-full flex items-center justify-center">
                        <span className="text-sm font-semibold text-[#2A5D67]">
                          {index + 1}
                        </span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <h5 className="text-sm font-medium text-[#1E293B] mb-1">
                          {step.title}
                        </h5>
                        <p className="text-xs text-[#1E293B]/60">
                          {step.description}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Documents */}
            <div>
              <h4 className="text-sm font-semibold text-[#2A5D67] mb-3 uppercase tracking-wider">
                Documenti necessari
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {selectedProcedure.documents.map((doc, index) => (
                  <div
                    key={index}
                    className="flex items-center space-x-2 text-sm text-[#1E293B]/70 bg-[#F8F5F1] rounded-lg px-3 py-2"
                  >
                    <FileText className="w-3.5 h-3.5 text-[#2A5D67] flex-shrink-0" />
                    <span className="truncate">{doc}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 bg-[#F8F5F1] border-t border-[#C4BDB4]/20">
            <Button
              onClick={handleStartForClient}
              className="w-full bg-gradient-to-r from-[#2A5D67] to-[#1E293B] hover:from-[#1E293B] hover:to-[#2A5D67] text-white font-medium"
            >
              <UserCheck className="w-4 h-4 mr-2" />
              Avvia per un cliente
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </Card>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="my-4"
    >
      <Card className="border-[#C4BDB4]/30 shadow-lg overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#2A5D67] to-[#1E293B] px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white mb-1">
                Seleziona Procedura
              </h3>
              <p className="text-sm text-white/80">
                Scegli una procedura per consultarla o avviarla per un cliente
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="text-white hover:bg-white/10"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="p-6 pb-4 bg-white border-b border-[#C4BDB4]/20">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#1E293B]/40" />
            <Input
              type="text"
              placeholder="Cerca procedura..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 border-[#C4BDB4]/30 focus:border-[#2A5D67] focus:ring-[#2A5D67]"
            />
          </div>
        </div>

        {/* Category Chips */}
        <div className="px-6 py-4 bg-[#F8F5F1]/50 border-b border-[#C4BDB4]/20">
          <div className="flex items-center space-x-2 overflow-x-auto pb-1">
            <button
              onClick={() => setSelectedCategory("tutte")}
              className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                selectedCategory === "tutte"
                  ? "bg-[#2A5D67] text-white"
                  : "bg-white text-[#1E293B] hover:bg-[#F8F5F1]"
              }`}
            >
              Tutte
            </button>
            {Object.entries(categoryConfig).map(([key, config]) => (
              <button
                key={key}
                onClick={() => setSelectedCategory(key)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors flex items-center space-x-1.5 ${
                  selectedCategory === key
                    ? "bg-[#2A5D67] text-white"
                    : "bg-white text-[#1E293B] hover:bg-[#F8F5F1]"
                }`}
              >
                {React.createElement(config.icon, { className: "w-3.5 h-3.5" })}
                <span>{config.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Procedure List */}
        <div className="max-h-[400px] overflow-y-auto p-6 space-y-3">
          {filteredProcedures.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="w-12 h-12 mx-auto text-[#C4BDB4] mb-3" />
              <p className="text-[#1E293B]/60">Nessuna procedura trovata</p>
            </div>
          ) : (
            filteredProcedures.map((procedure) => {
              const config = categoryConfig[procedure.category];
              return (
                <motion.div
                  key={procedure.id}
                  whileHover={{ scale: 1.01 }}
                  onClick={() => handleProcedureClick(procedure)}
                  className="bg-white border border-[#C4BDB4]/20 rounded-lg p-4 cursor-pointer hover:shadow-md hover:border-[#2A5D67]/30 transition-all group"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <h4 className="font-medium text-[#1E293B] group-hover:text-[#2A5D67] transition-colors">
                          {procedure.name}
                        </h4>
                        <ChevronRight className="w-4 h-4 text-[#1E293B]/40 group-hover:text-[#2A5D67] transition-colors" />
                      </div>
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.color}`}
                      >
                        {React.createElement(config.icon, {
                          className: "w-3 h-3 mr-1",
                        })}
                        {config.label}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-[#1E293B]/60 mb-3">
                    {procedure.description}
                  </p>
                  <div className="flex items-center space-x-4 text-xs text-[#1E293B]/50">
                    <div className="flex items-center space-x-1">
                      <FileText className="w-3.5 h-3.5" />
                      <span>{procedure.stepCount} passi</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{procedure.estimatedTime}</span>
                    </div>
                  </div>
                </motion.div>
              );
            })
          )}
        </div>
      </Card>
    </motion.div>
  );
}

// Command Popover Component
interface CommandPopoverProps {
  onSelectCommand: (command: string) => void;
  onClose: () => void;
}

export function CommandPopover({
  onSelectCommand,
  onClose,
}: CommandPopoverProps) {
  const commands = [
    {
      id: "procedura",
      name: "/procedura",
      description: "Avvia o consulta una procedura",
      icon: FileText,
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: -10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.95 }}
      className="absolute bottom-full left-0 mb-2 z-50"
    >
      <Card className="w-80 shadow-xl border-[#C4BDB4]/30 overflow-hidden">
        <div className="bg-[#F8F5F1] px-4 py-2 border-b border-[#C4BDB4]/20">
          <p className="text-xs font-medium text-[#2A5D67] uppercase tracking-wider">
            Comandi disponibili
          </p>
        </div>
        <div className="p-2">
          {commands.map((command) => (
            <button
              key={command.id}
              onClick={() => {
                onSelectCommand(command.id);
                onClose();
              }}
              className="w-full flex items-start space-x-3 px-3 py-2.5 rounded-lg hover:bg-[#F8F5F1] transition-colors group text-left"
            >
              <div className="flex-shrink-0 w-8 h-8 bg-[#2A5D67]/10 rounded-lg flex items-center justify-center group-hover:bg-[#2A5D67] transition-colors">
                <command.icon className="w-4 h-4 text-[#2A5D67] group-hover:text-white transition-colors" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-[#1E293B] text-sm group-hover:text-[#2A5D67] transition-colors">
                  {command.name}
                </p>
                <p className="text-xs text-[#1E293B]/60">
                  {command.description}
                </p>
              </div>
            </button>
          ))}
        </div>
      </Card>
    </motion.div>
  );
}
