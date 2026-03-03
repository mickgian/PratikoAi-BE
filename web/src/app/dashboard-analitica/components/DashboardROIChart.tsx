'use client';

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { MonthlyValueData } from '../types';
import { formatCurrency } from '../utils/formatters';

interface DashboardROIChartProps {
  data: MonthlyValueData[];
}

export function DashboardROIChart({ data }: DashboardROIChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="colorValore" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#2A5D67" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#2A5D67" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="colorManuale" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#D4A574" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#D4A574" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#C4BDB4" opacity={0.3} />
        <XAxis dataKey="month" stroke="#1E293B" style={{ fontSize: '12px' }} />
        <YAxis
          stroke="#1E293B"
          style={{ fontSize: '12px' }}
          tickFormatter={(value: number) => `€${value}`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #C4BDB4',
            borderRadius: '8px',
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
  );
}
