import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Button } from "./ui/button";
import {
  ArrowLeft,
  Calendar,
  Clock,
  AlertTriangle,
  CheckCircle,
  Bell,
  Filter,
  Search,
  Download,
  Plus,
  ChevronLeft,
  ChevronRight,
  CalendarDays,
  Building,
  Receipt,
  CreditCard,
  FileText,
  Euro,
  Users,
  Target,
  Brain,
} from "lucide-react";

interface ScadenzaFiscale {
  id: string;
  title: string;
  description: string;
  date: string;
  category: "iva" | "imposte" | "contributi" | "dichiarazioni" | "versamenti";
  priority: "alta" | "media" | "bassa";
  completed: boolean;
  applicableTo: string[];
  amount?: string;
  penalties?: string;
}

interface ScadenzeFiscaliPageProps {
  onBackToChat: () => void;
}

export function ScadenzeFiscaliPage({
  onBackToChat,
}: ScadenzeFiscaliPageProps) {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [viewMode, setViewMode] = useState<"calendar" | "list">("list");

  const categories = [
    {
      id: "iva",
      name: "IVA",
      icon: Receipt,
      color: "bg-blue-100 text-blue-700",
    },
    {
      id: "imposte",
      name: "Imposte Dirette",
      icon: Building,
      color: "bg-green-100 text-green-700",
    },
    {
      id: "contributi",
      name: "Contributi",
      icon: Users,
      color: "bg-purple-100 text-purple-700",
    },
    {
      id: "dichiarazioni",
      name: "Dichiarazioni",
      icon: FileText,
      color: "bg-orange-100 text-orange-700",
    },
    {
      id: "versamenti",
      name: "Versamenti",
      icon: CreditCard,
      color: "bg-pink-100 text-pink-700",
    },
  ];

  const mockScadenze: ScadenzaFiscale[] = [
    {
      id: "1",
      title: "Versamento IVA Mensile",
      description: "Versamento dell'IVA relativa al mese di gennaio 2025",
      date: "2025-02-16",
      category: "iva",
      priority: "alta",
      completed: false,
      applicableTo: ["Soggetti IVA mensili"],
      amount: "Variabile",
      penalties: "30% dell'imposta dovuta + interessi",
    },
    {
      id: "2",
      title: "Ritenute alla Fonte",
      description:
        "Versamento ritenute IRPEF su lavoro dipendente e assimilati",
      date: "2025-02-16",
      category: "imposte",
      priority: "alta",
      completed: false,
      applicableTo: ["Datori di lavoro", "Sostituti d'imposta"],
      amount: "Secondo il modello F24",
      penalties: "30% dell'imposta + interessi",
    },
    {
      id: "3",
      title: "Contributi INPS",
      description: "Versamento contributi previdenziali dipendenti",
      date: "2025-02-16",
      category: "contributi",
      priority: "alta",
      completed: false,
      applicableTo: ["Aziende con dipendenti"],
      amount: "Secondo DM10",
      penalties: "Sanzioni dal 3% al 15%",
    },
    {
      id: "4",
      title: "Comunicazione Dati IVA",
      description: "Invio telematico dei dati delle fatture emesse e ricevute",
      date: "2025-02-25",
      category: "iva",
      priority: "media",
      completed: false,
      applicableTo: ["Tutti i soggetti IVA"],
      amount: "Gratuito",
      penalties: "Da €250 a €2.000 per omessa comunicazione",
    },
    {
      id: "5",
      title: "Acconto Imposte 2025",
      description: "Primo acconto IRPEF/IRES per il periodo d'imposta 2025",
      date: "2025-06-16",
      category: "imposte",
      priority: "media",
      completed: false,
      applicableTo: ["Persone fisiche", "Società"],
      amount: "40% dell'imposta dell'anno precedente",
      penalties: "30% dell'imposta + interessi",
    },
    {
      id: "6",
      title: "Modello 770 Semplificato",
      description: "Dichiarazione annuale sostituti d'imposta",
      date: "2025-07-31",
      category: "dichiarazioni",
      priority: "alta",
      completed: false,
      applicableTo: ["Sostituti d'imposta"],
      amount: "Gratuito",
      penalties: "Da €258 a €2.065",
    },
  ];

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "alta":
        return "bg-red-100 text-red-700 border-red-200";
      case "media":
        return "bg-yellow-100 text-yellow-700 border-yellow-200";
      case "bassa":
        return "bg-green-100 text-green-700 border-green-200";
      default:
        return "bg-gray-100 text-gray-700 border-gray-200";
    }
  };

  const getCategoryInfo = (category: string) => {
    return categories.find((cat) => cat.id === category) || categories[0];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("it-IT", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const isUpcoming = (dateString: string) => {
    const scadenza = new Date(dateString);
    const oggi = new Date();
    const diffTime = scadenza.getTime() - oggi.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays <= 7 && diffDays >= 0;
  };

  const filteredScadenze = mockScadenze.filter((scadenza) => {
    const matchesCategory =
      selectedCategory === "all" || scadenza.category === selectedCategory;
    const matchesSearch =
      scadenza.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      scadenza.description.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const upcomingScadenze = filteredScadenze.filter((scadenza) =>
    isUpcoming(scadenza.date),
  );

  return (
    <div className="min-h-screen bg-[#F8F5F1] relative">
      <div className="relative">
        {/* Header */}
        <div className="bg-white border-b border-[#C4BDB4]/20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <Button
                  onClick={onBackToChat}
                  variant="ghost"
                  size="sm"
                  className="text-[#2A5D67] hover:bg-[#F8F5F1]"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Torna alla Chat
                </Button>
                <div className="w-px h-6 bg-[#C4BDB4]" />
                <div>
                  <h1 className="text-2xl font-bold text-[#2A5D67]">
                    Scadenze Fiscali
                  </h1>
                  <p className="text-[#1E293B] text-sm">
                    Gestisci le tue scadenze fiscali e rimani sempre aggiornato
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                {/* View Toggle */}
                <div className="flex bg-[#F8F5F1] rounded-lg p-1">
                  <button
                    onClick={() => setViewMode("list")}
                    className={`p-2 rounded-md transition-all ${
                      viewMode === "list"
                        ? "bg-white text-[#2A5D67] shadow-sm"
                        : "text-[#C4BDB4] hover:text-[#2A5D67]"
                    }`}
                  >
                    <FileText className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setViewMode("calendar")}
                    className={`p-2 rounded-md transition-all ${
                      viewMode === "calendar"
                        ? "bg-white text-[#2A5D67] shadow-sm"
                        : "text-[#C4BDB4] hover:text-[#2A5D67]"
                    }`}
                  >
                    <CalendarDays className="w-4 h-4" />
                  </button>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  className="text-[#2A5D67] border-[#2A5D67]/20 hover:bg-[#F8F5F1]"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Esporta
                </Button>

                <Button
                  size="sm"
                  className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Aggiungi Scadenza
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Alert Scadenze Imminenti */}
        {upcomingScadenze.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-r from-red-50 to-orange-50 border-l-4 border-red-400 p-4 mx-4 mt-4 rounded-r-lg"
          >
            <div className="flex items-center">
              <AlertTriangle className="w-5 h-5 text-red-400 mr-3" />
              <div>
                <h3 className="font-semibold text-red-800">
                  {upcomingScadenze.length} scadenz
                  {upcomingScadenze.length === 1 ? "a" : "e"} nei prossimi 7
                  giorni
                </h3>
                <p className="text-red-600 text-sm">
                  Controlla le scadenze imminenti per evitare sanzioni
                </p>
              </div>
            </div>
          </motion.div>
        )}

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* Sidebar */}
            <div className="lg:col-span-1">
              <div className="space-y-6">
                {/* Search */}
                <div className="bg-white rounded-xl p-6 shadow-sm border border-[#C4BDB4]/20">
                  <h3 className="font-semibold text-[#2A5D67] mb-4">
                    Cerca Scadenze
                  </h3>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-[#C4BDB4]" />
                    <input
                      type="text"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      placeholder="Cerca per titolo..."
                      className="w-full pl-10 pr-4 py-3 border border-[#C4BDB4]/20 rounded-lg focus:ring-2 focus:ring-[#2A5D67]/20 focus:border-[#2A5D67] transition-all"
                    />
                  </div>
                </div>

                {/* Categories */}
                <div className="bg-white rounded-xl p-6 shadow-sm border border-[#C4BDB4]/20">
                  <h3 className="font-semibold text-[#2A5D67] mb-4">
                    Categorie
                  </h3>
                  <div className="space-y-2">
                    <button
                      onClick={() => setSelectedCategory("all")}
                      className={`w-full text-left p-3 rounded-lg transition-all ${
                        selectedCategory === "all"
                          ? "bg-[#2A5D67] text-white"
                          : "hover:bg-[#F8F5F1] text-[#1E293B]"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>Tutte le Scadenze</span>
                        <span className="text-sm opacity-70">
                          {mockScadenze.length}
                        </span>
                      </div>
                    </button>

                    {categories.map((category) => {
                      const count = mockScadenze.filter(
                        (s) => s.category === category.id,
                      ).length;
                      return (
                        <motion.button
                          key={category.id}
                          onClick={() => setSelectedCategory(category.id)}
                          whileHover={{ scale: 1.02 }}
                          className={`w-full text-left p-3 rounded-lg transition-all ${
                            selectedCategory === category.id
                              ? "bg-[#2A5D67] text-white"
                              : "hover:bg-[#F8F5F1] text-[#1E293B]"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                              <category.icon className="w-4 h-4" />
                              <span className="text-sm">{category.name}</span>
                            </div>
                            <span className="text-xs opacity-70">{count}</span>
                          </div>
                        </motion.button>
                      );
                    })}
                  </div>
                </div>

                {/* Quick Stats */}
                <div className="bg-white rounded-xl p-6 shadow-sm border border-[#C4BDB4]/20">
                  <h3 className="font-semibold text-[#2A5D67] mb-4">
                    Statistiche
                  </h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-[#1E293B]">
                        Scadenze Totali
                      </span>
                      <span className="font-semibold text-[#2A5D67]">
                        {mockScadenze.length}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-[#1E293B]">
                        Imminenti (7gg)
                      </span>
                      <span className="font-semibold text-red-600">
                        {upcomingScadenze.length}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-[#1E293B]">Completate</span>
                      <span className="font-semibold text-green-600">
                        {mockScadenze.filter((s) => s.completed).length}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Main Content */}
            <div className="lg:col-span-3">
              <AnimatePresence mode="wait">
                {viewMode === "calendar" ? (
                  <motion.div
                    key="calendar"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="bg-white rounded-xl shadow-sm border border-[#C4BDB4]/20 p-6"
                  >
                    <div className="text-center py-20">
                      <Calendar className="w-16 h-16 text-[#C4BDB4] mx-auto mb-4" />
                      <h3 className="text-xl font-semibold text-[#2A5D67] mb-2">
                        Vista Calendario
                      </h3>
                      <p className="text-[#1E293B] mb-4">
                        Funzionalità in arrivo! Visualizza le tue scadenze in
                        formato calendario
                      </p>
                      <Button
                        onClick={() => setViewMode("list")}
                        variant="outline"
                        className="text-[#2A5D67] border-[#2A5D67] hover:bg-[#F8F5F1]"
                      >
                        Passa alla Vista Lista
                      </Button>
                    </div>
                  </motion.div>
                ) : (
                  <motion.div
                    key="list"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    className="space-y-4"
                  >
                    {filteredScadenze.map((scadenza, index) => {
                      const categoryInfo = getCategoryInfo(scadenza.category);
                      const isImminente = isUpcoming(scadenza.date);

                      return (
                        <motion.div
                          key={scadenza.id}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: index * 0.1 }}
                          className={`bg-white rounded-xl shadow-sm border transition-all hover:shadow-md ${
                            isImminente
                              ? "border-red-200 bg-red-50"
                              : "border-[#C4BDB4]/20"
                          }`}
                        >
                          <div className="p-6">
                            <div className="flex items-start justify-between mb-4">
                              <div className="flex items-start space-x-4">
                                <div
                                  className={`w-12 h-12 rounded-lg flex items-center justify-center ${categoryInfo.color}`}
                                >
                                  <categoryInfo.icon className="w-6 h-6" />
                                </div>
                                <div className="flex-1">
                                  <div className="flex items-center space-x-3 mb-2">
                                    <h3 className="text-lg font-semibold text-[#2A5D67]">
                                      {scadenza.title}
                                    </h3>
                                    {isImminente && (
                                      <motion.span
                                        animate={{ scale: [1, 1.1, 1] }}
                                        transition={{
                                          duration: 1,
                                          repeat: Infinity,
                                        }}
                                        className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full"
                                      >
                                        Imminente
                                      </motion.span>
                                    )}
                                    <span
                                      className={`px-2 py-1 text-xs font-medium rounded-full border ${getPriorityColor(scadenza.priority)}`}
                                    >
                                      {scadenza.priority === "alta"
                                        ? "Alta Priorità"
                                        : scadenza.priority === "media"
                                          ? "Media Priorità"
                                          : "Bassa Priorità"}
                                    </span>
                                  </div>
                                  <p className="text-[#1E293B] mb-3">
                                    {scadenza.description}
                                  </p>
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                                    <div className="flex items-center space-x-2">
                                      <Calendar className="w-4 h-4 text-[#C4BDB4]" />
                                      <span className="text-[#1E293B]">
                                        {formatDate(scadenza.date)}
                                      </span>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                      <Euro className="w-4 h-4 text-[#C4BDB4]" />
                                      <span className="text-[#1E293B]">
                                        {scadenza.amount}
                                      </span>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                      <Target className="w-4 h-4 text-[#C4BDB4]" />
                                      <span className="text-[#1E293B]">
                                        {scadenza.applicableTo.join(", ")}
                                      </span>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                      <AlertTriangle className="w-4 h-4 text-red-400" />
                                      <span className="text-[#1E293B]">
                                        {scadenza.penalties}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center space-x-2">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-[#C4BDB4] hover:text-[#D4A574] hover:bg-[#F8F5F1]"
                                >
                                  <Bell className="w-4 h-4" />
                                </Button>
                                {scadenza.completed ? (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="text-green-600 hover:bg-green-50"
                                  >
                                    <CheckCircle className="w-4 h-4 mr-2" />
                                    Completata
                                  </Button>
                                ) : (
                                  <Button
                                    size="sm"
                                    className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                                  >
                                    <Clock className="w-4 h-4 mr-2" />
                                    Segna come Completata
                                  </Button>
                                )}
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      );
                    })}

                    {/* Empty State */}
                    {filteredScadenze.length === 0 && (
                      <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-center py-12 bg-white rounded-xl border border-[#C4BDB4]/20"
                      >
                        <Calendar className="w-16 h-16 text-[#C4BDB4] mx-auto mb-4" />
                        <h3 className="text-xl font-semibold text-[#2A5D67] mb-2">
                          Nessuna scadenza trovata
                        </h3>
                        <p className="text-[#1E293B] mb-4">
                          Modifica i filtri di ricerca per vedere più risultati
                        </p>
                        <Button
                          onClick={() => {
                            setSearchTerm("");
                            setSelectedCategory("all");
                          }}
                          variant="outline"
                          className="text-[#2A5D67] border-[#2A5D67] hover:bg-[#F8F5F1]"
                        >
                          Resetta Filtri
                        </Button>
                      </motion.div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>

        {/* Work in Progress Overlay */}
        <div
          className="fixed inset-0 bg-white/60 backdrop-blur-[2px] z-50 flex items-center justify-center cursor-pointer"
          onClick={onBackToChat}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="bg-white/95 backdrop-blur-sm rounded-2xl shadow-2xl border border-[#C4BDB4]/30 p-10 text-center max-w-lg mx-4 cursor-default"
            onClick={(e) => e.stopPropagation()}
          >
            <motion.div
              animate={{
                rotate: [0, 10, -10, 0],
                scale: [1, 1.1, 1],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut",
              }}
              className="w-16 h-16 bg-[#2A5D67] rounded-2xl flex items-center justify-center mx-auto mb-6"
            >
              <motion.div
                animate={{
                  scale: [1, 1.2, 1],
                  rotate: [0, 5, -5, 0],
                }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  ease: "easeInOut",
                  delay: 0.5,
                }}
              >
                <Brain className="w-8 h-8 text-white" />
              </motion.div>
            </motion.div>

            <h3 className="text-2xl font-semibold text-[#2A5D67] mb-4">
              Funzionalità in Sviluppo
            </h3>

            <p className="text-[#1E293B] text-lg leading-relaxed mb-2">
              Stiamo perfezionando il sistema di gestione delle scadenze fiscali
              per offrirti la migliore esperienza possibile.
            </p>
            <p className="text-[#C4BDB4] text-sm">
              Intravedi un'anteprima di quello che ti aspetta...
            </p>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
