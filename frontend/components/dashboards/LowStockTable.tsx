"use client";

import { AlertTriangle, AlertCircle, Info } from "lucide-react";

interface LowStockItem {
  product_id: number;
  product_name: string;
  category: string;
  subcategory: string;
  quantity: number;
  list_price: number;
  profit_margin: number;
  status: "critical" | "low" | "warning";
}

interface LowStockTableProps {
  data: LowStockItem[];
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

const getStatusBadge = (status: string) => {
  switch (status) {
    case "critical":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
          <AlertCircle className="w-3 h-3" />
          Critical
        </span>
      );
    case "low":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
          <AlertTriangle className="w-3 h-3" />
          Low
        </span>
      );
    case "warning":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
          <Info className="w-3 h-3" />
          Warning
        </span>
      );
    default:
      return null;
  }
};

export default function LowStockTable({
  data,
  loading = false,
  error = null
}: LowStockTableProps) {
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
        No low stock products found
      </div>
    );
  }

  return (
    <div>
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
                Price
              </th>
              <th className="px-3 py-2 text-right font-medium text-gray-500 uppercase tracking-wider">
                Margin
              </th>
              <th className="px-3 py-2 text-center font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {data.map((item) => (
              <tr
                key={item.product_id}
                className="hover:bg-gray-50 transition-colors"
              >
                <td className="px-3 py-2">
                  <div className="font-medium text-gray-900" title={item.product_name}>
                    {item.product_name}
                  </div>
                </td>
                <td className="px-3 py-2">
                  <div className="text-gray-600">{item.category}</div>
                </td>
                <td className="px-3 py-2 text-right">
                  <span
                    className={`font-semibold ${
                      item.quantity < 10
                        ? "text-red-600"
                        : item.quantity < 25
                        ? "text-amber-600"
                        : "text-gray-900"
                    }`}
                  >
                    {item.quantity}
                  </span>
                </td>
                <td className="px-3 py-2 text-right text-gray-700">
                  {formatCurrency(item.list_price)}
                </td>
                <td className="px-3 py-2 text-right">
                  <span
                    className={`font-medium ${
                      item.profit_margin >= 50
                        ? "text-green-600"
                        : item.profit_margin >= 30
                        ? "text-amber-600"
                        : "text-red-600"
                    }`}
                  >
                    {formatPercent(item.profit_margin)}
                  </span>
                </td>
                <td className="px-3 py-2 text-center">
                  {getStatusBadge(item.status)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary footer */}
      <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>Showing {data.length} low stock products</span>
        </div>
      </div>
    </div>
  );
}
