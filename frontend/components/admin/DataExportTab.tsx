"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Download, FileJson, FileSpreadsheet, Loader2 } from "lucide-react";

const EXPORT_TABLES = [
  { key: "participants", label: "Participants", description: "Demographics, conditions, survey responses" },
  { key: "tasks", label: "Tasks", description: "Task performance, durations, quality scores" },
  { key: "interactions", label: "Interactions", description: "Dashboard and chatbot interaction logs" },
  { key: "queries", label: "Query History", description: "NL2SQL queries, tokens, costs, errors" },
];

function downloadFile(content: string, filename: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function jsonToCsv(data: any[]): string {
  if (!data || data.length === 0) return "";
  const headers = Object.keys(data[0]);
  const rows = data.map((row) =>
    headers.map((h) => {
      const val = row[h];
      if (val === null || val === undefined) return "";
      const str = typeof val === "object" ? JSON.stringify(val) : String(val);
      return str.includes(",") || str.includes('"') || str.includes("\n")
        ? `"${str.replace(/"/g, '""')}"`
        : str;
    }).join(",")
  );
  return [headers.join(","), ...rows].join("\n");
}

export default function DataExportTab() {
  const [loading, setLoading] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>(EXPORT_TABLES.map((t) => t.key));

  const toggleTable = (key: string) => {
    setSelected((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const handleExport = async (format: "json" | "csv") => {
    if (selected.length === 0) return;
    setLoading(format);
    try {
      const data = await api.getExportData(selected.join(","));
      const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, "-");

      if (format === "json") {
        downloadFile(JSON.stringify(data, null, 2), `experiment-export-${timestamp}.json`, "application/json");
      } else {
        // Export each table as separate CSV
        for (const table of selected) {
          const tableData = table === "queries" ? data.query_history : data[table as keyof typeof data];
          if (Array.isArray(tableData) && tableData.length > 0) {
            const csv = jsonToCsv(tableData);
            downloadFile(csv, `${table}-${timestamp}.csv`, "text/csv");
          }
        }
      }
    } catch (err: any) {
      console.error("Export failed:", err);
      alert(`Export failed: ${err.message}`);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Export Experiment Data</h2>
        <p className="text-sm text-gray-600 mb-6">
          Download raw experiment data for thesis analysis. Select the tables to include in the export.
        </p>

        {/* Table selection */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
          {EXPORT_TABLES.map((table) => (
            <label
              key={table.key}
              className={`flex items-start gap-3 p-4 rounded-lg border cursor-pointer transition-colors ${
                selected.includes(table.key) ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:bg-gray-50"
              }`}
            >
              <input
                type="checkbox"
                checked={selected.includes(table.key)}
                onChange={() => toggleTable(table.key)}
                className="mt-0.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <div>
                <p className="text-sm font-medium text-gray-900">{table.label}</p>
                <p className="text-xs text-gray-500">{table.description}</p>
              </div>
            </label>
          ))}
        </div>

        {/* Export buttons */}
        <div className="flex gap-3">
          <button
            onClick={() => handleExport("json")}
            disabled={loading !== null || selected.length === 0}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading === "json" ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileJson className="w-4 h-4" />}
            Export JSON
          </button>
          <button
            onClick={() => handleExport("csv")}
            disabled={loading !== null || selected.length === 0}
            className="flex items-center gap-2 px-5 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading === "csv" ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSpreadsheet className="w-4 h-4" />}
            Export CSV
          </button>
        </div>

        {selected.length === 0 && (
          <p className="text-sm text-amber-600 mt-3">Select at least one table to export.</p>
        )}
      </div>

      {/* Info card */}
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-2">Export Details</h3>
        <ul className="text-xs text-gray-500 space-y-1">
          <li><strong>JSON:</strong> Single file with all selected tables nested under keys</li>
          <li><strong>CSV:</strong> One file per table, flattened for spreadsheet compatibility</li>
          <li>Nested objects (JSON columns) are serialized as JSON strings in CSV</li>
          <li>All timestamps are in ISO 8601 format (UTC)</li>
        </ul>
      </div>
    </div>
  );
}
