import useSWR from 'swr';
import { api } from '@/lib/api';

// Fetcher function for SWR
const dashboardFetcher = async (url: string) => {
  const [, dashboard, endpoint, queryString] = url.split('|');
  const params = queryString ? JSON.parse(queryString) : {};

  if (endpoint === 'kpis') {
    return api.getDashboardKPIs(dashboard, params);
  }

  return api.getDashboardChart(dashboard, endpoint, params);
};

// Hook for dashboard KPIs
export function useDashboardKPIs(dashboard: string, params: Record<string, string> = {}) {
  const key = `dashboard|${dashboard}|kpis|${JSON.stringify(params)}`;

  const { data, error, isLoading, mutate } = useSWR(key, dashboardFetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 60000, // Dedupe requests within 60s
    shouldRetryOnError: false,
  });

  return {
    data,
    error: error?.message || null,
    loading: isLoading,
    refresh: mutate,
  };
}

// Hook for dashboard charts
export function useDashboardChart(
  dashboard: string,
  chart: string,
  params: Record<string, string> = {}
) {
  const key = `dashboard|${dashboard}|${chart}|${JSON.stringify(params)}`;

  const { data, error, isLoading, mutate } = useSWR(key, dashboardFetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 60000,
    shouldRetryOnError: false,
  });

  return {
    data,
    error: error?.message || null,
    loading: isLoading,
    refresh: mutate,
  };
}

// Hook for fetching all sales dashboard data in parallel
export function useSalesDashboard(params: Record<string, string> = {}) {
  const kpis = useDashboardKPIs('sales', params);
  const territoryData = useDashboardChart('sales', 'revenue-by-territory', params);
  const trendData = useDashboardChart('sales', 'revenue-trend', { ...params, granularity: 'month' });
  const categoryData = useDashboardChart('sales', 'category-breakdown', params);
  const salesRepsData = useDashboardChart('sales', 'sales-reps', { ...params, limit: '5' });

  const loading = kpis.loading || territoryData.loading || trendData.loading || categoryData.loading || salesRepsData.loading;
  const error = kpis.error || territoryData.error || trendData.error || categoryData.error || salesRepsData.error;

  return {
    kpis: kpis.data,
    territoryData: territoryData.data || [],
    trendData: trendData.data || [],
    categoryData: categoryData.data || [],
    salesRepsData: salesRepsData.data || [],
    loading,
    error,
    refresh: () => {
      kpis.refresh();
      territoryData.refresh();
      trendData.refresh();
      categoryData.refresh();
      salesRepsData.refresh();
    },
  };
}

// Hoisted default params for production dashboard
const PRODUCTION_EMPTY_PARAMS = {};
const PRODUCTION_LOW_STOCK_PARAMS = { limit: '10' };

// Hook for fetching all production dashboard data in parallel
export function useProductionDashboard() {
  const kpis = useDashboardKPIs('production', PRODUCTION_EMPTY_PARAMS);
  const inventoryData = useDashboardChart('production', 'inventory-by-category', PRODUCTION_EMPTY_PARAMS);
  const profitMarginData = useDashboardChart('production', 'profit-margins', PRODUCTION_EMPTY_PARAMS);
  const lowStockData = useDashboardChart('production', 'low-stock', PRODUCTION_LOW_STOCK_PARAMS);
  const highMarginLowStockData = useDashboardChart('production', 'high-margin-low-stock', PRODUCTION_EMPTY_PARAMS);

  const loading = kpis.loading || inventoryData.loading || profitMarginData.loading || lowStockData.loading || highMarginLowStockData.loading;
  const error = kpis.error || inventoryData.error || profitMarginData.error || lowStockData.error || highMarginLowStockData.error;

  return {
    kpis: kpis.data,
    inventoryData: inventoryData.data || [],
    profitMarginData: profitMarginData.data || [],
    lowStockData: lowStockData.data || [],
    highMarginLowStockData: highMarginLowStockData.data || [],
    loading,
    error,
    refresh: () => {
      kpis.refresh();
      inventoryData.refresh();
      profitMarginData.refresh();
      lowStockData.refresh();
      highMarginLowStockData.refresh();
    },
  };
}

// Hoisted default params for workforce dashboard
const WORKFORCE_EMPTY_PARAMS = {};

// Hook for fetching all workforce/operations dashboard data in parallel
export function useWorkforceDashboard() {
  const kpis = useDashboardKPIs('workforce', WORKFORCE_EMPTY_PARAMS);
  const employeesByDeptData = useDashboardChart('workforce', 'departments', WORKFORCE_EMPTY_PARAMS);
  const salaryDistributionData = useDashboardChart('workforce', 'salary-distribution', WORKFORCE_EMPTY_PARAMS);
  const salesROIData = useDashboardChart('workforce', 'sales-roi', WORKFORCE_EMPTY_PARAMS);
  const departmentTableData = useDashboardChart('workforce', 'departments', WORKFORCE_EMPTY_PARAMS);

  const loading = kpis.loading || employeesByDeptData.loading || salaryDistributionData.loading || salesROIData.loading || departmentTableData.loading;
  const error = kpis.error || employeesByDeptData.error || salaryDistributionData.error || salesROIData.error || departmentTableData.error;

  return {
    kpis: kpis.data,
    employeesByDeptData: employeesByDeptData.data || [],
    salaryDistributionData: salaryDistributionData.data || [],
    salesROIData: salesROIData.data,
    departmentTableData: departmentTableData.data || [],
    loading,
    error,
    refresh: () => {
      kpis.refresh();
      employeesByDeptData.refresh();
      salaryDistributionData.refresh();
      salesROIData.refresh();
      departmentTableData.refresh();
    },
  };
}
