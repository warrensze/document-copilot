import { cn } from "@/lib/utils"

interface CitationBadgeProps {
  index: number
  excerpt: string
  className?: string
}

export default function CitationBadge({ index, excerpt, className }: CitationBadgeProps) {
  return (
    <sup
      title={excerpt}
      className={cn(
        "inline-flex items-center justify-center h-4 min-w-4 px-1 rounded-sm",
        "bg-muted-foreground/15 text-muted-foreground text-[10px] font-medium",
        "cursor-help not-italic",
        "hover:bg-muted-foreground/25 transition-colors",
        className,
      )}
    >
      {index}
    </sup>
  )
}
