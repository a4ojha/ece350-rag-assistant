"use client";

import { memo, useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  FileText,
  Code,
  Calculator,
  Image,
  ExternalLink,
} from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { Source } from "@/lib/types";

interface SourceCardProps {
  source: Source;
  onViewPdf?: (source: Source) => void;
  onShowContext?: (source: Source) => void;
  isExpanded?: boolean;
}

export const SourceCard = memo(function SourceCard({
  source,
  onViewPdf,
  onShowContext,
  isExpanded: initialExpanded = false,
}: SourceCardProps) {
  const [isExpanded, setIsExpanded] = useState(initialExpanded);

  const lectureNum = source.lecture.num.toString().padStart(2, "0");
  const scorePercent = Math.round(source.relevance_score * 100);

  return (
    <Card className="overflow-hidden border-border/30 bg-card/50 backdrop-blur-sm hover:border-primary/20 transition-all duration-300">
      <CardHeader className="p-4 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            {/* Lecture badge and score */}
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="font-mono text-xs border-primary/30 text-primary">
                L{lectureNum}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {scorePercent}% match
              </span>
            </div>

            {/* Title/breadcrumb */}
            <h4 className="font-medium text-sm text-foreground truncate">
              {source.lecture.title}
            </h4>
            <p className="text-xs text-muted-foreground mt-0.5 truncate">
              {source.location.breadcrumb}
            </p>
          </div>

          {/* Feature badges */}
          <div className="flex items-center gap-1.5 shrink-0">
            {source.features.has_code && (
              <Badge
                variant="secondary"
                className="h-6 w-6 p-0 flex items-center justify-center"
                title="Contains code"
              >
                <Code className="h-3 w-3" />
              </Badge>
            )}
            {source.features.has_math && (
              <Badge
                variant="secondary"
                className="h-6 w-6 p-0 flex items-center justify-center"
                title="Contains math"
              >
                <Calculator className="h-3 w-3" />
              </Badge>
            )}
            {source.features.has_images.length > 0 && (
              <Badge
                variant="secondary"
                className="h-6 w-6 p-0 flex items-center justify-center"
                title="Contains images"
              >
                <Image className="h-3 w-3" />
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-4 pt-0">
        {/* Preview text */}
        <p
          className={cn(
            "text-sm text-foreground/80 leading-relaxed",
            !isExpanded && "line-clamp-3"
          )}
        >
          {isExpanded ? source.text_full : source.text_preview}
        </p>

        {/* Expand/collapse button */}
        {source.text_full.length > source.text_preview.length && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="mt-2 h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="h-3 w-3 mr-1" />
                Show less
              </>
            ) : (
              <>
                <ChevronDown className="h-3 w-3 mr-1" />
                Show more
              </>
            )}
          </Button>
        )}

        <Separator className="my-3" />

        {/* Actions */}
        <div className="flex items-center gap-2">
          {source.source.pdf_file && onViewPdf && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onViewPdf(source)}
              className="h-8 text-xs border-primary/30 hover:bg-primary/10 hover:border-primary/50"
            >
              <FileText className="h-3 w-3 mr-1.5 text-primary" />
              View PDF
              {source.source.pdf_pages && (
                <span className="ml-1 text-muted-foreground">
                  p.{source.source.pdf_pages[0]}
                  {source.source.pdf_pages[1] !== source.source.pdf_pages[0] &&
                    `-${source.source.pdf_pages[1]}`}
                </span>
              )}
            </Button>
          )}
          {onShowContext && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onShowContext(source)}
              className="h-8 text-xs"
            >
              <ExternalLink className="h-3 w-3 mr-1.5" />
              Show context
            </Button>
          )}
        </div>

        {/* Keywords */}
        {source.features.keywords.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {source.features.keywords.slice(0, 5).map((keyword) => (
              <Badge
                key={keyword}
                variant="secondary"
                className="text-[10px] px-1.5 py-0 font-normal"
              >
                {keyword}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
});
