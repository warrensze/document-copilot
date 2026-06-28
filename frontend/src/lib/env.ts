class EnvError extends Error {
  constructor(key: string) {
    super(`Missing required env var: ${key}`)
    this.name = "EnvError"
  }
}

function requireEnv(key: string): string {
  const val = import.meta.env[key] as string | undefined
  if (!val) throw new EnvError(key)
  return val
}

export const API_BASE_URL = requireEnv("VITE_API_BASE_URL")
export const SUPABASE_URL = requireEnv("VITE_SUPABASE_URL")
export const SUPABASE_ANON_KEY = requireEnv("VITE_SUPABASE_ANON_KEY")
