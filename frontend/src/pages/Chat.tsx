import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport } from "ai"
import { useCallback, useState } from "react"
import { Navigate } from "react-router-dom"

import ChatInput from "@/components/chat/ChatInput"
import MessageList from "@/components/chat/MessageList"
import Sidebar from "@/components/chat/Sidebar"
import { useSession } from "@/lib/auth"
import { API_BASE_URL } from "@/lib/env"
import { getAccessToken } from "@/lib/supabase"

type StageState = "waiting" | "active" | "done" | "failed"

interface PipelineState {
  retrieving: StageState
  generating: StageState
  grounding: StageState
}

const IDLE_PIPELINE: PipelineState = {
  retrieving: "waiting",
  generating: "waiting",
  grounding: "waiting",
}

export default function ChatPage() {
  const { session } = useSession()
  const [threadId, setThreadId] = useState(() => crypto.randomUUID())
  const [refreshKey, setRefreshKey] = useState(0)
  const [pipelineStatus, setPipelineStatus] = useState<PipelineState>(IDLE_PIPELINE)

  const { messages, status, append, setMessages } = useChat({
    id: threadId,
    transport: new DefaultChatTransport({
      api: `${API_BASE_URL}/chat/stream`,
      headers: async () => ({
        Authorization: `Bearer ${await getAccessToken()}`,
      }),
    }),
    onChunk({ chunk }) {
      if (chunk.type !== "data") return
      const data = chunk.data as Record<string, unknown>
      const event = data.event as string
      if (event === "status") {
        const s = data.status as string
        setPipelineStatus((prev) => {
          const next = { ...prev }
          if (s === "retrieving") {
            next.retrieving = "active"
          } else if (s === "generating") {
            next.retrieving = "done"
            next.generating = "active"
          } else if (s === "grounding") {
            next.generating = "done"
            next.grounding = "active"
          } else if (s === "grounding_failed") {
            next.grounding = "failed"
          } else if (s === "complete") {
            next.grounding = "done"
          }
          return next
        })
      } else if (event === "citations") {
        const citations = data.citations as Array<Record<string, unknown>>
        setMessages((msgs) => {
          const last = msgs[msgs.length - 1]
          if (!last || last.role !== "assistant") return msgs
          const updated = { ...last, data: { citations } } as typeof last
          return [...msgs.slice(0, -1), updated]
        })
      }
    },
    onFinish() {
      setPipelineStatus(IDLE_PIPELINE)
      setRefreshKey((k) => k + 1)
    },
  })

  const handleNewChat = useCallback(() => {
    const newId = crypto.randomUUID()
    setThreadId(newId)
    setPipelineStatus(IDLE_PIPELINE)
    setRefreshKey((k) => k + 1)
  }, [])

  const handleSelectThread = useCallback((id: string) => {
    setThreadId(id)
    setPipelineStatus(IDLE_PIPELINE)
    // Load messages for thread... (deferred - server messages not wired yet)
  }, [])

  if (!session) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="flex h-screen">
      <Sidebar
        activeThreadId={threadId}
        onNewChat={handleNewChat}
        onSelectThread={handleSelectThread}
        refreshKey={refreshKey}
      />
      <div className="flex flex-col flex-1 min-w-0">
        <MessageList
          messages={messages}
          status={status}
          pipelineStatus={pipelineStatus}
        />
        <ChatInput
          onSend={(text) => append({ role: "user", content: text })}
          disabled={status === "streaming" || status === "submitted"}
        />
      </div>
    </div>
  )
}
