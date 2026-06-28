import { Navigate, Route, Routes } from "react-router-dom"

import { useSession } from "@/lib/auth"
import Login from "@/pages/Login"
import SignUp from "@/pages/SignUp"

function Home() {
  const { session } = useSession()

  if (!session) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-lg text-gray-500">
        Signed in as {session.user.email}
      </p>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<SignUp />} />
      <Route path="/*" element={<Home />} />
    </Routes>
  )
}
