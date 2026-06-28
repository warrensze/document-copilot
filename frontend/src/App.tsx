import { Navigate, Route, Routes } from "react-router-dom"

import ChatPage from "@/pages/Chat"
import Login from "@/pages/Login"
import SignUp from "@/pages/SignUp"

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<SignUp />} />
      <Route path="/chat" element={<ChatPage />} />
      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  )
}
