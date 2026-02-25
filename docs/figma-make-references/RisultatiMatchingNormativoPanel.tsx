import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  CheckCircle,
  Calendar,
  ExternalLink,
  Target,
  Info,
  Mail,
  XCircle,
  Check,
  Filter,
  Search,
  FileText,
  Clock,
  TrendingUp,
  User,
} from "lucide-react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { Checkbox } from "./ui/checkbox";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

type UrgencyLevel = "critical" | "high" | "medium" | "informational";
type MatchType = "NORMATIVA" | "SCADENZA" | "OPPORTUNITA";

interface NormativeMatch {
  id: string;
  title: string;
  type: MatchType;
  urgency: UrgencyLevel;
  relevanceScore: number;
  matchReason: string;
  actionRequired: string;
  deadline?: string;
  sourceLink: string;
  sourceName: string;
  publishDate: string;
  matchedAttributes: string[];
  status: "new" | "reviewed" | "handled" | "ignored";
}

interface RisultatiMatchingNormativoPanelProps {
  clientName?: string;
  clientId?: string;
  matches?: NormativeMatch[];
  onGenerateCommunication?: (matchIds: string[]) => void;
  onIgnore?: (matchIds: string[]) => void;
  onMarkAsHandled?: (matchIds: string[]) => void;
  embedded?: boolean;
}

