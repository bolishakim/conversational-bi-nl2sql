"use client";

import dynamic from 'next/dynamic';
import { Cell } from 'recharts';  // Static import - Cell must be static for colors to work

// Dynamic import Recharts components to reduce initial bundle size
const PieChart = dynamic(() => import('recharts').then(mod => mod.PieChart), { ssr: false });
const Pie = dynamic(() => import('recharts').then(mod => mod.Pie), { ssr: false });
const ResponsiveContainer = dynamic(() => import('recharts').then(mod => mod.ResponsiveContainer), { ssr: false });
const Tooltip = dynamic(() => import('recharts').then(mod => mod.Tooltip), { ssr: false });
const Legend = dynamic(() => import('recharts').then(mod => mod.Legend), { ssr: false });

interface CategoryData {
  category: string;
  revenue: number;
  percentage: number;
  orders?: number;
  units_sold?: number;
  [key: string]: string | number | undefined; // Index signature for Recharts compatibility
}

interface CategoryBreakdownChartProps {
  data: CategoryData[];
  loading?: boolean;
  error?: string | null;
}

// Color palette for categories - hoisted outside component
const COLORS = [
  "#3b82f6", // blue
  "#10b981", // green
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#14b8a6", // teal
  "#f97316", // orange
];

// Hoist CustomTooltip outside component
const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white p-4 rounded-lg shadow-lg border border-gray-200">
        <p className="font-semibold text-gray-900 mb-2">{data.category}</p>
        <p className="text-sm text-gray-600">
          Revenue: <span className="font-medium text-blue-600">${(data.revenue / 1000000).toFixed(2)}M</span>
        </p>
        <p className="text-sm text-gray-600">
          Percentage: <span className="font-medium">{data.percentage.toFixed(1)}%</span>
        </p>
        {data.orders && (
          <p className="text-sm text-gray-600">
            Orders: <span className="font-medium">{data.orders.toLocaleString()}</span>
          </p>
        )}
        {data.units_sold && (
          <p className="text-sm text-gray-600">
            Units Sold: <span className="font-medium">{data.units_sold.toLocaleString()}</span>
          </p>
        )}
      </div>
    );
  }
  return null;
};

// Hoist custom label function outside component
const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percentage }: any) => {
  if (percentage < 5) return null; // Don't show label for small slices

  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central"
      fontSize={12}
      fontWeight="bold"
    >
      {`${percentage.toFixed(0)}%`}
    </text>
  );
};

export default function CategoryBreakdownChart({
  data,
  loading = false,
  error = null
}: CategoryBreakdownChartProps) {
  if (loading) {
    return (
      <div className="h-[280px] bg-gray-100 rounded-lg flex items-center justify-center animate-pulse">
        <p className="text-gray-400">Loading chart...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-[280px] bg-red-50 rounded-lg flex items-center justify-center border border-red-200">
        <p className="text-red-600">⚠️ {error}</p>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="h-[280px] bg-gray-50 rounded-lg flex items-center justify-center">
        <p className="text-gray-500">No data available</p>
      </div>
    );
  }

  return (
    <div className="h-[280px]">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomLabel}
            outerRadius={90}
            fill="#8884d8"
            dataKey="revenue"
            nameKey="category"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            verticalAlign="bottom"
            height={36}
            iconType="circle"
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
