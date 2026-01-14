"use client";

import { memo } from "react";
import { FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { Source } from "@/lib/types";

interface SourceBadgeProps {
  source: Source;
  onClick?: (source: Source) => void;
  compact?: boolean;
}

export const SourceBadge = memo(function SourceBadge({
  source,
  onClick,
  compact = false,
}: SourceBadgeProps) {
  const lectureNum = source.lecture.num.toString().padStart(2, "0");
  const label = compact
    ? `L${lectureNum}`
    : `L${lectureNum} ${source.location.short_breadcrumb}`;

  const scorePercent = Math.round(source.relevance_score * 100);

  return (
    <Badge
      variant="outline"
      className="cursor-pointer border-primary/30 hover:bg-primary/10 hover:border-primary/50 transition-all duration-200 gap-1.5 py-1 px-2.5 text-xs font-medium"
      onClick={() => onClick?.(source)}
    >
      <FileText className="h-3 w-3 text-primary" />
      <span>{label}</span>
      {!compact && (
        <span className="text-muted-foreground/70 ml-1">{scorePercent}%</span>
      )}
    </Badge>
  );
});
