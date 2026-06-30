import { useState } from "react"

interface CitationPanelCitation {
  chunk_id: string
  excerpt: string
  ticker?: string
  company_name?: string
  year?: string
  section?: string | null
}

interface CitationPanelProps {
  citations: CitationPanelCitation[]
}

export default function CitationPanel({ citations }: CitationPanelProps) {
  const [expanded, setExpanded] = useState(false)

  if (citations.length === 0) return null

  return (
    <div className="mt-2 border-t pt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        {expanded ? "Hide" : "Show"} {citations.length} source{citations.length !== 1 ? "s" : ""}
      </button>
      {expanded && (
        <div className="mt-2 space-y-2">
          {citations.map((c, i) => (
            <div key={c.chunk_id} className="text-xs border rounded-md p-2 bg-muted/30">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium text-muted-foreground">[{i + 1}]</span>
                {c.ticker && (
                  <span className="font-semibold text-foreground">{c.ticker}</span>
                )}
                {c.company_name && (
                  <span className="text-muted-foreground">{c.company_name}</span>
                )}
                {c.year && <span className="text-muted-foreground">{c.year}</span>}
                {c.section && (
                  <span className="text-muted-foreground truncate">{c.section}</span>
                )}
              </div>
              <p className="text-muted-foreground leading-relaxed">
                &ldquo;{c.excerpt}&rdquo;
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
