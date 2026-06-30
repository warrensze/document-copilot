import { cn } from "@/lib/utils"

export type StageStatus = "waiting" | "active" | "done" | "failed"

export interface Stage {
  label: string
  status: StageStatus
}

interface StatusIndicatorProps {
  stages: Stage[]
  className?: string
}

const dot = (status: StageStatus) => {
  switch (status) {
    case "done":
      return <span className="text-green-600">✓</span>
    case "active":
      return <span className="inline-block h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
    case "failed":
      return <span className="text-destructive">✗</span>
    default:
      return <span className="text-muted-foreground">○</span>
  }
}

export default function StatusIndicator({ stages, className }: StatusIndicatorProps) {
  const allDone = stages.every((s) => s.status === "done")
  if (allDone) return null

  return (
    <div
      className={cn(
        "flex items-center gap-4 px-4 py-2 text-xs text-muted-foreground border-b",
        className,
      )}
    >
      {stages.map((stage) => (
        <span
          key={stage.label}
          className={cn(
            "flex items-center gap-1.5",
            stage.status === "active" && "text-blue-600 font-medium",
            stage.status === "failed" && "text-destructive font-medium",
            stage.status === "done" && "text-green-600",
          )}
        >
          {dot(stage.status)}
          {stage.label}
        </span>
      ))}
    </div>
  )
}
