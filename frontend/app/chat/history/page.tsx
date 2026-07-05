"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import type { QueryHistoryItem } from "@/types/history";
import AuthenticatedLayout from "@/components/AuthenticatedLayout";
import {
  Clock,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Trash2,
  BarChart3,
  Table,
  MessageSquare,
  Loader2,
} from "lucide-react";

// Dynamic import for Plotly (no SSR)
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

export default function HistoryPage() {
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.getHistory(100, 0);
      setHistory(response.queries || []);
    } catch (err: any) {
      setError(err.message || "Failed to load history");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (queryId: string) => {
    if (!confirm("Are you sure you want to delete this query from history?")) {
      return;
    }

    try {
      setDeletingId(queryId);
      await api.deleteHistoryItem(queryId);
      setHistory((prev) => prev.filter((item) => item.id !== queryId));
    } catch (err: any) {
      alert("Failed to delete: " + err.message);
    } finally {
      setDeletingId(null);
    }
  };

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return "-";
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <AuthenticatedLayout
      title="Query History"
      subtitle="View your past queries and responses"
    >
      <div className="flex flex-col h-full bg-gray-50 p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Clock className="w-6 h-6 text-gray-600" />
            <h2 className="text-lg font-semibold text-gray-800">
              Your Query History
            </h2>
            {!loading && (
              <span className="text-sm text-gray-500">
                ({history.length} queries)
              </span>
            )}
          </div>
          <button
            onClick={loadHistory}
            disabled={loading}
            className="px-3 py-1.5 text-sm bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Refresh
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-64 text-red-500">
              <XCircle className="w-12 h-12 mb-2" />
              <p>{error}</p>
              <button
                onClick={loadHistory}
                className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                Try Again
              </button>
            </div>
          ) : history.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-gray-500">
              <MessageSquare className="w-12 h-12 mb-2" />
              <p>No queries yet</p>
              <p className="text-sm mt-1">
                Start asking questions in the Query Assistant
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {history.map((item) => (
                <HistoryCard
                  key={item.id}
                  item={item}
                  isExpanded={expandedId === item.id}
                  isDeleting={deletingId === item.id}
                  onToggle={() => toggleExpand(item.id)}
                  onDelete={() => handleDelete(item.id)}
                  formatDate={formatDate}
                  formatDuration={formatDuration}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </AuthenticatedLayout>
  );
}

interface HistoryCardProps {
  item: QueryHistoryItem;
  isExpanded: boolean;
  isDeleting: boolean;
  onToggle: () => void;
  onDelete: () => void;
  formatDate: (date: string) => string;
  formatDuration: (ms?: number) => string;
}

function HistoryCard({
  item,
  isExpanded,
  isDeleting,
  onToggle,
  onDelete,
  formatDate,
  formatDuration,
}: HistoryCardProps) {
  const isSuccess = item.execution_status === "success" && !item.error_occurred;
  const isDirect = item.orchestrator_action === "DIRECT_ANSWER";

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
      {/* Header - Always visible */}
      <div
        className="flex items-start gap-3 p-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={onToggle}
      >
        {/* Status icon */}
        <div className="mt-0.5">
          {isSuccess ? (
            <CheckCircle2 className="w-5 h-5 text-green-500" />
          ) : (
            <XCircle className="w-5 h-5 text-red-500" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Query */}
          <p className="text-sm font-medium text-gray-800 line-clamp-2">
            {item.user_query}
          </p>

          {/* Meta info */}
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
            <span>{formatDate(item.created_at)}</span>
            {item.domain && (
              <span className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full">
                {item.domain}
              </span>
            )}
            {isDirect && (
              <span className="px-2 py-0.5 bg-purple-50 text-purple-600 rounded-full">
                Direct Answer
              </span>
            )}
            {item.chart_type && item.chart_type !== "table" && (
              <span className="flex items-center gap-1 px-2 py-0.5 bg-green-50 text-green-600 rounded-full">
                <BarChart3 className="w-3 h-3" />
                {item.chart_type}
              </span>
            )}
            {item.row_count !== undefined && item.row_count > 0 && (
              <span className="flex items-center gap-1">
                <Table className="w-3 h-3" />
                {item.row_count} rows
              </span>
            )}
            <span>{formatDuration(item.total_duration_ms)}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            disabled={isDeleting}
            className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
            title="Delete"
          >
            {isDeleting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Trash2 className="w-4 h-4" />
            )}
          </button>
          {isExpanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="border-t border-gray-100 p-4 bg-gray-50 space-y-4">
          {/* Agent Response / Analysis Summary */}
          {item.analysis?.summary && (
            <div>
              <h4 className="text-xs font-semibold text-blue-600 uppercase mb-2">
                Agent Response
              </h4>
              <div className="bg-white p-3 rounded-lg border border-blue-100">
                <p className="text-sm text-gray-700">{item.analysis.summary}</p>
              </div>
            </div>
          )}

          {/* Key Insights */}
          {item.analysis?.key_insights && item.analysis.key_insights.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                Key Insights
              </h4>
              <div className="space-y-2">
                {item.analysis.key_insights.map((insight, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <span className="text-blue-500 mt-0.5 flex-shrink-0 font-bold">•</span>
                    <span className="text-sm text-gray-700 leading-relaxed">{insight}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Data Quality Notes */}
          {item.analysis?.data_quality_notes && item.analysis.data_quality_notes.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-amber-600 uppercase mb-2">
                Data Quality Notes
              </h4>
              <div className="bg-amber-50 border border-amber-100 rounded-lg p-3 space-y-2">
                {item.analysis.data_quality_notes.map((note, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <span className="text-amber-500 mt-0.5 flex-shrink-0 font-bold">•</span>
                    <span className="text-sm text-amber-800 leading-relaxed">{note}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Visualization */}
          {item.chart_config && item.chart_config.data && item.chart_config.data.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-green-600 uppercase mb-2">
                Visualization
              </h4>
              <div className="bg-white p-3 rounded-lg border border-green-100">
                <Plot
                  data={item.chart_config.data}
                  layout={{
                    ...item.chart_config.layout,
                    autosize: true,
                    margin: { l: 50, r: 20, t: 40, b: 40 },
                    height: 350,
                  }}
                  config={{
                    responsive: true,
                    displayModeBar: false,
                    ...item.chart_config.config,
                  }}
                  style={{ width: "100%", height: "350px" }}
                />
              </div>
            </div>
          )}

          {/* SQL Query */}
          {item.generated_sql && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                SQL Query
              </h4>
              <pre className="text-xs bg-gray-800 text-green-400 p-3 rounded-lg overflow-x-auto">
                {item.generated_sql}
              </pre>
            </div>
          )}

          {/* Execution Error */}
          {item.execution_error && (
            <div>
              <h4 className="text-xs font-semibold text-red-500 uppercase mb-2">
                Error
              </h4>
              <p className="text-sm text-red-600 bg-red-50 p-3 rounded-lg">
                {item.execution_error}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
