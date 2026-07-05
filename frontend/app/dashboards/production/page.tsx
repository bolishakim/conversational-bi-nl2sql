"use client";

import AuthenticatedLayout from "@/components/AuthenticatedLayout";
import TaskOverlay from "@/components/TaskOverlay";
import KPICard from "@/components/dashboards/KPICard";
import InventoryByCategoryChart from "@/components/dashboards/InventoryByCategoryChart";
import ProfitMarginChart from "@/components/dashboards/ProfitMarginChart";
import LowStockTable from "@/components/dashboards/LowStockTable";
import HighMarginLowStockTable from "@/components/dashboards/HighMarginLowStockTable";
import { Package, AlertTriangle, TrendingUp, DollarSign, Percent, Star } from "lucide-react";
import { useProductionDashboard } from "@/lib/hooks/useDashboard";
import { useDashboardTracking } from "@/lib/hooks/useDashboardTracking";

interface ProductionKPIs {
  total_inventory_value: number;
  total_products: number;
  low_stock_count: number;
  avg_profit_margin: number;
  avg_production_cost: number;
  high_margin_products: number;
}

export default function ProductionDashboard() {
  // Use SWR hook for automatic request deduplication and caching
  const { kpis, inventoryData, profitMarginData, lowStockData, highMarginLowStockData, loading, error } = useProductionDashboard();

  // Initialize dashboard tracking
  const { trackClick } = useDashboardTracking("production");

  return (
    <AuthenticatedLayout
      title="Production & Inventory"
      subtitle="Monitor inventory levels, product margins, and stock alerts"
    >
      <div className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">Inventory Overview</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Current inventory status and product metrics
            </p>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 text-sm">⚠️ {error}</p>
          </div>
        )}

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
          <KPICard
            title="Inventory Value"
            value={kpis?.total_inventory_value || 0}
            format="currency"
            icon={<DollarSign className="w-4 h-4" />}
            loading={loading}
            onClick={() => trackClick("kpi_inventory_value", { value: kpis?.total_inventory_value })}
          />

          <KPICard
            title="Total Products"
            value={kpis?.total_products || 0}
            format="number"
            icon={<Package className="w-4 h-4" />}
            loading={loading}
            onClick={() => trackClick("kpi_total_products", { value: kpis?.total_products })}
          />

          <KPICard
            title="Low Stock Items"
            value={kpis?.low_stock_count || 0}
            format="number"
            icon={<AlertTriangle className="w-4 h-4 text-red-500" />}
            loading={loading}
            onClick={() => trackClick("kpi_low_stock_items", { value: kpis?.low_stock_count })}
          />

          <KPICard
            title="Avg Production Cost"
            value={kpis?.avg_production_cost || 0}
            format="currency"
            decimals={2}
            icon={<Package className="w-4 h-4" />}
            loading={loading}
            onClick={() => trackClick("kpi_avg_production_cost", { value: kpis?.avg_production_cost })}
          />

          <KPICard
            title="Avg Profit Margin"
            value={kpis?.avg_profit_margin || 0}
            format="percentage"
            decimals={2}
            icon={<TrendingUp className="w-4 h-4" />}
            loading={loading}
            onClick={() => trackClick("kpi_avg_profit_margin", { value: kpis?.avg_profit_margin })}
          />

          <KPICard
            title="High Margin Products"
            value={kpis?.high_margin_products || 0}
            format="number"
            subtitle="> 60% margin"
            icon={<Star className="w-4 h-4 text-yellow-500" />}
            loading={loading}
            onClick={() => trackClick("kpi_high_margin_products", { value: kpis?.high_margin_products })}
          />
        </div>

        {/* Charts Section - Row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {/* Inventory by Category Chart */}
          <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-900 mb-2">
              Inventory by Category
            </h3>
            <InventoryByCategoryChart
              data={inventoryData}
              loading={loading}
              error={error}
            />
          </div>

          {/* Profit Margin by Category Chart */}
          <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-900 mb-2">
              Profit Margin by Category
            </h3>
            <ProfitMarginChart
              data={profitMarginData}
              loading={loading}
              error={error}
            />
          </div>
        </div>

        {/* Tables Section - Row 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {/* Low Stock Alerts Table */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
            <div className="p-4 pb-0">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-gray-900">
                  Low Stock Alerts
                </h3>
                <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                  Products with {"<"} 50 units
                </span>
              </div>
            </div>
            <LowStockTable
              data={lowStockData}
              loading={loading}
              error={error}
            />
          </div>

          {/* High Margin Low Stock Table */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
            <div className="p-4 pb-0">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-gray-900">
                  High Margin, Low Stock Risk
                </h3>
                <span className="text-xs text-gray-500 bg-amber-100 text-amber-700 px-2 py-1 rounded-full">
                  {">"} 60% margin, {"<"} 50 units
                </span>
              </div>
            </div>
            <HighMarginLowStockTable
              data={highMarginLowStockData}
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
