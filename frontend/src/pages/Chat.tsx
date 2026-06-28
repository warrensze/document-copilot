import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport } from "ai"
import { useState } from "react"
import { Navigate } from "react-router-dom"

import ChatInput from "@/components/chat/ChatInput"
import MessageList from "@/components/chat/MessageList"
import Sidebar from "@/components/chat/Sidebar"
import { useSession } from "@/lib/auth"
import { API_BASE_URL } from "@/lib/env"
import { getAccessToken } from "@/lib/supabase"

export default function ChatPage() {
  const { session } = useSession()
  const [threadId, setThreadId] = useState(() => crypto.randomUUID())

  const { messages, sendMessage, status, error } = useChat({
    id: threadId,
    transport: new DefaultChatTransport({
      api: `${API_BASE_URL}/chat/stream`,
      headers: async () => ({
        Authorization: `Bearer ${await getAccessToken()}`,
      }),
    }),
  })

  if (!session) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="flex h-screen">
      <Sidebar onNewChat={() => setThreadId(crypto.randomUUID())} />
      <div className="flex flex-col flex-1 min-w-0">
        {error && (
          <div className="bg-destructive/10 text-destructive text-sm p-3 text-center">
            {error.message}
          </div>
        )}
        <MessageList messages={messages} status={status} />
        <ChatInput
          onSend={(text) => sendMessage({ text })}
          disabled={status === "streaming" || status === "submitted"}
        />
      </div>
    </div>
  )
}
