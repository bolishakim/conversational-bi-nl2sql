"use client";

import dynamic from "next/dynamic";
import { useTaskComparison } from "@/lib/hooks/useAdminData";

const BarChart = dynamic(() => import("recharts").then((m) => m.BarChart), { ssr: false });
const Bar = dynamic(() => import("recharts").then((m) => m.Bar), { ssr: false });
const XAxis = dynamic(() => import("recharts").then((m) => m.XAxis), { ssr: false });
const YAxis = dynamic(() => import("recharts").then((m) => m.YAxis), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((m) => m.Tooltip), { ssr: false });
const Legend = dynamic(() => import("recharts").then((m) => m.Legend), { ssr: false });
const ResponsiveContainer = dynamic(() => import("recharts").then((m) => m.ResponsiveContainer), { ssr: false });

const CONTROL_COLOR = "#3b82f6";
const EXPERIMENTAL_COLOR = "#10b981";

export default function TaskComparisonTab() {
  const { data, loading, error } = useTaskComparison();

  if (loading) return <div className="p-6 text-center text-gray-500">Loading task comparison...</div>;
  if (error) return <div className="p-6 text-center text-red-500">{error}</div>;
  if (!data || data.tasks.length === 0) return <div className="p-6 text-center text-gray-500">No task data available</div>;

  // Build chart data arrays
  const durationData = data.tasks.map((t) => ({
    name: `Task ${t.task_number}`,
    Control: t.control.avg_duration ? Math.round(t.control.avg_duration) : 0,
    Experimental: t.experimental.avg_duration ? Math.round(t.experimental.avg_duration) : 0,
  }));

  const difficultyData = data.tasks.map((t) => ({
    name: `Task ${t.task_number}`,
    Control: t.control.avg_difficulty ?? 0,
    Experimental: t.experimental.avg_difficulty ?? 0,
  }));

  const confidenceData = data.tasks.map((t) => ({
    name: `Task ${t.task_number}`,
    Control: t.control.avg_confidence ?? 0,
    Experimental: t.experimental.avg_confidence ?? 0,
  }));

  const interactionsData = data.tasks.map((t) => ({
    name: `Task ${t.task_number}`,
    Control: t.control.avg_interactions ?? 0,
    Experimental: t.experimental.avg_interactions ?? 0,
  }));

  const qualityData = data.tasks.map((t) => ({
    name: `Task ${t.task_number}`,
    Control: t.control.avg_quality ?? 0,
    Experimental: t.experimental.avg_quality ?? 0,
  }));

  const charts = [
    { title: "Avg Duration (seconds)", data: durationData },
    { title: "Avg Difficulty Rating (1-5)", data: difficultyData },
    { title: "Avg Confidence Rating (1-5)", data: confidenceData },
    { title: "Avg Interactions", data: interactionsData },
    { title: "Avg Answer Quality", data: qualityData },
  ];

  return (
    <div className="space-y-6">
      {/* Overall summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <SummaryCard label="Control Avg Duration" value={data.overall.control_avg_duration ? `${Math.round(data.overall.control_avg_duration)}s` : "N/A"} />
        <SummaryCard label="Experimental Avg Duration" value={data.overall.experimental_avg_duration ? `${Math.round(data.overall.experimental_avg_duration)}s` : "N/A"} />
        <SummaryCard label="Control Avg Quality" value={data.overall.control_avg_quality?.toFixed(2) ?? "N/A"} />
        <SummaryCard label="Experimental Avg Quality" value={data.overall.experimental_avg_quality?.toFixed(2) ?? "N/A"} />
      </div>

      {/* Task details table */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 overflow-x-auto">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Task Details</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="pb-2 pr-4">Task</th>
              <th className="pb-2 pr-4">Domain</th>
              <th className="pb-2 pr-4">Complexity</th>
              <th className="pb-2 pr-4">Control (n)</th>
              <th className="pb-2 pr-4">Experimental (n)</th>
            </tr>
          </thead>
          <tbody>
            {data.tasks.map((t) => (
              <tr key={t.task_number} className="border-b border-gray-100">
                <td className="py-2 pr-4 font-medium">Task {t.task_number}</td>
                <td className="py-2 pr-4">{t.domain ?? "-"}</td>
                <td className="py-2 pr-4">{t.complexity_level ?? "-"}</td>
                <td className="py-2 pr-4">{t.control.completion_count}</td>
                <td className="py-2 pr-4">{t.experimental.completion_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Charts grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {charts.map((chart) => (
          <div key={chart.title} className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">{chart.title}</h3>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chart.data} barGap={2}>
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="Control" fill={CONTROL_COLOR} radius={[4, 4, 0, 0]} />
                <Bar dataKey="Experimental" fill={EXPERIMENTAL_COLOR} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-xl font-bold text-gray-900 mt-1">{value}</p>
    </div>
  );
}
