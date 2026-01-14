"use client";

import { useState, useCallback, KeyboardEvent } from "react";
import { Send, Square } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ChatInputProps {
  onSend: (message: string) => void;
  onCancel?: () => void;
  isLoading?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  onCancel,
  isLoading = false,
  disabled = false,
  placeholder = "Ask RTOS related questions...",
}: ChatInputProps) {
  const [input, setInput] = useState("");

  const handleSubmit = useCallback(() => {
    if (input.trim() && !disabled && !isLoading) {
      onSend(input.trim());
      setInput("");
    }
  }, [input, disabled, isLoading, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleCancel = useCallback(() => {
    onCancel?.();
  }, [onCancel]);

  return (
    <div className="relative flex items-end gap-3 p-4 border-t border-border/30 bg-background/60 backdrop-blur-xl">
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled || isLoading}
        rows={1}
        className="flex-1 resize-none rounded-xl border border-border/50 bg-muted/50 px-4 py-3 text-sm placeholder:text-muted-foreground/50 disabled:opacity-50 disabled:cursor-not-allowed min-h-12 max-h-50"
        onInput={(e) => {
          const target = e.target as HTMLTextAreaElement;
          target.style.height = "auto";
          target.style.height = Math.min(target.scrollHeight, 200) + "px";
        }}
      />
      {isLoading ? (
        <Button
          variant="outline"
          size="icon"
          onClick={handleCancel}
          className="h-12 w-12 rounded-xl shrink-0 border-border/50 hover:bg-destructive/10 hover:text-destructive hover:border-destructive/50 transition-all duration-200"
        >
          <Square className="h-4 w-4" />
          <span className="sr-only">Cancel</span>
        </Button>
      ) : (
        <Button
          onClick={handleSubmit}
          disabled={!input.trim() || disabled}
          size="icon"
          className="h-12 w-12 rounded-xl shrink-0 bg-gradient-to-br from-primary to-accent hover:opacity-90 disabled:opacity-30 disabled:from-muted disabled:to-muted transition-all duration-200 glow-sm"
        >
          <Send className="h-4 w-4" />
          <span className="sr-only">Send</span>
        </Button>
      )}
    </div>
  );
}
