import React, { useState } from "react";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Users,
  Clock,
  Mail,
  FileText,
  TrendingUp,
  TrendingDown,
  CheckCircle,
  AlertTriangle,
  Calendar,
  Target,
  Euro,
  Activity,
  Bell,
  FileCheck,
  Building2,
  Briefcase,
  PieChart,
  BarChart3,
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
import {
  PieChart as RechartsPie,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  Area,
  AreaChart,
} from "recharts";

interface DashboardPageProps {
  onBackToChat: () => void;
}

// Mock data for charts
const monthlyValueData = [
  { month: "Gen", valore: 4200, manuale: 8500 },
  { month: "Feb", valore: 4800, manuale: 8700 },
  { month: "Mar", valore: 5200, manuale: 9200 },
  { month: "Apr", valore: 5800, manuale: 9800 },
  { month: "Mag", valore: 6200, manuale: 10200 },
  { month: "Giu", valore: 6800, manuale: 10800 },
];

const regimeFiscaleData = [
  { name: "Forfettario", value: 42, color: "#2A5D67" },
  { name: "Semplificato", value: 28, color: "#D4A574" },
  { name: "Ordinario", value: 18, color: "#1E293B" },
  { name: "Altro", value: 12, color: "#94A3B8" },
];

const atecoSectorData = [
  { sector: "Servizi Prof.", count: 35 },
  { sector: "Commercio", count: 28 },
  { sector: "Manifattura", count: 18 },
  { sector: "Edilizia", count: 15 },
  { sector: "Altro", count: 12 },
];

const clientStatusData = [
  { name: "Attivi", value: 82, color: "#10B981" },
  { name: "In attesa", value: 14, color: "#F59E0B" },
  { name: "Inattivi", value: 4, color: "#EF4444" },
];

const activityTimeline = [
  {
    id: "act_001",
    type: "match",
    title: "Nuovo match normativo",
    description: "D.L. 142/2024 - Bonus Investimenti Sud → 3 clienti",
    timestamp: "2024-02-25T10:30:00",
    icon: Target,
    color: "text-blue-600 bg-blue-50",
  },
  {
    id: "act_002",
    type: "communication",
    title: "Comunicazione inviata",
    description: "Aggiornamento IVA 2024 → Studio Legale Rossi",
    timestamp: "2024-02-25T09:15:00",
    icon: Mail,
    color: "text-green-600 bg-green-50",
  },
  {
    id: "act_003",
    type: "procedura",
    title: "Procedura completata",
    description: "Apertura P.IVA → Commercialista Ferrari",
    timestamp: "2024-02-25T08:45:00",
    icon: CheckCircle,
    color: "text-purple-600 bg-purple-50",
  },
  {
    id: "act_004",
    type: "deadline",
    title: "Alert scadenza",
    description: "Dichiarazione IVA trimestrale - 5 clienti",
    timestamp: "2024-02-25T08:00:00",
    icon: AlertTriangle,
    color: "text-orange-600 bg-orange-50",
  },
  {
    id: "act_005",
    type: "match",
    title: "Nuovo match normativo",
    description: "Circolare INPS 23/2024 → 7 clienti",
    timestamp: "2024-02-24T16:20:00",
    icon: Target,
    color: "text-blue-600 bg-blue-50",
  },
  {
    id: "act_006",
    type: "communication",
    title: "Comunicazione inviata",
    description: "Scadenza contributi → Immobiliare Milano",
    timestamp: "2024-02-24T15:00:00",
    icon: Mail,
    color: "text-green-600 bg-green-50",
  },
];

const upcomingDeadlines = [
  {
    id: "dead_001",
    title: "Versamento IVA mensile",
    date: "2024-02-27",
    clientCount: 12,
    priority: "high",
  },
  {
    id: "dead_002",
    title: "Presentazione F24",
    date: "2024-02-28",
    clientCount: 8,
    priority: "high",
  },
  {
    id: "dead_003",
    title: "Dichiarazione INTRASTAT",
    date: "2024-03-01",
    clientCount: 5,
    priority: "medium",
  },
  {
    id: "dead_004",
    title: "Invio CU dipendenti",
    date: "2024-03-02",
    clientCount: 15,
    priority: "medium",
  },
];

