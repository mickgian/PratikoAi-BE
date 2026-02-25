import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  ArrowLeft,
  Plus,
  Edit,
  Send,
  Check,
  Trash2,
  Filter,
  Mail,
  MessageCircle,
  FileText,
  Calendar,
  User,
  X,
  ChevronDown,
  Eye,
  Clock,
  CheckCircle,
  AlertCircle,
  Inbox,
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

interface GestioneComunicazioniPageProps {
  onBackToChat: () => void;
}

type CommunicationStatus = "bozza" | "in_revisione" | "approvata" | "inviata";
type CommunicationChannel = "email" | "whatsapp";
type FilterTab = "tutte" | "bozze" | "in_revisione" | "approvate" | "inviate";

interface Communication {
  id: string;
  subject: string;
  clientName: string;
  clientId: string;
  channel: CommunicationChannel;
  status: CommunicationStatus;
  normativaReference: string;
  createdDate: string;
  body: string;
  template?: string;
}

const mockCommunications: Communication[] = [
  {
    id: "com_001",
    subject: "Nuove regole Superbonus 2024 - Azione richiesta",
    clientName: "Studio Legale Rossi & Associati",
    clientId: "cli_001",
    channel: "email",
    status: "inviata",
    normativaReference: "L. Bilancio 2024",
    createdDate: "2024-02-20T10:30:00",
    body: "Gentile Cliente, vi informiamo che sono state introdotte importanti modifiche al Superbonus...",
    template: "normativa_update",
  },
  {
    id: "com_002",
    subject: "Scadenza dichiarazione IMU - Promemoria",
    clientName: "Immobiliare Milano SpA",
    clientId: "cli_002",
    channel: "whatsapp",
    status: "approvata",
    normativaReference: "D.Lgs 504/1992",
    createdDate: "2024-02-22T14:15:00",
    body: "Le ricordiamo che la scadenza per la dichiarazione IMU è fissata per il 30 giugno 2024...",
    template: "scadenza_reminder",
  },
  {
    id: "com_003",
    subject: "Aggiornamento regime forfettario 2024",
    clientName: "Consulenza Bianchi SRL",
    clientId: "cli_003",
    channel: "email",
    status: "in_revisione",
    normativaReference: "L. 190/2014",
    createdDate: "2024-02-23T09:20:00",
    body: "In riferimento alle novità sul regime forfettario, si segnala che...",
    template: "normativa_update",
  },
  {
    id: "com_004",
    subject: "Reverse charge edilizia - Chiarimenti",
    clientName: "Costruzioni Verdi Srl",
    clientId: "cli_004",
    channel: "email",
    status: "bozza",
    normativaReference: "DPR 633/1972",
    createdDate: "2024-02-24T11:45:00",
    body: "Con la presente desideriamo chiarire le modalità applicative del reverse charge...",
    template: "custom",
  },
  {
    id: "com_005",
    subject: "Circolare AdE su detrazioni fiscali",
    clientName: "Commercialista Ferrari",
    clientId: "cli_005",
    channel: "whatsapp",
    status: "bozza",
    normativaReference: "Circolare 13/E/2024",
    createdDate: "2024-02-24T15:30:00",
    body: "Vi informiamo della pubblicazione della nuova circolare dell'Agenzia delle Entrate...",
    template: "normativa_update",
  },
  {
    id: "com_006",
    subject: "Nuovo obbligo fatturazione elettronica",
    clientName: "Azienda Tessile Lombarda",
    clientId: "cli_006",
    channel: "email",
    status: "in_revisione",
    normativaReference: "D.Lgs 127/2015",
    createdDate: "2024-02-23T16:00:00",
    body: "A partire dal 1° luglio 2024, sarà obbligatorio...",
    template: "normativa_update",
  },
  {
    id: "com_007",
    subject: "Promemoria versamento F24",
    clientName: "Ristorante Da Luca",
    clientId: "cli_007",
    channel: "whatsapp",
    status: "inviata",
    normativaReference: "DPR 600/1973",
    createdDate: "2024-02-21T08:00:00",
    body: "Le ricordiamo che il versamento F24 per il mese corrente è previsto entro...",
    template: "scadenza_reminder",
  },
  {
    id: "com_008",
    subject: "Bonus ristrutturazione 2024 - Opportunità",
    clientName: "Famiglia Moretti",
    clientId: "cli_008",
    channel: "email",
    status: "approvata",
    normativaReference: "L. Bilancio 2024",
    createdDate: "2024-02-22T10:30:00",
    body: "Desideriamo informarla sulle nuove opportunità relative al bonus ristrutturazione...",
    template: "opportunita_fiscale",
  },
];

