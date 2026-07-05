"use client";

import { TrendingUp, Users, DollarSign, Award } from "lucide-react";

interface SalesROI {
  year: number;
  sales_employees: number;
  avg_sales_salary: number;
  company_avg_salary: number;
  total_revenue: number;
  revenue_per_sales_employee: number;
  roi_multiple: number;
  summary: string;
}

interface SalesROICardProps {
  data: SalesROI | null;
  loading?: boolean;
  error?: string | null;
}

// Hoisted outside component
const formatCurrency = (value: number): string => {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(2)}M`;
  } else if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`;
  }
  return `$${value.toFixed(0)}`;
};

export default function SalesROICard({
  data,
  loading = false,
  error = null
}: SalesROICardProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/2"></div>
          <div className="h-16 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
        <div className="text-red-500 text-sm">{error}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
        <div className="text-gray-500 text-sm">No data available</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900">
          Sales Department ROI
        </h3>
        <span className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded-full">
          {data.year}
        </span>
      </div>

      {/* Main ROI Metric */}
      <div className="bg-blue-50 rounded-lg p-3 mb-3 border border-blue-100">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] text-gray-600">Revenue per Sales Employee</p>
            <p className="text-xl font-bold text-blue-600">
              {formatCurrency(data.revenue_per_sales_employee)}
            </p>
          </div>
          <div className="flex items-center gap-1.5 bg-green-100 text-green-700 px-2 py-1.5 rounded-lg">
            <Award className="w-4 h-4" />
            <span className="text-lg font-bold">{data.roi_multiple.toFixed(0)}x</span>
            <span className="text-[10px]">ROI</span>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
          <div className="flex items-center gap-1.5 mb-0.5">
            <Users className="w-3 h-3 text-gray-400" />
            <span className="text-[10px] text-gray-500">Sales Team</span>
          </div>
          <p className="text-sm font-semibold text-gray-900">
            {data.sales_employees} employees
          </p>
        </div>

        <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
          <div className="flex items-center gap-1.5 mb-0.5">
            <DollarSign className="w-3 h-3 text-gray-400" />
            <span className="text-[10px] text-gray-500">Avg Sales Salary</span>
          </div>
          <p className="text-sm font-semibold text-gray-900">
            {formatCurrency(data.avg_sales_salary)}
          </p>
        </div>

        <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
          <div className="flex items-center gap-1.5 mb-0.5">
            <TrendingUp className="w-3 h-3 text-gray-400" />
            <span className="text-[10px] text-gray-500">Total Revenue</span>
          </div>
          <p className="text-sm font-semibold text-gray-900">
            {formatCurrency(data.total_revenue)}
          </p>
        </div>

        <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
          <div className="flex items-center gap-1.5 mb-0.5">
            <DollarSign className="w-3 h-3 text-gray-400" />
            <span className="text-[10px] text-gray-500">Company Avg Salary</span>
          </div>
          <p className="text-sm font-semibold text-gray-900">
            {formatCurrency(data.company_avg_salary)}
          </p>
        </div>
      </div>

      {/* Summary */}
      <div className="bg-blue-50 rounded-lg p-2.5 border border-blue-100">
        <p className="text-xs text-blue-800">
          <strong>Insight:</strong> {data.summary}
        </p>
      </div>

      {/* Note for Q3 */}
      <p className="mt-2 text-[10px] text-gray-400 text-center">
        Key metric for workforce ROI analysis (Q3)
      </p>
    </div>
  );
}
