import { Button } from "@/components/ui/button"
import ThreadList from "@/components/chat/ThreadList"
import { supabase } from "@/lib/supabase"

interface SidebarProps {
  activeThreadId: string
  onNewChat: () => void
  onSelectThread: (id: string) => void
  onDeleteThread: (id: string) => void
  refreshKey: number
}

export default function Sidebar({ activeThreadId, onNewChat, onSelectThread, onDeleteThread, refreshKey }: SidebarProps) {
  return (
    <aside className="w-60 border-r flex flex-col bg-muted/30">
      <div className="p-4 border-b">
        <h1 className="font-heading text-base font-semibold tracking-tight">
          Document Copilot
        </h1>
      </div>

      <div className="p-3">
        <Button
          onClick={onNewChat}
          variant="outline"
          className="w-full justify-start gap-2"
        >
          + New chat
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-2">
        <ThreadList
          activeThreadId={activeThreadId}
          onSelectThread={onSelectThread}
          onDeleteThread={onDeleteThread}
          refreshKey={refreshKey}
        />
      </div>

      <div className="p-3 border-t">
        <Button
          onClick={() => supabase.auth.signOut()}
          variant="ghost"
          className="w-full justify-start text-muted-foreground"
        >
          Sign out
        </Button>
      </div>
    </aside>
  )
}
