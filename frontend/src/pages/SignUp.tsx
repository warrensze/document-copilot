import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { supabase } from "@/lib/supabase"

export default function SignUp() {
  const navigate = useNavigate()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    const { error: err } = await supabase.auth.signUp({ email, password })
    if (err) {
      setError(err.message)
    } else {
      navigate("/login")
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <form
        onSubmit={handleSubmit}
        className="flex w-full max-w-sm flex-col gap-4"
      >
        <h1 className="text-2xl font-bold">Sign up</h1>
        {error && <p className="text-sm text-red-500">{error}</p>}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="rounded border px-3 py-2"
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="rounded border px-3 py-2"
        />
        <Button type="submit">Sign up</Button>
        <p className="text-sm text-gray-500">
          Already have an account?{" "}
          <Link to="/login" className="text-blue-500 underline">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  )
}
