"use client";

import AuthenticatedLayout from "@/components/AuthenticatedLayout";
import TaskOverlay from "@/components/TaskOverlay";
import KPICard from "@/components/dashboards/KPICard";
import EmployeesByDepartmentChart from "@/components/dashboards/EmployeesByDepartmentChart";
import SalaryDistributionChart from "@/components/dashboards/SalaryDistributionChart";
import SalesROICard from "@/components/dashboards/SalesROICard";
import DepartmentTable from "@/components/dashboards/DepartmentTable";
import { Users, DollarSign, Building2, Clock, Briefcase, TrendingUp } from "lucide-react";
import { useWorkforceDashboard } from "@/lib/hooks/useDashboard";
import { useDashboardTracking } from "@/lib/hooks/useDashboardTracking";

interface WorkforceKPIs {
  total_employees: number;
  avg_annual_salary: number;
  total_payroll: number;
  avg_tenure_years: number;
  departments_count: number;
  sales_employees: number;
}

export default function WorkforceDashboard() {
  // Use SWR hook for automatic request deduplication and caching
  const { kpis, employeesByDeptData, salaryDistributionData, salesROIData, departmentTableData, loading, error } = useWorkforceDashboard();

  // Initialize dashboard tracking
  const { trackClick } = useDashboardTracking("operations");

  return (
    <AuthenticatedLayout
      title="Workforce & Operations"
      subtitle="Monitor employee metrics, salaries, and departmental performance"
    >
      <div className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">Workforce Overview</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Current employee metrics and departmental data
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
            title="Total Employees"
            value={kpis?.total_employees || 0}
            format="number"
            icon={<Users className="w-4 h-4" />}
            loading={loading}
            onClick={() => trackClick("kpi_total_employees", { value: kpis?.total_employees })}
          />

          <KPICard
            title="Avg Annual Salary"
            value={kpis?.avg_annual_salary || 0}
            format="currency"
            decimals={0}
            icon={<DollarSign className="w-4 h-4" />}
            loading={loading}
            onClick={() => trackClick("kpi_avg_salary", { value: kpis?.avg_annual_salary })}
          />

          <KPICard
            title="Total Payroll"
            value={kpis?.total_payroll || 0}
            format="currency"
            icon={<TrendingUp className="w-4 h-4" />}
            loading={loading}
            onClick={() => trackClick("kpi_total_payroll", { value: kpis?.total_payroll })}
          />

          <KPICard
            title="Avg Tenure"
            value={`${(kpis?.avg_tenure_years || 0).toFixed(1)} yrs`}
            format="text"
            icon={<Clock className="w-4 h-4" />}
            loading={loading}
            onClick={() => trackClick("kpi_avg_tenure", { years: kpis?.avg_tenure_years })}
          />

          <KPICard
            title="Departments"
            value={kpis?.departments_count || 0}
            format="number"
            icon={<Building2 className="w-4 h-4" />}
            loading={loading}
            onClick={() => trackClick("kpi_departments", { value: kpis?.departments_count })}
          />

          <KPICard
            title="Sales Team"
            value={kpis?.sales_employees || 0}
            format="number"
            subtitle="employees"
            icon={<Briefcase className="w-4 h-4 text-blue-500" />}
            loading={loading}
            onClick={() => trackClick("kpi_sales_team", { value: kpis?.sales_employees })}
          />
        </div>

        {/* Charts Section - Row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {/* Employees by Department Chart */}
          <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-900 mb-2">
              Headcount by Department
            </h3>
            <EmployeesByDepartmentChart
              data={employeesByDeptData}
              loading={loading}
              error={error}
            />
          </div>

          {/* Salary Distribution Chart */}
          <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-900 mb-2">
              Salary Distribution
            </h3>
            <SalaryDistributionChart
              data={salaryDistributionData}
              loading={loading}
              error={error}
            />
          </div>
        </div>

        {/* Row 2 - Sales ROI and Department Table */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {/* Sales ROI Card */}
          <SalesROICard
            data={salesROIData}
            loading={loading}
            error={error}
          />

          {/* Department Details Table */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
            <div className="p-4 pb-0">
              <h3 className="text-sm font-semibold text-gray-900 mb-2">
                Department Details
              </h3>
            </div>
            <DepartmentTable
              data={departmentTableData}
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
