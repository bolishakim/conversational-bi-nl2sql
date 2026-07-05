"use client";

import { memo } from "react";
import type { EdgeStatus } from "./hooks/useWorkflowStream";

interface WorkflowEdgeProps {
  status: EdgeStatus;
  isCompact?: boolean;
  isRetryLoop?: boolean;
  isIterationLoop?: boolean;
}

// Edge status styles
const EDGE_STYLES: Record<EdgeStatus, { stroke: string; strokeWidth: number; dashArray?: string; animate?: boolean }> = {
  inactive: { stroke: "#D1D5DB", strokeWidth: 1, dashArray: "4,4" },
  pending: { stroke: "#9CA3AF", strokeWidth: 1.5 },
  active: { stroke: "#3B82F6", strokeWidth: 2, animate: true },
  completed: { stroke: "#10B981", strokeWidth: 2 },
  failed: { stroke: "#EF4444", strokeWidth: 2 },
  retry: { stroke: "#F59E0B", strokeWidth: 2, animate: true },
};

function WorkflowEdge({ status, isCompact = false, isRetryLoop = false, isIterationLoop = false }: WorkflowEdgeProps) {
  const styles = EDGE_STYLES[status];

  // Compact mode - simple line with arrow
  if (isCompact) {
    return (
      <div className="flex items-center px-1">
        <svg
          width="24"
          height="12"
          viewBox="0 0 24 12"
          className={styles.animate ? "animate-pulse" : ""}
        >
          {/* Line */}
          <line
            x1="0"
            y1="6"
            x2="18"
            y2="6"
            stroke={styles.stroke}
            strokeWidth={styles.strokeWidth}
            strokeDasharray={styles.dashArray}
            className={styles.animate ? "animate-flow" : ""}
          />
          {/* Arrow head */}
          <polygon
            points="18,3 24,6 18,9"
            fill={styles.stroke}
          />
        </svg>
      </div>
    );
  }

  // Expanded mode with curved paths for loops
  if (isRetryLoop || isIterationLoop) {
    return (
      <svg
        width="60"
        height="40"
        viewBox="0 0 60 40"
        className={`${styles.animate ? "animate-pulse" : ""} overflow-visible`}
      >
        {/* Curved path going back */}
        <path
          d="M 0 20 Q 30 -10 60 20"
          fill="none"
          stroke={styles.stroke}
          strokeWidth={styles.strokeWidth}
          strokeDasharray={styles.dashArray}
          className={styles.animate ? "animate-flow" : ""}
        />
        {/* Arrow head */}
        <polygon
          points="55,17 60,20 55,23"
          fill={styles.stroke}
          transform="rotate(15, 60, 20)"
        />
      </svg>
    );
  }

  // Standard expanded edge
  return (
    <svg
      width="40"
      height="20"
      viewBox="0 0 40 20"
      className={styles.animate ? "animate-pulse" : ""}
    >
      {/* Line */}
      <line
        x1="0"
        y1="10"
        x2="32"
        y2="10"
        stroke={styles.stroke}
        strokeWidth={styles.strokeWidth}
        strokeDasharray={styles.dashArray}
        className={styles.animate ? "animate-flow" : ""}
      />
      {/* Arrow head */}
      <polygon
        points="32,6 40,10 32,14"
        fill={styles.stroke}
      />
    </svg>
  );
}

export default memo(WorkflowEdge);
