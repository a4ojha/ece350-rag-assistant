"use client";

import { useState, useCallback, useEffect } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Download,
  Loader2,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiClient } from "@/lib/api";
import type { Source } from "@/lib/types";

interface PDFViewerModalProps {
  source: Source | null;
  isOpen: boolean;
  onClose: () => void;
}

export function PDFViewerModal({ source, isOpen, onClose }: PDFViewerModalProps) {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pdfComponents, setPdfComponents] = useState<{
    Document: React.ComponentType<any>;
    Page: React.ComponentType<any>;
  } | null>(null);

  // Dynamically load react-pdf on client side only
  useEffect(() => {
    if (typeof window !== "undefined" && isOpen && !pdfComponents) {
      import("react-pdf").then((mod) => {
        // Set up worker
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
    if (source?.source.pdf_pages) {
      setCurrentPage(source.source.pdf_pages[0]);
    } else {
      setCurrentPage(1);
    }
    setScale(1.0);
    setError(null);
    setIsLoading(true);
  }, [source]);

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

  const goToPage = useCallback(
    (page: number) => {
      if (numPages) {
        setCurrentPage(Math.max(1, Math.min(page, numPages)));
      }
    },
    [numPages]
  );

  const zoomIn = useCallback(() => {
    setScale((s) => Math.min(s + 0.25, 3));
  }, []);

  const zoomOut = useCallback(() => {
    setScale((s) => Math.max(s - 0.25, 0.5));
  }, []);

  if (!source) return null;

  const pdfUrl = apiClient.getPdfUrl(source.lecture.num);
  const lectureNum = source.lecture.num.toString().padStart(2, "0");

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl h-[90vh] p-0 flex flex-col overflow-hidden">
        {/* Header */}
        <DialogHeader className="p-4 pb-0 shrink-0">
          <DialogTitle className="text-lg font-semibold truncate">
            Lecture {lectureNum}: {source.lecture.title}
          </DialogTitle>
          <p className="text-sm text-muted-foreground mt-0.5 truncate">
            {source.location.breadcrumb}
          </p>
        </DialogHeader>

        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30 shrink-0">
          {/* Page navigation */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              onClick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              className="h-8 w-8"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm tabular-nums min-w-[80px] text-center">
              Page {currentPage} / {numPages || "..."}
            </span>
            <Button
              variant="outline"
              size="icon"
              onClick={() => goToPage(currentPage + 1)}
              disabled={!numPages || currentPage >= numPages}
              className="h-8 w-8"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>

          {/* Zoom controls */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              onClick={zoomOut}
              disabled={scale <= 0.5}
              className="h-8 w-8"
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="text-sm tabular-nums min-w-[60px] text-center">
              {Math.round(scale * 100)}%
            </span>
            <Button
              variant="outline"
              size="icon"
              onClick={zoomIn}
              disabled={scale >= 3}
              className="h-8 w-8"
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
          </div>

          {/* Download */}
          <Button variant="outline" size="sm" asChild className="h-8">
            <a href={pdfUrl} download={`L${lectureNum}.pdf`}>
              <Download className="h-4 w-4 mr-1.5" />
              Download
            </a>
          </Button>
        </div>

        {/* PDF Content */}
        <ScrollArea className="flex-1">
          <div className="flex justify-center p-4 min-h-full">
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
                className="shadow-lg rounded-lg overflow-hidden"
              >
                <pdfComponents.Page
                  pageNumber={currentPage}
                  scale={scale}
                  loading={<PDFLoadingState />}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                />
              </pdfComponents.Document>
            )}
          </div>
        </ScrollArea>

        {/* Page range indicator */}
        {source.source.pdf_pages && (
          <div className="px-4 py-2 border-t bg-muted/30 text-center text-xs text-muted-foreground shrink-0">
            Source content spans pages {source.source.pdf_pages[0]}
            {source.source.pdf_pages[1] !== source.source.pdf_pages[0] &&
              ` - ${source.source.pdf_pages[1]}`}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function PDFLoadingState() {
  return (
    <div className="flex items-center justify-center py-20">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  );
}
