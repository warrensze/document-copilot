import { useEffect, useRef } from "react"
import type { UIMessage } from "@ai-sdk/react"

import CitationBadge from "@/components/chat/CitationBadge"
import CitationPanel from "@/components/chat/CitationPanel"
import StatusIndicator, { type Stage } from "@/components/chat/StatusIndicator"

interface PipelineState {
  retrieving: "waiting" | "active" | "done" | "failed"
  generating: "waiting" | "active" | "done" | "failed"
  grounding: "waiting" | "active" | "done" | "failed"
}

interface AssistantMeta {
  citations?: Array<{
    chunk_id: string
    excerpt: string
    ticker?: string
    company_name?: string
    year?: string
    section?: string | null
  }>
}

interface MessageListProps {
  messages: UIMessage[]
  status: "ready" | "streaming" | "submitted" | "error"
  pipelineStatus: PipelineState
}

const pipelineToStages = (p: PipelineState): Stage[] => [
  { label: "Searching", status: p.retrieving },
  { label: "Generating", status: p.generating },
  { label: "Validating", status: p.grounding },
]

function inlineCitations(text: string, citations: AssistantMeta["citations"]) {
  if (!citations || citations.length === 0) return text
  const parts = text.split(/(\[\d+\])/g)
  return parts.map((part, i) => {
    const match = part.match(/\[(\d+)\]/)
    if (match) {
      const idx = parseInt(match[1]) - 1
      const c = citations[idx]
      if (c) {
        return (
          <CitationBadge key={i} index={idx + 1} excerpt={c.excerpt} />
        )
      }
    }
    return part
  })
}

export default function MessageList({ messages, status, pipelineStatus }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, messages[messages.length - 1]?.parts])

  const isRunning = status === "submitted" || status === "streaming"

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-center p-8">
        <p className="text-muted-foreground text-lg">
          Ask a question about SEC filings
        </p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((message) => {
        const isUser = message.role === "user"
        const text = message.parts
          .filter((p) => p.type === "text")
          .map((p) => p.text)
          .join("")

        const assistantMeta: AssistantMeta = (message as Record<string, unknown>).data as AssistantMeta | undefined ?? {}

        return (
          <div key={message.id}>
            {isRunning && message === messages[messages.length - 1] && message.role === "assistant" && (
              <StatusIndicator stages={pipelineToStages(pipelineStatus)} className="mb-2 -mx-4" />
            )}
            <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
              <div
                className={`rounded-lg px-4 py-2 max-w-[80%] whitespace-pre-wrap ${
                  isUser
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {isUser ? text : inlineCitations(text, assistantMeta.citations)}
              </div>
            </div>
            {!isUser && assistantMeta.citations && assistantMeta.citations.length > 0 && (
              <div className="ml-2">
                <CitationPanel citations={assistantMeta.citations} />
              </div>
            )}
          </div>
        )
      })}
      {status === "submitted" && (
        <div className="flex justify-start">
          <div className="bg-muted text-muted-foreground rounded-lg px-4 py-2">
            <span className="animate-pulse">▊</span>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
