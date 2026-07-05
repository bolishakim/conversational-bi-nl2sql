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

interface SalaryBucket {
  salary_range: string;
  min_salary: number;
  max_salary: number;
  employee_count: number;
  percentage: number;
}

interface SalaryDistributionChartProps {
  data: SalaryBucket[];
  loading?: boolean;
  error?: string | null;
}

// Hoisted outside component
const BAR_COLOR = "#F59E0B"; // Amber to differentiate from department chart

export default function SalaryDistributionChart({
  data,
  loading = false,
  error = null
}: SalaryDistributionChartProps) {
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

  // Calculate stats
  const total = data.reduce((sum, b) => sum + b.employee_count, 0);

  // Find median bucket (bucket containing 50th percentile)
  let cumulative = 0;
  let medianBucket = data[0];
  for (const bucket of data) {
    cumulative += bucket.employee_count;
    if (cumulative >= total / 2) {
      medianBucket = bucket;
      break;
    }
  }

  const stats = {
    median: (medianBucket.min_salary + medianBucket.max_salary) / 2,
    total
  };

  return (
    <div>
      {/* Chart */}
      <ResponsiveContainer width="100%" height={180}>
        <BarChart
          data={data}
          margin={{ top: 5, right: 15, left: 5, bottom: 50 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="salary_range"
            tick={{ fontSize: 9, fill: "#6B7280" }}
            angle={-45}
            textAnchor="end"
            height={70}
            interval={0}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#6B7280" }}
            width={40}
          />
          <Tooltip
            formatter={(value, _name, props) => {
              const bucket = props.payload;
              return [
                <div key="tooltip" className="text-sm">
                  <div><strong>{value}</strong> employees</div>
                  <div className="text-gray-500">
                    {bucket.percentage.toFixed(1)}% of workforce
                  </div>
                </div>,
                ""
              ];
            }}
            labelFormatter={(label) => `Salary Range: ${label}`}
            contentStyle={{
              backgroundColor: "#fff",
              border: "1px solid #E5E7EB",
              borderRadius: "8px",
              fontSize: "12px",
            }}
          />
          <Bar dataKey="employee_count" radius={[4, 4, 0, 0]} fill={BAR_COLOR} />
        </BarChart>
      </ResponsiveContainer>

      {/* Statistics */}
      <div className="mt-2 grid grid-cols-2 gap-3 border-t border-gray-100 pt-2">
        <div className="text-center">
          <p className="text-base font-bold text-gray-900">
            ${Math.round(stats.median).toLocaleString()}
          </p>
          <p className="text-[10px] text-gray-500">Estimated Median Salary</p>
        </div>
        <div className="text-center">
          <p className="text-base font-bold text-gray-900">
            {stats.total}
          </p>
          <p className="text-[10px] text-gray-500">Total Employees</p>
        </div>
      </div>

      {/* Distribution Note */}
      <div className="mt-2 text-[10px] text-gray-500 text-center">
        Annual salary calculated as hourly rate × 40 hrs × 52 weeks
      </div>
    </div>
  );
}
