"use client";

import { Bot } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export function ChatSkeleton() {
  return (
    <div className="flex gap-4 px-4 py-6 bg-muted/30">
      {/* Avatar */}
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
        <Bot className="h-4 w-4" />
      </div>

      {/* Content */}
      <div className="flex-1 space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground">
            ECE 350 Assistant
          </span>
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary/60 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
            </span>
            Thinking...
          </span>
        </div>

        {/* Skeleton lines */}
        <div className="space-y-2.5">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-[90%]" />
          <Skeleton className="h-4 w-[75%]" />
        </div>

        {/* Skeleton sources */}
        <div className="flex gap-2 pt-2">
          <Skeleton className="h-6 w-20 rounded-full" />
          <Skeleton className="h-6 w-24 rounded-full" />
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
      </div>
    </div>
  );
}
