import { useEffect, useRef, useState } from "react"

import { api } from "@/lib/http"
import { API_BASE_URL } from "@/lib/env"

interface Thread {
  id: string
  title: string
  created_at: string | null
  updated_at: string | null
}

interface ThreadListProps {
  activeThreadId: string
  onSelectThread: (id: string) => void
  onDeleteThread: (id: string) => void
  refreshKey: number
}

export default function ThreadList({ activeThreadId, onSelectThread, onDeleteThread, refreshKey }: ThreadListProps) {
  const [threads, setThreads] = useState<Thread[]>([])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api.get<Thread[]>(`${API_BASE_URL}/chat/threads`).then(setThreads).catch(() => {})
  }, [refreshKey])

  function startRename(thread: Thread) {
    setEditingId(thread.id)
    setEditValue(thread.title)
    setTimeout(() => inputRef.current?.select(), 0)
  }

  async function commitRename(threadId: string) {
    const title = editValue.trim() || "Untitled"
    setEditingId(null)
    try {
      await api.patch(`${API_BASE_URL}/chat/threads/${threadId}`, { title })
      setThreads((prev) => prev.map((t) => (t.id === threadId ? { ...t, title } : t)))
    } catch {
      // revert on failure
    }
  }

  async function handleDelete(e: React.MouseEvent, threadId: string) {
    e.stopPropagation()
    try {
      await api.delete(`${API_BASE_URL}/chat/threads/${threadId}`)
      setThreads((prev) => prev.filter((t) => t.id !== threadId))
      onDeleteThread(threadId)
    } catch {
      // ignore
    }
  }

  return (
    <div className="flex flex-col gap-0.5">
      {threads.map((thread) => (
        <div key={thread.id} className="group flex items-center">
          {editingId === thread.id ? (
            <input
              ref={inputRef}
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={() => commitRename(thread.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitRename(thread.id)
                if (e.key === "Escape") setEditingId(null)
              }}
              className="w-full bg-background border border-input rounded px-2 py-1 text-sm outline-none"
              autoFocus
            />
          ) : (
            <>
              <button
                onClick={() => onSelectThread(thread.id)}
                onDoubleClick={() => startRename(thread)}
                className={`flex-1 text-left px-3 py-1.5 text-sm rounded-md transition-colors truncate ${
                  thread.id === activeThreadId
                    ? "bg-muted text-foreground font-medium"
                    : "text-muted-foreground hover:bg-muted/50"
                }`}
              >
                {thread.title || "Untitled"}
              </button>
              <button
                onClick={(e) => handleDelete(e, thread.id)}
                className="opacity-0 group-hover:opacity-100 mr-1 p-1 text-muted-foreground hover:text-destructive transition-opacity"
                title="Delete chat"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 6h18" />
                  <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                  <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                </svg>
              </button>
            </>
          )}
        </div>
      ))}
    </div>
  )
}
