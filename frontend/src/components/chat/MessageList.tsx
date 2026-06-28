import { useEffect, useRef } from "react"
import type { UIMessage } from "@ai-sdk/react"

interface MessageListProps {
  messages: UIMessage[]
  status: "ready" | "streaming" | "submitted" | "error"
}

export default function MessageList({ messages, status }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, messages[messages.length - 1]?.parts])

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

        return (
          <div
            key={message.id}
            className={`flex ${isUser ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`rounded-lg px-4 py-2 max-w-[80%] whitespace-pre-wrap ${
                isUser
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {text}
            </div>
          </div>
        )
      })}
      {status === "streaming" && (
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
