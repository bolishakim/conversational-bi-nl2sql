"use client";

import { useState, useCallback, useRef } from "react";

// Node status types
export type NodeStatus = "idle" | "running" | "completed" | "failed" | "skipped" | "retrying";

// Edge status types
export type EdgeStatus = "inactive" | "pending" | "active" | "completed" | "failed" | "retry";

// Node state interface
export interface NodeState {
  status: NodeStatus;
  startTime?: number;
  endTime?: number;
  duration?: number;
  message?: string;
  details?: Record<string, unknown>;
}

// Token usage stats
export interface TokenStats {
  totalTokens: number;
  inputTokens: number;
  outputTokens: number;
  totalCost: number;
  llmCalls: number;
}

// Workflow state interface
export interface WorkflowState {
  isActive: boolean;
  currentNode: string | null;
  nodes: Record<string, NodeState>;
  edges: Record<string, EdgeStatus>;
  retryCount: number;
  iterationCount: number;
  error?: string;
  startTime?: number;
  endTime?: number;
  tokenStats?: TokenStats;
}

// SSE Event interface
export interface WorkflowEvent {
  type: "start" | "progress" | "result" | "error";
  stage?: string;
  status?: string;
  message?: string;
  query?: string;
  details?: Record<string, unknown>;
  data?: unknown;
}

// Define workflow nodes in order
export const WORKFLOW_NODES = [
  "orchestrator",
  "schema_agent",
  "sql_agent",
  "validator",
  "executor",
  "viz_generator",
  "accumulate_results",
  "iteration_decision",
] as const;

// Define edges between nodes
export const WORKFLOW_EDGES = [
  "start-orchestrator",
  "orchestrator-schema_agent",
  "orchestrator-end", // Direct answer path
  "schema_agent-sql_agent",
  "sql_agent-validator",
  "validator-sql_agent", // Retry loop
  "validator-executor",
  "executor-viz_generator",
  "viz_generator-accumulate_results",
  "accumulate_results-iteration_decision",
  "iteration_decision-sql_agent", // Iteration loop
  "iteration_decision-end",
] as const;

// Initial workflow state
const createInitialState = (): WorkflowState => ({
  isActive: false,
  currentNode: null,
  nodes: Object.fromEntries(
    WORKFLOW_NODES.map((node) => [node, { status: "idle" as NodeStatus }])
  ),
  edges: Object.fromEntries(
    WORKFLOW_EDGES.map((edge) => [edge, "inactive" as EdgeStatus])
  ),
  retryCount: 0,
  iterationCount: 0,
});

// Hook return type
interface UseWorkflowStreamReturn {
  workflowState: WorkflowState;
  startStream: (query: string, token: string) => Promise<unknown>;
  resetWorkflow: () => void;
  isStreaming: boolean;
}

