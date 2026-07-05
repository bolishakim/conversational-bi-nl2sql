"use client";

import { AlertTriangle } from "lucide-react";

interface ProductInventoryItem {
  product_id: number;
  product_name: string;
  category: string;
  subcategory: string;
  quantity: number;
  list_price: number;
  standard_cost: number;
  profit_margin: number;
  inventory_value: number;
}

interface HighMarginLowStockTableProps {
  data: ProductInventoryItem[];
  loading?: boolean;
  error?: string | null;
}

// Hoisted outside component
const formatCurrency = (value: number): string => {
  return `$${value.toFixed(2)}`;
};

const formatPercent = (value: number): string => {
  return `${value.toFixed(1)}%`;
};

export default function HighMarginLowStockTable({
  data,
  loading = false,
  error = null
}: HighMarginLowStockTableProps) {
  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-10 bg-gray-100 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="text-red-500 text-sm">{error}</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="p-6 text-center text-gray-500 text-sm">
        No high-margin low-stock products found
      </div>
    );
  }

  // Calculate category stats for summary
  const categoryStats: { [key: string]: number } = {};
  data.forEach((item) => {
    categoryStats[item.category] = (categoryStats[item.category] || 0) + 1;
  });

  return (
    <div>
      {/* Category Summary */}
      <div className="px-4 pb-3 border-b border-gray-100">
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(categoryStats)
            .sort((a, b) => b[1] - a[1])
            .map(([category, count]) => (
              <div
                key={category}
                className="inline-flex items-center gap-1 px-2 py-1 bg-amber-50 border border-amber-200 rounded-full"
              >
                <span className="text-xs font-medium text-amber-800">
                  {category}
                </span>
                <span className="text-[10px] font-bold text-amber-600 bg-amber-100 px-1.5 py-0.5 rounded-full">
                  {count}
                </span>
              </div>
            ))}
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Total: {data.length} high-margin, low-stock products
        </p>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full divide-y divide-gray-200 text-xs">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-gray-500 uppercase tracking-wider">
                Product
              </th>
              <th className="px-3 py-2 text-left font-medium text-gray-500 uppercase tracking-wider">
                Category
              </th>
              <th className="px-3 py-2 text-right font-medium text-gray-500 uppercase tracking-wider">
                Stock
              </th>
              <th className="px-3 py-2 text-right font-medium text-gray-500 uppercase tracking-wider">
                Margin
              </th>
              <th className="px-3 py-2 text-right font-medium text-gray-500 uppercase tracking-wider">
                Value
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {data.map((item) => (
              <tr
                key={item.product_id}
                className="hover:bg-amber-50 transition-colors"
              >
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    <AlertTriangle className="w-3 h-3 text-amber-500 flex-shrink-0" />
                    <div className="font-medium text-gray-900" title={item.product_name}>
                      {item.product_name}
                    </div>
                  </div>
                </td>
                <td className="px-3 py-2">
                  <div className="text-gray-600">{item.category}</div>
                </td>
                <td className="px-3 py-2 text-right">
                  <span className="font-semibold text-amber-600">
                    {item.quantity}
                  </span>
                </td>
                <td className="px-3 py-2 text-right">
                  <span className="font-semibold text-green-600">
                    {formatPercent(item.profit_margin)}
                  </span>
                </td>
                <td className="px-3 py-2 text-right text-gray-700">
                  {formatCurrency(item.inventory_value)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Risk Summary */}
      <div className="p-3 bg-amber-50 border-t border-amber-100">
        <div className="flex items-start gap-2 text-xs">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
          <span className="text-amber-800">
            <strong>Risk Alert:</strong> These {data.length} high-margin products have low
            inventory and may need restocking to avoid stockouts.
          </span>
        </div>
      </div>
    </div>
  );
}
