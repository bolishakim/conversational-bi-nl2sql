import type { Message } from "@/types/message";

interface UserMessageProps {
  message: Message;
}

export default function UserMessage({ message }: UserMessageProps) {
  return (
    <div className="flex justify-end mb-4">
      <div className="max-w-[70%]">
        <div className="bg-blue-500 text-white rounded-lg px-4 py-3">
          <p className="text-sm">{message.content}</p>
        </div>
        <p className="text-xs text-gray-500 mt-1 text-right">
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
    </div>
  );
}
