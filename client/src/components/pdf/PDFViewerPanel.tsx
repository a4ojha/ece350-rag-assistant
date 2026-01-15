"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import {
  ZoomIn,
  ZoomOut,
  Download,
  Loader2,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";
import type { Source } from "@/lib/types";
import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";

interface PDFViewerPanelProps {
  source: Source | null;
  isOpen: boolean;
  onClose: () => void;
  /** When true, PDF takes full width minus sources panel (for sources-panel flow) */
  flexibleWidth?: boolean;
}

export function PDFViewerPanel({ source, isOpen, onClose, flexibleWidth = false }: PDFViewerPanelProps) {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.2);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pdfComponents, setPdfComponents] = useState<{
    Document: React.ComponentType<any>;
    Page: React.ComponentType<any>;
  } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // Dynamically load react-pdf on client side only
  useEffect(() => {
    if (typeof window !== "undefined" && isOpen && !pdfComponents) {
      import("react-pdf").then((mod) => {
        mod.pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${mod.pdfjs.version}/build/pdf.worker.min.mjs`;
        setPdfComponents({
          Document: mod.Document,
          Page: mod.Page,
        });
      });
    }
  }, [isOpen, pdfComponents]);

  // Reset state when source changes
  useEffect(() => {
    setScale(1.2);
    setError(null);
    setIsLoading(true);
  }, [source]);

  // Scroll to initial page after document loads
  useEffect(() => {
    if (!isLoading && numPages && source?.source.pdf_pages) {
      const targetPage = source.source.pdf_pages[0];
      // Small delay to ensure pages are rendered
      setTimeout(() => {
        const pageElement = pageRefs.current.get(targetPage);
        if (pageElement && containerRef.current) {
          pageElement.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }, 100);
    }
  }, [isLoading, numPages, source]);

  // Track current visible page during scroll
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !numPages) return;

    const handleScroll = () => {
      const containerRect = container.getBoundingClientRect();
      const containerCenter = containerRect.top + containerRect.height / 3;

      let closestPage = 1;
      let closestDistance = Infinity;

      pageRefs.current.forEach((element, pageNum) => {
        const rect = element.getBoundingClientRect();
        const pageCenter = rect.top + rect.height / 2;
        const distance = Math.abs(pageCenter - containerCenter);

        if (distance < closestDistance) {
          closestDistance = distance;
          closestPage = pageNum;
        }
      });

      setCurrentPage(closestPage);
    };

    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => container.removeEventListener("scroll", handleScroll);
  }, [numPages]);

  // Ctrl+scroll zoom handler
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleWheel = (e: WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        setScale((s) => Math.min(Math.max(s + delta, 0.5), 3));
      }
    };

    container.addEventListener("wheel", handleWheel, { passive: false });
    return () => container.removeEventListener("wheel", handleWheel);
  }, []);

  const onDocumentLoadSuccess = useCallback(
    ({ numPages }: { numPages: number }) => {
      setNumPages(numPages);
      setIsLoading(false);
    },
    []
  );

  const onDocumentLoadError = useCallback((error: Error) => {
    console.error("PDF load error:", error);
    setError("Failed to load PDF");
    setIsLoading(false);
  }, []);

  const zoomIn = useCallback(() => {
    setScale((s) => Math.min(s + 0.25, 3));
  }, []);

  const zoomOut = useCallback(() => {
    setScale((s) => Math.max(s - 0.25, 0.5));
  }, []);

  const setPageRef = useCallback((pageNum: number, element: HTMLDivElement | null) => {
    if (element) {
      pageRefs.current.set(pageNum, element);
    } else {
      pageRefs.current.delete(pageNum);
    }
  }, []);

  if (!source) return null;

  const pdfUrl = apiClient.getPdfUrl(source.lecture.num);
  const lectureNum = source.lecture.num;
  const lectureNumPadded = source.lecture.num.toString().padStart(2, "0");

  // Sources panel width is w-full sm:max-w-md (448px on sm+)
  const sourcesPanelWidth = "28rem";

  return (
    <div
      className={`
        pdf-panel
        fixed left-0 top-0 h-screen z-40
        flex flex-col
        bg-background/95 backdrop-blur-xl
        border-r border-border/50
        transform transition-all duration-300 ease-out
        ${isOpen ? "translate-x-0 opacity-100" : "-translate-x-full opacity-0"}
        ${flexibleWidth ? "pdf-panel-flexible" : ""}
      `}
      style={{
        width: flexibleWidth
          ? `calc(100vw - ${sourcesPanelWidth})`
          : "min(55vw, 800px)"
      }}
    >
      {/* Header */}
      <div className="shrink-0 p-4 pb-2 border-b border-border/30">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h2 className="text-base font-semibold truncate">
              Lecture {lectureNum}: {source.lecture.title}
            </h2>
            <p className="text-sm font-display text-muted-foreground mt-0.5 wrap">
              {(() => {
                const parts = source.location.breadcrumb.split(" > ");
                if (parts.length <= 1) return source.location.breadcrumb;
                const leading = parts.slice(0, -1).join(" > ");
                const last = parts[parts.length - 1];
                return (
                  <>
                    {leading} &gt; <span className="text-foreground font-medium">{last}</span>
                  </>
                );
              })()}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8 shrink-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border/30 bg-muted/20 shrink-0">
        {/* Page indicator (read-only, updates on scroll) */}
        <span className="text-xs tabular-nums text-muted-foreground">
          Page {currentPage} / {numPages || "..."}
        </span>

        {/* Zoom controls */}
        <div className="flex items-center gap-1.5">
          <Button
            variant="outline"
            size="icon"
            onClick={zoomOut}
            disabled={scale <= 0.5}
            className="h-7 w-7"
            title="Zoom out (or Ctrl+scroll)"
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </Button>
          <span className="text-xs tabular-nums min-w-[50px] text-center">
            {Math.round(scale * 100)}%
          </span>
          <Button
            variant="outline"
            size="icon"
            onClick={zoomIn}
            disabled={scale >= 3}
            className="h-7 w-7"
            title="Zoom in (or Ctrl+scroll)"
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </Button>
        </div>

        {/* Download */}
        <Button variant="outline" size="sm" asChild className="h-7 text-xs">
          <a href={pdfUrl} download={`L${lectureNumPadded}.pdf`}>
            <Download className="h-3.5 w-3.5 mr-1" />
            Download
          </a>
        </Button>
      </div>

      {/* PDF Content - continuous scroll */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto"
      >
        <div className="flex flex-col items-center p-4 gap-4">
          {error ? (
            <div className="flex flex-col items-center justify-center text-muted-foreground py-12">
              <p className="text-sm">{error}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setError(null);
                  setIsLoading(true);
                }}
                className="mt-4"
              >
                Try again
              </Button>
            </div>
          ) : !pdfComponents ? (
            <PDFLoadingState />
          ) : (
            <pdfComponents.Document
              file={pdfUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={<PDFLoadingState />}
              className="flex flex-col items-center gap-4"
            >
              {numPages && Array.from({ length: numPages }, (_, i) => i + 1).map((pageNum) => (
                <div
                  key={pageNum}
                  ref={(el) => setPageRef(pageNum, el)}
                  className="shadow-xl rounded-lg overflow-hidden"
                >
                  <pdfComponents.Page
                    pageNumber={pageNum}
                    scale={scale}
                    loading={<PDFLoadingState />}
                    renderTextLayer={true}
                    renderAnnotationLayer={true}
                  />
                </div>
              ))}
            </pdfComponents.Document>
          )}
        </div>
      </div>

      {/* Page range indicator */}
      {/* {source.source.pdf_pages && (
        <div className="px-4 py-2 border-t border-border/30 bg-muted/20 text-center text-xs text-muted-foreground shrink-0">
          Source content spans pages {source.source.pdf_pages[0]}
          {source.source.pdf_pages[1] !== source.source.pdf_pages[0] &&
            ` - ${source.source.pdf_pages[1]}`}
        </div>
      )} */}
    </div>
  );
}

function PDFLoadingState() {
  return (
    <div className="flex items-center justify-center py-20">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  );
}
