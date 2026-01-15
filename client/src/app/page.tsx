"use client";

import { useState, useCallback } from "react";
import { Cpu, FileStack, LibraryBig } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ChatContainer, ChatInput } from "@/components/chat";
import { SourcePanel } from "@/components/sources";
import { PDFViewerPanel } from "@/components/pdf";
import { useChat, useSourceSelection } from "@/hooks/useChat";
import type { Source } from "@/lib/types";

// Deduplicate sources by breadcrumb, keeping the highest relevance score
function deduplicateSources(sources: Source[]): Source[] {
  const seen = new Map<string, Source>();
  for (const source of sources) {
    const key = source.location.breadcrumb;
    const existing = seen.get(key);
    if (!existing || source.relevance_score > existing.relevance_score) {
      seen.set(key, source);
    }
  }
  return Array.from(seen.values());
}

export default function Home() {
  const { messages, isLoading, sendMessage, clearChat, cancelRequest } =
    useChat();
  const { selectedSource, isPdfOpen, pdfOrigin, openPdf, closePdf, swapPdf } = useSourceSelection();

  // Source panel state
  const [isSourcePanelOpen, setIsSourcePanelOpen] = useState(false);
  const [panelSources, setPanelSources] = useState<Source[]>([]);
  const [panelAvgScore, setPanelAvgScore] = useState<number | undefined>();

  // Get the latest assistant message sources for the panel
  const latestAssistantMessage = [...messages]
    .reverse()
    .find((m) => m.role === "assistant" && m.sources);

  // Handle clicking a source- opens PDF in left panel
  const handleSourceClick = useCallback(
    (source: Source) => {
      if (source.source.pdf_file) {
        // If PDF panel is already open, swap content; otherwise open it
        if (isPdfOpen) {
          swapPdf(source);
        } else {
          openPdf(source);
        }
      } else {
        // If no PDF, open the source panel
        const sources = latestAssistantMessage?.sources || [source];
        setPanelSources(sources);
        setPanelAvgScore(latestAssistantMessage?.stats?.avg_score);
        setIsSourcePanelOpen(true);
      }
    },
    [openPdf, swapPdf, isPdfOpen, latestAssistantMessage]
  );

  // Handle "View All Sources" button - opens sources panel on right
  const handleViewAllSources = useCallback(() => {
    if (latestAssistantMessage?.sources) {
      setPanelSources(latestAssistantMessage.sources);
      setPanelAvgScore(latestAssistantMessage.stats?.avg_score);
      setIsSourcePanelOpen(true);
    }
  }, [latestAssistantMessage]);

  // Handle viewing PDF from within sources panel (secondary flow)
  // This opens PDF in "connected" mode - PDF fills left, sources stay right, chat hidden
  const handleViewPdfFromPanel = useCallback(
    (source: Source) => {
      if (isPdfOpen) {
        swapPdf(source);
      } else {
        openPdf(source, "sources-panel");
      }
    },
    [openPdf, swapPdf, isPdfOpen]
  );

  const handleSend = useCallback(
    (message: string) => {
      sendMessage(message);
    },
    [sendMessage]
  );

  return (
    <div className="flex flex-col h-screen bg-background bg-gradient-mesh overflow-hidden">
      {/* PDF Viewer Panel - Fixed Left Side (chat flow) or Full Width minus sources (sources-panel flow) */}
      <PDFViewerPanel
        source={selectedSource}
        isOpen={isPdfOpen}
        onClose={closePdf}
        flexibleWidth={pdfOrigin === "sources-panel"}
      />

      {/* Main Layout Container - Shifts right when PDF is open (chat flow), or hidden (sources-panel flow) */}
      <div
        className={`
          main-content
          flex flex-col h-screen
          transition-all duration-300 ease-out
          ${isPdfOpen && pdfOrigin === "chat" ? "pdf-open" : ""}
          ${isPdfOpen && pdfOrigin === "sources-panel" ? "hidden" : ""}
        `}
      >
        {/* Header */}
        <header className="sticky top-0 z-10 shrink-0 border-b border-border/50 bg-background/60 backdrop-blur-lg select-none relative after:absolute after:left-0 after:right-0 after:top-full after:h-6 after:bg-linear-to-b after:from-neutral-800/15 after:to-transparent after:pointer-events-none">

          <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary/70 to-accent/70 text-primary-foreground glow-sm">
                <Cpu className="h-4 w-4" />
              </div>
              <div>
                <h1 className="font-italic text-md font-bold gradient-text">ECE 350 Assistant</h1>
                <p className="font-display text-sm text-muted-foreground">
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
                    Sources ({deduplicateSources(latestAssistantMessage.sources).length})
                  </Button>
                )}

              {messages.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={clearChat}
                  className="h-8 text-xs text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  Clear chat
                </Button>
              )}

              <Separator orientation="vertical" className="h-6 mx-1" />

              <Button variant="secondary" size="icon" className="h-9 w-9" asChild>
                <a
                  href="https://github.com/jzarnett/ece350/blob/main/lectures/compiled"
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Source lecture notes"
                >
                  <LibraryBig className="size-5" />
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
      </div>

      {/* Source Panel - Slides in from right */}
      <SourcePanel
        sources={panelSources}
        isOpen={isSourcePanelOpen}
        onClose={() => setIsSourcePanelOpen(false)}
        onViewPdf={handleViewPdfFromPanel}
        avgScore={panelAvgScore}
        isPdfOpen={isPdfOpen}
        pdfOrigin={pdfOrigin}
      />
    </div>
  );
}