// Mock data
const mockMatches: NormativeMatch[] = [
  {
    id: "match_001",
    title: "D.L. 142/2024 - Bonus Investimenti Sud 4.0",
    type: "OPPORTUNITA",
    urgency: "high",
    relevanceScore: 95,
    matchReason:
      "Cliente con sede operativa in Campania (Zona ZES), ATECO 62.01 (sviluppo software), investimenti pianificati 2024",
    actionRequired:
      "Verificare requisiti di accesso e preparare domanda entro la scadenza. Credito d'imposta fino al 45% per investimenti in beni strumentali.",
    deadline: "2024-03-31",
    sourceLink:
      "https://www.gazzettaufficiale.it/eli/id/2024/02/15/24G00142/sg",
    sourceName: "Gazzetta Ufficiale Serie Generale n.38",
    publishDate: "2024-02-15",
    matchedAttributes: [
      "Localizzazione: Campania (ZES)",
      "Settore ATECO: 62.01",
      "Investimenti programmati",
    ],
    status: "new",
  },
  {
    id: "match_002",
    title: "Circolare INPS 23/2024 - Nuovi massimali contributivi",
    type: "NORMATIVA",
    urgency: "critical",
    relevanceScore: 92,
    matchReason:
      "Cliente con dipendenti a tempo indeterminato, obbligo di adeguamento contributi dal 01/03/2024",
    actionRequired:
      "URGENTE: Aggiornare sistema paghe con i nuovi massimali. Ricalcolare contributi di febbraio. Comunicare ai dipendenti le variazioni in busta paga.",
    deadline: "2024-02-28",
    sourceLink:
      "https://www.inps.it/circolari/circolare-numero-23-del-12-02-2024",
    sourceName: "INPS - Circolare n.23",
    publishDate: "2024-02-12",
    matchedAttributes: [
      "Dipendenti: 5 a tempo indeterminato",
      "Regime: Ordinario",
      "Obblighi contributivi attivi",
    ],
    status: "new",
  },
  {
    id: "match_003",
    title: "Legge di Bilancio 2024 - Detrazioni ristrutturazioni",
    type: "OPPORTUNITA",
    urgency: "medium",
    relevanceScore: 78,
    matchReason:
      "Cliente proprietario immobile commerciale, possibile accesso a superbonus ristrutturazioni per efficientamento energetico",
    actionRequired:
      "Valutare interventi di efficientamento energetico. Nuove aliquote: 70% per spese sostenute nel 2024, scende al 65% nel 2025.",
    deadline: "2024-12-31",
    sourceLink:
      "https://www.agenziaentrate.gov.it/portale/web/guest/legge-bilancio-2024",
    sourceName: "Agenzia delle Entrate",
    publishDate: "2024-01-01",
    matchedAttributes: [
      "Proprietà immobile commerciale",
      "Categoria catastale C/1",
      "Interesse dichiarato: sostenibilità",
    ],
    status: "reviewed",
  },
  {
    id: "match_004",
    title: "Provvedimento ADE 45782/2024 - Fatturazione elettronica verso PA",
    type: "SCADENZA",
    urgency: "high",
    relevanceScore: 88,
    matchReason:
      "Cliente con contratti attivi verso enti pubblici, nuovo obbligo di split payment dal 01/04/2024",
    actionRequired:
      "Verificare tutti i contratti PA attivi. Aggiornare software fatturazione per gestione automatica split payment. Formare personale amministrativo.",
    deadline: "2024-03-25",
    sourceLink:
      "https://www.agenziaentrate.gov.it/portale/provvedimento-45782-2024",
    sourceName: "Agenzia delle Entrate",
    publishDate: "2024-02-10",
    matchedAttributes: [
      "Clienti PA: 3 attivi",
      "Fatturato PA: 35% del totale",
      "Software: Fatturazione elettronica",
    ],
    status: "new",
  },
  {
    id: "match_005",
    title: "Decreto MEF 18/2024 - Nuove regole compensazione crediti IVA",
    type: "NORMATIVA",
    urgency: "medium",
    relevanceScore: 71,
    matchReason:
      "Cliente con credito IVA trimestrale superiore a €5.000, nuove procedure di verifica preventiva",
    actionRequired:
      "Predisporre documentazione aggiuntiva per compensazione crediti IVA. Richiesta visto di conformità per importi superiori a €5.000.",
    deadline: "2024-03-15",
    sourceLink: "https://www.mef.gov.it/decreti/decreto-18-2024",
    sourceName: "Ministero Economia e Finanze",
    publishDate: "2024-02-05",
    matchedAttributes: [
      "Credito IVA trimestrale: €7.200",
      "Regime IVA: Ordinario",
      "Trimestrale: Attivo",
    ],
    status: "new",
  },
  {
    id: "match_006",
    title: "Comunicazione Agenzia Entrate - Privacy e GDPR per professionisti",
    type: "NORMATIVA",
    urgency: "informational",
    relevanceScore: 65,
    matchReason:
      "Cliente con attività professionale, aggiornamento linee guida trattamento dati clienti",
    actionRequired:
      "Informativa: Revisione delle linee guida sul trattamento dati. Consigliato aggiornamento informativa privacy clienti entro 6 mesi.",
    sourceLink:
      "https://www.agenziaentrate.gov.it/portale/privacy-professionisti",
    sourceName: "Agenzia delle Entrate",
    publishDate: "2024-01-20",
    matchedAttributes: [
      "Attività: Libero professionista",
      "Gestione dati clienti",
      "Privacy: GDPR compliance",
    ],
    status: "reviewed",
  },
  {
    id: "match_007",
    title: "D.L. 156/2024 - Proroga termini dichiarazione redditi",
    type: "SCADENZA",
    urgency: "informational",
    relevanceScore: 82,
    matchReason:
      "Proroga automatica al 15 ottobre 2024 per dichiarazione dei redditi",
    actionRequired:
      "Informare il cliente della proroga. Riprogrammare scadenze interne di studio. Nessuna azione immediata richiesta.",
    deadline: "2024-10-15",
    sourceLink: "https://www.agenziaentrate.gov.it/portale/decreto-156-2024",
    sourceName: "Agenzia delle Entrate",
    publishDate: "2024-02-18",
    matchedAttributes: [
      "Soggetto: Persona fisica",
      "Dichiarazione: Modello 730/2024",
      "Scadenza originaria: 30/09",
    ],
    status: "handled",
  },
];

