"use client";

import dynamic from "next/dynamic";
import { Cell } from "recharts";
import { useChatbotAnalytics } from "@/lib/hooks/useAdminData";
import { Bot, Zap, DollarSign, Clock, CheckCircle, Users } from "lucide-react";

const BarChart = dynamic(() => import("recharts").then((m) => m.BarChart), { ssr: false });
const Bar = dynamic(() => import("recharts").then((m) => m.Bar), { ssr: false });
const PieChart = dynamic(() => import("recharts").then((m) => m.PieChart), { ssr: false });
const Pie = dynamic(() => import("recharts").then((m) => m.Pie), { ssr: false });
const LineChart = dynamic(() => import("recharts").then((m) => m.LineChart), { ssr: false });
const Line = dynamic(() => import("recharts").then((m) => m.Line), { ssr: false });
const XAxis = dynamic(() => import("recharts").then((m) => m.XAxis), { ssr: false });
const YAxis = dynamic(() => import("recharts").then((m) => m.YAxis), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((m) => m.Tooltip), { ssr: false });
const Legend = dynamic(() => import("recharts").then((m) => m.Legend), { ssr: false });
const ResponsiveContainer = dynamic(() => import("recharts").then((m) => m.ResponsiveContainer), { ssr: false });

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];

export default function ChatbotAnalyticsTab() {
  const { data, loading, error } = useChatbotAnalytics();

  if (loading) return <div className="p-6 text-center text-gray-500">Loading chatbot analytics...</div>;
  if (error) return <div className="p-6 text-center text-red-500">{error}</div>;
  if (!data) return <div className="p-6 text-center text-gray-500">No chatbot data available</div>;

  const kpis = [
    { label: "Total Queries", value: data.total_queries, icon: Bot },
    { label: "Success Rate", value: `${data.success_rate_percent}%`, icon: CheckCircle },
    { label: "Avg Execution Time", value: data.avg_execution_time_ms ? `${data.avg_execution_time_ms}ms` : "N/A", icon: Clock },
    { label: "Total Tokens", value: data.total_tokens.toLocaleString(), icon: Zap },
    { label: "Total Cost", value: `$${data.total_cost_usd.toFixed(4)}`, icon: DollarSign },
    { label: "Avg Queries/Participant", value: data.avg_queries_per_participant, icon: Users },
  ];

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-medium text-gray-600">{kpi.label}</h3>
              <kpi.icon className="w-4 h-4 text-gray-400" />
            </div>
            <p className="text-xl font-bold text-gray-900">{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Queries Over Time */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Queries Over Time</h3>
          {data.queries_over_time.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={data.queries_over_time}>
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip />
                <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-12">No data yet</p>
          )}
        </div>

        {/* Domain Breakdown */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Domain Breakdown</h3>
          {data.domain_breakdown.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={data.domain_breakdown} dataKey="count" nameKey="domain" cx="50%" cy="50%" outerRadius={100} label={({ name, value }: any) => `${name} (${value})`}>
                  {data.domain_breakdown.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-12">No data yet</p>
          )}
        </div>

        {/* Token Usage by Participant */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Token Usage by Participant</h3>
          {data.token_usage_by_participant.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.token_usage_by_participant}>
                <XAxis dataKey="participant_code" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(value: any) => Number(value).toLocaleString()} />
                <Bar dataKey="total_tokens" name="Tokens" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-12">No data yet</p>
          )}
        </div>

        {/* Error Stages */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Error Stages</h3>
          {data.error_stages.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.error_stages} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
                <YAxis dataKey="stage" type="category" tick={{ fontSize: 11 }} width={100} />
                <Tooltip />
                <Bar dataKey="count" fill="#ef4444" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-12">No errors recorded</p>
          )}
        </div>
      </div>

      {/* Cost table */}
      {data.token_usage_by_participant.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4 overflow-x-auto">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Cost Breakdown by Participant</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-2 pr-4">Participant</th>
                <th className="pb-2 pr-4">Queries</th>
                <th className="pb-2 pr-4">Total Tokens</th>
                <th className="pb-2 pr-4">Total Cost</th>
              </tr>
            </thead>
            <tbody>
              {data.token_usage_by_participant.map((p) => (
                <tr key={p.participant_code} className="border-b border-gray-100">
                  <td className="py-2 pr-4 font-medium">{p.participant_code}</td>
                  <td className="py-2 pr-4">{p.query_count}</td>
                  <td className="py-2 pr-4">{p.total_tokens.toLocaleString()}</td>
                  <td className="py-2 pr-4">${p.total_cost.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
