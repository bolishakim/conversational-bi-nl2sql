"use client";

import dynamic from 'next/dynamic';

// Dynamic imports for Recharts
const BarChart = dynamic(() => import('recharts').then(mod => mod.BarChart), { ssr: false });
const Bar = dynamic(() => import('recharts').then(mod => mod.Bar), { ssr: false });
const XAxis = dynamic(() => import('recharts').then(mod => mod.XAxis), { ssr: false });
const YAxis = dynamic(() => import('recharts').then(mod => mod.YAxis), { ssr: false });
const CartesianGrid = dynamic(() => import('recharts').then(mod => mod.CartesianGrid), { ssr: false });
const Tooltip = dynamic(() => import('recharts').then(mod => mod.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(() => import('recharts').then(mod => mod.ResponsiveContainer), { ssr: false });

interface DepartmentStats {
  department: string;
  employee_count: number;
  avg_salary: number;
  total_payroll: number;
  avg_tenure_years: number;
}

interface EmployeesByDepartmentChartProps {
  data: DepartmentStats[];
  loading?: boolean;
  error?: string | null;
}

// Hoisted outside component
const BAR_COLOR = "#3B82F6";

const formatCurrency = (value: number): string => {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  } else if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
};

export default function EmployeesByDepartmentChart({
  data,
  loading = false,
  error = null
}: EmployeesByDepartmentChartProps) {
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

  // Get total employees for percentage calculation
  const totalEmployees = data.reduce((sum, d) => sum + d.employee_count, 0);

  return (
    <div>
      {/* Chart */}
      <ResponsiveContainer width="100%" height={200}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 5, right: 20, left: 5, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            type="number"
            tick={{ fontSize: 11, fill: "#6B7280" }}
          />
          <YAxis
            type="category"
            dataKey="department"
            tick={{ fontSize: 10, fill: "#374151" }}
            width={115}
          />
          <Tooltip
            formatter={(value, name, props) => {
              const dept = props.payload;
              const numValue = value as number;
              return [
                <div key="tooltip" className="text-sm">
                  <div><strong>{numValue}</strong> employees</div>
                  <div className="text-gray-500">
                    {((numValue / totalEmployees) * 100).toFixed(1)}% of total
                  </div>
                  <div className="text-gray-500 mt-1">
                    Avg Salary: {formatCurrency(dept.avg_salary)}
                  </div>
                </div>,
                ""
              ];
            }}
            labelFormatter={(label) => `${label}`}
            contentStyle={{
              backgroundColor: "#fff",
              border: "1px solid #E5E7EB",
              borderRadius: "8px",
              fontSize: "12px",
            }}
          />
          <Bar dataKey="employee_count" radius={[0, 4, 4, 0]} fill={BAR_COLOR} />
        </BarChart>
      </ResponsiveContainer>

      {/* Summary Stats */}
      <div className="mt-2 grid grid-cols-3 gap-3 text-center border-t border-gray-100 pt-2">
        <div>
          <p className="text-base font-bold text-gray-900">{totalEmployees}</p>
          <p className="text-[10px] text-gray-500">Total Employees</p>
        </div>
        <div>
          <p className="text-base font-bold text-gray-900">{data.length}</p>
          <p className="text-[10px] text-gray-500">Departments</p>
        </div>
        <div>
          <p className="text-base font-bold text-gray-900">
            {data.length > 0 ? Math.round(totalEmployees / data.length) : 0}
          </p>
          <p className="text-[10px] text-gray-500">Avg per Dept</p>
        </div>
      </div>
    </div>
  );
}