const getUrgencyColor = (urgency: UrgencyLevel) => {
  switch (urgency) {
    case "critical":
      return {
        bg: "bg-red-50",
        border: "border-red-300",
        text: "text-red-700",
        badge: "bg-red-100 text-red-700 border-red-300",
        icon: "text-red-600",
      };
    case "high":
      return {
        bg: "bg-orange-50",
        border: "border-orange-300",
        text: "text-orange-700",
        badge: "bg-orange-100 text-orange-700 border-orange-300",
        icon: "text-orange-600",
      };
    case "medium":
      return {
        bg: "bg-yellow-50",
        border: "border-yellow-300",
        text: "text-yellow-700",
        badge: "bg-yellow-100 text-yellow-700 border-yellow-300",
        icon: "text-yellow-600",
      };
    case "informational":
      return {
        bg: "bg-green-50",
        border: "border-green-300",
        text: "text-green-700",
        badge: "bg-green-100 text-green-700 border-green-300",
        icon: "text-green-600",
      };
  }
};

const getUrgencyLabel = (urgency: UrgencyLevel) => {
  switch (urgency) {
    case "critical":
      return "Critica";
    case "high":
      return "Alta";
    case "medium":
      return "Media";
    case "informational":
      return "Informativa";
  }
};

const getTypeIcon = (type: MatchType) => {
  switch (type) {
    case "NORMATIVA":
      return FileText;
    case "SCADENZA":
      return Clock;
    case "OPPORTUNITA":
      return TrendingUp;
  }
};

const getTypeColor = (type: MatchType) => {
  switch (type) {
    case "NORMATIVA":
      return "bg-blue-100 text-blue-700 border-blue-300";
    case "SCADENZA":
      return "bg-purple-100 text-purple-700 border-purple-300";
    case "OPPORTUNITA":
      return "bg-green-100 text-green-700 border-green-300";
  }
};

