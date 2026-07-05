"use client";

import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from "react";
import type { Message } from "@/types/message";
import type { WorkflowState, NodeStatus, EdgeStatus, TokenStats } from "@/components/workflow";
import { api, StreamEvent } from "@/lib/api";
import { auth } from "@/lib/auth";

// Workflow nodes in order (user-facing agents only)
const WORKFLOW_NODES = [
  "orchestrator",
  "schema_agent",
  "sql_agent",
  "validator",
  "executor",
  "viz_generator",
  "iteration_decision",
];

export const createInitialWorkflowState = (): WorkflowState => ({
  isActive: false,
  currentNode: null,
  nodes: Object.fromEntries(
    WORKFLOW_NODES.map((node) => [node, { status: "idle" as NodeStatus }])
  ),
  edges: {},
  retryCount: 0,
  iterationCount: 0,
});

interface ChatContextType {
  messages: Message[];
  isProcessing: boolean;
  workflowState: WorkflowState;
  addMessage: (msg: Message) => void;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  clearMessages: () => void;
  setIsProcessing: (val: boolean) => void;
  setWorkflowState: React.Dispatch<React.SetStateAction<WorkflowState>>;
  ensureParticipantScope: () => Promise<void>;
  sendMessage: (userInput: string) => Promise<void>;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [workflowState, setWorkflowState] = useState<WorkflowState>(createInitialWorkflowState);
  const currentParticipantRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Check current participant and clear messages if participant changed
  const ensureParticipantScope = useCallback(async () => {
    if (typeof window === "undefined") return;
    if (!auth.getToken()) return;

    try {
      const info = await api.getMyParticipantInfo();
      const pid = info.enrolled ? info.id : null;
      if (pid !== currentParticipantRef.current) {
        currentParticipantRef.current = pid;
        setMessages([]);
        setIsProcessing(false);
        setWorkflowState(createInitialWorkflowState());
      }
    } catch {
      // Not authenticated or no participant — clear
      if (currentParticipantRef.current !== null) {
        currentParticipantRef.current = null;
        setMessages([]);
        setIsProcessing(false);
        setWorkflowState(createInitialWorkflowState());
      }
    }
  }, []);

  // Scope on initial mount
  useEffect(() => {
    ensureParticipantScope();
  }, [ensureParticipantScope]);

