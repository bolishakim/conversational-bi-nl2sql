"use client";

import { Trophy, TrendingUp, MapPin } from "lucide-react";

interface SalesRepData {
  name: string;
  revenue: number;
  orders: number;
  territories?: string;
  avg_order_value?: number;
  territory?: string;
}

interface TopSalesRepsTableProps {
  data: SalesRepData[];
  loading?: boolean;
  error?: string | null;
}

// Hoist formatCurrency outside component
const formatCurrency = (value: number): string => {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(2)}M`;
  } else if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`;
  }
  return `$${value.toFixed(0)}`;
};

export default function TopSalesRepsTable({
  data,
  loading = false,
  error = null
}: TopSalesRepsTableProps) {
  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600 text-sm">⚠️ {error}</p>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="p-6">
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <p className="text-gray-500 text-sm text-center">No sales reps data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Rank
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Sales Rep
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Revenue
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Orders
            </th>
            {data[0]?.avg_order_value !== undefined && (
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Avg Order
              </th>
            )}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {data.map((rep, index) => (
            <tr
              key={index}
              className="hover:bg-gray-50 transition-colors duration-150"
            >
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  {index === 0 && (
                    <Trophy className="w-5 h-5 text-yellow-500 mr-2" />
                  )}
                  {index === 1 && (
                    <Trophy className="w-5 h-5 text-gray-400 mr-2" />
                  )}
                  {index === 2 && (
                    <Trophy className="w-5 h-5 text-amber-600 mr-2" />
                  )}
                  {index > 2 && (
                    <span className="text-sm text-gray-500 mr-2 ml-7">#{index + 1}</span>
                  )}
                  {index < 3 && (
                    <span className="text-sm font-semibold text-gray-700">
                      #{index + 1}
                    </span>
                  )}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex flex-col">
                  <div className="text-sm font-medium text-gray-900">
                    {rep.name}
                  </div>
                  {(rep.territory || rep.territories) && (
                    <div className="text-xs text-gray-500 flex items-center mt-1">
                      <MapPin className="w-3 h-3 mr-1" />
                      {rep.territory || rep.territories}
                    </div>
                  )}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right">
                <div className="flex items-center justify-end">
                  <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
                  <span className="text-sm font-semibold text-gray-900">
                    {formatCurrency(rep.revenue)}
                  </span>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right">
                <span className="text-sm text-gray-700">
                  {rep.orders.toLocaleString()}
                </span>
              </td>
              {rep.avg_order_value !== undefined && (
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <span className="text-sm text-gray-600">
                    {formatCurrency(rep.avg_order_value)}
                  </span>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
