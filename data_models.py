"""
Enhanced data models for traceable, hierarchical lecture content.
These models are designed to support future frontend integration.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Tuple
from pathlib import Path
import hashlib
import json

@dataclass
class SourceLocation:
    """Precise location of content in source files."""
    tex_file: str
    tex_file_hash: str
    char_start: int
    char_end: int
    line_start: int
    line_end: int
    pdf_file: Optional[str] = None
    pdf_page_start: Optional[int] = None
    pdf_page_end: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class HierarchyPath:
    """Hierarchical location within document structure."""
    lecture_num: int
    lecture_title: str
    section_id: str
    section_title: str
    subsection_id: Optional[str] = None
    subsection_title: Optional[str] = None
    
    @property
    def breadcrumb(self) -> str:
        """Human-readable hierarchy path."""
        parts = [f"Lecture {self.lecture_num}: {self.lecture_title}"]
        parts.append(self.section_title)
        if self.subsection_title:
            parts.append(self.subsection_title)
        return " > ".join(parts)
    
    @property
    def short_breadcrumb(self) -> str:
        """Compact version for UI display."""
        parts = [f"L{self.lecture_num}"]
        parts.append(self.section_title[:30])
        if self.subsection_title:
            parts.append(self.subsection_title[:30])
        return " > ".join(parts)
    
    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "breadcrumb": self.breadcrumb,
            "short_breadcrumb": self.short_breadcrumb
        }


@dataclass
class ContentFeatures:
    """Semantic features of chunk content."""
    has_code: bool = False
    has_math: bool = False
    has_images: List[str] = field(default_factory=list)
    has_lists: bool = False
    has_tables: bool = False
    keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Chunk:
    """
    Fully-traceable lecture chunk with rich metadata.
    Designed for both vector retrieval and frontend display.
    """
    # Identity
    chunk_id: str
    
    # Source traceability
    source: SourceLocation
    
    # Hierarchical context
    hierarchy: HierarchyPath
    
    # Position within structure
    chunk_position_in_section: int
    total_chunks_in_section: int
    chunk_position_in_lecture: int
    
    # Content
    text: str
    text_length: int
    word_count: int
    
    # Features
    features: ContentFeatures
    
    # Retrieval metadata (populated later)
    embedding: Optional[List[float]] = None
    relevance_score: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Export for JSON serialization."""
        data = {
            "chunk_id": self.chunk_id,
            "source": self.source.to_dict(),
            "hierarchy": self.hierarchy.to_dict(),
            "chunk_position_in_section": self.chunk_position_in_section,
            "total_chunks_in_section": self.total_chunks_in_section,
            "chunk_position_in_lecture": self.chunk_position_in_lecture,
            "text": self.text,
            "text_length": self.text_length,
            "word_count": self.word_count,
            "features": self.features.to_dict()
        }
        
        # Don't serialize embedding (too large for JSON)
        if self.relevance_score is not None:
            data["relevance_score"] = self.relevance_score
        
        return data
    
    def to_frontend_response(self) -> Dict:
        """
        Format for frontend consumption.
        """
        return {
            "chunk_id": self.chunk_id,
            "relevance_score": self.relevance_score,
            
            # Display metadata
            "lecture": {
                "num": self.hierarchy.lecture_num,
                "title": self.hierarchy.lecture_title
            },
            "location": {
                "section": self.hierarchy.section_title,
                "subsection": self.hierarchy.subsection_title,
                "breadcrumb": self.hierarchy.breadcrumb,
                "short_breadcrumb": self.hierarchy.short_breadcrumb
            },
            
            # Source linking (for viewer component)
            "source": {
                "tex_file": self.source.tex_file,
                "tex_lines": [self.source.line_start, self.source.line_end],
                "pdf_file": self.source.pdf_file,
                "pdf_pages": [self.source.pdf_page_start, self.source.pdf_page_end] 
                            if self.source.pdf_page_start else None
            },
            
            # Content
            "text_preview": self.text[:200] + "..." if len(self.text) > 200 else self.text,
            "text_full": self.text,
            "word_count": self.word_count,
            
            # Features (for UI hints)
            "features": {
                "has_code": self.features.has_code,
                "has_math": self.features.has_math,
                "has_images": self.features.has_images,
                "keywords": self.features.keywords
            },
            
            # Position context (for "show surrounding context" feature)
            "position": {
                "in_section": f"{self.chunk_position_in_section + 1}/{self.total_chunks_in_section}",
                "in_lecture": self.chunk_position_in_lecture
            }
        }


