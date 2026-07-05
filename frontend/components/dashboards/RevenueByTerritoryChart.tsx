"use client";

import dynamic from 'next/dynamic';

// Dynamic import Recharts components to reduce initial bundle size
const BarChart = dynamic(() => import('recharts').then(mod => mod.BarChart), { ssr: false });
const Bar = dynamic(() => import('recharts').then(mod => mod.Bar), { ssr: false });
const XAxis = dynamic(() => import('recharts').then(mod => mod.XAxis), { ssr: false });
const YAxis = dynamic(() => import('recharts').then(mod => mod.YAxis), { ssr: false });
const CartesianGrid = dynamic(() => import('recharts').then(mod => mod.CartesianGrid), { ssr: false });
const Tooltip = dynamic(() => import('recharts').then(mod => mod.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(() => import('recharts').then(mod => mod.ResponsiveContainer), { ssr: false });
const Legend = dynamic(() => import('recharts').then(mod => mod.Legend), { ssr: false });

interface TerritoryData {
  territory: string;
  revenue: number;
  orders: number;
  avg_order_value: number;
}

interface RevenueByTerritoryChartProps {
  data: TerritoryData[];
  loading?: boolean;
  error?: string | null;
}

// Hoist CustomTooltip outside component to prevent recreation on every render
const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white p-4 rounded-lg shadow-lg border border-gray-200">
        <p className="font-semibold text-gray-900 mb-2">{data.territory}</p>
        <p className="text-sm text-gray-600">
          Revenue: <span className="font-medium text-blue-600">${(data.revenue / 1000000).toFixed(2)}M</span>
        </p>
        <p className="text-sm text-gray-600">
          Orders: <span className="font-medium">{data.orders.toLocaleString()}</span>
        </p>
        <p className="text-sm text-gray-600">
          Avg Order: <span className="font-medium">${(data.avg_order_value / 1000).toFixed(1)}K</span>
        </p>
      </div>
    );
  }
  return null;
};

// Hoist formatYAxis outside component
const formatYAxis = (value: number) => {
  return `$${(value / 1000000).toFixed(0)}M`;
};

export default function RevenueByTerritoryChart({
  data,
  loading = false,
  error = null
}: RevenueByTerritoryChartProps) {
  if (loading) {
    return (
      <div className="h-[400px] bg-gray-100 rounded-lg flex items-center justify-center animate-pulse">
        <p className="text-gray-400">Loading chart...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-[400px] bg-red-50 rounded-lg flex items-center justify-center border border-red-200">
        <p className="text-red-600">⚠️ {error}</p>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="h-[400px] bg-gray-50 rounded-lg flex items-center justify-center">
        <p className="text-gray-500">No data available</p>
      </div>
    );
  }

  return (
    <div className="h-[400px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="territory"
            angle={-45}
            textAnchor="end"
            height={80}
            tick={{ fontSize: 12 }}
            stroke="#6b7280"
          />
          <YAxis
            tickFormatter={formatYAxis}
            tick={{ fontSize: 12 }}
            stroke="#6b7280"
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ paddingTop: "20px" }}
            iconType="circle"
          />
          <Bar
            dataKey="revenue"
            fill="#3b82f6"
            name="Revenue ($)"
            radius={[8, 8, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
