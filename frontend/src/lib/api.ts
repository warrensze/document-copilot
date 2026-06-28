import { API_BASE_URL } from "@/lib/env"
import { api } from "@/lib/http"

export function getThreads() {
  return api.get<unknown[]>(`${API_BASE_URL}/chat/threads`)
}

export function getThreadMessages(threadId: string) {
  return api.get<unknown[]>(`${API_BASE_URL}/chat/threads/${threadId}/messages`)
}

export function createThread() {
  return api.post<{ id: string }>(`${API_BASE_URL}/chat/threads`)
}
