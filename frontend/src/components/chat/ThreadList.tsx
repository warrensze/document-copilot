import { useEffect, useRef, useState } from "react"

import { api } from "@/lib/api"
import { API_BASE_URL } from "@/lib/env"
import { getAccessToken } from "@/lib/supabase"

interface Thread {
  id: string
  title: string
  created_at: string | null
  updated_at: string | null
}

interface ThreadListProps {
  activeThreadId: string
  onSelectThread: (id: string) => void
  refreshKey: number
}

export default function ThreadList({ activeThreadId, onSelectThread, refreshKey }: ThreadListProps) {
  const [threads, setThreads] = useState<Thread[]>([])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    getAccessToken().then((token) => {
      if (!token) return
      api
        .get<Thread[]>(`${API_BASE_URL}/chat/threads`)
        .then(setThreads)
        .catch(() => {})
    })
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

  return (
    <div className="flex flex-col gap-0.5">
      {threads.map((thread) => (
        <div key={thread.id}>
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
            <button
              onClick={() => onSelectThread(thread.id)}
              onDoubleClick={() => startRename(thread)}
              className={`w-full text-left px-3 py-1.5 text-sm rounded-md transition-colors truncate ${
                thread.id === activeThreadId
                  ? "bg-muted text-foreground font-medium"
                  : "text-muted-foreground hover:bg-muted/50"
              }`}
            >
              {thread.title || "Untitled"}
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
