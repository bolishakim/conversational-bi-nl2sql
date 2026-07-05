"use client";

import { useState, KeyboardEvent } from "react";
import { Trash2, MessageSquarePlus } from "lucide-react";
import { useChatContext } from "@/contexts/ChatContext";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const [input, setInput] = useState("");
  const { clearMessages, isProcessing, messages } = useChatContext();

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="border-t border-border bg-white">
      <div className="px-4 py-4">
        <div className="max-w-4xl mx-auto flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your data..."
            disabled={disabled}
            className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500"
            rows={1}
            style={{
              minHeight: "48px",
              maxHeight: "120px",
            }}
          />
          <button
            onClick={handleSend}
            disabled={disabled || !input.trim()}
            className="px-6 py-3 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
        <p className="text-xs text-gray-500 text-center mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>

      {hasMessages && (
        <div className="border-t border-gray-100 bg-gray-50/50 px-4 py-2 flex justify-between max-w-4xl mx-auto">
          <button
            onClick={clearMessages}
            disabled={isProcessing}
            className="text-xs text-gray-400 hover:text-red-500 flex items-center gap-1 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Trash2 size={14} />
            Clear Chat
          </button>
          <button
            onClick={clearMessages}
            disabled={isProcessing}
            className="text-xs text-gray-400 hover:text-blue-500 flex items-center gap-1 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <MessageSquarePlus size={14} />
            New Chat
          </button>
        </div>
      )}
    </div>
  );
}
