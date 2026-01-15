import type {
  QueryRequest,
  QueryResponse,
  Source,
  ChunkContextResponse,
  HealthResponse,
} from "./types";

const API_BASE = "/api";

class APIClient {
  private abortController: AbortController | null = null;

  /**
   * Cancel any in-flight request
   */
  cancelPendingRequest(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  /**
   * Send a query to the RAG pipeline
   */
  async query(request: QueryRequest): Promise<QueryResponse> {
    this.cancelPendingRequest();
    this.abortController = new AbortController();

    const response = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
      signal: this.abortController.signal,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        error: "Unknown error",
        message: response.statusText,
      }));

      // Special handling for rate limit errors
      if (response.status === 429) {
        const rateLimitError = new Error(error.message || "Rate limit exceeded");
        (rateLimitError as any).isRateLimit = true;
        (rateLimitError as any).limit = error.limit;
        throw rateLimitError;
      }

      throw new Error(error.message || error.error || "Query failed");
    }

    return response.json();
  }

  /**
   * Get a specific chunk by ID
   */
  async getChunk(chunkId: string): Promise<Source> {
    const response = await fetch(`${API_BASE}/chunks/${chunkId}`);

    if (!response.ok) {
      throw new Error(`Failed to fetch chunk: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get surrounding context for a chunk
   */
  async getChunkContext(
    chunkId: string,
    size: number = 2
  ): Promise<ChunkContextResponse> {
    const response = await fetch(
      `${API_BASE}/chunks/${chunkId}/context?size=${size}`
    );

    if (!response.ok) {
      throw new Error(`Failed to fetch chunk context: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get PDF URL for a lecture
   */
  getPdfUrl(lectureNum: number): string {
    return `${API_BASE}/pdf/${lectureNum}`;
  }

  /**
   * Health check
   */
  async checkHealth(): Promise<HealthResponse> {
    try {
      const response = await fetch(`${API_BASE}/health`);
      if (!response.ok) {
        return { status: "unhealthy", message: response.statusText };
      }
      return response.json();
    } catch {
      return { status: "unhealthy", message: "Failed to connect to API" };
    }
  }
}

export const apiClient = new APIClient();
