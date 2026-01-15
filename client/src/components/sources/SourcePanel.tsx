"use client";

import { memo } from "react";
import { FileStack, TrendingUp, X } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { SourceCard } from "./SourceCard";
import type { Source } from "@/lib/types";
import type { PdfOrigin } from "@/hooks/useChat";

interface SourcePanelProps {
  sources: Source[];
  isOpen: boolean;
  onClose: () => void;
  onViewPdf?: (source: Source) => void;
  onShowContext?: (source: Source) => void;
  avgScore?: number;
  isPdfOpen?: boolean;
  pdfOrigin?: PdfOrigin;
}

// Deduplicate sources by breadcrumb, keeping the highest relevance score
function deduplicateSources(sources: Source[]): Source[] {
  const seen = new Map<string, Source>();
  for (const source of sources) {
    const key = source.location.breadcrumb;
    const existing = seen.get(key);
    if (!existing || source.relevance_score > existing.relevance_score) {
      seen.set(key, source);
    }
  }
  return Array.from(seen.values());
}

export const SourcePanel = memo(function SourcePanel({
  sources,
  isOpen,
  onClose,
  onViewPdf,
  onShowContext,
  avgScore,
  isPdfOpen = false,
  pdfOrigin = "chat",
}: SourcePanelProps) {
  // In "sources-panel" mode with PDF open, panels are connected (no overlay, no border-left gap)
  const isConnectedMode = isPdfOpen && pdfOrigin === "sources-panel";

  // Deduplicate sources by breadcrumb
  const uniqueSources = deduplicateSources(sources);

  return (
    <>
      {/* Overlay - only show when PDF is not open OR when in chat flow */}
      {isOpen && !isPdfOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm animate-fade-in"
          onClick={onClose}
        />
      )}

      {/* Panel */}
      <div
        className={`
          sources-panel
          fixed top-0 right-0 h-screen z-50
          flex flex-col
          bg-background/95 backdrop-blur-xl
          w-full sm:max-w-md
          transform transition-all duration-300 ease-out
          ${isOpen ? "translate-x-0 opacity-100" : "translate-x-full opacity-0"}
          ${isConnectedMode ? "border-l-0" : "border-l border-border/50"}
        `}
      >
        {/* Header */}
        <div className="shrink-0 p-4 pb-0">
          <div className="flex items-center justify-between gap-4">
            <h2 className="flex items-center gap-2 text-base font-semibold">
              <FileStack className="h-5 w-5" />
              Retrieved Sources
            </h2>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="h-8 w-8 shrink-0"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Stats bar */}
          <div className="flex items-center gap-4 py-3 text-sm text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <FileStack className="h-4 w-4" />
              {uniqueSources.length} sources
            </span>
            {avgScore !== undefined && (
              <span className="flex items-center gap-1.5">
                <TrendingUp className="h-4 w-4" />
                {Math.round(avgScore * 100)}% avg relevance
              </span>
            )}
          </div>
        </div>

        <Separator />

        <div className="flex-1 min-h-0 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="space-y-4 p-4">
              {uniqueSources.map((source) => (
                <SourceCard
                  key={source.chunk_id}
                  source={source}
                  onViewPdf={onViewPdf}
                  onShowContext={onShowContext}
                />
              ))}
            </div>
          </ScrollArea>
        </div>
      </div>
    </>
  );
});
