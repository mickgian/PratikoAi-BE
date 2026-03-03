'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useState } from 'react';
import {
  ArrowLeft,
  Euro,
  FileCheck,
  Loader2,
  RefreshCw,
  Target,
  TrendingUp,
} from 'lucide-react';
import { motion } from 'motion/react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { useDashboard } from '@/lib/hooks/useDashboard';
import {
  monthlyValueData,
  activityTimeline,
  upcomingDeadlines,
} from '../data/mock-data';
import { KPIData, MatchingStats, Period } from '../types';
import { formatCurrency } from '../utils/formatters';
import { DashboardActivityTimeline } from './DashboardActivityTimeline';
import { DashboardDeadlines } from './DashboardDeadlines';
import { DashboardKPICards } from './DashboardKPICards';

const DashboardROIChart = dynamic(
  () =>
    import('./DashboardROIChart').then(mod => ({
      default: mod.DashboardROIChart,
    })),
  { ssr: false }
);

const DashboardDistributionCharts = dynamic(
  () =>
    import('./DashboardDistributionCharts').then(mod => ({
      default: mod.DashboardDistributionCharts,
    })),
  { ssr: false }
);

const hourlyRate = 75;

export function DashboardView() {
  const [selectedPeriod, setSelectedPeriod] = useState<Period>('month');
  const { data, isLoading, error, refresh } = useDashboard(selectedPeriod);

  // Derive KPI and matching stats from API data, fall back to zeros
  const kpiData: KPIData = data
    ? {
        clientiAttivi: data.clients.total,
        oreRisparmiate: data.roi.hours_saved,
        comunicazioniInviate: data.communications.total,
        normativeMonitorate: data.matches.active_rules,
      }
    : {
        clientiAttivi: 0,
        oreRisparmiate: 0,
        comunicazioniInviate: 0,
        normativeMonitorate: 0,
      };

  const matchingStats: MatchingStats = data
    ? {
        totalMatches: data.matching.total_matches,
        conversionRate: data.matching.conversion_rate,
        pendingReviews: data.matching.pending_reviews,
      }
    : { totalMatches: 0, conversionRate: 0, pendingReviews: 0 };

  const totalSavings = kpiData.oreRisparmiate * hourlyRate;
  const monthlyGrowth = 12.5; // Static for now until backend provides growth metrics

  // Distribution data from API or empty arrays
  const regimeFiscaleData = data
    ? data.distributions.by_regime.map((d, i) => ({
        name: d.regime,
        value: d.count,
        color: ['#2A5D67', '#D4A574', '#1E293B', '#94A3B8'][i % 4],
      }))
    : [];
  const atecoSectorData = data
    ? data.distributions.by_ateco.map(d => ({
        sector: d.ateco,
        count: d.count,
      }))
    : [];
  const clientStatusData = data
    ? data.distributions.by_status.map((d, i) => ({
        name: d.status,
        value: d.count,
        color: ['#10B981', '#F59E0B', '#EF4444'][i % 3],
      }))
    : [];

  if (error) {
    return (
      <div className="min-h-screen bg-[#F8F5F1] flex items-center justify-center">
        <Card className="border-[#C4BDB4]/20 max-w-md w-full">
          <CardContent className="pt-6 text-center">
            <p className="text-red-600 mb-4">{error}</p>
            <Button onClick={refresh} className="bg-[#2A5D67]">
              <RefreshCw className="w-4 h-4 mr-2" />
              Riprova
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      {/* Header */}
      <div className="bg-white border-b border-[#C4BDB4]/20 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <Link href="/chat">
            <Button
              variant="ghost"
              className="text-[#2A5D67] hover:bg-[#F8F5F1] mb-3 -ml-2"
            >
              <ArrowLeft className="w-5 h-5 mr-2" />
              Indietro
            </Button>
          </Link>
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
              {(['week', 'month', 'year'] as Period[]).map(period => (
                <Button
                  key={period}
                  variant={selectedPeriod === period ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedPeriod(period)}
                  className={selectedPeriod === period ? 'bg-[#2A5D67]' : ''}
                >
                  {period === 'week'
                    ? 'Settimana'
                    : period === 'month'
                      ? 'Mese'
                      : 'Anno'}
                </Button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-[#2A5D67]" />
            <span className="ml-3 text-[#1E293B]">Caricamento dati...</span>
          </div>
        ) : (
          <>
            <DashboardKPICards kpiData={kpiData} />

            {/* ROI + Matching Stats Row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
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
                    <DashboardROIChart data={monthlyValueData} />
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
                        <span className="text-sm text-[#1E293B]">
                          Match Totali
                        </span>
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
                          style={{
                            width: `${matchingStats.conversionRate}%`,
                          }}
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

            {/* Activity + Deadlines Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
              >
                <DashboardActivityTimeline activities={activityTimeline} />
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 }}
              >
                <DashboardDeadlines deadlines={upcomingDeadlines} />
              </motion.div>
            </div>

            {/* Distribution Charts */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
            >
              <DashboardDistributionCharts
                regimeFiscaleData={regimeFiscaleData}
                atecoSectorData={atecoSectorData}
                clientStatusData={clientStatusData}
              />
            </motion.div>
          </>
        )}
      </div>
    </div>
  );
}
