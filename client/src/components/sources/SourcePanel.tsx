"use client";

import { memo } from "react";
import { FileStack, TrendingUp } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { SourceCard } from "./SourceCard";
import type { Source } from "@/lib/types";

interface SourcePanelProps {
  sources: Source[];
  isOpen: boolean;
  onClose: () => void;
  onViewPdf?: (source: Source) => void;
  onShowContext?: (source: Source) => void;
  avgScore?: number;
}

export const SourcePanel = memo(function SourcePanel({
  sources,
  isOpen,
  onClose,
  onViewPdf,
  onShowContext,
  avgScore,
}: SourcePanelProps) {
  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full sm:max-w-lg p-0 flex flex-col overflow-hidden">
        <SheetHeader className="p-4 pb-0">
          <SheetTitle className="flex items-center gap-2">
            <FileStack className="h-5 w-5" />
            Retrieved Sources
          </SheetTitle>

          {/* Stats bar */}
          <div className="flex items-center gap-4 py-3 text-sm text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <FileStack className="h-4 w-4" />
              {sources.length} sources
            </span>
            {avgScore !== undefined && (
              <span className="flex items-center gap-1.5">
                <TrendingUp className="h-4 w-4" />
                {Math.round(avgScore * 100)}% avg relevance
              </span>
            )}
          </div>
        </SheetHeader>

        <Separator />

        <div className="flex-1 min-h-0 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="space-y-4 p-4">
              {sources.map((source, index) => (
                <SourceCard
                  key={source.chunk_id}
                  source={source}
                  onViewPdf={onViewPdf}
                  onShowContext={onShowContext}
                  isExpanded={index === 0}
                />
              ))}
            </div>
          </ScrollArea>
        </div>
      </SheetContent>
    </Sheet>
  );
});
