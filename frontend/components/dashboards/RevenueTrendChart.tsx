"use client";

import dynamic from 'next/dynamic';

// Dynamic import Recharts components to reduce initial bundle size
const LineChart = dynamic(() => import('recharts').then(mod => mod.LineChart), { ssr: false });
const Line = dynamic(() => import('recharts').then(mod => mod.Line), { ssr: false });
const XAxis = dynamic(() => import('recharts').then(mod => mod.XAxis), { ssr: false });
const YAxis = dynamic(() => import('recharts').then(mod => mod.YAxis), { ssr: false });
const CartesianGrid = dynamic(() => import('recharts').then(mod => mod.CartesianGrid), { ssr: false });
const Tooltip = dynamic(() => import('recharts').then(mod => mod.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(() => import('recharts').then(mod => mod.ResponsiveContainer), { ssr: false });
const Legend = dynamic(() => import('recharts').then(mod => mod.Legend), { ssr: false });

interface TrendData {
  date: string;  // Backend returns 'date' not 'period'
  revenue: number;
  orders: number;
}

interface RevenueTrendChartProps {
  data: TrendData[];
  loading?: boolean;
  error?: string | null;
  granularity?: "day" | "week" | "month" | "quarter";
}

// Hoist formatYAxis outside component
const formatYAxis = (value: number) => {
  return `$${(value / 1000000).toFixed(0)}M`;
};

// Hoist formatXAxis outside component
const formatXAxis = (dateStr: string, granularity: string = 'month') => {
  const date = new Date(dateStr);
  if (granularity === 'day') {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } else if (granularity === 'month') {
    return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
  } else if (granularity === 'quarter') {
    const quarter = Math.floor(date.getMonth() / 3) + 1;
    return `Q${quarter} ${date.getFullYear().toString().slice(-2)}`;
  }
  return date.toLocaleDateString('en-US', { month: 'short' });
};

// Hoist CustomTooltip outside component
const CustomTooltip = ({ active, payload, granularity }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const date = new Date(data.date);  // Use 'date' field from backend
    const formattedDate = date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      ...(granularity === 'day' && { day: 'numeric' })
    });

    return (
      <div className="bg-white p-4 rounded-lg shadow-lg border border-gray-200">
        <p className="font-semibold text-gray-900 mb-2">{formattedDate}</p>
        <p className="text-sm text-gray-600">
          Revenue: <span className="font-medium text-blue-600">${(data.revenue / 1000000).toFixed(2)}M</span>
        </p>
        <p className="text-sm text-gray-600">
          Orders: <span className="font-medium">{data.orders.toLocaleString()}</span>
        </p>
      </div>
    );
  }
  return null;
};

export default function RevenueTrendChart({
  data,
  loading = false,
  error = null,
  granularity = "month"
}: RevenueTrendChartProps) {
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
        <LineChart
          data={data}
          margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            tickFormatter={(value) => formatXAxis(value, granularity)}
            tick={{ fontSize: 12 }}
            stroke="#6b7280"
          />
          <YAxis
            tickFormatter={formatYAxis}
            tick={{ fontSize: 12 }}
            stroke="#6b7280"
          />
          <Tooltip content={(props) => <CustomTooltip {...props} granularity={granularity} />} />
          <Legend
            wrapperStyle={{ paddingTop: "20px" }}
            iconType="circle"
          />
          <Line
            type="monotone"
            dataKey="revenue"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ fill: "#3b82f6", r: 4 }}
            activeDot={{ r: 6 }}
            name="Revenue ($)"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
