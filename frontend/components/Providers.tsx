"use client";

import { TaskSessionProvider } from "@/contexts/TaskSessionContext";
import { ChatProvider } from "@/contexts/ChatContext";

interface ProvidersProps {
  children: React.ReactNode;
}

export default function Providers({ children }: ProvidersProps) {
  return (
    <TaskSessionProvider>
      <ChatProvider>
        {children}
      </ChatProvider>
    </TaskSessionProvider>
  );
}
