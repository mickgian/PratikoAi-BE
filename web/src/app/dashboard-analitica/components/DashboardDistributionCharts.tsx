'use client';

import { BarChart3, Building2, PieChart } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart as RechartsPie,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChartData, PieChartData } from '../types';

interface DashboardDistributionChartsProps {
  regimeFiscaleData: PieChartData[];
  atecoSectorData: BarChartData[];
  clientStatusData: PieChartData[];
}

export function DashboardDistributionCharts({
  regimeFiscaleData,
  atecoSectorData,
  clientStatusData,
}: DashboardDistributionChartsProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Regime Fiscale - Pie Chart */}
      <Card className="border-[#C4BDB4]/20">
        <CardHeader>
          <CardTitle className="text-lg text-[#2A5D67] flex items-center">
            <PieChart className="w-5 h-5 mr-2" />
            Per Regime Fiscale
          </CardTitle>
        </CardHeader>
        <CardContent>
          {regimeFiscaleData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <RechartsPie>
                <Pie
                  data={regimeFiscaleData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({
                    name,
                    percent,
                  }: {
                    name?: string;
                    percent?: number;
                  }) => `${name ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {regimeFiscaleData.map((entry, index) => (
                    <Cell key={`cell-regime-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </RechartsPie>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-[#94A3B8] text-center py-12">
              Nessun dato disponibile
            </p>
          )}
        </CardContent>
      </Card>

      {/* ATECO Sector - Bar Chart */}
      <Card className="border-[#C4BDB4]/20">
        <CardHeader>
          <CardTitle className="text-lg text-[#2A5D67] flex items-center">
            <BarChart3 className="w-5 h-5 mr-2" />
            Per Settore ATECO
          </CardTitle>
        </CardHeader>
        <CardContent>
          {atecoSectorData.length > 0 ? (
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
                  style={{ fontSize: '11px' }}
                  angle={-15}
                  textAnchor="end"
                  height={60}
                />
                <YAxis stroke="#1E293B" style={{ fontSize: '12px' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #C4BDB4',
                    borderRadius: '8px',
                  }}
                />
                <Bar dataKey="count" fill="#2A5D67" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-[#94A3B8] text-center py-12">
              Nessun dato disponibile
            </p>
          )}
        </CardContent>
      </Card>

      {/* Client Status - Donut Chart */}
      <Card className="border-[#C4BDB4]/20">
        <CardHeader>
          <CardTitle className="text-lg text-[#2A5D67] flex items-center">
            <Building2 className="w-5 h-5 mr-2" />
            Per Stato Cliente
          </CardTitle>
        </CardHeader>
        <CardContent>
          {clientStatusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <RechartsPie>
                <Pie
                  data={clientStatusData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({
                    name,
                    percent,
                  }: {
                    name?: string;
                    percent?: number;
                  }) => `${name ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
                  innerRadius={60}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {clientStatusData.map((entry, index) => (
                    <Cell key={`cell-status-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </RechartsPie>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-[#94A3B8] text-center py-12">
              Nessun dato disponibile
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
