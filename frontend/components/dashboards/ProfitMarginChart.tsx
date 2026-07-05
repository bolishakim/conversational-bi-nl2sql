"use client";

import dynamic from 'next/dynamic';
import { Cell } from 'recharts';  // Static import - Cell must be static for colors to work

// Dynamic imports for Recharts
const BarChart = dynamic(() => import('recharts').then(mod => mod.BarChart), { ssr: false });
const Bar = dynamic(() => import('recharts').then(mod => mod.Bar), { ssr: false });
const XAxis = dynamic(() => import('recharts').then(mod => mod.XAxis), { ssr: false });
const YAxis = dynamic(() => import('recharts').then(mod => mod.YAxis), { ssr: false });
const CartesianGrid = dynamic(() => import('recharts').then(mod => mod.CartesianGrid), { ssr: false });
const Tooltip = dynamic(() => import('recharts').then(mod => mod.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(() => import('recharts').then(mod => mod.ResponsiveContainer), { ssr: false });
const ReferenceLine = dynamic(() => import('recharts').then(mod => mod.ReferenceLine), { ssr: false });

interface ProfitMarginData {
  category: string;
  avg_margin: number;
  min_margin: number;
  max_margin: number;
  product_count: number;
}

interface ProfitMarginChartProps {
  data: ProfitMarginData[];
  loading?: boolean;
  error?: string | null;
}

// Hoisted outside component
const COLORS = {
  high: "#10B981",
  medium: "#F59E0B",
  low: "#EF4444",
};

const getBarColor = (margin: number): string => {
  if (margin >= 50) return COLORS.high;
  if (margin >= 30) return COLORS.medium;
  return COLORS.low;
};

const formatPercent = (value: number): string => `${value.toFixed(1)}%`;

export default function ProfitMarginChart({
  data,
  loading = false,
  error = null
}: ProfitMarginChartProps) {
  if (loading) {
    return (
      <div className="h-80 flex items-center justify-center">
        <div className="animate-pulse text-gray-400">Loading chart...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-80 flex items-center justify-center">
        <div className="text-red-500 text-sm">{error}</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="h-80 flex items-center justify-center">
        <div className="text-gray-500 text-sm">No data available</div>
      </div>
    );
  }

  return (
    <div>
      {/* Chart */}
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" margin={{ top: 5, right: 20, left: 100, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis type="number" domain={[0, 100]} tickFormatter={formatPercent} tick={{ fontSize: 12, fill: "#6B7280" }} />
          <YAxis type="category" dataKey="category" tick={{ fontSize: 11, fill: "#374151" }} width={95} />
          <Tooltip
            formatter={(value, name) => name === "avg_margin" ? [formatPercent(value as number), "Avg Margin"] : [formatPercent(value as number), name]}
            labelFormatter={(label) => `Category: ${label}`}
            contentStyle={{ backgroundColor: "#fff", border: "1px solid #E5E7EB", borderRadius: "8px", fontSize: "12px" }}
          />
          <ReferenceLine x={60} stroke="#10B981" strokeDasharray="5 5" label={{ value: "60%", position: "top", fill: "#10B981", fontSize: 10 }} />
          <ReferenceLine x={30} stroke="#F59E0B" strokeDasharray="5 5" label={{ value: "30%", position: "top", fill: "#F59E0B", fontSize: 10 }} />
          <Bar dataKey="avg_margin" name="Avg Margin" radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(entry.avg_margin)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Legend & Stats */}
      <div className="mt-4 grid grid-cols-3 gap-4 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: COLORS.high }} />
          <span className="text-gray-600">High Margin ({">"} 50%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: COLORS.medium }} />
          <span className="text-gray-600">Medium (30-50%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: COLORS.low }} />
          <span className="text-gray-600">Low Margin ({"<"} 30%)</span>
        </div>
      </div>

      {/* Category Details */}
      <div className="mt-4 border-t border-gray-100 pt-4">
        <div className="grid grid-cols-4 gap-2 text-xs font-medium text-gray-500 mb-2">
          <div>Category</div>
          <div className="text-right">Min</div>
          <div className="text-right">Avg</div>
          <div className="text-right">Max</div>
        </div>
        {data.map((item) => (
          <div key={item.category} className="grid grid-cols-4 gap-2 text-xs text-gray-700 py-1 border-b border-gray-50">
            <div className="font-medium">{item.category}</div>
            <div className="text-right">{item.min_margin.toFixed(1)}%</div>
            <div className="text-right font-semibold">{item.avg_margin.toFixed(1)}%</div>
            <div className="text-right">{item.max_margin.toFixed(1)}%</div>
          </div>
        ))}
      </div>
    </div>
  );
}
