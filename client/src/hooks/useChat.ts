import { useState, useCallback, useRef } from "react";
import type { ChatMessage, Source } from "@/lib/types";
import { apiClient } from "@/lib/api";

// set to false for production
const TEST_MODE = false; // When true, shows skeleton without API call

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loadingRef = useRef(false);

  const sendMessage = useCallback(async (question: string) => {
    if (loadingRef.current || !question.trim()) return;

    loadingRef.current = true;
    setIsLoading(true);
    setError(null);

    // Add user message immediately (optimistic UI)
    const userMessage: ChatMessage = {
      id: generateId(),
      role: "user",
      content: question.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);

    // Test mode: just show skeleton, no API call
    if (TEST_MODE) {
      return;
    }

    try {
      const response = await apiClient.query({ question: question.trim() });

      // Add assistant message with response
      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: response.answer,
        sources: response.sources,
        confidence: response.confidence,
        stats: {
          retrieval_time_ms: response.retrieval_stats.retrieval_time_ms,
          generation_time_ms: response.metadata.generation_time_ms,
          avg_score: response.retrieval_stats.avg_score,
        },
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "An unexpected error occurred";
      setError(errorMessage);

      // Add error message to chat
      const errorChatMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: `Sorry, I encountered an error: ${errorMessage}`,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorChatMessage]);
    } finally {
      setIsLoading(false);
      loadingRef.current = false;
    }
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
    apiClient.cancelPendingRequest();
  }, []);

  const cancelRequest = useCallback(() => {
    apiClient.cancelPendingRequest();
    setIsLoading(false);
    loadingRef.current = false;
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearChat,
    cancelRequest,
  };
}

// Origin of PDF open action - determines layout behavior
export type PdfOrigin = "chat" | "sources-panel";

// Hook for managing selected source for PDF viewing with panel layout
export function useSourceSelection() {
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  const [isPdfOpen, setIsPdfOpen] = useState(false);
  const [pdfOrigin, setPdfOrigin] = useState<PdfOrigin>("chat");

  const openPdf = useCallback((source: Source, origin: PdfOrigin = "chat") => {
    setSelectedSource(source);
    setPdfOrigin(origin);
    setIsPdfOpen(true);
  }, []);

  const closePdf = useCallback(() => {
    setIsPdfOpen(false);
    // Keep selectedSource briefly for exit animation, then clear
    setTimeout(() => {
      setSelectedSource(null);
      setPdfOrigin("chat");
    }, 300);
  }, []);

  // Swap PDF content without closing panel (for multiple PDFs)
  const swapPdf = useCallback((source: Source) => {
    setSelectedSource(source);
  }, []);

  return {
    selectedSource,
    isPdfOpen,
    pdfOrigin,
    openPdf,
    closePdf,
    swapPdf,
  };
}
