import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  ArrowLeft,
  Check,
  FileText,
  Plus,
  Paperclip,
  User,
  ChevronRight,
  Circle,
  CheckCircle,
  AlertCircle,
  Clock,
  Calendar,
  Download,
  Upload,
  Trash2,
  Edit,
  Eye,
  PlayCircle,
  BookOpen,
} from "lucide-react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";

interface ProceduraInterattivaPageProps {
  onBackToChat: () => void;
  clientId?: string;
  clientName?: string;
  proceduraId?: string;
}

interface ChecklistItem {
  id: string;
  text: string;
  completed: boolean;
}

interface Document {
  id: string;
  name: string;
  required: boolean;
  uploaded: boolean;
  uploadDate?: string;
}

interface Note {
  id: string;
  text: string;
  date: string;
  attachments?: string[];
}

interface Step {
  id: string;
  number: number;
  title: string;
  description: string;
  checklist: ChecklistItem[];
  documents: Document[];
  notes: Note[];
  completed: boolean;
}

interface Procedura {
  id: string;
  title: string;
  description: string;
  category: string;
  totalSteps: number;
  completedSteps: number;
  progress: number;
  steps: Step[];
  clientId?: string;
  clientName?: string;
  lastUpdated?: string;
}

const mockProcedure: Procedura[] = [
  {
    id: "proc_001",
    title: "Apertura Partita IVA",
    description: "Procedura completa per l'apertura di una nuova Partita IVA",
    category: "Fiscale",
    totalSteps: 7,
    completedSteps: 3,
    progress: 42,
    lastUpdated: "2024-02-24T15:30:00",
    steps: [
      {
        id: "step_001",
        number: 1,
        title: "Raccolta documenti identificativi",
        description:
          "Raccogliere tutta la documentazione necessaria per identificare il richiedente",
        completed: true,
        checklist: [
          { id: "cl_001", text: "Carta d'identità valida", completed: true },
          { id: "cl_002", text: "Codice fiscale", completed: true },
          { id: "cl_003", text: "Certificato di residenza", completed: true },
        ],
        documents: [
          {
            id: "doc_001",
            name: "Carta Identità.pdf",
            required: true,
            uploaded: true,
            uploadDate: "2024-02-20",
          },
          {
            id: "doc_002",
            name: "Codice Fiscale.pdf",
            required: true,
            uploaded: true,
            uploadDate: "2024-02-20",
          },
        ],
        notes: [
          {
            id: "note_001",
            text: "Documenti ricevuti via email dal cliente",
            date: "2024-02-20T10:00:00",
          },
        ],
      },
      {
        id: "step_002",
        number: 2,
        title: "Scelta del regime fiscale",
        description:
          "Determinare il regime fiscale più vantaggioso per l'attività",
        completed: true,
        checklist: [
          { id: "cl_004", text: "Analisi fatturato previsto", completed: true },
          {
            id: "cl_005",
            text: "Verifica requisiti regime forfettario",
            completed: true,
          },
          {
            id: "cl_006",
            text: "Confronto tra regimi disponibili",
            completed: true,
          },
        ],
        documents: [],
        notes: [
          {
            id: "note_002",
            text: "Il cliente rientra nei requisiti per il regime forfettario. Fatturato previsto: €35.000",
            date: "2024-02-21T14:00:00",
          },
        ],
      },
      {
        id: "step_003",
        number: 3,
        title: "Compilazione modulo AA9/12",
        description:
          "Compilare e verificare il modulo di dichiarazione di inizio attività",
        completed: false,
        checklist: [
          {
            id: "cl_007",
            text: "Inserimento dati anagrafici",
            completed: true,
          },
          { id: "cl_008", text: "Selezione codice ATECO", completed: true },
          {
            id: "cl_009",
            text: "Dichiarazione regime fiscale",
            completed: false,
          },
          { id: "cl_010", text: "Firma del modulo", completed: false },
        ],
        documents: [
          {
            id: "doc_003",
            name: "Modulo AA9_12 bozza.pdf",
            required: true,
            uploaded: true,
            uploadDate: "2024-02-23",
          },
          {
            id: "doc_004",
            name: "Modulo AA9_12 firmato.pdf",
            required: true,
            uploaded: false,
          },
        ],
        notes: [],
      },
      {
        id: "step_004",
        number: 4,
        title: "Iscrizione INPS",
        description:
          "Procedere con l'iscrizione alla gestione INPS appropriata",
        completed: false,
        checklist: [
          {
            id: "cl_011",
            text: "Verifica gestione INPS di competenza",
            completed: false,
          },
          {
            id: "cl_012",
            text: "Compilazione domanda iscrizione",
            completed: false,
          },
          { id: "cl_013", text: "Invio documentazione", completed: false },
        ],
        documents: [
          {
            id: "doc_005",
            name: "Domanda iscrizione INPS.pdf",
            required: true,
            uploaded: false,
          },
        ],
        notes: [],
      },
      {
        id: "step_005",
        number: 5,
        title: "Comunicazione Unica (ComUnica)",
        description:
          "Invio della Comunicazione Unica telematica all'Agenzia delle Entrate",
        completed: false,
        checklist: [
          {
            id: "cl_014",
            text: "Preparazione file telematico",
            completed: false,
          },
          {
            id: "cl_015",
            text: "Invio tramite Entratel/Fisconline",
            completed: false,
          },
          {
            id: "cl_016",
            text: "Ricezione ricevuta di protocollazione",
            completed: false,
          },
        ],
        documents: [],
        notes: [],
      },
      {
        id: "step_006",
        number: 6,
        title: "Apertura PEC e firma digitale",
        description: "Attivazione casella PEC e certificato di firma digitale",
        completed: false,
        checklist: [
          { id: "cl_017", text: "Richiesta casella PEC", completed: false },
          { id: "cl_018", text: "Richiesta firma digitale", completed: false },
          {
            id: "cl_019",
            text: "Test funzionamento servizi",
            completed: false,
          },
        ],
        documents: [],
        notes: [],
      },
      {
        id: "step_007",
        number: 7,
        title: "Configurazione fatturazione elettronica",
        description: "Setup del sistema di fatturazione elettronica",
        completed: false,
        checklist: [
          {
            id: "cl_020",
            text: "Scelta software fatturazione",
            completed: false,
          },
          { id: "cl_021", text: "Configurazione SdI", completed: false },
          {
            id: "cl_022",
            text: "Test invio fattura di prova",
            completed: false,
          },
        ],
        documents: [],
        notes: [],
      },
    ],
  },
  {
    id: "proc_002",
    title: "Assunzione Dipendente",
    description: "Procedura completa per l'assunzione di un nuovo dipendente",
    category: "Lavoro",
    totalSteps: 6,
    completedSteps: 1,
    progress: 16,
    steps: [],
  },
  {
    id: "proc_003",
    title: "Chiusura Bilancio",
    description: "Procedura per la chiusura e deposito del bilancio annuale",
    category: "Contabilità",
    totalSteps: 8,
    completedSteps: 5,
    progress: 62,
    steps: [],
  },
  {
    id: "proc_004",
    title: "Dichiarazione IVA",
    description:
      "Procedura per la compilazione e invio della dichiarazione IVA annuale",
    category: "Fiscale",
    totalSteps: 5,
    completedSteps: 0,
    progress: 0,
    steps: [],
  },
  {
    id: "proc_005",
    title: "Richiesta DURC",
    description:
      "Procedura per la richiesta del Documento Unico di Regolarità Contributiva",
    category: "Previdenziale",
    totalSteps: 4,
    completedSteps: 4,
    progress: 100,
    steps: [],
  },
  {
    id: "proc_006",
    title: "Cessione Credito d'Imposta",
    description: "Procedura per la cessione di crediti d'imposta",
    category: "Fiscale",
    totalSteps: 6,
    completedSteps: 2,
    progress: 33,
    steps: [],
  },
];