  const addMessage = useCallback((msg: Message) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setIsProcessing(false);
    setWorkflowState(createInitialWorkflowState());
  }, []);

  // Process workflow events from SSE stream
  const handleWorkflowEvent = useCallback((event: StreamEvent) => {
    const { type, stage, status, message, details } = event;

    if (type === "start") {
      setWorkflowState((prev) => ({
        ...prev,
        isActive: true,
        startTime: Date.now(),
        currentNode: "orchestrator",
        nodes: {
          ...prev.nodes,
          orchestrator: { status: "running", startTime: Date.now() },
        },
        edges: {
          ...prev.edges,
          "start-orchestrator": "active" as EdgeStatus,
        },
      }));
      return;
    }

    if (type === "progress" && stage) {
      if (stage === "complete") {
        setWorkflowState((prev) => ({
          ...prev,
          isActive: false,
          currentNode: null,
          endTime: Date.now(),
          edges: {
            ...prev.edges,
            "iteration_decision-end": "completed",
          },
        }));
        return;
      }

      const now = Date.now();

      setWorkflowState((prev) => {
        const newState = { ...prev };
        const newNodes = { ...prev.nodes };
        const newEdges = { ...prev.edges };

        if (status === "completed") {
          newNodes[stage] = {
            ...newNodes[stage],
            status: "completed",
            endTime: now,
            message,
            details,
          };

          const nodeIndex = WORKFLOW_NODES.indexOf(stage);

          if (nodeIndex === 0) {
            newEdges["start-orchestrator"] = "completed";
          } else if (nodeIndex > 0) {
            const prevNode = WORKFLOW_NODES[nodeIndex - 1];
            newEdges[`${prevNode}-${stage}`] = "completed";
          }

          if (stage === "orchestrator" && details?.action === "DIRECT_ANSWER") {
            newEdges["orchestrator-end"] = "completed";
            newState.isActive = false;
            newState.currentNode = null;
          } else if (nodeIndex >= 0 && nodeIndex < WORKFLOW_NODES.length - 1) {
            const nextNode = WORKFLOW_NODES[nodeIndex + 1];
            newNodes[nextNode] = { status: "running", startTime: now };
            newEdges[`${stage}-${nextNode}`] = "active";
            newState.currentNode = nextNode;
          }
        }

        if (status === "retrying") {
          newNodes[stage] = {
            ...newNodes[stage],
            status: "retrying",
            message,
            details,
          };
          newEdges["validator-sql_agent"] = "retry";
          newNodes["sql_agent"] = { status: "running", startTime: now };
          newState.currentNode = "sql_agent";
          newState.retryCount = (details?.retry_attempt as number) || prev.retryCount + 1;
        }

        if (status === "needs_followup") {
          newNodes[stage] = {
            ...newNodes[stage],
            status: "completed",
            endTime: now,
            message,
            details,
          };
          newEdges["iteration_decision-sql_agent"] = "active";
          newNodes["sql_agent"] = { status: "running", startTime: now };
          newState.currentNode = "sql_agent";
          newState.iterationCount = prev.iterationCount + 1;
        }

        if (status === "failed") {
          newNodes[stage] = {
            ...newNodes[stage],
            status: "failed",
            endTime: now,
            message,
            details,
          };
          newState.currentNode = null;
          newState.error = message;
        }

        return {
          ...newState,
          nodes: newNodes,
          edges: newEdges,
        };
      });
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
  }, []);

  // Send message and stream response — runs in the context (survives navigation)
  const sendMessage = useCallback(async (userInput: string) => {
    // Abort any previous running stream (only when sending a NEW query)
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: userInput,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsProcessing(true);
    setWorkflowState(createInitialWorkflowState());

    try {
      const response = await api.queryStream(
        userInput,
        handleWorkflowEvent,
        controller.signal
      );

      // Extract token stats from response
      const tokenUsage = response?.token_usage;
      if (tokenUsage) {
        const tokenStats: TokenStats = {
          totalTokens: tokenUsage.total_tokens || 0,
          inputTokens: tokenUsage.total_input_tokens || 0,
          outputTokens: tokenUsage.total_output_tokens || 0,
          totalCost: tokenUsage.total_cost_usd || 0,
          llmCalls: tokenUsage.total_llm_calls || 0,
        };
        setWorkflowState((prev) => ({
          ...prev,
          tokenStats,
        }));
      }

      // Add system message with response
      const systemMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "system",
        content: response?.analysis?.summary || "Query completed successfully",
        timestamp: new Date(),
        sqlQuery: response?.sql_query,
        results: response?.results,
        chart: response?.chart,
        analysis: response?.analysis,
      };

      setMessages((prev) => [...prev, systemMessage]);
    } catch (error: any) {
      // On abort (user sent a new query), just return silently
      if (error.name === "AbortError") return;

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "system",
        content: "An error occurred while processing your request.",
        timestamp: new Date(),
        error: error.message || "Unknown error occurred",
      };

      setMessages((prev) => [...prev, errorMessage]);

      setWorkflowState((prev) => ({
        ...prev,
        isActive: false,
        error: error.message,
      }));
    } finally {
      setIsProcessing(false);
    }
  }, [handleWorkflowEvent]);

  const value: ChatContextType = {
    messages,
    isProcessing,
    workflowState,
    addMessage,
    setMessages,
    clearMessages,
    setIsProcessing,
    setWorkflowState,
    ensureParticipantScope,
    sendMessage,
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error("useChatContext must be used within a ChatProvider");
  }
  return context;
}