export function DashboardPage({ onBackToChat }: DashboardPageProps) {
  const [selectedPeriod, setSelectedPeriod] = useState<
    "week" | "month" | "year"
  >("month");

  // KPI values
  const kpiData = {
    clientiAttivi: 82,
    oreRisparmiate: 156.5,
    comunicazioniInviate: 247,
    normativeMonitorate: 1842,
  };

  // ROI calculations
  const hourlyRate = 75; // €/hour
  const totalSavings = kpiData.oreRisparmiate * hourlyRate;
  const monthlyGrowth = 12.5; // %

  // Matching stats
  const matchingStats = {
    totalMatches: 342,
    conversionRate: 73.2,
    pendingReviews: 18,
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("it-IT", {
      style: "currency",
      currency: "EUR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatRelativeTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins} min fa`;
    if (diffHours < 24) return `${diffHours}h fa`;
    return `${diffDays}g fa`;
  };

  const getDaysUntil = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffDays = Math.ceil(diffMs / 86400000);
    return diffDays;
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "high":
        return "bg-red-100 text-red-700 border-red-300";
      case "medium":
        return "bg-yellow-100 text-yellow-700 border-yellow-300";
      case "low":
        return "bg-green-100 text-green-700 border-green-300";
      default:
        return "bg-gray-100 text-gray-700 border-gray-300";
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      {/* Header */}
      <div className="bg-white border-b border-[#C4BDB4]/20 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <Button
            variant="ghost"
            onClick={onBackToChat}
            className="text-[#2A5D67] hover:bg-[#F8F5F1] mb-3 -ml-2"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Indietro
          </Button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-[#2A5D67] mb-1">
                Dashboard Analitica
              </h1>
              <p className="text-sm text-[#1E293B]">
                Panoramica completa delle tue attività e performance
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant={selectedPeriod === "week" ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedPeriod("week")}
                className={selectedPeriod === "week" ? "bg-[#2A5D67]" : ""}
              >
                Settimana
              </Button>
              <Button
                variant={selectedPeriod === "month" ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedPeriod("month")}
                className={selectedPeriod === "month" ? "bg-[#2A5D67]" : ""}
              >
                Mese
              </Button>
              <Button
                variant={selectedPeriod === "year" ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedPeriod("year")}
                className={selectedPeriod === "year" ? "bg-[#2A5D67]" : ""}
              >
                Anno
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0 }}
          >
            <Card className="border-[#C4BDB4]/20 hover:shadow-lg transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-[#1E293B]">
                    Clienti Attivi
                  </CardTitle>
                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                    <Users className="w-5 h-5 text-blue-600" />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-[#2A5D67] mb-1">
                  {kpiData.clientiAttivi}
                </div>
                <div className="flex items-center text-sm">
                  <TrendingUp className="w-4 h-4 text-green-600 mr-1" />
                  <span className="text-green-600 font-medium">+8.2%</span>
                  <span className="text-[#1E293B] ml-1">vs mese scorso</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card className="border-[#C4BDB4]/20 hover:shadow-lg transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-[#1E293B]">
                    Ore Risparmiate
                  </CardTitle>
                  <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
                    <Clock className="w-5 h-5 text-purple-600" />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-[#2A5D67] mb-1">
                  {kpiData.oreRisparmiate.toFixed(1)}
                </div>
                <div className="flex items-center text-sm">
                  <TrendingUp className="w-4 h-4 text-green-600 mr-1" />
                  <span className="text-green-600 font-medium">+15.3%</span>
                  <span className="text-[#1E293B] ml-1">vs mese scorso</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="border-[#C4BDB4]/20 hover:shadow-lg transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-[#1E293B]">
                    Comunicazioni Inviate
                  </CardTitle>
                  <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                    <Mail className="w-5 h-5 text-green-600" />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-[#2A5D67] mb-1">
                  {kpiData.comunicazioniInviate}
                </div>
                <div className="flex items-center text-sm">
                  <TrendingUp className="w-4 h-4 text-green-600 mr-1" />
                  <span className="text-green-600 font-medium">+22.7%</span>
                  <span className="text-[#1E293B] ml-1">vs mese scorso</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="border-[#C4BDB4]/20 hover:shadow-lg transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-[#1E293B]">
                    Normative Monitorate
                  </CardTitle>
                  <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center">
                    <FileText className="w-5 h-5 text-orange-600" />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-[#2A5D67] mb-1">
                  {kpiData.normativeMonitorate.toLocaleString("it-IT")}
                </div>
                <div className="flex items-center text-sm">
                  <Activity className="w-4 h-4 text-[#2A5D67] mr-1" />
                  <span className="text-[#1E293B]">
                    Aggiornate in tempo reale
                  </span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* ROI Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="lg:col-span-2"
          >
            <Card className="border-[#C4BDB4]/20">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-xl text-[#2A5D67] flex items-center">
                      <Euro className="w-5 h-5 mr-2" />
                      Valore Generato
                    </CardTitle>
                    <CardDescription className="mt-1">
                      Confronto risparmio vs lavoro manuale
                    </CardDescription>
                  </div>
                  <Badge className="bg-green-100 text-green-700 border-green-300 border">
                    <TrendingUp className="w-3 h-3 mr-1" />+{monthlyGrowth}%
                    questo mese
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                {/* Savings Summary */}
                <div className="bg-[#F8F5F1] rounded-lg p-4 mb-6">
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-[#1E293B] mb-1">
                        Ore Risparmiate
                      </p>
                      <p className="text-2xl font-bold text-[#2A5D67]">
                        {kpiData.oreRisparmiate}h
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-[#1E293B] mb-1">
                        Tariffa Oraria
                      </p>
                      <p className="text-2xl font-bold text-[#2A5D67]">
                        €{hourlyRate}/h
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-[#1E293B] mb-1">
                        Valore Totale
                      </p>
                      <p className="text-2xl font-bold text-green-600">
                        {formatCurrency(totalSavings)}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Chart */}
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={monthlyValueData}>
                    <defs>
                      <linearGradient
                        id="colorValore"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="5%"
                          stopColor="#2A5D67"
                          stopOpacity={0.3}
                        />
                        <stop
                          offset="95%"
                          stopColor="#2A5D67"
                          stopOpacity={0}
                        />
                      </linearGradient>
                      <linearGradient
                        id="colorManuale"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="5%"
                          stopColor="#D4A574"
                          stopOpacity={0.3}
                        />
                        <stop
                          offset="95%"
                          stopColor="#D4A574"
                          stopOpacity={0}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#C4BDB4"
                      opacity={0.3}
                    />
                    <XAxis
                      dataKey="month"
                      stroke="#1E293B"
                      style={{ fontSize: "12px" }}
                    />
                    <YAxis
                      stroke="#1E293B"
                      style={{ fontSize: "12px" }}
                      tickFormatter={(value) => `€${value}`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "white",
                        border: "1px solid #C4BDB4",
                        borderRadius: "8px",
                      }}
                      formatter={(value: number) => formatCurrency(value)}
                    />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="valore"
                      name="Con PratikoAI"
                      stroke="#2A5D67"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#colorValore)"
                    />
                    <Area
                      type="monotone"
                      dataKey="manuale"
                      name="Lavoro manuale"
                      stroke="#D4A574"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#colorManuale)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>

          {/* Matching Stats */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <Card className="border-[#C4BDB4]/20">
              <CardHeader>
                <CardTitle className="text-xl text-[#2A5D67] flex items-center">
                  <Target className="w-5 h-5 mr-2" />
                  Statistiche Matching
                </CardTitle>
                <CardDescription>Performance sistema AI</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-[#1E293B]">Match Totali</span>
                    <span className="text-2xl font-bold text-[#2A5D67]">
                      {matchingStats.totalMatches}
                    </span>
                  </div>
                  <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div className="h-full bg-[#2A5D67] w-full" />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-[#1E293B]">
                      Tasso Conversione
                    </span>
                    <span className="text-2xl font-bold text-green-600">
                      {matchingStats.conversionRate}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-500"
                      style={{ width: `${matchingStats.conversionRate}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-[#1E293B]">
                      In attesa di revisione
                    </span>
                    <span className="text-2xl font-bold text-orange-600">
                      {matchingStats.pendingReviews}
                    </span>
                  </div>
                  <Button
                    className="w-full bg-[#2A5D67] hover:bg-[#1E293B] text-white mt-2"
                    size="sm"
                  >
                    <FileCheck className="w-4 h-4 mr-2" />
                    Rivedi match
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Activity Timeline */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
          >
            <Card className="border-[#C4BDB4]/20">
              <CardHeader>
                <CardTitle className="text-xl text-[#2A5D67] flex items-center">
                  <Activity className="w-5 h-5 mr-2" />
                  Attività Recenti
                </CardTitle>
                <CardDescription>Timeline delle ultime azioni</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {activityTimeline.map((activity, index) => {
                    const IconComponent = activity.icon;
                    return (
                      <motion.div
                        key={activity.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.6 + index * 0.05 }}
                        className="flex items-start space-x-3 pb-4 border-b border-[#C4BDB4]/20 last:border-0"
                      >
                        <div
                          className={`w-10 h-10 rounded-lg ${activity.color} flex items-center justify-center flex-shrink-0`}
                        >
                          <IconComponent className="w-5 h-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-[#2A5D67] text-sm">
                            {activity.title}
                          </p>
                          <p className="text-sm text-[#1E293B] mt-1">
                            {activity.description}
                          </p>
                          <p className="text-xs text-[#94A3B8] mt-1">
                            {formatRelativeTime(activity.timestamp)}
                          </p>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Upcoming Deadlines */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
          >
            <Card className="border-[#C4BDB4]/20">
              <CardHeader>
                <CardTitle className="text-xl text-[#2A5D67] flex items-center">
                  <Calendar className="w-5 h-5 mr-2" />
                  Scadenze Imminenti
                </CardTitle>
                <CardDescription>Prossimi 7 giorni</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {upcomingDeadlines.map((deadline, index) => {
                    const daysUntil = getDaysUntil(deadline.date);
                    return (
                      <motion.div
                        key={deadline.id}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.7 + index * 0.05 }}
                        className="bg-white border border-[#C4BDB4]/20 rounded-lg p-4 hover:shadow-md transition-shadow"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <h4 className="font-semibold text-[#2A5D67] text-sm">
                            {deadline.title}
                          </h4>
                          <Badge
                            className={`${getPriorityColor(deadline.priority)} border text-xs`}
                          >
                            {deadline.priority === "high"
                              ? "Urgente"
                              : "Normale"}
                          </Badge>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <div className="flex items-center text-[#1E293B]">
                            <Calendar className="w-4 h-4 mr-1" />
                            {new Date(deadline.date).toLocaleDateString(
                              "it-IT",
                              {
                                day: "numeric",
                                month: "short",
                              },
                            )}
                            <span className="mx-2">•</span>
                            <span className="text-[#94A3B8]">
                              {daysUntil === 0
                                ? "Oggi"
                                : daysUntil === 1
                                  ? "Domani"
                                  : `Tra ${daysUntil} giorni`}
                            </span>
                          </div>
                          <div className="flex items-center text-[#2A5D67]">
                            <Users className="w-4 h-4 mr-1" />
                            {deadline.clientCount}
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Client Distribution Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Regime Fiscale - Pie Chart */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
          >
            <Card className="border-[#C4BDB4]/20">
              <CardHeader>
                <CardTitle className="text-lg text-[#2A5D67] flex items-center">
                  <PieChart className="w-5 h-5 mr-2" />
                  Per Regime Fiscale
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <RechartsPie>
                    <Pie
                      data={regimeFiscaleData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) =>
                        `${name} ${(percent * 100).toFixed(0)}%`
                      }
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {regimeFiscaleData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </RechartsPie>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>

          {/* ATECO Sector - Bar Chart */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.9 }}
          >
            <Card className="border-[#C4BDB4]/20">
              <CardHeader>
                <CardTitle className="text-lg text-[#2A5D67] flex items-center">
                  <BarChart3 className="w-5 h-5 mr-2" />
                  Per Settore ATECO
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={atecoSectorData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#C4BDB4"
                      opacity={0.3}
                    />
                    <XAxis
                      dataKey="sector"
                      stroke="#1E293B"
                      style={{ fontSize: "11px" }}
                      angle={-15}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis stroke="#1E293B" style={{ fontSize: "12px" }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "white",
                        border: "1px solid #C4BDB4",
                        borderRadius: "8px",
                      }}
                    />
                    <Bar dataKey="count" fill="#2A5D67" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>

          {/* Client Status - Donut Chart */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.0 }}
          >
            <Card className="border-[#C4BDB4]/20">
              <CardHeader>
                <CardTitle className="text-lg text-[#2A5D67] flex items-center">
                  <Building2 className="w-5 h-5 mr-2" />
                  Per Stato Cliente
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <RechartsPie>
                    <Pie
                      data={clientStatusData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) =>
                        `${name} ${(percent * 100).toFixed(0)}%`
                      }
                      innerRadius={60}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {clientStatusData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </RechartsPie>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
