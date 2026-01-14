"use client";

import { memo } from "react";
import { User, Bot, Clock, Zap, AlertCircle, CheckCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageType, Source } from "@/lib/types";
import { SourceBadge } from "./SourceBadge";

interface ChatMessageProps {
  message: ChatMessageType;
  onSourceClick?: (source: Source) => void;
}

export const ChatMessage = memo(function ChatMessage({
  message,
  onSourceClick,
}: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "group flex gap-4 px-4 py-6",
        isUser ? "bg-transparent" : "bg-muted/20"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          isUser
            ? "bg-secondary text-secondary-foreground"
            : "bg-gradient-to-br from-primary to-accent text-primary-foreground glow-sm"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Content */}
      <div className="flex-1 space-y-3 overflow-hidden">
        {/* Role label */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground">
            {isUser ? "You" : "ECE 350 Assistant"}
          </span>
          {!isUser && message.confidence && (
            <ConfidenceBadge confidence={message.confidence} />
          )}
        </div>

        {/* Message content */}
        <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none">
          <ReactMarkdown
            components={{
              p: ({ children }) => (
                <p className="mb-3 last:mb-0 leading-relaxed text-foreground/90">
                  {children}
                </p>
              ),
              ul: ({ children }) => (
                <ul className="mb-3 list-disc pl-4 space-y-1">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="mb-3 list-decimal pl-4 space-y-1">{children}</ol>
              ),
              li: ({ children }) => (
                <li className="text-foreground/90">{children}</li>
              ),
              code: ({ children, className }) => {
                const isInline = !className;
                if (isInline) {
                  return (
                    <code className="rounded bg-muted px-1.5 py-0.5 text-sm font-mono">
                      {children}
                    </code>
                  );
                }
                return (
                  <code className="block rounded-lg bg-muted p-3 text-sm font-mono overflow-x-auto">
                    {children}
                  </code>
                );
              },
              pre: ({ children }) => (
                <pre className="mb-3 overflow-x-auto rounded-lg bg-muted p-0">
                  {children}
                </pre>
              ),
              strong: ({ children }) => (
                <strong className="font-semibold text-foreground">
                  {children}
                </strong>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-2">
            {message.sources.map((source) => (
              <SourceBadge
                key={source.chunk_id}
                source={source}
                onClick={onSourceClick}
              />
            ))}
          </div>
        )}

        {/* Stats */}
        {!isUser && message.stats && (
          <div className="flex items-center gap-4 pt-2 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {message.stats.retrieval_time_ms}ms retrieval
            </span>
            <span className="flex items-center gap-1">
              <Zap className="h-3 w-3" />
              {message.stats.generation_time_ms}ms generation
            </span>
          </div>
        )}
      </div>
    </div>
  );
});

function ConfidenceBadge({
  confidence,
}: {
  confidence: "high" | "low" | "no_context";
}) {
  const config = {
    high: {
      icon: CheckCircle,
      label: "High confidence",
      className: "text-green-600 dark:text-green-400",
    },
    low: {
      icon: AlertCircle,
      label: "Low confidence",
      className: "text-amber-600 dark:text-amber-400",
    },
    no_context: {
      icon: AlertCircle,
      label: "No context found",
      className: "text-red-600 dark:text-red-400",
    },
  };

  const { icon: Icon, label, className } = config[confidence];

  return (
    <span className={cn("flex items-center gap-1 text-xs", className)}>
      <Icon className="h-3 w-3" />
      {label}
    </span>
  );
}