const mockClients = [
  { id: "cli_001", name: "Studio Legale Rossi & Associati" },
  { id: "cli_002", name: "Immobiliare Milano SpA" },
  { id: "cli_003", name: "Consulenza Bianchi SRL" },
  { id: "cli_004", name: "Costruzioni Verdi Srl" },
  { id: "cli_005", name: "Commercialista Ferrari" },
  { id: "cli_006", name: "Azienda Tessile Lombarda" },
  { id: "cli_007", name: "Ristorante Da Luca" },
  { id: "cli_008", name: "Famiglia Moretti" },
];

const mockTemplates = [
  { id: "normativa_update", name: "Aggiornamento Normativo" },
  { id: "scadenza_reminder", name: "Promemoria Scadenza" },
  { id: "opportunita_fiscale", name: "Opportunità Fiscale" },
  { id: "richiesta_documenti", name: "Richiesta Documenti" },
  { id: "custom", name: "Personalizzata" },
];

const getStatusBadge = (status: CommunicationStatus) => {
  const configs = {
    bozza: {
      label: "Bozza",
      className: "bg-gray-100 text-gray-700 border-gray-300",
    },
    in_revisione: {
      label: "In Revisione",
      className: "bg-yellow-100 text-yellow-700 border-yellow-300",
    },
    approvata: {
      label: "Approvata",
      className: "bg-green-100 text-green-700 border-green-300",
    },
    inviata: {
      label: "Inviata",
      className: "bg-blue-100 text-blue-700 border-blue-300",
    },
  };
  const config = configs[status];
  return <Badge className={`${config.className} border`}>{config.label}</Badge>;
};

const getChannelIcon = (channel: CommunicationChannel) => {
  return channel === "email" ? (
    <Mail className="w-4 h-4 text-[#2A5D67]" />
  ) : (
    <MessageCircle className="w-4 h-4 text-[#2A5D67]" />
  );
};