export function useWorkflowStream(): UseWorkflowStreamReturn {
  const [workflowState, setWorkflowState] = useState<WorkflowState>(createInitialState());
  const [isStreaming, setIsStreaming] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Reset workflow to initial state
  const resetWorkflow = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setWorkflowState(createInitialState());
    setIsStreaming(false);
  }, []);

  // Update node state
  const updateNode = useCallback((nodeId: string, updates: Partial<NodeState>) => {
    setWorkflowState((prev) => ({
      ...prev,
      nodes: {
        ...prev.nodes,
        [nodeId]: {
          ...prev.nodes[nodeId],
          ...updates,
        },
      },
    }));
  }, []);

  // Update edge state
  const updateEdge = useCallback((edgeId: string, status: EdgeStatus) => {
    setWorkflowState((prev) => ({
      ...prev,
      edges: {
        ...prev.edges,
        [edgeId]: status,
      },
    }));
  }, []);

  // Get the previous node in the workflow
  const getPreviousNode = (currentNode: string): string | null => {
    const nodeIndex = WORKFLOW_NODES.indexOf(currentNode as typeof WORKFLOW_NODES[number]);
    if (nodeIndex <= 0) return null;
    return WORKFLOW_NODES[nodeIndex - 1];
  };

  // Process workflow event
  const processEvent = useCallback((event: WorkflowEvent) => {
    const { type, stage, status, message, details } = event;

    if (type === "start") {
      setWorkflowState((prev) => ({
        ...prev,
        isActive: true,
        startTime: Date.now(),
        currentNode: "orchestrator",
      }));
      updateNode("orchestrator", { status: "running", startTime: Date.now() });
      updateEdge("start-orchestrator", "active");
      return;
    }

    if (type === "progress" && stage) {
      const nodeId = stage;
      const now = Date.now();

      // Handle completion status
      if (status === "completed") {
        updateNode(nodeId, {
          status: "completed",
          endTime: now,
          message,
          details,
        });

        // Update edge to completed
        const prevNode = getPreviousNode(nodeId);
        if (prevNode) {
          updateEdge(`${prevNode}-${nodeId}`, "completed");
        } else if (nodeId === "orchestrator") {
          updateEdge("start-orchestrator", "completed");
        }

        // Determine next node and set it as running
        const nodeIndex = WORKFLOW_NODES.indexOf(nodeId as typeof WORKFLOW_NODES[number]);
        if (nodeIndex >= 0 && nodeIndex < WORKFLOW_NODES.length - 1) {
          // Check for special routing
          if (nodeId === "orchestrator" && details?.action === "DIRECT_ANSWER") {
            // Direct answer - skip to end
            updateEdge("orchestrator-end", "completed");
            setWorkflowState((prev) => ({
              ...prev,
              currentNode: null,
              isActive: false,
            }));
          } else {
            const nextNode = WORKFLOW_NODES[nodeIndex + 1];
            updateNode(nextNode, { status: "running", startTime: now });
            updateEdge(`${nodeId}-${nextNode}`, "active");
            setWorkflowState((prev) => ({
              ...prev,
              currentNode: nextNode,
            }));
          }
        }
      }

      // Handle retrying status (validator failed)
      if (status === "retrying") {
        updateNode(nodeId, {
          status: "retrying",
          message,
          details,
        });
        // Mark retry edge
        updateEdge("validator-sql_agent", "retry");
        // SQL agent should start again
        updateNode("sql_agent", { status: "running", startTime: now });
        setWorkflowState((prev) => ({
          ...prev,
          currentNode: "sql_agent",
          retryCount: (details?.retry_attempt as number) || prev.retryCount + 1,
        }));
      }

      // Handle needs_followup status (iteration decision)
      if (status === "needs_followup") {
        updateNode(nodeId, {
          status: "completed",
          endTime: now,
          message,
          details,
        });
        // Mark iteration edge
        updateEdge("iteration_decision-sql_agent", "active");
        // SQL agent should start again for new iteration
        updateNode("sql_agent", { status: "running", startTime: now });
        setWorkflowState((prev) => ({
          ...prev,
          currentNode: "sql_agent",
          iterationCount: (details?.iteration as number) || prev.iterationCount + 1,
        }));
      }

      // Handle failed status
      if (status === "failed") {
        updateNode(nodeId, {
          status: "failed",
          endTime: now,
          message,
          details,
        });
        setWorkflowState((prev) => ({
          ...prev,
          currentNode: null,
          error: message,
        }));
      }
    }

    if (type === "progress" && stage === "complete") {
      // Mark final edge as completed
      updateEdge("iteration_decision-end", "completed");
      setWorkflowState((prev) => ({
        ...prev,
        isActive: false,
        currentNode: null,
        endTime: Date.now(),
      }));
    }

    if (type === "error") {
      setWorkflowState((prev) => ({
        ...prev,
        isActive: false,
        currentNode: null,
        error: message,
        endTime: Date.now(),
      }));
    }
  }, [updateNode, updateEdge]);

  // Start streaming query
  const startStream = useCallback(async (query: string, token: string): Promise<unknown> => {
    // Reset state
    resetWorkflow();
    setIsStreaming(true);

    // Create abort controller
    abortControllerRef.current = new AbortController();

    return new Promise((resolve, reject) => {
      const eventSource = new EventSource(
        `http://localhost:8000/api/v1/query/stream?query=${encodeURIComponent(query)}`,
        // Note: EventSource doesn't support custom headers, so we'll use fetch instead
      );

      // Use fetch with streaming for better header support
      fetch("http://localhost:8000/api/v1/query/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ query }),
        signal: abortControllerRef.current?.signal,
      })
        .then(async (response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          const reader = response.body?.getReader();
          if (!reader) {
            throw new Error("No response body");
          }

          const decoder = new TextDecoder();
          let buffer = "";
          let finalResult: unknown = null;

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE events
            const lines = buffer.split("\n");
            buffer = lines.pop() || ""; // Keep incomplete line in buffer

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                try {
                  const data = JSON.parse(line.slice(6));
                  processEvent(data);

                  // Store final result
                  if (data.type === "result") {
                    finalResult = data.data;
                  }
                } catch {
                  // Ignore JSON parse errors
                }
              }
            }
          }

          setIsStreaming(false);
          resolve(finalResult);
        })
        .catch((error) => {
          if (error.name === "AbortError") {
            setIsStreaming(false);
            resolve(null);
          } else {
            setIsStreaming(false);
            setWorkflowState((prev) => ({
              ...prev,
              isActive: false,
              error: error.message,
            }));
            reject(error);
          }
        });

      // Clean up EventSource (not used, but kept for reference)
      eventSource.close();
    });
  }, [resetWorkflow, processEvent]);

  return {
    workflowState,
    startStream,
    resetWorkflow,
    isStreaming,
  };
}
