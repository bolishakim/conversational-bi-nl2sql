"use client";

import { useState, useMemo } from "react";
import AuthenticatedLayout from "@/components/AuthenticatedLayout";
import TaskOverlay from "@/components/TaskOverlay";
import KPICard from "@/components/dashboards/KPICard";
import RevenueByTerritoryChart from "@/components/dashboards/RevenueByTerritoryChart";
import RevenueTrendChart from "@/components/dashboards/RevenueTrendChart";
import CategoryBreakdownChart from "@/components/dashboards/CategoryBreakdownChart";
import TopSalesRepsTable from "@/components/dashboards/TopSalesRepsTable";
import TimeRangeFilter, { TimeRange } from "@/components/dashboards/TimeRangeFilterStepBased";
import { TrendingUp, ShoppingCart, DollarSign, MapPin } from "lucide-react";
import { useSalesDashboard } from "@/lib/hooks/useDashboard";
import { useDashboardTracking } from "@/lib/hooks/useDashboardTracking";

interface SalesKPIs {
  total_revenue: number;
  total_orders: number;
  avg_order_value: number;
  yoy_growth: number;
  top_territory: string;
  top_territory_revenue: number;
}

interface TerritoryData {
  territory: string;
  revenue: number;
  orders: number;
  avg_order_value: number;
}

interface TrendData {
  period: string;
  revenue: number;
  orders: number;
}

interface CategoryData {
  category: string;
  revenue: number;
  percentage: number;
}

interface SalesRepData {
  name: string;
  revenue: number;
  orders: number;
  territories: string;
}

export default function SalesDashboard() {
  const [timeRange, setTimeRange] = useState<TimeRange>({
    startDate: "2024-01-01",
    endDate: "2024-12-31",
    granularity: "annual",
    label: "Year 2024"
  });

  // Memoize params to prevent unnecessary re-renders
  const params = useMemo(() => ({
    start_date: timeRange.startDate,
    end_date: timeRange.endDate,
  }), [timeRange.startDate, timeRange.endDate]);

  // Use SWR hook for automatic request deduplication and caching
  const { kpis, territoryData, trendData, categoryData, salesRepsData, loading, error } = useSalesDashboard(params);

  // Initialize dashboard tracking
  const { trackFilterChange, trackClick } = useDashboardTracking("sales");

  // Handle time range change
  const handleTimeRangeChange = (newRange: TimeRange) => {
    setTimeRange(newRange);
    // Track filter change
    trackFilterChange("time_range", {
      granularity: newRange.granularity,
      label: newRange.label,
    });
  };

  // Get comparison label based on time range
  const getComparisonLabel = (): string => {
    const startYear = new Date(timeRange.startDate).getFullYear();
    const prevYear = startYear - 1;

    switch (timeRange.granularity) {
      case "annual":
        return `vs. ${prevYear}`;
      case "quarterly":
        return "vs. last year";
      case "monthly":
        return "vs. last year";
      case "custom":
        return "vs. previous period";
      default:
        return "vs. previous period";
    }
  };

  return (
    <AuthenticatedLayout
      title="Sales & Revenue Analytics"
      subtitle="Monitor sales performance, territories, and revenue trends"
    >
      <div className="p-4 space-y-3">
        {/* Time Filter Bar */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">Dashboard Overview</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Viewing data for: <span className="font-medium text-gray-700">{timeRange.label}</span>
            </p>
          </div>
          <TimeRangeFilter onChange={handleTimeRangeChange} defaultGranularity="annual" />
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 text-sm">⚠️ {error}</p>
          </div>
        )}

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          <KPICard
            title="Total Revenue"
            value={kpis?.total_revenue || 0}
            format="currency"
            change={kpis?.yoy_growth}
            changeLabel={getComparisonLabel()}
            icon={<DollarSign className="w-4 h-4" />}
            loading={loading}
            onClick={() => trackClick("kpi_total_revenue", { value: kpis?.total_revenue })}
          />

          <KPICard
            title="Total Orders"
            value={kpis?.total_orders || 0}
            format="number"
            icon={<ShoppingCart className="w-4 h-4" />}
            loading={loading}
            onClick={() => trackClick("kpi_total_orders", { value: kpis?.total_orders })}
          />

          <KPICard
            title="Avg Order Value"
            value={kpis?.avg_order_value || 0}
            format="currency"
            decimals={2}
            icon={<TrendingUp className="w-4 h-4" />}
            loading={loading}
            onClick={() => trackClick("kpi_avg_order_value", { value: kpis?.avg_order_value })}
          />

          <KPICard
            title="Top Territory"
            value={kpis?.top_territory || "N/A"}
            format="text"
            subtitle={kpis?.top_territory_revenue ? `$${(kpis.top_territory_revenue / 1000000).toFixed(1)}M revenue` : undefined}
            icon={<MapPin className="w-4 h-4" />}
            loading={loading}
            onClick={() => trackClick("kpi_top_territory", { territory: kpis?.top_territory })}
          />
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {/* Revenue by Territory Chart */}
          <div
            className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm cursor-pointer hover:border-blue-200 transition-colors"
            onClick={() => trackClick("chart_revenue_by_territory")}
          >
            <h3 className="text-sm font-semibold text-gray-900 mb-2">
              Revenue by Territory
            </h3>
            <RevenueByTerritoryChart
              data={territoryData}
              loading={loading}
              error={error}
            />
          </div>

          {/* Revenue Trend Chart */}
          <div
            className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm cursor-pointer hover:border-blue-200 transition-colors"
            onClick={() => trackClick("chart_revenue_trend")}
          >
            <h3 className="text-sm font-semibold text-gray-900 mb-2">
              Revenue Trend
            </h3>
            <RevenueTrendChart
              data={trendData}
              loading={loading}
              error={error}
            />
          </div>

          {/* Category Breakdown Chart */}
          <div
            className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm cursor-pointer hover:border-blue-200 transition-colors"
            onClick={() => trackClick("chart_category_breakdown")}
          >
            <h3 className="text-sm font-semibold text-gray-900 mb-2">
              Revenue by Product Category
            </h3>
            <CategoryBreakdownChart
              data={categoryData}
              loading={loading}
              error={error}
            />
          </div>

          {/* Top Sales Reps Table */}
          <div
            className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden cursor-pointer hover:border-blue-200 transition-colors"
            onClick={() => trackClick("table_top_sales_reps")}
          >
            <div className="p-4 pb-0">
              <h3 className="text-sm font-semibold text-gray-900 mb-2">
                Top Sales Representatives
              </h3>
            </div>
            <TopSalesRepsTable
              data={salesRepsData}
              loading={loading}
              error={error}
            />
          </div>
        </div>
      </div>

      {/* Task Overlay */}
      <TaskOverlay />
    </AuthenticatedLayout>
  );
}
