import { supabase } from "@/lib/supabase"

export class ApiError extends Error {
  status: number
  isNetworkError: boolean

  constructor(message: string, status: number, isNetworkError: boolean = false) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.isNetworkError = isNetworkError
  }
}

async function getAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

async function request<T>(
  method: string,
  url: string,
  body?: unknown
): Promise<T> {
  const token = await getAccessToken()
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  let res: Response
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError("Network error", 0, true)
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error")
    throw new ApiError(text, res.status)
  }

  return res.json()
}

export const api = {
  get: <T>(url: string) => request<T>("GET", url),
  post: <T>(url: string, body?: unknown) => request<T>("POST", url, body),
  put: <T>(url: string, body?: unknown) => request<T>("PUT", url, body),
  patch: <T>(url: string, body?: unknown) => request<T>("PATCH", url, body),
  delete: <T>(url: string) => request<T>("DELETE", url),
}
