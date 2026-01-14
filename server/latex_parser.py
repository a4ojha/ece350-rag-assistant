"""
LaTeX parser with full source traceability.
Tracks character offsets, line numbers, and hierarchical structure.
Pulled from https://github.com/jzarnett/ece350/tree/main/lectures
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from data_models import (
    Chunk, SourceLocation, HierarchyPath, 
    ContentFeatures, compute_file_hash
)


@dataclass
class SourceSpan:
    """Track where content appears in source file."""
    char_start: int
    char_end: int
    line_start: int
    line_end: int


class LaTeXParser:
    """
    Parse LaTeX lectures with full source tracking.
    Every piece of content knows exactly where it came from.
    """
    
    def __init__(self, lectures_dir: str = "lecs/", pdfs_dir: Optional[str] = None):
        self.lectures_dir = Path(lectures_dir)
        self.pdfs_dir = Path(pdfs_dir) if pdfs_dir else self.lectures_dir
        
    def get_line_number(self, text: str, char_pos: int) -> int:
        """Convert character position to line number."""
        return text[:char_pos].count('\n') + 1
    
    def extract_lecture_metadata(self, content: str) -> Tuple[int, str]:
        """Extract lecture number and title"""
        match = re.search(r'\\lecture\{\s*(\d+)\s*---\s*(.+?)\s*\}', content)
        if match:
            return int(match.group(1)), match.group(2).strip()
        return 0, "Unknown"

    def get_lecture_number_from_filename(self, tex_file: Path) -> int:
        """Extract lecture number from filename (L01.tex, L02.tex)"""
        match = re.match(r'L(\d+)\.tex', tex_file.name)
        if match:
            return int(match.group(1))
        return 0
    
    def find_pdf_pages(self, tex_file: Path, line_start: int, line_end: int) -> Optional[Tuple[int, int]]:
        """
        Estimate PDF page numbers from line numbers.        
        Rough estimate: ~50 lines per PDF page for typical academic slides.
        DO NOT use in frontend yet. Page numbers are not accurate.
        """
        # Check if PDF exists
        pdf_file = self.pdfs_dir / tex_file.with_suffix('.pdf').name
        if not pdf_file.exists():
            return None
        
        # Heuristic mapping
        LINES_PER_PAGE = 50
        page_start = (line_start // LINES_PER_PAGE) + 1
        page_end = (line_end // LINES_PER_PAGE) + 1
        
        return page_start, page_end
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract potential keywords from text.
        Simple heuristic: capitalized terms, technical terms.
        """
        # Find capitalized words (potential proper nouns/technical terms)
        caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        
        # Find acronyms
        acronyms = re.findall(r'\b[A-Z]{2,}\b', text)
        
        # Find technical terms (words with underscores, CamelCase)
        technical = re.findall(r'\b[a-z]+_[a-z_]+\b|\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', text)
        
        # Combine and deduplicate
        all_keywords = caps + acronyms + technical
        seen = set()
        keywords = []
        for kw in all_keywords:
            if kw.lower() not in seen and len(kw) > 3:
                seen.add(kw.lower())
                keywords.append(kw)
                if len(keywords) >= max_keywords:
                    break
        
        return keywords
    
    def detect_features(self, raw_text: str) -> ContentFeatures:
        """Detect content features in LaTeX source"""
        has_code = bool(re.search(r'\\begin\{(verbatim|lstlisting|minted)\}', raw_text))
        has_math = bool(re.search(r'(\$[^$]+\$|\\\[[^\]]+\\\]|\\begin\{(equation|align)\})', raw_text))
        has_lists = bool(re.search(r'\\begin\{(enumerate|itemize)\}', raw_text))
        has_tables = bool(re.search(r'\\begin\{(tabular|table)\}', raw_text))
        
        # Extract image filenames
        images = re.findall(r'\\includegraphics(?:\[.*?\])?\{(.+?)\}', raw_text)
        
        # Extract keywords from cleaned text
        cleaned = self.clean_latex(raw_text)
        keywords = self.extract_keywords(cleaned)
        
        return ContentFeatures(
            has_code=has_code,
            has_math=has_math,
            has_images=images,
            has_lists=has_lists,
            has_tables=has_tables,
            keywords=keywords
        )
    
    def clean_latex(self, text: str) -> str:
        """Remove LaTeX commands while preserving content."""
        # Replace images with placeholders
        text = re.sub(r'\\includegraphics(?:\[.*?\])?\{(.+?)\}', r'[Image: \1]', text)
        
        # Preserve inline math
        text = re.sub(r'\$([^$]+)\$', r'[\1]', text)
        
        # Preserve display math
        text = re.sub(r'\\\[(.+?)\\\]', r'[Math: \1]', text, flags=re.DOTALL)
        
        # Remove common commands but keep content
        text = re.sub(r'\\textbf\{(.+?)\}', r'\1', text)
        text = re.sub(r'\\textit\{(.+?)\}', r'\1', text)
        text = re.sub(r'\\emph\{(.+?)\}', r'\1', text)
        text = re.sub(r'\\texttt\{(.+?)\}', r'`\1`', text)
        
        # Remove citations and labels
        text = re.sub(r'\\cite\{.+?\}', '', text)
        text = re.sub(r'\\label\{.+?\}', '', text)
        text = re.sub(r'\\ref\{.+?\}', '', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_sections_with_spans(self, content: str) -> List[Dict]:
        """
        Extract sections/subsections with precise character offsets.
        Returns list of {section, subsection, raw_content, span}.
        """
        sections = []
        
        # Pattern for sections and subsections with positions
        section_pattern = r'\\section\*?\{(.+?)\}'
        subsection_pattern = r'\\subsection\*?\{(.+?)\}'
        
        # Find all section positions
        section_matches = list(re.finditer(section_pattern, content))
        
        for i, section_match in enumerate(section_matches):
            section_title = section_match.group(1).strip()
            section_start = section_match.end()
            
            # Find where this section ends (next section or end of file)
            if i + 1 < len(section_matches):
                section_end = section_matches[i + 1].start()
            else:
                section_end = len(content)
            
            section_content = content[section_start:section_end]
            
            # Now find subsections within this section
            subsection_matches = list(re.finditer(subsection_pattern, section_content))
            
            if not subsection_matches:
                # No subsections - whole section is one chunk
                sections.append({
                    'section': section_title,
                    'subsection': None,
                    'raw_content': section_content,
                    'span': SourceSpan(
                        char_start=section_start,
                        char_end=section_end,
                        line_start=self.get_line_number(content, section_start),
                        line_end=self.get_line_number(content, section_end)
                    )
                })
            else:
                # Has subsections
                for j, subsec_match in enumerate(subsection_matches):
                    subsec_title = subsec_match.group(1).strip()
                    subsec_start = section_start + subsec_match.end()
                    
                    # Find where subsection ends
                    if j + 1 < len(subsection_matches):
                        subsec_end = section_start + subsection_matches[j + 1].start()
                    else:
                        subsec_end = section_end
                    
                    subsec_content = content[subsec_start:subsec_end]
                    
                    sections.append({
                        'section': section_title,
                        'subsection': subsec_title,
                        'raw_content': subsec_content,
                        'span': SourceSpan(
                            char_start=subsec_start,
                            char_end=subsec_end,
                            line_start=self.get_line_number(content, subsec_start),
                            line_end=self.get_line_number(content, subsec_end)
                        )
                    })
        
        return sections
    
    def chunk_with_overlap(
        self, 
        text: str, 
        base_span: SourceSpan,
        max_tokens: int = 600,
        overlap_tokens: int = 50
    ) -> List[Tuple[str, SourceSpan]]:
        """Split text into chunks with source tracking."""
        words = text.split()
        max_words = max(1, int(max_tokens * 0.75))  # Ensure at least 1
        overlap_words = min(max_words - 1, int(overlap_tokens * 0.75))  # Prevent overlap >= max_words
        
        if len(words) <= max_words:
            return [(text, base_span)]
        
        chunks = []
        start_word = 0
        iterations = 0
        MAX_ITERATIONS = 10000  # Safety limit
        
        while start_word < len(words) and iterations < MAX_ITERATIONS:
            iterations += 1
            end_word = min(start_word + max_words, len(words))
            
            if end_word <= start_word:  # Safety check
                break
            
            chunk_words = words[start_word:end_word]
            chunk_text = ' '.join(chunk_words)
            
            char_start = base_span.char_start + int((base_span.char_end - base_span.char_start) * (start_word / len(words)))
            char_end = base_span.char_start + int((base_span.char_end - base_span.char_start) * (end_word / len(words)))
            
            line_start = base_span.line_start + chunk_text[:char_start - base_span.char_start].count('\n')
            line_end = base_span.line_start + chunk_text[:char_end - base_span.char_start].count('\n')
            
            span = SourceSpan(
                char_start=char_start,
                char_end=char_end,
                line_start=max(base_span.line_start, line_start),
                line_end=min(base_span.line_end, line_end)
            )
            
            chunks.append((chunk_text, span))
            start_word = end_word - overlap_words
            
            if end_word >= len(words):
                break
        
        return chunks
    
    def parse_lecture(self, lecture_file: Path) -> List[Chunk]:
        """Parse lecture into chunks with full traceability."""
        with open(lecture_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Compute file hash for change detection
        file_hash = compute_file_hash(str(lecture_file))
        
        # Extract metadata
        lecture_num, lecture_title = self.extract_lecture_metadata(content)
        
        if lecture_num == 0:
            lecture_num = self.get_lecture_number_from_filename(lecture_file)
        
        print(f"  Extracting sections...")
        sections = self.extract_sections_with_spans(content)
        print(f"  Found {len(sections)} sections")
    
        # Find PDF path
        pdf_filename = f"L{lecture_num:02d}.pdf"
        pdf_file = self.pdfs_dir / pdf_filename
        pdf_path = str(pdf_file) if pdf_file.exists() else None
        
        # Extract sections with positions
        sections = self.extract_sections_with_spans(content)
        
        # Create chunks
        all_chunks = []
        lecture_chunk_counter = 0
        
        for sec_idx, sec in enumerate(sections):
            raw_content = sec['raw_content']
            cleaned_content = self.clean_latex(raw_content)
            
            if not cleaned_content.strip():
                continue
            
            # Detect features from raw LaTeX
            features = self.detect_features(raw_content)
            
            # Split into sub-chunks if needed
            sub_chunks = self.chunk_with_overlap(
                cleaned_content, 
                sec['span']
            )
            
            for chunk_idx, (chunk_text, chunk_span) in enumerate(sub_chunks):
                # Build IDs
                section_id = f"sec{sec_idx:02d}"
                subsection_id = f"subsec{chunk_idx:02d}" if sec['subsection'] else None
                chunk_id = f"lec{lecture_num:02d}_{section_id}"
                if subsection_id:
                    chunk_id += f"_{subsection_id}"
                chunk_id += f"_chunk{chunk_idx:02d}"
                
                # Create source location
                pdf_pages = self.find_pdf_pages(lecture_file, chunk_span.line_start, chunk_span.line_end)
                source = SourceLocation(
                    tex_file=str(lecture_file),
                    tex_file_hash=file_hash,
                    char_start=chunk_span.char_start,
                    char_end=chunk_span.char_end,
                    line_start=chunk_span.line_start,
                    line_end=chunk_span.line_end,
                    pdf_file=pdf_path,
                    pdf_page_start=pdf_pages[0] if pdf_pages else None,
                    pdf_page_end=pdf_pages[1] if pdf_pages else None
                )
                
                # Create hierarchy
                hierarchy = HierarchyPath(
                    lecture_num=lecture_num,
                    lecture_title=lecture_title,
                    section_id=section_id,
                    section_title=sec['section'],
                    subsection_id=subsection_id,
                    subsection_title=sec['subsection']
                )
                
                # Create chunk
                chunk = Chunk(
                    chunk_id=chunk_id,
                    source=source,
                    hierarchy=hierarchy,
                    chunk_position_in_section=chunk_idx,
                    total_chunks_in_section=len(sub_chunks),
                    chunk_position_in_lecture=lecture_chunk_counter,
                    text=chunk_text,
                    text_length=len(chunk_text),
                    word_count=len(chunk_text.split()),
                    features=features
                )
                
                all_chunks.append(chunk)
                lecture_chunk_counter += 1
        
        return all_chunks
    
    def parse_all_lectures(self) -> List[Chunk]:
        """Parse all lectures with full metadata."""
        all_chunks = []
        
        lecture_files = sorted(self.lectures_dir.glob("L*.tex"))
        
        for lecture_file in lecture_files:
            print(f"Parsing {lecture_file.name}...")
            chunks = self.parse_lecture(lecture_file)
            all_chunks.extend(chunks)
            print(f"  → {len(chunks)} chunks created")
        
        print(f"\n✓ Total chunks: {len(all_chunks)}")
        return all_chunks
    
    def save_chunks(self, chunks: List[Chunk], output_file: str = "lecture_chunks.json"):
        """Save chunks to JSON."""
        import json
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([c.to_dict() for c in chunks], f, indent=2)
        
        print(f"✓ Saved {len(chunks)} chunks to {output_file}")


# Example usage
if __name__ == "__main__":
    parser = LaTeXParser(
        lectures_dir="lecs/",
        pdfs_dir="compiled/"
    )
    
    chunks = parser.parse_all_lectures()
    parser.save_chunks(chunks)
    
    # Display sample with full traceability
    if chunks:
        print("\n" + "="*80)
        print("SAMPLE CHUNK")
        print("="*80)
        sample = chunks[10]
        
        print(f"\nChunk ID: {sample.chunk_id}")
        print(f"Hierarchy: {sample.hierarchy.breadcrumb}")
        print(f"\nSource Traceability:")
        print(f"  File: {sample.source.tex_file}")
        print(f"  Lines: {sample.source.line_start}-{sample.source.line_end}")
        print(f"  Characters: {sample.source.char_start}-{sample.source.char_end}")
        if sample.source.pdf_file:
            print(f"  PDF: {sample.source.pdf_file}, pages {sample.source.pdf_page_start}-{sample.source.pdf_page_end}")
        
        print(f"\nContent Features:")
        print(f"  Code: {sample.features.has_code}")
        print(f"  Math: {sample.features.has_math}")
        print(f"  Images: {sample.features.has_images}")
        print(f"  Keywords: {', '.join(sample.features.keywords[:5])}")
        
        print(f"\nText Preview:")
        print(f"  {sample.text[:200]}...")