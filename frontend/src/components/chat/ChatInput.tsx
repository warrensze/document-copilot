import { type FormEvent, useState } from "react"

import { Button } from "@/components/ui/button"

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState("")

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || disabled) return
    onSend(text)
    setInput("")
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t p-4 flex gap-2 items-end"
    >
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask a question about SEC filings..."
        disabled={disabled}
        className="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
      />
      <Button type="submit" disabled={!input.trim() || disabled} size="default">
        Send
      </Button>
    </form>
  )
}
