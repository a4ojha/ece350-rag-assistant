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
  const scorePercent = Math.round(source.relevance_score * 100);

  // Score color: green/yellow/red based on relevance
  const scoreColor =
    scorePercent > 55
      ? "text-green-600/70 dark:text-green-400/70"
      : scorePercent > 35
        ? "text-amber-600/70 dark:text-amber-400/70"
        : "text-red-600/70 dark:text-red-400/70";

  // Parse breadcrumb into parts: "L4 > Section > Subsection"
  const breadcrumbParts = source.location.short_breadcrumb.split(" > ");
  const lecturePart = breadcrumbParts[0]; // "L4"
  const hierarchyParts = breadcrumbParts.slice(1); // ["Section", "Subsection"]

  if (compact) {
    return (
      <Badge
        variant="outline"
        className="cursor-pointer border-primary/30 hover:bg-primary/10 hover:border-primary/50 transition-all duration-200 gap-1.5 py-1 px-2.5 text-xs font-medium"
        onClick={() => onClick?.(source)}
      >
        <FileText className="h-3 w-3 text-primary" />
        <span>L{lectureNum}</span>
      </Badge>
    );
  }

  return (
    <Badge
      variant="outline"
      className="cursor-pointer border-primary/30 hover:bg-primary/10 hover:border-primary/50 transition-all duration-200 gap-1.5 py-1 px-2.5 text-xs font-medium"
      onClick={() => onClick?.(source)}
    >
      <FileText className="h-3 w-3 text-primary" />
      <span>{lecturePart}</span>
      {hierarchyParts.length > 0 && (
        <span className="text-muted-foreground/80">
          {" > "}
          {hierarchyParts.join(" > ")}
        </span>
      )}
      <span className={`${scoreColor} ml-1`}>{scorePercent}%</span>
    </Badge>
  );
});
