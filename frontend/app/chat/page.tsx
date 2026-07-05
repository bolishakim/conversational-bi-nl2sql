"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import MessageList from "@/components/MessageList";
import ChatInput from "@/components/ChatInput";
import AuthenticatedLayout from "@/components/AuthenticatedLayout";
import TaskOverlay from "@/components/TaskOverlay";
import { AgentWorkflowGraph } from "@/components/workflow";
import { useChatContext } from "@/contexts/ChatContext";

export default function ChatPage() {
  const router = useRouter();
  const { messages, isProcessing, workflowState, ensureParticipantScope, sendMessage } = useChatContext();
  const [accessChecked, setAccessChecked] = useState(false);

  // Check if user has chatbot access and scope messages to current participant
  useEffect(() => {
    const checkAccess = async () => {
      try {
        const user = await api.me();
        if (!user.can_access_chatbot) {
          router.push("/dashboards/sales");
        } else {
          await ensureParticipantScope();
          setAccessChecked(true);
        }
      } catch (error) {
        console.error("Failed to check access:", error);
        router.push("/login");
      }
    };
    checkAccess();
  }, [router, ensureParticipantScope]);

  // Show loading while checking access
  if (!accessChecked) {
    return (
      <AuthenticatedLayout
        title="Query Assistant"
        subtitle="Checking access..."
      >
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="text-gray-600 mt-3">Verifying access...</p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout
      title="Query Assistant"
      subtitle="Ask questions about your data in natural language"
    >
      <div className="flex flex-col h-full bg-gray-50">
        {/* Workflow Visualization */}
        <div className="px-4 pt-4">
          <AgentWorkflowGraph workflowState={workflowState} />
        </div>

        {/* Messages */}
        <MessageList messages={messages} />

        {/* Input */}
        <ChatInput onSend={sendMessage} disabled={isProcessing} />

        {/* Task Overlay */}
        <TaskOverlay />
      </div>
    </AuthenticatedLayout>
  );
}
