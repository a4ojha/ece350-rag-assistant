"use client";

import { useRef, useEffect, memo } from "react";
import { BotMessageSquare } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatMessage } from "./ChatMessage";
import { ChatSkeleton } from "./ChatSkeleton";
import type { ChatMessage as ChatMessageType, Source } from "@/lib/types";

interface ChatContainerProps {
  messages: ChatMessageType[];
  isLoading?: boolean;
  onSourceClick?: (source: Source) => void;
  onExampleClick?: (question: string) => void;
}

export const ChatContainer = memo(function ChatContainer({
  messages,
  isLoading = false,
  onSourceClick,
  onExampleClick,
}: ChatContainerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  if (messages.length === 0 && !isLoading) {
    return <EmptyState onExampleClick={onExampleClick} />;
  }

  return (
    <div className="flex-1 min-h-0 overflow-hidden animate-fade-in" ref={scrollRef}>
      <ScrollArea className="h-full">
        <div className="divide-y divide-border/30">
          {messages.map((message, index) => (
            <div
              key={message.id}
              className="animate-float-up"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <ChatMessage
                message={message}
                onSourceClick={onSourceClick}
              />
            </div>
          ))}
          {isLoading && (
            <div className="animate-float-up">
              <ChatSkeleton />
            </div>
          )}
        </div>
        <div ref={bottomRef} />
      </ScrollArea>
    </div>
  );
});

interface EmptyStateProps {
  onExampleClick?: (question: string) => void;
}

function EmptyState({ onExampleClick }: EmptyStateProps) {
  const examples = [
    "What is thrashing?",
    "Explain the SCAN algorithm.",
    "Summarize file allocation methods.",
    "What are semaphores?",
  ];

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 text-center animate-fade-in">
      <div className="rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 p-6 mb-6 glow animate-float-up">
        <BotMessageSquare className="h-12 w-12 text-primary/80" />
      </div>
      <h2 className="text-3xl font-display font-bold gradient-text mb-1 animate-float-up" style={{ animationDelay: "50ms" }}>
        ECE 350 Assistant
      </h2>
      <p className="text-xl font-display text-muted-foreground max-w-md leading-relaxed mb-4 animate-float-up" style={{ animationDelay: "100ms" }}>
        Ask any questions about course content.
      </p>
      <p className="text-muted-foreground/80 max-w-md leading-relaxed text-sm animate-float-up" style={{ animationDelay: "150ms" }}>
        Responses are strictly based off of Prof. Zarnett's{" "}
        <a
          href="https://github.com/jzarnett/ece350/tree/main/lectures/compiled"
          target="_blank"
          rel="noopener noreferrer"
          className="text-muted-foreground/60 underline decoration-dotted underline-offset-2 hover:opacity-70 transition-opacity"
        >
          lecture notes
        </a>{""}.
      </p>
      <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl w-full">
        {examples.map((question, index) => (
          <ExampleQuestion
            key={question}
            question={question}
            onClick={onExampleClick}
            animationDelay={200 + index * 50}
          />
        ))}
      </div>
    </div>
  );
}

interface ExampleQuestionProps {
  question: string;
  onClick?: (question: string) => void;
  animationDelay?: number;
}

function ExampleQuestion({ question, onClick, animationDelay }: ExampleQuestionProps) {
  return (
    <button
      onClick={() => onClick?.(question)}
      className="text-left p-3 rounded-xl border border-border/50 bg-card/50 hover:bg-primary/10 hover:border-primary/30 transition-all duration-200 text-sm text-muted-foreground hover:text-foreground cursor-pointer animate-float-up"
      style={animationDelay ? { animationDelay: `${animationDelay}ms` } : undefined}
    >
      {question}
    </button>
  );
}
