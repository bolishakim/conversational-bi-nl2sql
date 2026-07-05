"use client";

import { memo } from "react";
import {
  Brain,
  Database,
  Code,
  Shield,
  Play,
  BarChart3,
  Layers,
  GitBranch,
  Check,
  X,
  RefreshCw,
  Loader2,
  Minus,
} from "lucide-react";
import type { NodeStatus, NodeState } from "./hooks/useWorkflowStream";

interface WorkflowNodeProps {
  nodeId: string;
  state: NodeState;
  isCompact?: boolean;
  showLabel?: boolean;
}

// Node configuration with icons and labels
const NODE_CONFIG: Record<string, { icon: typeof Brain; label: string; shortLabel: string }> = {
  orchestrator: { icon: Brain, label: "Orchestrator", shortLabel: "Orch" },
  schema_agent: { icon: Database, label: "Schema Agent", shortLabel: "Schema" },
  sql_agent: { icon: Code, label: "SQL Agent", shortLabel: "SQL" },
  validator: { icon: Shield, label: "Validator", shortLabel: "Valid" },
  executor: { icon: Play, label: "Executor", shortLabel: "Exec" },
  viz_generator: { icon: BarChart3, label: "Viz Generator", shortLabel: "Viz" },
  accumulate_results: { icon: Layers, label: "Accumulate", shortLabel: "Accum" },
  iteration_decision: { icon: GitBranch, label: "Analyst", shortLabel: "Analyst" },
};

// Status colors and styles
const STATUS_STYLES: Record<NodeStatus, { bg: string; border: string; text: string; ring?: string }> = {
  idle: { bg: "bg-gray-100", border: "border-gray-300", text: "text-gray-400" },
  running: { bg: "bg-blue-100", border: "border-blue-500", text: "text-blue-600", ring: "ring-2 ring-blue-300" },
  completed: { bg: "bg-green-100", border: "border-green-500", text: "text-green-600" },
  failed: { bg: "bg-red-100", border: "border-red-500", text: "text-red-600" },
  skipped: { bg: "bg-gray-50", border: "border-gray-200", text: "text-gray-300" },
  retrying: { bg: "bg-amber-100", border: "border-amber-500", text: "text-amber-600", ring: "ring-2 ring-amber-300" },
};

// Status indicator icons
const StatusIcon = ({ status }: { status: NodeStatus }) => {
  switch (status) {
    case "completed":
      return <Check className="w-3 h-3" />;
    case "failed":
      return <X className="w-3 h-3" />;
    case "retrying":
      return <RefreshCw className="w-3 h-3 animate-spin" />;
    case "running":
      return <Loader2 className="w-3 h-3 animate-spin" />;
    case "skipped":
      return <Minus className="w-3 h-3" />;
    default:
      return null;
  }
};

function WorkflowNode({ nodeId, state, isCompact = false, showLabel = true }: WorkflowNodeProps) {
  const config = NODE_CONFIG[nodeId];
  if (!config) return null;

  const Icon = config.icon;
  const styles = STATUS_STYLES[state.status];
  const isAnimating = state.status === "running" || state.status === "retrying";

  // Compact mode (32px nodes)
  if (isCompact) {
    return (
      <div className="flex flex-col items-center gap-1">
        <div
          className={`
            relative w-8 h-8 rounded-full flex items-center justify-center
            border-2 transition-all duration-300
            ${styles.bg} ${styles.border} ${styles.ring || ""}
            ${isAnimating ? "animate-pulse" : ""}
          `}
          title={`${config.label}: ${state.status}${state.message ? ` - ${state.message}` : ""}`}
        >
          <Icon className={`w-4 h-4 ${styles.text}`} />

          {/* Status badge */}
          {state.status !== "idle" && (
            <div
              className={`
                absolute -bottom-1 -right-1 w-4 h-4 rounded-full
                flex items-center justify-center
                ${state.status === "completed" ? "bg-green-500 text-white" : ""}
                ${state.status === "failed" ? "bg-red-500 text-white" : ""}
                ${state.status === "running" ? "bg-blue-500 text-white" : ""}
                ${state.status === "retrying" ? "bg-amber-500 text-white" : ""}
              `}
            >
              <StatusIcon status={state.status} />
            </div>
          )}
        </div>

        {showLabel && (
          <span className={`text-[10px] font-medium ${styles.text}`}>
            {config.shortLabel}
          </span>
        )}
      </div>
    );
  }

  // Expanded mode (larger nodes with more detail)
  return (
    <div
      className={`
        relative p-3 rounded-lg border-2 transition-all duration-300 min-w-[120px]
        ${styles.bg} ${styles.border} ${styles.ring || ""}
        ${isAnimating ? "animate-pulse" : ""}
      `}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-1">
        <Icon className={`w-5 h-5 ${styles.text}`} />
        <span className={`text-sm font-semibold ${styles.text}`}>
          {config.label}
        </span>
      </div>

      {/* Status */}
      <div className="flex items-center gap-1 text-xs">
        <StatusIcon status={state.status} />
        <span className={`capitalize ${styles.text}`}>{state.status}</span>
      </div>

      {/* Message (if any) */}
      {state.message && (
        <p className="mt-1 text-xs text-gray-600 truncate max-w-[150px]" title={state.message}>
          {state.message}
        </p>
      )}

      {/* Duration (if completed) */}
      {state.duration && (
        <p className="mt-1 text-xs text-gray-400">
          {state.duration}ms
        </p>
      )}
    </div>
  );
}

export default memo(WorkflowNode);