export function RisultatiMatchingNormativoPanel({
  clientName = "Studio Legale Rossi & Associati",
  clientId = "client_001",
  matches = mockMatches,
  onGenerateCommunication,
  onIgnore,
  onMarkAsHandled,
  embedded = false,
}: RisultatiMatchingNormativoPanelProps) {
  const [expandedMatches, setExpandedMatches] = useState<Set<string>>(
    new Set(),
  );
  const [selectedMatches, setSelectedMatches] = useState<Set<string>>(
    new Set(),
  );
  const [filterType, setFilterType] = useState<MatchType | "all">("all");
  const [filterUrgency, setFilterUrgency] = useState<UrgencyLevel | "all">(
    "all",
  );
  const [filterStatus, setFilterStatus] = useState<
    "all" | "new" | "reviewed" | "handled" | "ignored"
  >("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const toggleExpanded = (matchId: string) => {
    const newExpanded = new Set(expandedMatches);
    if (newExpanded.has(matchId)) {
      newExpanded.delete(matchId);
    } else {
      newExpanded.add(matchId);
    }
    setExpandedMatches(newExpanded);
  };

  const toggleSelected = (matchId: string) => {
    const newSelected = new Set(selectedMatches);
    if (newSelected.has(matchId)) {
      newSelected.delete(matchId);
    } else {
      newSelected.add(matchId);
    }
    setSelectedMatches(newSelected);
  };

  const selectAll = () => {
    if (selectedMatches.size === filteredMatches.length) {
      setSelectedMatches(new Set());
    } else {
      setSelectedMatches(new Set(filteredMatches.map((m) => m.id)));
    }
  };

  const handleBulkAction = (action: "communicate" | "ignore" | "handled") => {
    const selectedIds = Array.from(selectedMatches);

    switch (action) {
      case "communicate":
        if (onGenerateCommunication) onGenerateCommunication(selectedIds);
        break;
      case "ignore":
        if (onIgnore) onIgnore(selectedIds);
        break;
      case "handled":
        if (onMarkAsHandled) onMarkAsHandled(selectedIds);
        break;
    }

    // Clear selection after action
    setSelectedMatches(new Set());
  };

  // Filter matches
  const filteredMatches = matches.filter((match) => {
    if (filterType !== "all" && match.type !== filterType) return false;
    if (filterUrgency !== "all" && match.urgency !== filterUrgency)
      return false;
    if (filterStatus !== "all" && match.status !== filterStatus) return false;
    if (
      searchQuery &&
      !match.title.toLowerCase().includes(searchQuery.toLowerCase())
    )
      return false;
    return true;
  });

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("it-IT", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  };

  const getDaysUntil = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffDays = Math.ceil(diffMs / 86400000);
    return diffDays;
  };

  return (
    <div className={embedded ? "" : "min-h-screen bg-[#F8F5F1] p-6"}>
      <div className={embedded ? "" : "max-w-6xl mx-auto"}>
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h2 className="text-2xl font-bold text-[#2A5D67] flex items-center">
                <Target className="w-6 h-6 mr-2" />
                Risultati Matching Normativo
              </h2>
              {clientName && (
                <p className="text-sm text-[#1E293B] mt-1 flex items-center">
                  <User className="w-4 h-4 mr-1" />
                  {clientName}
                </p>
              )}
            </div>
            <div className="flex items-center space-x-3">
              <Badge className="bg-[#2A5D67] text-white border-[#2A5D67] px-4 py-2 text-base">
                {filteredMatches.length} Match Trovati
              </Badge>
            </div>
          </div>
        </div>

        {/* Search and Filters */}
        <Card className="border-[#C4BDB4]/20 mb-6">
          <CardContent className="pt-6">
            <div className="space-y-4">
              {/* Search Bar */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-[#C4BDB4]" />
                <Input
                  placeholder="Cerca normativa per titolo..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 border-[#C4BDB4]/20"
                />
              </div>

              {/* Filter Toggle */}
              <div className="flex items-center justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowFilters(!showFilters)}
                  className="border-[#C4BDB4]/20"
                >
                  <Filter className="w-4 h-4 mr-2" />
                  {showFilters ? "Nascondi Filtri" : "Mostra Filtri"}
                </Button>

                {/* Active filters count */}
                {(filterType !== "all" ||
                  filterUrgency !== "all" ||
                  filterStatus !== "all") && (
                  <Badge
                    variant="outline"
                    className="border-[#2A5D67] text-[#2A5D67]"
                  >
                    {
                      [filterType, filterUrgency, filterStatus].filter(
                        (f) => f !== "all",
                      ).length
                    }{" "}
                    filtri attivi
                  </Badge>
                )}
              </div>

              {/* Filters */}
              <AnimatePresence>
                {showFilters && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-[#C4BDB4]/20"
                  >
                    {/* Type Filter */}
                    <div>
                      <Label className="text-sm font-medium text-[#1E293B] mb-2 block">
                        Tipo Match
                      </Label>
                      <div className="space-y-2">
                        {(
                          [
                            "all",
                            "NORMATIVA",
                            "SCADENZA",
                            "OPPORTUNITA",
                          ] as const
                        ).map((type) => (
                          <div key={type} className="flex items-center">
                            <input
                              type="radio"
                              id={`type-${type}`}
                              name="type"
                              checked={filterType === type}
                              onChange={() => setFilterType(type)}
                              className="w-4 h-4 text-[#2A5D67] focus:ring-[#2A5D67]"
                            />
                            <label
                              htmlFor={`type-${type}`}
                              className="ml-2 text-sm text-[#1E293B]"
                            >
                              {type === "all" ? "Tutti" : type}
                            </label>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Urgency Filter */}
                    <div>
                      <Label className="text-sm font-medium text-[#1E293B] mb-2 block">
                        Livello Urgenza
                      </Label>
                      <div className="space-y-2">
                        {(
                          [
                            "all",
                            "critical",
                            "high",
                            "medium",
                            "informational",
                          ] as const
                        ).map((urgency) => (
                          <div key={urgency} className="flex items-center">
                            <input
                              type="radio"
                              id={`urgency-${urgency}`}
                              name="urgency"
                              checked={filterUrgency === urgency}
                              onChange={() => setFilterUrgency(urgency)}
                              className="w-4 h-4 text-[#2A5D67] focus:ring-[#2A5D67]"
                            />
                            <label
                              htmlFor={`urgency-${urgency}`}
                              className="ml-2 text-sm text-[#1E293B]"
                            >
                              {urgency === "all"
                                ? "Tutti"
                                : getUrgencyLabel(urgency)}
                            </label>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Status Filter */}
                    <div>
                      <Label className="text-sm font-medium text-[#1E293B] mb-2 block">
                        Stato
                      </Label>
                      <div className="space-y-2">
                        {(
                          [
                            "all",
                            "new",
                            "reviewed",
                            "handled",
                            "ignored",
                          ] as const
                        ).map((status) => (
                          <div key={status} className="flex items-center">
                            <input
                              type="radio"
                              id={`status-${status}`}
                              name="status"
                              checked={filterStatus === status}
                              onChange={() => setFilterStatus(status)}
                              className="w-4 h-4 text-[#2A5D67] focus:ring-[#2A5D67]"
                            />
                            <label
                              htmlFor={`status-${status}`}
                              className="ml-2 text-sm text-[#1E293B] capitalize"
                            >
                              {status === "all"
                                ? "Tutti"
                                : status === "new"
                                  ? "Nuovo"
                                  : status === "reviewed"
                                    ? "Revisionato"
                                    : status === "handled"
                                      ? "Gestito"
                                      : "Ignorato"}
                            </label>
                          </div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </CardContent>
        </Card>

        {/* Bulk Actions */}
        {selectedMatches.size > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-[#2A5D67] text-white rounded-lg p-4 mb-6 shadow-lg"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-5 h-5" />
                <span className="font-semibold">
                  {selectedMatches.size} match selezionat
                  {selectedMatches.size === 1 ? "o" : "i"}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  size="sm"
                  onClick={() => handleBulkAction("communicate")}
                  className="bg-white text-[#2A5D67] hover:bg-[#F8F5F1]"
                >
                  <Mail className="w-4 h-4 mr-2" />
                  <span className="font-bold">Genera Comunicazione</span>
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleBulkAction("handled")}
                  className="border-white text-white hover:bg-[#1E293B]"
                >
                  <Check className="w-4 h-4 mr-2" />
                  <span className="font-bold">Segna come Gestito</span>
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleBulkAction("ignore")}
                  className="border-white text-white hover:bg-[#1E293B]"
                >
                  <XCircle className="w-4 h-4 mr-2" />
                  <span className="font-bold">Ignora</span>
                </Button>
              </div>
            </div>
          </motion.div>
        )}

        {/* Select All */}
        {filteredMatches.length > 0 && (
          <div className="mb-4 flex items-center space-x-2">
            <Checkbox
              id="select-all"
              checked={
                selectedMatches.size === filteredMatches.length &&
                filteredMatches.length > 0
              }
              onCheckedChange={selectAll}
            />
            <label
              htmlFor="select-all"
              className="text-sm font-medium text-[#1E293B] cursor-pointer"
            >
              Seleziona tutti ({filteredMatches.length})
            </label>
          </div>
        )}

        {/* Matches List */}
        <div className="space-y-4">
          {filteredMatches.length === 0 ? (
            <Card className="border-[#C4BDB4]/20">
              <CardContent className="py-12 text-center">
                <Info className="w-12 h-12 text-[#C4BDB4] mx-auto mb-4" />
                <p className="text-[#1E293B] text-lg">
                  Nessun match trovato con i filtri selezionati
                </p>
              </CardContent>
            </Card>
          ) : (
            filteredMatches.map((match, index) => {
              const isExpanded = expandedMatches.has(match.id);
              const isSelected = selectedMatches.has(match.id);
              const urgencyColors = getUrgencyColor(match.urgency);
              const TypeIcon = getTypeIcon(match.type);
              const daysUntil = match.deadline
                ? getDaysUntil(match.deadline)
                : null;

              return (
                <motion.div
                  key={match.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <Card
                    className={`border-2 ${isSelected ? "border-[#2A5D67] shadow-lg" : urgencyColors.border} ${urgencyColors.bg} transition-all`}
                  >
                    <CardHeader className="pb-3">
                      <div className="flex items-start space-x-3">
                        {/* Checkbox */}
                        <Checkbox
                          id={`match-${match.id}`}
                          checked={isSelected}
                          onCheckedChange={() => toggleSelected(match.id)}
                          className="mt-1"
                        />

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1">
                              <div className="flex items-center space-x-2 mb-2">
                                <Badge
                                  className={`${getTypeColor(match.type)} border`}
                                >
                                  <TypeIcon className="w-3 h-3 mr-1" />
                                  {match.type}
                                </Badge>
                                <Badge
                                  className={`${urgencyColors.badge} border`}
                                >
                                  <AlertTriangle className="w-3 h-3 mr-1" />
                                  {getUrgencyLabel(match.urgency)}
                                </Badge>
                                {match.deadline &&
                                  daysUntil !== null &&
                                  daysUntil <= 7 && (
                                    <Badge className="bg-red-100 text-red-700 border-red-300 border">
                                      <Calendar className="w-3 h-3 mr-1" />
                                      {daysUntil === 0
                                        ? "Oggi!"
                                        : daysUntil === 1
                                          ? "Domani"
                                          : `${daysUntil} giorni`}
                                    </Badge>
                                  )}
                              </div>
                              <h3 className="font-bold text-[#2A5D67] text-lg mb-1">
                                {match.title}
                              </h3>
                              <p className="text-sm text-[#1E293B] mb-2">
                                {match.matchReason}
                              </p>
                            </div>

                            {/* Relevance Score */}
                            <div className="ml-4 flex flex-col items-center">
                              <div className="relative w-16 h-16 flex items-center justify-center">
                                <svg
                                  className="w-full h-full transform -rotate-90"
                                  viewBox="0 0 64 64"
                                >
                                  <circle
                                    cx="32"
                                    cy="32"
                                    r="28"
                                    stroke="#E5E7EB"
                                    strokeWidth="6"
                                    fill="none"
                                  />
                                  <circle
                                    cx="32"
                                    cy="32"
                                    r="28"
                                    stroke="#2A5D67"
                                    strokeWidth="6"
                                    fill="none"
                                    strokeDasharray={`${match.relevanceScore * 1.76} 176`}
                                    strokeLinecap="round"
                                  />
                                </svg>
                                <div className="absolute inset-0 flex items-center justify-center">
                                  <span className="text-lg font-bold text-[#2A5D67]">
                                    {match.relevanceScore}%
                                  </span>
                                </div>
                              </div>
                              <span className="text-xs text-[#1E293B] mt-1">
                                Rilevanza
                              </span>
                            </div>
                          </div>

                          {/* Expandable Content */}
                          <AnimatePresence>
                            {isExpanded && (
                              <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: "auto" }}
                                exit={{ opacity: 0, height: 0 }}
                                className="border-t border-[#C4BDB4]/30 pt-4 mt-4 space-y-4"
                              >
                                {/* Action Required */}
                                <div>
                                  <h4 className="font-semibold text-[#2A5D67] mb-2 flex items-center">
                                    <CheckCircle className="w-4 h-4 mr-2" />
                                    Azione Richiesta
                                  </h4>
                                  <p className="text-sm text-[#1E293B] bg-white/50 p-3 rounded-lg">
                                    {match.actionRequired}
                                  </p>
                                </div>

                                {/* Deadline */}
                                {match.deadline && (
                                  <div>
                                    <h4 className="font-semibold text-[#2A5D67] mb-2 flex items-center">
                                      <Calendar className="w-4 h-4 mr-2" />
                                      Scadenza
                                    </h4>
                                    <p className="text-sm text-[#1E293B]">
                                      {formatDate(match.deadline)}
                                      {daysUntil !== null && (
                                        <span className="ml-2 text-[#94A3B8]">
                                          (
                                          {daysUntil === 0
                                            ? "Oggi!"
                                            : daysUntil === 1
                                              ? "Domani"
                                              : daysUntil > 0
                                                ? `Tra ${daysUntil} giorni`
                                                : `Scaduto da ${Math.abs(daysUntil)} giorni`}
                                          )
                                        </span>
                                      )}
                                    </p>
                                  </div>
                                )}

                                {/* Matched Attributes */}
                                <div>
                                  <h4 className="font-semibold text-[#2A5D67] mb-2 flex items-center">
                                    <Target className="w-4 h-4 mr-2" />
                                    Attributi Matchati
                                  </h4>
                                  <div className="flex flex-wrap gap-2">
                                    {match.matchedAttributes.map(
                                      (attr, idx) => (
                                        <Badge
                                          key={idx}
                                          variant="outline"
                                          className="bg-white/50 border-[#2A5D67] text-[#2A5D67]"
                                        >
                                          {attr}
                                        </Badge>
                                      ),
                                    )}
                                  </div>
                                </div>

                                {/* Source */}
                                <div>
                                  <h4 className="font-semibold text-[#2A5D67] mb-2 flex items-center">
                                    <FileText className="w-4 h-4 mr-2" />
                                    Fonte
                                  </h4>
                                  <div className="flex items-center justify-between bg-white/50 p-3 rounded-lg">
                                    <div>
                                      <p className="text-sm font-medium text-[#1E293B]">
                                        {match.sourceName}
                                      </p>
                                      <p className="text-xs text-[#94A3B8]">
                                        Pubblicato il{" "}
                                        {formatDate(match.publishDate)}
                                      </p>
                                    </div>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() =>
                                        window.open(match.sourceLink, "_blank")
                                      }
                                      className="border-[#2A5D67] text-[#2A5D67] hover:bg-[#2A5D67] hover:text-white"
                                    >
                                      <ExternalLink className="w-4 h-4 mr-2" />
                                      Apri Fonte
                                    </Button>
                                  </div>
                                </div>

                                {/* Individual Actions */}
                                <div className="flex items-center space-x-2 pt-2">
                                  <Button
                                    size="sm"
                                    className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                                    onClick={() => {
                                      if (onGenerateCommunication)
                                        onGenerateCommunication([match.id]);
                                    }}
                                  >
                                    <Mail className="w-4 h-4 mr-2" />
                                    <span className="font-bold">
                                      Genera Comunicazione
                                    </span>
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="border-[#2A5D67] text-[#2A5D67]"
                                    onClick={() => {
                                      if (onMarkAsHandled)
                                        onMarkAsHandled([match.id]);
                                    }}
                                  >
                                    <Check className="w-4 h-4 mr-2" />
                                    <span className="font-bold">Gestito</span>
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="border-[#94A3B8] text-[#94A3B8]"
                                    onClick={() => {
                                      if (onIgnore) onIgnore([match.id]);
                                    }}
                                  >
                                    <XCircle className="w-4 h-4 mr-2" />
                                    <span className="font-bold">Ignora</span>
                                  </Button>
                                </div>
                              </motion.div>
                            )}
                          </AnimatePresence>

                          {/* Expand/Collapse Button */}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => toggleExpanded(match.id)}
                            className="w-full mt-3 text-[#2A5D67] hover:bg-white/50"
                          >
                            {isExpanded ? (
                              <>
                                <ChevronUp className="w-4 h-4 mr-2" />
                                Mostra Meno
                              </>
                            ) : (
                              <>
                                <ChevronDown className="w-4 h-4 mr-2" />
                                Mostra Dettagli
                              </>
                            )}
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                  </Card>
                </motion.div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