export function GestioneComunicazioniPage({
  onBackToChat,
}: GestioneComunicazioniPageProps) {
  const [activeTab, setActiveTab] = useState<FilterTab>("tutte");
  const [selectedCommunications, setSelectedCommunications] = useState<
    Set<string>
  >(new Set());
  const [showEditor, setShowEditor] = useState(false);
  const [editingCommunication, setEditingCommunication] =
    useState<Communication | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Editor state
  const [editorSubject, setEditorSubject] = useState("");
  const [editorBody, setEditorBody] = useState("");
  const [editorClient, setEditorClient] = useState("");
  const [editorTemplate, setEditorTemplate] = useState("");
  const [editorChannel, setEditorChannel] =
    useState<CommunicationChannel>("email");

  // Filter communications based on active tab
  const getFilteredCommunications = () => {
    let filtered = mockCommunications;

    if (activeTab !== "tutte") {
      const statusMap: Record<FilterTab, CommunicationStatus | null> = {
        tutte: null,
        bozze: "bozza",
        in_revisione: "in_revisione",
        approvate: "approvata",
        inviate: "inviata",
      };
      const targetStatus = statusMap[activeTab];
      if (targetStatus) {
        filtered = filtered.filter((c) => c.status === targetStatus);
      }
    }

    if (searchQuery) {
      filtered = filtered.filter(
        (c) =>
          c.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
          c.clientName.toLowerCase().includes(searchQuery.toLowerCase()),
      );
    }

    return filtered;
  };

  const filteredCommunications = getFilteredCommunications();

  // Calculate stats
  const stats = {
    bozze: mockCommunications.filter((c) => c.status === "bozza").length,
    in_revisione: mockCommunications.filter((c) => c.status === "in_revisione")
      .length,
    approvate: mockCommunications.filter((c) => c.status === "approvata")
      .length,
    inviate: mockCommunications.filter((c) => c.status === "inviata").length,
  };

  const toggleSelectCommunication = (id: string) => {
    const newSelected = new Set(selectedCommunications);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedCommunications(newSelected);
  };

  const toggleSelectAll = () => {
    if (selectedCommunications.size === filteredCommunications.length) {
      setSelectedCommunications(new Set());
    } else {
      setSelectedCommunications(
        new Set(filteredCommunications.map((c) => c.id)),
      );
    }
  };

  const openEditor = (communication?: Communication) => {
    if (communication) {
      setEditingCommunication(communication);
      setEditorSubject(communication.subject);
      setEditorBody(communication.body);
      setEditorClient(communication.clientId);
      setEditorTemplate(communication.template || "");
      setEditorChannel(communication.channel);
    } else {
      setEditingCommunication(null);
      setEditorSubject("");
      setEditorBody("");
      setEditorClient("");
      setEditorTemplate("");
      setEditorChannel("email");
    }
    setShowEditor(true);
  };

  const closeEditor = () => {
    setShowEditor(false);
    setEditingCommunication(null);
  };

  const handleSaveCommunication = () => {
    // In a real app, this would save to backend
    console.log("Saving communication:", {
      subject: editorSubject,
      body: editorBody,
      client: editorClient,
      template: editorTemplate,
      channel: editorChannel,
    });
    closeEditor();
  };

  const handleBulkApprove = () => {
    console.log("Bulk approving:", Array.from(selectedCommunications));
    setSelectedCommunications(new Set());
  };

  const handleBulkSend = () => {
    console.log("Bulk sending:", Array.from(selectedCommunications));
    setSelectedCommunications(new Set());
  };

  const tabs: {
    id: FilterTab;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
  }[] = [
    { id: "tutte", label: "Tutte", icon: Inbox },
    { id: "bozze", label: "Bozze", icon: FileText },
    { id: "in_revisione", label: "In Revisione", icon: Clock },
    { id: "approvate", label: "Approvate", icon: CheckCircle },
    { id: "inviate", label: "Inviate", icon: Send },
  ];

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-[#C4BDB4]/20 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                onClick={onBackToChat}
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

      {/* Stats Bar */}
      <div className="bg-white border-b border-[#C4BDB4]/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-gray-50 rounded-lg p-4 border border-gray-200"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Bozze</p>
                  <p className="text-3xl font-bold text-gray-700">
                    {stats.bozze}
                  </p>
                </div>
                <FileText className="w-8 h-8 text-gray-400" />
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-yellow-50 rounded-lg p-4 border border-yellow-200"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-yellow-700">In Revisione</p>
                  <p className="text-3xl font-bold text-yellow-700">
                    {stats.in_revisione}
                  </p>
                </div>
                <Clock className="w-8 h-8 text-yellow-400" />
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="bg-green-50 rounded-lg p-4 border border-green-200"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-green-700">Approvate</p>
                  <p className="text-3xl font-bold text-green-700">
                    {stats.approvate}
                  </p>
                </div>
                <CheckCircle className="w-8 h-8 text-green-400" />
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="bg-blue-50 rounded-lg p-4 border border-blue-200"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-blue-700">Inviate</p>
                  <p className="text-3xl font-bold text-blue-700">
                    {stats.inviate}
                  </p>
                </div>
                <Send className="w-8 h-8 text-blue-400" />
              </div>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters and Search */}
        <div className="mb-6 space-y-4">
          {/* Filter Tabs */}
          <div className="bg-white rounded-lg shadow-sm border border-[#C4BDB4]/20 p-2">
            <div className="flex flex-wrap gap-2">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <motion.button
                    key={tab.id}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all ${
                      activeTab === tab.id
                        ? "bg-[#2A5D67] text-white shadow-md"
                        : "bg-white text-[#1E293B] hover:bg-[#F8F5F1]"
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="font-medium">{tab.label}</span>
                    {tab.id !== "tutte" && (
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          activeTab === tab.id
                            ? "bg-white/20 text-white"
                            : "bg-[#F8F5F1] text-[#2A5D67]"
                        }`}
                      >
                        {stats[tab.id as keyof typeof stats]}
                      </span>
                    )}
                  </motion.button>
                );
              })}
            </div>
          </div>

          {/* Search and Bulk Actions */}
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <Input
                type="text"
                placeholder="Cerca per oggetto o cliente..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full"
              />
            </div>

            <AnimatePresence>
              {selectedCommunications.size > 0 && (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="flex items-center space-x-2"
                >
                  <span className="text-sm text-[#2A5D67] font-medium">
                    {selectedCommunications.size} selezionate
                  </span>
                  <Button
                    onClick={handleBulkApprove}
                    size="sm"
                    className="bg-green-600 hover:bg-green-700 text-white"
                  >
                    <Check className="w-4 h-4 mr-1" />
                    Approva
                  </Button>
                  <Button
                    onClick={handleBulkSend}
                    size="sm"
                    className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                  >
                    <Send className="w-4 h-4 mr-1" />
                    Invia
                  </Button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Select All */}
          {filteredCommunications.length > 0 && (
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={
                  selectedCommunications.size === filteredCommunications.length
                }
                onChange={toggleSelectAll}
                className="w-4 h-4 text-[#2A5D67] border-[#C4BDB4] rounded focus:ring-[#2A5D67]"
              />
              <span className="text-sm text-[#1E293B]">
                Seleziona tutte le comunicazioni visibili
              </span>
            </div>
          )}
        </div>

        {/* Communications List */}
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
                    ? "Prova a modificare i filtri di ricerca"
                    : "Inizia creando una nuova comunicazione"}
                </p>
              </motion.div>
            ) : (
              filteredCommunications.map((communication, index) => (
                <motion.div
                  key={communication.id}
                  layout
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ delay: index * 0.05 }}
                  className={`bg-white rounded-lg shadow-sm border transition-all hover:shadow-md ${
                    selectedCommunications.has(communication.id)
                      ? "border-[#2A5D67] ring-2 ring-[#2A5D67]/20"
                      : "border-[#C4BDB4]/20"
                  }`}
                >
                  <div className="p-6">
                    <div className="flex items-start space-x-4">
                      {/* Checkbox */}
                      <div className="pt-1">
                        <input
                          type="checkbox"
                          checked={selectedCommunications.has(communication.id)}
                          onChange={() =>
                            toggleSelectCommunication(communication.id)
                          }
                          className="w-4 h-4 text-[#2A5D67] border-[#C4BDB4] rounded focus:ring-[#2A5D67]"
                        />
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <h3 className="text-lg font-semibold text-[#2A5D67] mb-1">
                              {communication.subject}
                            </h3>
                            <div className="flex flex-wrap items-center gap-3 text-sm text-[#1E293B]">
                              <div className="flex items-center space-x-1">
                                <User className="w-4 h-4" />
                                <span>{communication.clientName}</span>
                              </div>
                              <div className="flex items-center space-x-1">
                                {getChannelIcon(communication.channel)}
                                <span className="capitalize">
                                  {communication.channel}
                                </span>
                              </div>
                              <div className="flex items-center space-x-1">
                                <FileText className="w-4 h-4" />
                                <span>{communication.normativaReference}</span>
                              </div>
                              <div className="flex items-center space-x-1">
                                <Calendar className="w-4 h-4" />
                                <span>
                                  {new Date(
                                    communication.createdDate,
                                  ).toLocaleDateString("it-IT", {
                                    day: "2-digit",
                                    month: "short",
                                    year: "numeric",
                                  })}
                                </span>
                              </div>
                            </div>
                          </div>
                          <div className="ml-4">
                            {getStatusBadge(communication.status)}
                          </div>
                        </div>

                        <p className="text-sm text-[#1E293B] line-clamp-2 mb-4">
                          {communication.body}
                        </p>

                        {/* Action Buttons */}
                        <div className="flex items-center space-x-2">
                          <Button
                            onClick={() => openEditor(communication)}
                            size="sm"
                            variant="outline"
                            className="text-[#2A5D67] border-[#2A5D67] hover:bg-[#F8F5F1]"
                          >
                            <Edit className="w-4 h-4 mr-1" />
                            Modifica
                          </Button>

                          {communication.status === "bozza" && (
                            <Button
                              onClick={() =>
                                console.log("Send to review:", communication.id)
                              }
                              size="sm"
                              className="bg-yellow-600 hover:bg-yellow-700 text-white"
                            >
                              <Clock className="w-4 h-4 mr-1" />
                              Invia a Revisione
                            </Button>
                          )}

                          {communication.status === "in_revisione" && (
                            <Button
                              onClick={() =>
                                console.log("Approve:", communication.id)
                              }
                              size="sm"
                              className="bg-green-600 hover:bg-green-700 text-white"
                            >
                              <Check className="w-4 h-4 mr-1" />
                              Approva
                            </Button>
                          )}

                          {communication.status === "approvata" && (
                            <Button
                              onClick={() =>
                                console.log("Send:", communication.id)
                              }
                              size="sm"
                              className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                            >
                              <Send className="w-4 h-4 mr-1" />
                              <span className="font-bold">Invia</span>
                            </Button>
                          )}

                          {communication.status === "inviata" && (
                            <Button
                              onClick={() =>
                                console.log("View:", communication.id)
                              }
                              size="sm"
                              variant="outline"
                            >
                              <Eye className="w-4 h-4 mr-1" />
                              Visualizza
                            </Button>
                          )}

                          <Button
                            onClick={() =>
                              console.log("Delete:", communication.id)
                            }
                            size="sm"
                            variant="ghost"
                            className="text-red-600 hover:bg-red-50"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Communication Editor Modal */}
      <AnimatePresence>
        {showEditor && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
              onClick={closeEditor}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="fixed inset-4 md:inset-auto md:top-1/2 md:left-1/2 md:transform md:-translate-x-1/2 md:-translate-y-1/2 bg-white rounded-lg shadow-2xl z-50 md:w-full md:max-w-3xl max-h-[90vh] overflow-hidden flex flex-col"
            >
              {/* Editor Header */}
              <div className="flex items-center justify-between p-6 border-b border-[#C4BDB4]/20">
                <h2 className="text-2xl font-bold text-[#2A5D67]">
                  {editingCommunication
                    ? "Modifica Comunicazione"
                    : "Nuova Comunicazione"}
                </h2>
                <button
                  onClick={closeEditor}
                  className="text-[#C4BDB4] hover:text-[#2A5D67] transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {/* Editor Content */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {/* Client Selector */}
                <div>
                  <label className="block text-sm font-medium text-[#1E293B] mb-2">
                    Cliente *
                  </label>
                  <Select value={editorClient} onValueChange={setEditorClient}>
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
                </div>

                {/* Template Selector */}
                <div>
                  <label className="block text-sm font-medium text-[#1E293B] mb-2">
                    Template
                  </label>
                  <Select
                    value={editorTemplate}
                    onValueChange={setEditorTemplate}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Seleziona un template (opzionale)" />
                    </SelectTrigger>
                    <SelectContent>
                      {mockTemplates.map((template) => (
                        <SelectItem key={template.id} value={template.id}>
                          {template.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Channel Selector */}
                <div>
                  <label className="block text-sm font-medium text-[#1E293B] mb-2">
                    Canale *
                  </label>
                  <div className="flex space-x-4">
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => setEditorChannel("email")}
                      className={`flex-1 flex items-center justify-center space-x-2 p-4 rounded-lg border-2 transition-all ${
                        editorChannel === "email"
                          ? "border-[#2A5D67] bg-[#F8F5F1]"
                          : "border-[#C4BDB4]/20 hover:border-[#C4BDB4]"
                      }`}
                    >
                      <Mail className="w-5 h-5" />
                      <span className="font-medium">Email</span>
                    </motion.button>
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => setEditorChannel("whatsapp")}
                      className={`flex-1 flex items-center justify-center space-x-2 p-4 rounded-lg border-2 transition-all ${
                        editorChannel === "whatsapp"
                          ? "border-[#2A5D67] bg-[#F8F5F1]"
                          : "border-[#C4BDB4]/20 hover:border-[#C4BDB4]"
                      }`}
                    >
                      <MessageCircle className="w-5 h-5" />
                      <span className="font-medium">WhatsApp</span>
                    </motion.button>
                  </div>
                </div>

                {/* Subject */}
                <div>
                  <label className="block text-sm font-medium text-[#1E293B] mb-2">
                    Oggetto *
                  </label>
                  <Input
                    type="text"
                    value={editorSubject}
                    onChange={(e) => setEditorSubject(e.target.value)}
                    placeholder="Inserisci l'oggetto della comunicazione"
                    className="w-full"
                  />
                </div>

                {/* Body */}
                <div>
                  <label className="block text-sm font-medium text-[#1E293B] mb-2">
                    Contenuto *
                  </label>
                  <Textarea
                    value={editorBody}
                    onChange={(e) => setEditorBody(e.target.value)}
                    placeholder="Scrivi il contenuto della comunicazione..."
                    className="w-full min-h-[300px] resize-none"
                  />
                  <p className="text-xs text-[#C4BDB4] mt-2">
                    {editorBody.length} caratteri
                  </p>
                </div>
              </div>

              {/* Editor Footer */}
              <div className="flex items-center justify-end space-x-3 p-6 border-t border-[#C4BDB4]/20 bg-[#F8F5F1]">
                <Button
                  onClick={closeEditor}
                  variant="outline"
                  className="text-[#1E293B]"
                >
                  Annulla
                </Button>
                <Button
                  onClick={handleSaveCommunication}
                  disabled={!editorClient || !editorSubject || !editorBody}
                  className={`${
                    editorClient && editorSubject && editorBody
                      ? "bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                      : "bg-[#C4BDB4] text-white cursor-not-allowed"
                  }`}
                >
                  <Check className="w-4 h-4 mr-2" />
                  <span className="font-bold">Salva Bozza</span>
                </Button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