@dataclass
class RetrievalResult:
    """
    Complete retrieval response ready for frontend.
    """
    query: str
    answer: str
    confidence: str
    
    # Retrieved sources with full metadata
    sources: List[Chunk]
    
    # Retrieval statistics
    retrieval_stats: Dict = field(default_factory=dict)
    
    # Generation metadata
    model_used: str = "gpt-4o-mini"
    generation_time_ms: Optional[int] = None
    
    def to_dict(self) -> Dict:
        """Export complete response."""
        return {
            "query": self.query,
            "answer": self.answer,
            "confidence": self.confidence,
            "sources": [chunk.to_frontend_response() for chunk in self.sources],
            "retrieval_stats": self.retrieval_stats,
            "metadata": {
                "model_used": self.model_used,
                "generation_time_ms": self.generation_time_ms,
                "num_sources": len(self.sources)
            }
        }
    
    def print_structured(self):
        """Pretty print for console (current use case)"""
        print(f"\nQ: {self.query}\n")
        
        # retrieval display
        print(f"📚 Retrieved {len(self.sources)} relevant chunks:\n")
        for i, chunk in enumerate(self.sources, 1):
            print(f"  [{i}] Lecture {chunk.hierarchy.lecture_num}: {chunk.hierarchy.lecture_title}")
            print(f"      Section: {chunk.hierarchy.section_title}")
            if chunk.hierarchy.subsection_title:
                print(f"      Subsection: {chunk.hierarchy.subsection_title}")
            print(f"      Source: {chunk.source.tex_file} (lines {chunk.source.line_start}-{chunk.source.line_end})")
            if chunk.source.pdf_file:
                print(f"      PDF: {chunk.source.pdf_file} (pages {chunk.source.pdf_page_start}-{chunk.source.pdf_page_end})")
            print(f"      Score: {chunk.relevance_score:.3f}")
            print()
        
        print(f"A: {self.answer}\n")
        print(f"✓ Confidence: {self.confidence}")
        
        if self.retrieval_stats:
            print(f"⚡ Stats: {self.retrieval_stats.get('retrieval_time_ms', 'N/A')}ms retrieval, "
                  f"{self.generation_time_ms or 'N/A'}ms generation")


# Helper function to compute file hash
def compute_file_hash(file_path: str) -> str:
    """Compute SHA256 hash of file for change detection."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()[:12]  # First 12 chars sufficient


# Example usage
if __name__ == "__main__":
    # Create a sample chunk
    source = SourceLocation(
        tex_file="lecs/lecture5.tex",
        tex_file_hash="a3f2b9c1d4e5",
        char_start=1247,
        char_end=2891,
        line_start=45,
        line_end=78,
        pdf_file="lecs/lecture5.pdf",
        pdf_page_start=3,
        pdf_page_end=4
    )
    
    hierarchy = HierarchyPath(
        lecture_num=5,
        lecture_title="Processes and Threads",
        section_id="sec02",
        section_title="The Process Control Block",
        subsection_id="subsec01",
        subsection_title="Context Switching"
    )
    
    features = ContentFeatures(
        has_code=False,
        has_math=True,
        has_images=["pcb_diagram.png"],
        keywords=["context switch", "PCB", "registers", "overhead"]
    )
    
    chunk = Chunk(
        chunk_id="lec05_sec02_subsec01_chunk00",
        source=source,
        hierarchy=hierarchy,
        chunk_position_in_section=0,
        total_chunks_in_section=3,
        chunk_position_in_lecture=12,
        text="A context switch occurs when the operating system...",
        text_length=644,
        word_count=105,
        features=features,
        relevance_score=0.876
    )
    
    # Show different output formats
    print("=== Console Display ===")
    print(json.dumps(chunk.to_dict(), indent=2))
    
    print("\n=== Frontend Response ===")
    print(json.dumps(chunk.to_frontend_response(), indent=2))