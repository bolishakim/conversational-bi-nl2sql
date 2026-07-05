"use client";

import { memo, useMemo } from "react";
import { ChevronDown, ChevronUp, RefreshCw, AlertCircle, CheckCircle2 } from "lucide-react";
import WorkflowNode from "./WorkflowNode";
import WorkflowEdge from "./WorkflowEdge";
import type { WorkflowState, EdgeStatus } from "./hooks/useWorkflowStream";

interface WorkflowCompactProps {
  workflowState: WorkflowState;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}

// Main workflow nodes to display (simplified for compact view)
const MAIN_NODES = [
  "orchestrator",
  "schema_agent",
  "sql_agent",
  "validator",
  "executor",
  "viz_generator",
  "iteration_decision",
];

// Edge mappings for compact view
const COMPACT_EDGES: { from: string; to: string; edgeId: string }[] = [
  { from: "start", to: "orchestrator", edgeId: "start-orchestrator" },
  { from: "orchestrator", to: "schema_agent", edgeId: "orchestrator-schema_agent" },
  { from: "schema_agent", to: "sql_agent", edgeId: "schema_agent-sql_agent" },
  { from: "sql_agent", to: "validator", edgeId: "sql_agent-validator" },
  { from: "validator", to: "executor", edgeId: "validator-executor" },
  { from: "executor", to: "viz_generator", edgeId: "executor-viz_generator" },
  { from: "viz_generator", to: "iteration_decision", edgeId: "viz_generator-iteration_decision" },
];

function WorkflowCompact({ workflowState, isExpanded = false, onToggleExpand }: WorkflowCompactProps) {
  const { nodes, edges, isActive, retryCount, iterationCount, error } = workflowState;

  // Calculate overall status
  const overallStatus = useMemo(() => {
    if (error) return "error";
    if (!isActive && Object.values(nodes).some((n) => n.status === "completed")) {
      return "completed";
    }
    if (isActive) return "running";
    return "idle";
  }, [nodes, isActive, error]);

  // Get edge status with fallback
  const getEdgeStatus = (edgeId: string): EdgeStatus => {
    return edges[edgeId] || "inactive";
  };

  // Status summary text
  const statusText = useMemo(() => {
    if (error) return `Error: ${error}`;
    if (overallStatus === "completed") {
      // Count only user-facing agents (exclude accumulate_results which is internal)
      const userFacingAgents = ["orchestrator", "schema_agent", "sql_agent", "validator", "executor", "viz_generator", "iteration_decision"];
      const completedCount = Object.entries(nodes).filter(
        ([nodeId, n]) => n.status === "completed" && userFacingAgents.includes(nodeId)
      ).length;
      let text = `Completed (${completedCount} agent${completedCount !== 1 ? "s" : ""})`;
      if (retryCount > 0) text += ` - ${retryCount} retries`;
      if (iterationCount > 0) text += ` - ${iterationCount} iterations`;
      return text;
    }
    if (overallStatus === "running") {
      const currentNode = Object.entries(nodes).find(([, n]) => n.status === "running");
      if (currentNode) {
        return `Running: ${currentNode[0].replace("_", " ")}...`;
      }
      return "Processing...";
    }
    return "Ready";
  }, [nodes, overallStatus, error, retryCount, iterationCount]);

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200 cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={onToggleExpand}
      >
        <div className="flex items-center gap-3">
          {/* Status indicator */}
          <div className="flex items-center gap-2">
            {overallStatus === "running" && (
              <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />
            )}
            {overallStatus === "completed" && (
              <CheckCircle2 className="w-4 h-4 text-green-500" />
            )}
            {overallStatus === "error" && (
              <AlertCircle className="w-4 h-4 text-red-500" />
            )}
            {overallStatus === "idle" && (
              <div className="w-4 h-4 rounded-full border-2 border-gray-300" />
            )}
          </div>

          <span className="text-sm font-medium text-gray-700">
            Agent Workflow
          </span>

          {/* Status badge */}
          <span
            className={`
              text-xs px-2 py-0.5 rounded-full
              ${overallStatus === "running" ? "bg-blue-100 text-blue-700" : ""}
              ${overallStatus === "completed" ? "bg-green-100 text-green-700" : ""}
              ${overallStatus === "error" ? "bg-red-100 text-red-700" : ""}
              ${overallStatus === "idle" ? "bg-gray-100 text-gray-600" : ""}
            `}
          >
            {statusText}
          </span>

          {/* Retry/Iteration badges */}
          {retryCount > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
              {retryCount} retry{retryCount > 1 ? "ies" : ""}
            </span>
          )}
          {iterationCount > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700">
              {iterationCount} iter{iterationCount > 1 ? "s" : ""}
            </span>
          )}
        </div>

        {/* Expand/collapse button */}
        <button className="p-1 hover:bg-gray-200 rounded transition-colors">
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          )}
        </button>
      </div>

      {/* Workflow visualization */}
      <div className="px-4 py-3">
        <div className="flex items-center justify-center gap-0 overflow-x-auto">
          {/* Start node indicator */}
          <div className="flex flex-col items-center gap-1">
            <div
              className={`
                w-6 h-6 rounded-full flex items-center justify-center
                ${isActive || overallStatus === "completed" ? "bg-green-500" : "bg-gray-300"}
              `}
            >
              <div className="w-2 h-2 rounded-full bg-white" />
            </div>
            <span className="text-[10px] text-gray-400">Start</span>
          </div>

          {/* First edge */}
          <WorkflowEdge status={getEdgeStatus("start-orchestrator")} isCompact />

          {/* Main workflow nodes */}
          {MAIN_NODES.map((nodeId, index) => (
            <div key={nodeId} className="flex items-center">
              <WorkflowNode
                nodeId={nodeId}
                state={nodes[nodeId] || { status: "idle" }}
                isCompact
                showLabel
              />

              {/* Edge to next node (except for last) */}
              {index < MAIN_NODES.length - 1 && (
                <WorkflowEdge
                  status={getEdgeStatus(COMPACT_EDGES[index + 1]?.edgeId || "inactive")}
                  isCompact
                />
              )}
            </div>
          ))}

          {/* Final edge to end */}
          <WorkflowEdge status={getEdgeStatus("iteration_decision-end")} isCompact />

          {/* End node indicator */}
          <div className="flex flex-col items-center gap-1">
            <div
              className={`
                w-6 h-6 rounded-full flex items-center justify-center border-2
                ${overallStatus === "completed" ? "bg-green-500 border-green-500" : "bg-white border-gray-300"}
              `}
            >
              {overallStatus === "completed" && (
                <CheckCircle2 className="w-4 h-4 text-white" />
              )}
            </div>
            <span className="text-[10px] text-gray-400">End</span>
          </div>
        </div>

        {/* Retry loop indicator */}
        {retryCount > 0 && (
          <div className="mt-2 flex items-center justify-center">
            <div className="flex items-center gap-2 text-xs text-amber-600">
              <RefreshCw className="w-3 h-3" />
              <span>Validation retry loop active</span>
            </div>
          </div>
        )}

        {/* Iteration loop indicator */}
        {iterationCount > 0 && (
          <div className="mt-2 flex items-center justify-center">
            <div className="flex items-center gap-2 text-xs text-purple-600">
              <RefreshCw className="w-3 h-3" />
              <span>Multi-query iteration {iterationCount}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default memo(WorkflowCompact);
