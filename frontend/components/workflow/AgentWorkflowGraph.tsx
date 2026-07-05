"use client";

import { useState, memo } from "react";
import { Hash, Zap, Coins } from "lucide-react";
import WorkflowCompact from "./WorkflowCompact";
import WorkflowNode from "./WorkflowNode";
import WorkflowEdge from "./WorkflowEdge";
import type { WorkflowState, EdgeStatus } from "./hooks/useWorkflowStream";

interface AgentWorkflowGraphProps {
  workflowState: WorkflowState;
  defaultExpanded?: boolean;
}

function AgentWorkflowGraph({ workflowState, defaultExpanded = false }: AgentWorkflowGraphProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const handleToggleExpand = () => {
    setIsExpanded((prev) => !prev);
  };

  // Get edge status with fallback
  const getEdgeStatus = (edgeId: string): EdgeStatus => {
    return workflowState.edges[edgeId] || "inactive";
  };

  // Check if workflow is completed (not active and has completed nodes)
  const isWorkflowCompleted = !workflowState.isActive &&
    Object.values(workflowState.nodes).some((n) => n.status === "completed");

  // Don't render if no workflow activity and not showing previous state
  const hasActivity = workflowState.isActive ||
    Object.values(workflowState.nodes).some((n) => n.status !== "idle");

  if (!hasActivity) {
    return null;
  }

  // Compact view
  if (!isExpanded) {
    return (
      <WorkflowCompact
        workflowState={workflowState}
        isExpanded={isExpanded}
        onToggleExpand={handleToggleExpand}
      />
    );
  }

  // Expanded view with full graph
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
      {/* Header (clickable to collapse) */}
      <div
        className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200 cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={handleToggleExpand}
      >
        <span className="text-sm font-medium text-gray-700">
          Agent Workflow (Expanded)
        </span>
        <span className="text-xs text-gray-500">Click to collapse</span>
      </div>

      {/* Full graph layout */}
      <div className="p-6 overflow-x-auto">
        <div className="min-w-[800px]">
          {/* Row 1: Main pipeline */}
          <div className="flex items-center justify-center gap-2 mb-8">
            {/* Start */}
            <div className="flex flex-col items-center">
              <div className="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center">
                <div className="w-3 h-3 rounded-full bg-white" />
              </div>
              <span className="text-xs text-gray-500 mt-1">Start</span>
            </div>

            <WorkflowEdge status={getEdgeStatus("start-orchestrator")} />

            {/* Orchestrator */}
            <WorkflowNode
              nodeId="orchestrator"
              state={workflowState.nodes.orchestrator || { status: "idle" }}
            />

            <WorkflowEdge status={getEdgeStatus("orchestrator-schema_agent")} />

            {/* Schema Agent */}
            <WorkflowNode
              nodeId="schema_agent"
              state={workflowState.nodes.schema_agent || { status: "idle" }}
            />

            <WorkflowEdge status={getEdgeStatus("schema_agent-sql_agent")} />

            {/* SQL Agent */}
            <WorkflowNode
              nodeId="sql_agent"
              state={workflowState.nodes.sql_agent || { status: "idle" }}
            />
          </div>

          {/* Row 2: Validation and Execution */}
          <div className="flex items-center justify-center gap-2 mb-8">
            <div className="w-[200px]" /> {/* Spacer */}

            {/* Validator with retry loop indicator */}
            <div className="relative">
              <WorkflowNode
                nodeId="validator"
                state={workflowState.nodes.validator || { status: "idle" }}
              />
              {/* Retry loop arrow (shown when retrying) */}
              {workflowState.retryCount > 0 && (
                <div className="absolute -top-8 left-1/2 transform -translate-x-1/2">
                  <div className="flex items-center gap-1 text-amber-600">
                    <svg width="60" height="30" viewBox="0 0 60 30">
                      <path
                        d="M 30 30 Q 30 0 0 15"
                        fill="none"
                        stroke="#F59E0B"
                        strokeWidth="2"
                        markerEnd="url(#arrowhead)"
                      />
                      <defs>
                        <marker
                          id="arrowhead"
                          markerWidth="10"
                          markerHeight="7"
                          refX="9"
                          refY="3.5"
                          orient="auto"
                        >
                          <polygon points="0 0, 10 3.5, 0 7" fill="#F59E0B" />
                        </marker>
                      </defs>
                    </svg>
                    <span className="text-xs">Retry</span>
                  </div>
                </div>
              )}
            </div>

            <WorkflowEdge status={getEdgeStatus("validator-executor")} />

            {/* Executor */}
            <WorkflowNode
              nodeId="executor"
              state={workflowState.nodes.executor || { status: "idle" }}
            />

            <WorkflowEdge status={getEdgeStatus("executor-viz_generator")} />

            {/* Viz Generator */}
            <WorkflowNode
              nodeId="viz_generator"
              state={workflowState.nodes.viz_generator || { status: "idle" }}
            />

            <WorkflowEdge status={getEdgeStatus("viz_generator-iteration_decision")} />

            {/* Analyst with iteration loop indicator */}
            <div className="relative">
              <WorkflowNode
                nodeId="iteration_decision"
                state={workflowState.nodes.iteration_decision || { status: "idle" }}
              />
              {/* Iteration loop arrow (shown when iterating) */}
              {workflowState.iterationCount > 0 && (
                <div className="absolute -top-8 left-1/2 transform -translate-x-1/2">
                  <div className="flex items-center gap-1 text-purple-600">
                    <svg width="80" height="30" viewBox="0 0 80 30">
                      <path
                        d="M 40 30 Q 40 0 0 15"
                        fill="none"
                        stroke="#8B5CF6"
                        strokeWidth="2"
                        markerEnd="url(#arrowhead2)"
                      />
                      <defs>
                        <marker
                          id="arrowhead2"
                          markerWidth="10"
                          markerHeight="7"
                          refX="9"
                          refY="3.5"
                          orient="auto"
                        >
                          <polygon points="0 0, 10 3.5, 0 7" fill="#8B5CF6" />
                        </marker>
                      </defs>
                    </svg>
                    <span className="text-xs">Iter {workflowState.iterationCount}</span>
                  </div>
                </div>
              )}
            </div>

            <WorkflowEdge status={getEdgeStatus("iteration_decision-end")} />

            {/* End */}
            <div className="flex flex-col items-center">
              <div
                className={`
                  w-10 h-10 rounded-full border-2 flex items-center justify-center
                  ${
                    isWorkflowCompleted
                      ? "bg-green-500 border-green-500"
                      : "bg-white border-gray-300"
                  }
                `}
              >
                {isWorkflowCompleted && (
                  <div className="w-3 h-3 rounded-full bg-white" />
                )}
              </div>
              <span className="text-xs text-gray-500 mt-1">End</span>
            </div>
          </div>

          {/* Legend */}
          <div className="mt-8 pt-4 border-t border-gray-100">
            <div className="flex items-center justify-center gap-6 text-xs text-gray-500">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-gray-300" />
                <span>Idle</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500 animate-pulse" />
                <span>Running</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span>Completed</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-amber-500" />
                <span>Retrying</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <span>Failed</span>
              </div>
            </div>
          </div>

          {/* Token Stats - shown when workflow is completed */}
          {workflowState.tokenStats && isWorkflowCompleted && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <div className="flex items-center justify-center gap-8 text-sm">
                <div className="flex items-center gap-2 text-gray-600">
                  <Hash className="w-4 h-4 text-blue-500" />
                  <span className="font-semibold">{workflowState.tokenStats.totalTokens.toLocaleString()}</span>
                  <span className="text-gray-400">tokens</span>
                </div>
                <div className="flex items-center gap-2 text-gray-600">
                  <Zap className="w-4 h-4 text-amber-500" />
                  <span className="font-semibold">{workflowState.tokenStats.llmCalls}</span>
                  <span className="text-gray-400">LLM calls</span>
                </div>
                <div className="flex items-center gap-2 text-gray-600">
                  <Coins className="w-4 h-4 text-green-500" />
                  <span className="font-semibold">${workflowState.tokenStats.totalCost.toFixed(4)}</span>
                  <span className="text-gray-400">cost</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default memo(AgentWorkflowGraph);
