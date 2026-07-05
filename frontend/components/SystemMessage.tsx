"use client";

import type { Message } from "@/types/message";
import dynamic from "next/dynamic";
import ReactMarkdown from "react-markdown";
import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

// Dynamically import Plotly to avoid SSR issues
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

// Custom markdown components for styling
const markdownComponents = {
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="text-sm text-gray-700 mb-2 last:mb-0 leading-relaxed">{children}</p>
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="font-semibold text-gray-900">{children}</strong>
  ),
  em: ({ children }: { children?: React.ReactNode }) => (
    <em className="italic text-gray-600">{children}</em>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className="space-y-2 mb-3">{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol className="space-y-2 mb-3">{children}</ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => (
    <li className="text-sm text-gray-700 flex items-start gap-2 leading-relaxed">
      <span className="text-blue-500 mt-1 flex-shrink-0">•</span>
      <span className="flex-1">{children}</span>
    </li>
  ),
  code: ({ children }: { children?: React.ReactNode }) => (
    <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono text-gray-800">{children}</code>
  ),
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h1 className="text-lg font-bold text-gray-900 mb-2">{children}</h1>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h2 className="text-base font-semibold text-gray-900 mb-2">{children}</h2>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="text-sm font-semibold text-gray-900 mb-1">{children}</h3>
  ),
};

interface SystemMessageProps {
  message: Message;
}

export default function SystemMessage({ message }: SystemMessageProps) {
  const [showSql, setShowSql] = useState(false);

  // Check if this is a content-only message (no structured data)
  const isContentOnly =
    !message.error &&
    !message.sqlQuery &&
    !message.results &&
    !message.chart &&
    !message.analysis;

  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[85%]">
        <div className="bg-white border border-border rounded-lg p-4 shadow-sm">
          {/* Error Display */}
          {message.error && (
            <div className="mb-4">
              <h4 className="text-xs font-semibold text-red-500 uppercase mb-2">
                Error
              </h4>
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                <p className="text-sm">{message.error}</p>
              </div>
            </div>
          )}

          {/* SQL Query Display - Collapsible, Dark Theme */}
          {message.sqlQuery && (
            <div className="mb-4">
              <button
                onClick={() => setShowSql(!showSql)}
                className="flex items-center gap-2 text-xs font-semibold text-gray-500 uppercase hover:text-gray-700 transition-colors mb-2 group"
              >
                {showSql ? (
                  <ChevronDown className="w-4 h-4 text-gray-400 group-hover:text-gray-600" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600" />
                )}
                <span>SQL Query {showSql ? "(click to hide)" : "(click to view)"}</span>
              </button>
              {showSql && (
                <pre className="text-xs bg-gray-800 text-green-400 p-3 rounded-lg overflow-x-auto">
                  {message.sqlQuery}
                </pre>
              )}
            </div>
          )}

          {/* Results Table */}
          {message.results && message.results.data.length > 0 && (
            <div className="mb-4">
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                Results
                <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 normal-case">
                  {message.results.row_count} rows
                </span>
              </h4>
              <div className="overflow-x-auto">
                <table className="min-w-full border border-gray-200 rounded-lg text-xs">
                  <thead className="bg-gray-50">
                    <tr>
                      {message.results.columns.map((col, idx) => (
                        <th
                          key={idx}
                          className="px-3 py-2 text-left font-semibold text-gray-700 border-b border-gray-200"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {message.results.data.slice(0, 10).map((row, rowIdx) => (
                      <tr
                        key={rowIdx}
                        className={rowIdx % 2 === 0 ? "bg-white" : "bg-gray-50"}
                      >
                        {row.map((cell, cellIdx) => (
                          <td
                            key={cellIdx}
                            className="px-3 py-2 text-gray-800 border-b border-gray-200"
                          >
                            {cell !== null && cell !== undefined
                              ? String(cell)
                              : "—"}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {message.results.row_count > 10 && (
                <p className="text-xs text-gray-500 mt-2">
                  Showing first 10 of {message.results.row_count} rows
                </p>
              )}
            </div>
          )}

          {/* Chart Display */}
          {message.chart && (
            <div className="mb-4">
              <h4 className="text-xs font-semibold text-green-600 uppercase mb-2">
                Visualization
              </h4>
              <div className="bg-white p-3 rounded-lg border border-green-100">
                <Plot
                  data={message.chart.data}
                  layout={{
                    ...message.chart.layout,
                    autosize: true,
                    margin: { l: 50, r: 20, t: 40, b: 40 },
                  }}
                  config={{
                    responsive: true,
                    displayModeBar: false,
                    ...message.chart.config,
                  }}
                  style={{ width: "100%", height: "400px" }}
                />
              </div>
            </div>
          )}

          {/* Analysis */}
          {message.analysis && (
            <div className="space-y-4">
              {/* Summary */}
              {message.analysis.summary && (
                <div>
                  <h4 className="text-xs font-semibold text-blue-600 uppercase mb-2">
                    Summary
                  </h4>
                  <div className="bg-white p-3 rounded-lg border border-blue-100">
                    <div className="text-sm text-gray-700 prose prose-sm max-w-none">
                      <ReactMarkdown components={markdownComponents}>
                        {message.analysis.summary}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              )}

              {/* Key Insights */}
              {message.analysis.key_insights && message.analysis.key_insights.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                    Key Insights
                  </h4>
                  <div className="space-y-2">
                    {message.analysis.key_insights.map((insight, idx) => (
                      <div key={idx} className="flex items-start gap-2">
                        <span className="text-blue-500 mt-1 flex-shrink-0 font-bold">•</span>
                        <div className="flex-1 text-sm text-gray-700 leading-relaxed">
                          <ReactMarkdown components={markdownComponents}>
                            {insight}
                          </ReactMarkdown>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Data Quality Notes */}
              {message.analysis.data_quality_notes && message.analysis.data_quality_notes.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-amber-600 uppercase mb-2">
                    Data Quality Notes
                  </h4>
                  <div className="bg-amber-50 border border-amber-100 rounded-lg p-3 space-y-2">
                    {message.analysis.data_quality_notes.map((note, idx) => (
                      <div key={idx} className="flex items-start gap-2">
                        <span className="text-amber-500 mt-1 flex-shrink-0 font-bold">•</span>
                        <div className="flex-1 text-sm text-amber-800 leading-relaxed">
                          <ReactMarkdown components={markdownComponents}>
                            {note}
                          </ReactMarkdown>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Fallback Content - Blue bordered card */}
          {isContentOnly && (
            <div>
              <h4 className="text-xs font-semibold text-blue-600 uppercase mb-2">
                Agent Response
              </h4>
              <div className="bg-white p-3 rounded-lg border border-blue-100">
                <p className="text-sm text-gray-700">{message.content}</p>
              </div>
            </div>
          )}
        </div>

        <p className="text-xs text-gray-500 mt-1">
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
    </div>
  );
}
