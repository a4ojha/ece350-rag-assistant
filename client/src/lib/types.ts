// API Response Types

export interface Source {
  chunk_id: string;
  relevance_score: number;
  lecture: {
    num: number;
    title: string;
  };
  location: {
    section: string;
    subsection: string | null;
    breadcrumb: string;
    short_breadcrumb: string;
  };
  source: {
    tex_file: string;
    tex_lines: [number, number];
    pdf_file: string | null;
    pdf_pages: [number, number] | null;
  };
  text_preview: string;
  text_full: string;
  word_count: number;
  features: {
    has_code: boolean;
    has_math: boolean;
    has_images: string[];
    keywords: string[];
  };
  position: {
    in_section: string;
    in_lecture: number;
  };
}

export interface RetrievalStats {
  retrieval_time_ms: number;
  avg_score: number;
}

export interface QueryMetadata {
  model_used: string;
  generation_time_ms: number;
}

export interface QueryResponse {
  query: string;
  answer: string;
  confidence: "high" | "low" | "no_context";
  sources: Source[];
  retrieval_stats: RetrievalStats;
  metadata: QueryMetadata;
}

export interface QueryRequest {
  question: string;
  top_k?: number;
}

// Chat Types

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  confidence?: "high" | "low" | "no_context";
  stats?: {
    retrieval_time_ms: number;
    generation_time_ms: number;
    avg_score: number;
  };
  timestamp: Date;
}

// API Error Types

export interface APIError {
  error: string;
  message: string;
  status?: number;
}

// Health Check Response

export interface HealthResponse {
  status: "healthy" | "unhealthy";
  message?: string;
}

// Chunk Context Response

export interface ChunkContextResponse {
  chunk: Source;
  context: {
    before: Source[];
    after: Source[];
  };
}

// Lecture Search Response

export interface LectureInfo {
  lecture_num: number;
  title: string;
  sections: string[];
  chunk_count: number;
}

export interface LectureSearchResponse {
  lectures: LectureInfo[];
}
