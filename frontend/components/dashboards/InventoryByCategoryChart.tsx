"use client";

import { useState } from "react";
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

interface InventoryCategory {
  category: string;
  total_quantity: number;
  inventory_value: number;
  product_count: number;
}

interface InventoryByCategoryChartProps {
  data: InventoryCategory[];
  loading?: boolean;
  error?: string | null;
}

// Hoisted outside component
const COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"];

const formatCurrency = (value: number): string => {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
};

const formatNumber = (value: number): string => value.toLocaleString();

export default function InventoryByCategoryChart({
  data,
  loading = false,
  error = null
}: InventoryByCategoryChartProps) {
  const [viewMode, setViewMode] = useState<"value" | "quantity">("value");

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

  const chartData = data.map((item) => ({
    ...item,
    displayValue: viewMode === "value" ? item.inventory_value : item.total_quantity,
  }));

  return (
    <div>
      {/* View Mode Toggle */}
      <div className="flex justify-end mb-4">
        <div className="inline-flex rounded-lg border border-gray-200 p-1 bg-gray-50">
          <button
            onClick={() => setViewMode("value")}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
              viewMode === "value" ? "bg-white text-blue-600 shadow-sm" : "text-gray-600 hover:text-gray-900"
            }`}
          >
            Value ($)
          </button>
          <button
            onClick={() => setViewMode("quantity")}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
              viewMode === "quantity" ? "bg-white text-blue-600 shadow-sm" : "text-gray-600 hover:text-gray-900"
            }`}
          >
            Quantity
          </button>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 20, left: 100, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis type="number" tickFormatter={viewMode === "value" ? formatCurrency : formatNumber} tick={{ fontSize: 12, fill: "#6B7280" }} />
          <YAxis type="category" dataKey="category" tick={{ fontSize: 11, fill: "#374151" }} width={95} />
          <Tooltip
            formatter={(value) => viewMode === "value" ? formatCurrency(value as number) : formatNumber(value as number) + " units"}
            labelFormatter={(label) => `Category: ${label}`}
            contentStyle={{ backgroundColor: "#fff", border: "1px solid #E5E7EB", borderRadius: "8px", fontSize: "12px" }}
          />
          <Bar dataKey="displayValue" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-4 mt-4 text-xs">
        {data.map((item, index) => (
          <div key={item.category} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
            <span className="text-gray-600">{item.category} ({item.product_count} products)</span>
          </div>
        ))}
      </div>
    </div>
  );
}