const mockClients = [
  { id: "cli_001", name: "Studio Legale Rossi & Associati" },
  { id: "cli_002", name: "Immobiliare Milano SpA" },
  { id: "cli_003", name: "Consulenza Bianchi SRL" },
  { id: "cli_004", name: "Costruzioni Verdi Srl" },
  { id: "cli_005", name: "Commercialista Ferrari" },
];

export function ProceduraInterattivaPage({
  onBackToChat,
  clientId,
  clientName,
  proceduraId,
}: ProceduraInterattivaPageProps) {
  const [selectedProceduraId, setSelectedProceduraId] = useState(
    proceduraId || "proc_001",
  );
  const [currentStepIndex, setCurrentStepIndex] = useState(2); // Step 3 (index 2) as current
  const [showNoteEditor, setShowNoteEditor] = useState(false);
  const [newNote, setNewNote] = useState("");
  const [showClientSelector, setShowClientSelector] = useState(false);
  const [selectedClient, setSelectedClient] = useState(clientId || "");
  const [isClientMode, setIsClientMode] = useState(!!clientId);

  const selectedProcedura =
    mockProcedure.find((p) => p.id === selectedProceduraId) || mockProcedure[0];
  const currentStep = selectedProcedura.steps[currentStepIndex];

  const handleToggleChecklistItem = (itemId: string) => {
    console.log("Toggle checklist item:", itemId);
    // In real app, update backend
  };

  const handleCompleteStep = () => {
    console.log("Complete step:", currentStep?.id);
    if (currentStepIndex < selectedProcedura.totalSteps - 1) {
      setCurrentStepIndex(currentStepIndex + 1);
    }
  };

  const handleAddNote = () => {
    console.log("Add note:", newNote);
    setNewNote("");
    setShowNoteEditor(false);
  };

  const handleStartForClient = () => {
    setShowClientSelector(true);
  };

  const handleConfirmClient = () => {
    if (selectedClient) {
      setIsClientMode(true);
      setShowClientSelector(false);
    }
  };

  const getProgressColor = (progress: number) => {
    if (progress === 100) return "bg-green-500";
    if (progress >= 50) return "bg-blue-500";
    if (progress > 0) return "bg-yellow-500";
    return "bg-gray-300";
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      Fiscale: "bg-blue-100 text-blue-700 border-blue-300",
      Lavoro: "bg-purple-100 text-purple-700 border-purple-300",
      Contabilità: "bg-green-100 text-green-700 border-green-300",
      Previdenziale: "bg-orange-100 text-orange-700 border-orange-300",
    };
    return colors[category] || "bg-gray-100 text-gray-700 border-gray-300";
  };

  return (
    <div className="min-h-screen bg-[#F8F5F1] flex">
      {/* Left Sidebar - Procedure List */}
      <div className="w-80 bg-white border-r border-[#C4BDB4]/20 flex flex-col overflow-hidden">
        {/* Sidebar Header */}
        <div className="p-4 border-b border-[#C4BDB4]/20 bg-[#2A5D67] text-white">
          <Button
            variant="ghost"
            onClick={onBackToChat}
            className="text-white hover:bg-white/10 mb-3 -ml-2"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Indietro
          </Button>
          <h2 className="text-xl font-bold flex items-center">
            <BookOpen className="w-5 h-5 mr-2" />
            Procedure
          </h2>
          <p className="text-sm text-white/80 mt-1">
            Guide passo-passo interattive
          </p>
        </div>

        {/* Procedure List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {mockProcedure.map((procedura, index) => (
            <motion.button
              key={procedura.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              onClick={() => {
                setSelectedProceduraId(procedura.id);
                setCurrentStepIndex(
                  procedura.completedSteps < procedura.totalSteps
                    ? procedura.completedSteps
                    : 0,
                );
              }}
              className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                selectedProceduraId === procedura.id
                  ? "border-[#2A5D67] bg-[#F8F5F1] shadow-md"
                  : "border-[#C4BDB4]/20 hover:border-[#C4BDB4] hover:bg-[#F8F5F1]/50"
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-[#2A5D67] text-sm leading-tight pr-2">
                  {procedura.title}
                </h3>
                <Badge
                  className={`${getCategoryColor(procedura.category)} border text-xs flex-shrink-0`}
                >
                  {procedura.category}
                </Badge>
              </div>

              <p className="text-xs text-[#1E293B] mb-3 line-clamp-2">
                {procedura.description}
              </p>

              {/* Progress Bar */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs text-[#1E293B]">
                  <span>
                    {procedura.completedSteps} di {procedura.totalSteps} passi
                  </span>
                  <span className="font-semibold">{procedura.progress}%</span>
                </div>
                <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${procedura.progress}%` }}
                    transition={{ duration: 0.5, delay: index * 0.05 }}
                    className={`h-full ${getProgressColor(procedura.progress)} rounded-full`}
                  />
                </div>
              </div>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <div className="bg-white border-b border-[#C4BDB4]/20 px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-[#2A5D67] mb-1">
                {selectedProcedura.title}
              </h1>
              <p className="text-sm text-[#1E293B]">
                {selectedProcedura.description}
              </p>
            </div>

            {/* Mode Badge */}
            <div className="flex items-center space-x-2">
              {!isClientMode ? (
                <>
                  <Badge className="bg-gray-100 text-gray-700 border-gray-300 border px-3 py-1">
                    <Eye className="w-3 h-3 mr-1" />
                    Modalità consultazione
                  </Badge>
                  <Button
                    onClick={handleStartForClient}
                    className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                  >
                    <PlayCircle className="w-4 h-4 mr-2" />
                    <span className="font-bold">Avvia per un cliente</span>
                  </Button>
                </>
              ) : (
                <Badge className="bg-blue-100 text-blue-700 border-blue-300 border px-3 py-1.5">
                  <User className="w-4 h-4 mr-1" />
                  {clientName ||
                    mockClients.find((c) => c.id === selectedClient)?.name}
                </Badge>
              )}
            </div>
          </div>

          {/* Progress Bar */}
          {isClientMode && currentStep && (
            <div className="bg-[#F8F5F1] rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-[#2A5D67]">
                  Passo {currentStep.number} di {selectedProcedura.totalSteps} -{" "}
                  {selectedProcedura.progress}% completato
                </span>
                <span className="text-xs text-[#1E293B]">
                  Ultimo aggiornamento:{" "}
                  {new Date(
                    selectedProcedura.lastUpdated || "",
                  ).toLocaleDateString("it-IT")}
                </span>
              </div>
              <div className="w-full h-3 bg-white rounded-full overflow-hidden border border-[#C4BDB4]/20">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${selectedProcedura.progress}%` }}
                  className={`h-full ${getProgressColor(selectedProcedura.progress)}`}
                />
              </div>
            </div>
          )}
        </div>

        {/* Main Content - Steps */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-5xl mx-auto">
            {/* Stepper */}
            <div className="mb-8">
              <div className="flex items-start justify-between relative">
                {/* Progress Line */}
                <div
                  className="absolute top-5 left-0 right-0 h-0.5 bg-[#C4BDB4]/30"
                  style={{ zIndex: 0 }}
                />

                {selectedProcedura.steps.map((step, index) => (
                  <div
                    key={step.id}
                    className="flex flex-col items-center relative"
                    style={{ flex: 1, zIndex: 1 }}
                  >
                    <motion.button
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => setCurrentStepIndex(index)}
                      className={`w-10 h-10 rounded-full flex items-center justify-center transition-all mb-2 ${
                        step.completed
                          ? "bg-green-500 text-white"
                          : index === currentStepIndex
                            ? "bg-[#2A5D67] text-white ring-4 ring-[#2A5D67]/20"
                            : "bg-white text-[#1E293B] border-2 border-[#C4BDB4]"
                      }`}
                    >
                      {step.completed ? (
                        <Check className="w-5 h-5" />
                      ) : (
                        <span className="font-semibold text-sm">
                          {step.number}
                        </span>
                      )}
                    </motion.button>
                    <span
                      className={`text-xs text-center max-w-[100px] ${
                        index === currentStepIndex
                          ? "font-semibold text-[#2A5D67]"
                          : "text-[#1E293B]"
                      }`}
                    >
                      {step.title.length > 20
                        ? step.title.substring(0, 20) + "..."
                        : step.title}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Current Step Content */}
            {currentStep && (
              <motion.div
                key={currentStep.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white rounded-lg shadow-lg border border-[#C4BDB4]/20 overflow-hidden"
              >
                {/* Step Header */}
                <div className="bg-[#2A5D67] text-white p-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2 mb-2">
                        <Badge className="bg-white/20 text-white border-white/30 border">
                          Passo {currentStep.number}
                        </Badge>
                        {currentStep.completed && (
                          <Badge className="bg-green-500 text-white border-green-400 border">
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Completato
                          </Badge>
                        )}
                      </div>
                      <h2 className="text-2xl font-bold mb-2">
                        {currentStep.title}
                      </h2>
                      <p className="text-white/90">{currentStep.description}</p>
                    </div>
                  </div>
                </div>

                <div className="p-6 space-y-6">
                  {/* Checklist */}
                  <div>
                    <h3 className="text-lg font-semibold text-[#2A5D67] mb-3 flex items-center">
                      <CheckCircle className="w-5 h-5 mr-2" />
                      Checklist
                    </h3>
                    <div className="space-y-2">
                      {currentStep.checklist.map((item) => (
                        <motion.div
                          key={item.id}
                          whileHover={{ x: 4 }}
                          className={`flex items-center space-x-3 p-3 rounded-lg border transition-all ${
                            item.completed
                              ? "bg-green-50 border-green-200"
                              : "bg-white border-[#C4BDB4]/20 hover:border-[#C4BDB4]"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={item.completed}
                            onChange={() => handleToggleChecklistItem(item.id)}
                            disabled={!isClientMode}
                            className="w-5 h-5 text-[#2A5D67] border-[#C4BDB4] rounded focus:ring-[#2A5D67] disabled:opacity-50"
                          />
                          <span
                            className={`flex-1 ${
                              item.completed
                                ? "text-green-700 line-through"
                                : "text-[#1E293B]"
                            }`}
                          >
                            {item.text}
                          </span>
                          {item.completed && (
                            <Check className="w-5 h-5 text-green-600" />
                          )}
                        </motion.div>
                      ))}
                    </div>
                  </div>

                  {/* Documents */}
                  {currentStep.documents.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold text-[#2A5D67] mb-3 flex items-center">
                        <FileText className="w-5 h-5 mr-2" />
                        Documenti richiesti
                      </h3>
                      <div className="space-y-2">
                        {currentStep.documents.map((doc) => (
                          <div
                            key={doc.id}
                            className={`flex items-center justify-between p-3 rounded-lg border ${
                              doc.uploaded
                                ? "bg-green-50 border-green-200"
                                : "bg-white border-[#C4BDB4]/20"
                            }`}
                          >
                            <div className="flex items-center space-x-3">
                              <div
                                className={`w-10 h-10 rounded flex items-center justify-center ${
                                  doc.uploaded ? "bg-green-100" : "bg-gray-100"
                                }`}
                              >
                                {doc.uploaded ? (
                                  <CheckCircle className="w-5 h-5 text-green-600" />
                                ) : (
                                  <FileText className="w-5 h-5 text-gray-400" />
                                )}
                              </div>
                              <div>
                                <p className="font-medium text-[#2A5D67]">
                                  {doc.name}
                                </p>
                                {doc.uploaded && doc.uploadDate && (
                                  <p className="text-xs text-green-600">
                                    Caricato il{" "}
                                    {new Date(
                                      doc.uploadDate,
                                    ).toLocaleDateString("it-IT")}
                                  </p>
                                )}
                                {!doc.uploaded && doc.required && (
                                  <p className="text-xs text-red-600">
                                    Obbligatorio
                                  </p>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center space-x-2">
                              {doc.uploaded ? (
                                <>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    className="text-[#2A5D67]"
                                  >
                                    <Download className="w-4 h-4" />
                                  </Button>
                                  {isClientMode && (
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      className="text-red-600 hover:bg-red-50"
                                    >
                                      <Trash2 className="w-4 h-4" />
                                    </Button>
                                  )}
                                </>
                              ) : (
                                isClientMode && (
                                  <Button
                                    size="sm"
                                    className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                                  >
                                    <Upload className="w-4 h-4 mr-1" />
                                    Carica
                                  </Button>
                                )
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Notes */}
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-semibold text-[#2A5D67] flex items-center">
                        <Paperclip className="w-5 h-5 mr-2" />
                        Note e allegati
                      </h3>
                      {isClientMode && (
                        <Button
                          onClick={() => setShowNoteEditor(true)}
                          size="sm"
                          variant="outline"
                          className="text-[#2A5D67] border-[#2A5D67]"
                        >
                          <Plus className="w-4 h-4 mr-1" />
                          Aggiungi nota
                        </Button>
                      )}
                    </div>

                    {currentStep.notes.length === 0 && !showNoteEditor && (
                      <div className="text-center py-8 bg-[#F8F5F1] rounded-lg border border-[#C4BDB4]/20">
                        <Paperclip className="w-8 h-8 text-[#C4BDB4] mx-auto mb-2" />
                        <p className="text-sm text-[#C4BDB4]">
                          Nessuna nota aggiunta
                        </p>
                      </div>
                    )}

                    {/* Note Editor */}
                    <AnimatePresence>
                      {showNoteEditor && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          className="mb-4 p-4 bg-[#F8F5F1] rounded-lg border border-[#2A5D67]"
                        >
                          <Textarea
                            value={newNote}
                            onChange={(e) => setNewNote(e.target.value)}
                            placeholder="Scrivi una nota..."
                            className="mb-3 min-h-[100px]"
                          />
                          <div className="flex items-center justify-end space-x-2">
                            <Button
                              onClick={() => {
                                setShowNoteEditor(false);
                                setNewNote("");
                              }}
                              size="sm"
                              variant="ghost"
                            >
                              Annulla
                            </Button>
                            <Button
                              onClick={handleAddNote}
                              size="sm"
                              className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                              disabled={!newNote.trim()}
                            >
                              <Check className="w-4 h-4 mr-1" />
                              Salva nota
                            </Button>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {/* Notes List */}
                    {currentStep.notes.length > 0 && (
                      <div className="space-y-3">
                        {currentStep.notes.map((note) => (
                          <div
                            key={note.id}
                            className="p-4 bg-white rounded-lg border border-[#C4BDB4]/20"
                          >
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex items-center space-x-2 text-xs text-[#1E293B]">
                                <Calendar className="w-4 h-4" />
                                <span>
                                  {new Date(note.date).toLocaleString("it-IT")}
                                </span>
                              </div>
                              {isClientMode && (
                                <div className="flex space-x-1">
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    className="h-6 w-6 p-0"
                                  >
                                    <Edit className="w-3 h-3" />
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    className="h-6 w-6 p-0 text-red-600"
                                  >
                                    <Trash2 className="w-3 h-3" />
                                  </Button>
                                </div>
                              )}
                            </div>
                            <p className="text-[#1E293B]">{note.text}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Step Actions */}
                {isClientMode && (
                  <div className="bg-[#F8F5F1] px-6 py-4 border-t border-[#C4BDB4]/20 flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {currentStepIndex > 0 && (
                        <Button
                          onClick={() =>
                            setCurrentStepIndex(currentStepIndex - 1)
                          }
                          variant="outline"
                          className="text-[#2A5D67] border-[#2A5D67]"
                        >
                          <ArrowLeft className="w-4 h-4 mr-1" />
                          Passo precedente
                        </Button>
                      )}
                    </div>

                    <div className="flex items-center space-x-2">
                      {!currentStep.completed ? (
                        <Button
                          onClick={handleCompleteStep}
                          className="bg-green-600 hover:bg-green-700 text-white"
                        >
                          <CheckCircle className="w-4 h-4 mr-2" />
                          <span className="font-bold">
                            Segna come completato
                          </span>
                        </Button>
                      ) : (
                        currentStepIndex < selectedProcedura.totalSteps - 1 && (
                          <Button
                            onClick={() =>
                              setCurrentStepIndex(currentStepIndex + 1)
                            }
                            className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                          >
                            <span className="font-bold">Passo successivo</span>
                            <ChevronRight className="w-4 h-4 ml-1" />
                          </Button>
                        )
                      )}
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </div>
        </div>
      </div>

      {/* Client Selector Modal */}
      <AnimatePresence>
        {showClientSelector && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
              onClick={() => setShowClientSelector(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg shadow-2xl z-50 w-full max-w-md"
            >
              <div className="p-6">
                <h2 className="text-2xl font-bold text-[#2A5D67] mb-4">
                  Seleziona un cliente
                </h2>
                <p className="text-sm text-[#1E293B] mb-6">
                  Scegli il cliente per cui vuoi avviare questa procedura
                </p>

                <Select
                  value={selectedClient}
                  onValueChange={setSelectedClient}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleziona un cliente" />
                  </SelectTrigger>
                  <SelectContent>
                    {mockClients.map((client) => (
                      <SelectItem key={client.id} value={client.id}>
                        {client.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <div className="flex items-center justify-end space-x-3 mt-6">
                  <Button
                    onClick={() => setShowClientSelector(false)}
                    variant="outline"
                  >
                    Annulla
                  </Button>
                  <Button
                    onClick={handleConfirmClient}
                    disabled={!selectedClient}
                    className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                  >
                    <PlayCircle className="w-4 h-4 mr-2" />
                    <span className="font-bold">Avvia procedura</span>
                  </Button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
