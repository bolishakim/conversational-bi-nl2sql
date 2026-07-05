"use client";

import { useState } from "react";

interface DepartmentStats {
  department: string;
  employee_count: number;
  avg_salary: number;
  total_payroll: number;
  avg_tenure_years: number;
}

interface DepartmentTableProps {
  data: DepartmentStats[];
  loading?: boolean;
  error?: string | null;
}

// Hoisted outside component
const formatCurrency = (value: number): string => {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  } else if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
};

export default function DepartmentTable({
  data,
  loading = false,
  error = null
}: DepartmentTableProps) {
  const [sortField, setSortField] = useState<keyof DepartmentStats>("employee_count");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const handleSort = (field: keyof DepartmentStats) => {
    if (field === sortField) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const getSortIcon = (field: keyof DepartmentStats) => {
    if (field !== sortField) return "↕";
    return sortDirection === "asc" ? "↑" : "↓";
  };

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
      <div className="p-6">
        <div className="text-gray-500 text-sm">No data available</div>
      </div>
    );
  }

  const sortedData = [...data].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];

    if (typeof aVal === "string" && typeof bVal === "string") {
      return sortDirection === "asc"
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    }

    return sortDirection === "asc"
      ? (aVal as number) - (bVal as number)
      : (bVal as number) - (aVal as number);
  });

  // Find highest paid department
  const highestPaidDept = data.reduce(
    (max, d) => (d.avg_salary > max.avg_salary ? d : max),
    data[0]
  );

  // Find largest department
  const largestDept = data.reduce(
    (max, d) => (d.employee_count > max.employee_count ? d : max),
    data[0]
  );

  return (
    <div>
      {/* Summary badges */}
      <div className="px-3 pb-2 flex flex-wrap gap-1.5">
        <span className="text-[10px] bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
          Largest: {largestDept?.department} ({largestDept?.employee_count})
        </span>
        <span className="text-[10px] bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
          Highest Paid: {highestPaidDept?.department} ({formatCurrency(highestPaidDept?.avg_salary || 0)})
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto max-h-[320px] overflow-y-auto">
        <table className="w-full divide-y divide-gray-200 text-xs">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              <th
                className="px-3 py-2 text-left font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort("department")}
              >
                Department {getSortIcon("department")}
              </th>
              <th
                className="px-3 py-2 text-right font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort("employee_count")}
              >
                # {getSortIcon("employee_count")}
              </th>
              <th
                className="px-3 py-2 text-right font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort("avg_salary")}
              >
                Avg $ {getSortIcon("avg_salary")}
              </th>
              <th
                className="px-3 py-2 text-right font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort("avg_tenure_years")}
              >
                Tenure {getSortIcon("avg_tenure_years")}
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {sortedData.map((dept) => (
              <tr
                key={dept.department}
                className={`hover:bg-gray-50 transition-colors ${
                  dept.department === "Sales" ? "bg-blue-50" : ""
                }`}
              >
                <td className="px-3 py-1.5">
                  <span className="font-medium text-gray-900">
                    {dept.department}
                  </span>
                </td>
                <td className="px-3 py-1.5 text-right text-gray-700">
                  {dept.employee_count}
                </td>
                <td className="px-3 py-1.5 text-right">
                  <span
                    className={`font-medium ${
                      dept.avg_salary >= 100000
                        ? "text-green-600"
                        : dept.avg_salary >= 50000
                        ? "text-gray-700"
                        : "text-gray-500"
                    }`}
                  >
                    {formatCurrency(dept.avg_salary)}
                  </span>
                </td>
                <td className="px-3 py-1.5 text-right text-gray-600">
                  {dept.avg_tenure_years.toFixed(1)}y
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Note */}
      <div className="px-3 py-2 bg-gray-50 border-t border-gray-100 text-[10px] text-gray-500">
        Click headers to sort. Sales highlighted for Q3.
      </div>
    </div>
  );
}
