import type { Message } from "@/types/message";
import UserMessage from "./UserMessage";
import SystemMessage from "./SystemMessage";
import { useEffect, useRef } from "react";

interface MessageListProps {
  messages: Message[];
}

export default function MessageList({ messages }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      {messages.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-center">
          <div className="text-4xl mb-4">💬</div>
          <h3 className="text-lg font-semibold text-gray-700 mb-2">
            Start a conversation
          </h3>
          <p className="text-sm text-gray-500 max-w-md">
            Ask questions about your data in natural language, and I'll help you
            analyze it with SQL queries and visualizations.
          </p>
          <div className="mt-6 grid grid-cols-1 gap-3 max-w-md">
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-left">
              <p className="text-xs text-gray-600">
                "What were the total sales last month?"
              </p>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-left">
              <p className="text-xs text-gray-600">
                "Show me the top 10 customers by revenue"
              </p>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-left">
              <p className="text-xs text-gray-600">
                "Compare sales trends over the last 6 months"
              </p>
            </div>
          </div>
        </div>
      ) : (
        <>
          {messages.map((message) =>
            message.role === "user" ? (
              <UserMessage key={message.id} message={message} />
            ) : (
              <SystemMessage key={message.id} message={message} />
            )
          )}
          <div ref={messagesEndRef} />
        </>
      )}
    </div>
  );
}
