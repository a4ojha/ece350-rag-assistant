"use client";

import { useState, useCallback } from "react";
import { Cpu, FileStack, BookText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ChatContainer, ChatInput } from "@/components/chat";
import { SourcePanel } from "@/components/sources";
import { PDFViewerModal } from "@/components/pdf";
import { useChat, useSourceSelection } from "@/hooks/useChat";
import type { Source } from "@/lib/types";

export default function Home() {
  const { messages, isLoading, sendMessage, clearChat, cancelRequest } =
    useChat();
  const { selectedSource, isPdfOpen, openPdf, closePdf } = useSourceSelection();

  // Source panel state
  const [isSourcePanelOpen, setIsSourcePanelOpen] = useState(false);
  const [panelSources, setPanelSources] = useState<Source[]>([]);
  const [panelAvgScore, setPanelAvgScore] = useState<number | undefined>();

  // Get the latest assistant message sources for the panel
  const latestAssistantMessage = [...messages]
    .reverse()
    .find((m) => m.role === "assistant" && m.sources);

  const handleSourceClick = useCallback(
    (source: Source) => {
      if (source.source.pdf_file) {
        openPdf(source);
      } else {
        // If no PDF, just open the source panel
        const sources = latestAssistantMessage?.sources || [source];
        setPanelSources(sources);
        setPanelAvgScore(latestAssistantMessage?.stats?.avg_score);
        setIsSourcePanelOpen(true);
      }
    },
    [openPdf, latestAssistantMessage]
  );

  const handleViewAllSources = useCallback(() => {
    if (latestAssistantMessage?.sources) {
      setPanelSources(latestAssistantMessage.sources);
      setPanelAvgScore(latestAssistantMessage.stats?.avg_score);
      setIsSourcePanelOpen(true);
    }
  }, [latestAssistantMessage]);

  const handleSend = useCallback(
    (message: string) => {
      sendMessage(message);
    },
    [sendMessage]
  );

  return (
    <div className="flex flex-col h-screen bg-background bg-gradient-mesh">
      {/* Header */}
      <header className="sticky top-0 z-10 shrink-0 border-b border-border/50 bg-background/60 backdrop-blur-xl select-none">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary/70 to-accent/70 text-primary-foreground glow-sm">
              <Cpu className="h-4 w-4" />
            </div>
            <div>
              <h1 className="font-italic text-sm font-bold gradient-text">ECE 350 Assistant</h1>
              <p className="font-display text-xs text-muted-foreground">
                Real-Time Operating Systems
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {latestAssistantMessage?.sources &&
              latestAssistantMessage.sources.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleViewAllSources}
                  className="h-8 text-xs gap-1.5 hover:text-foreground/50 cursor-pointer"
                >
                  <FileStack className="h-3.5 w-3.5" />
                  Sources ({latestAssistantMessage.sources.length})
                </Button>
              )}

            {messages.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearChat}
                className="h-8 text-xs text-muted-foreground hover:text-foreground cursor-pointer"
              >
                Clear chat
              </Button>
            )}

            <Separator orientation="vertical" className="h-6 mx-1" />

            <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
              <a
                href="https://github.com/jzarnett/ece350/blob/main/lectures/compiled"
                target="_blank"
                rel="noopener noreferrer"
                title="Source lecture notes"
              >
                <BookText className="h-4 w-4" />
              </a>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden max-w-5xl mx-auto w-full">
        <ChatContainer
          messages={messages}
          isLoading={isLoading}
          onSourceClick={handleSourceClick}
          onExampleClick={handleSend}
        />

        <ChatInput
          onSend={handleSend}
          onCancel={cancelRequest}
          isLoading={isLoading}
        />
      </main>

      {/* Source Panel */}
      <SourcePanel
        sources={panelSources}
        isOpen={isSourcePanelOpen}
        onClose={() => setIsSourcePanelOpen(false)}
        onViewPdf={openPdf}
        avgScore={panelAvgScore}
      />

      {/* PDF Viewer Modal */}
      <PDFViewerModal
        source={selectedSource}
        isOpen={isPdfOpen}
        onClose={closePdf}
      />
    </div>
  );
}
