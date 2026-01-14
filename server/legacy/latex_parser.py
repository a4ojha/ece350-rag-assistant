import re
import os
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import json

@dataclass
class LectureChunk:
    """Structured representation of a lecture chunk with metadata."""
    chunk_id: str
    lecture_num: int
    lecture_title: str
    section: str
    subsection: Optional[str]
    chunk_position: int
    text: str
    has_code: bool
    has_math: bool
    word_count: int
    
    def to_dict(self):
        return asdict(self)


class LaTeXLectureParser:
    """Parse ECE 350 LaTeX lectures into structured chunks for RAG."""
    
    def __init__(self, lectures_dir: str = "lecs/"):
        self.lectures_dir = Path(lectures_dir)
        
    def extract_lecture_metadata(self, content: str) -> tuple[int, str]:
        """Extract lecture number and title from \lecture{} command."""
        # Pattern: \lecture{ 20 --- More About Input/Output Devices }
        match = re.search(r'\\lecture\{\s*(\d+)\s*---\s*(.+?)\s*\}', content)
        if match:
            return int(match.group(1)), match.group(2).strip()
        return 0, "Unknown"
    
    def clean_latex(self, text: str) -> str:
        """Remove LaTeX commands, keep context"""
        # Replace images with placeholders
        text = re.sub(r'\\includegraphics(?:\[.*?\])?\{(.+?)\}', 
                     r'[Image: \1]', text)
        
        # Preserve inline math
        text = re.sub(r'\$(.+?)\$', r'[\1]', text)
        
        # Preserve display math
        text = re.sub(r'\\\[(.+?)\\\]', r'[Math: \1]', text, flags=re.DOTALL)
        
        # Remove common commands but keep content
        text = re.sub(r'\\textbf\{(.+?)\}', r'\1', text)
        text = re.sub(r'\\textit\{(.+?)\}', r'\1', text)
        text = re.sub(r'\\emph\{(.+?)\}', r'\1', text)
        text = re.sub(r'\\texttt\{(.+?)\}', r'`\1`', text)
        
        # Remove citations
        text = re.sub(r'\\cite\{.+?\}', '', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_sections(self, content: str) -> List[Dict]:
        """Extract sections and subsections with their content."""
        sections = []
        
        # Find all section markers
        section_pattern = r'\\section\*?\{(.+?)\}'
        subsection_pattern = r'\\subsection\*?\{(.+?)\}'
        
        # Split content by sections
        section_splits = re.split(section_pattern, content)
        
        current_section = None
        current_section_content = []
        
        for i, part in enumerate(section_splits):
            if i == 0:
                continue  # Skip preamble
            
            if i % 2 == 1:  # This is a section title
                if current_section:
                    # Save previous section
                    sections.append({
                        'section': current_section,
                        'content': ''.join(current_section_content)
                    })
                current_section = part.strip()
                current_section_content = []
            else:  # This is section content
                current_section_content.append(part)
        
        # Don't forget the last section
        if current_section:
            sections.append({
                'section': current_section,
                'content': ''.join(current_section_content)
            })
        
        # Now split by subsections
        detailed_sections = []
        for sec in sections:
            subsection_splits = re.split(subsection_pattern, sec['content'])
            
            if len(subsection_splits) == 1:
                # No subsections
                detailed_sections.append({
                    'section': sec['section'],
                    'subsection': None,
                    'content': subsection_splits[0]
                })
            else:
                # Has subsections
                for i, part in enumerate(subsection_splits):
                    if i == 0 and part.strip():
                        # Content before first subsection
                        detailed_sections.append({
                            'section': sec['section'],
                            'subsection': None,
                            'content': part
                        })
                    elif i % 2 == 1:  # Subsection title
                        detailed_sections.append({
                            'section': sec['section'],
                            'subsection': part.strip(),
                            'content': subsection_splits[i + 1] if i + 1 < len(subsection_splits) else ''
                        })
        
        return detailed_sections
    
    def detect_features(self, text: str) -> tuple[bool, bool]:
        """Detect if chunk contains code or math."""
        has_code = bool(re.search(r'\\begin\{(verbatim|lstlisting|minted)\}', text))
        has_math = bool(re.search(r'(\$.*?\$|\\\[.*?\\\])', text, re.DOTALL))
        return has_code, has_math
    
    def chunk_section(self, text: str, max_tokens: int = 600) -> List[str]:
        """
        Split large sections into smaller chunks with overlap.
        Rough estimate: 1 token = 0.75 words.
        """
        words = text.split()
        max_words = int(max_tokens * 0.75)
        overlap_words = 50
        
        if len(words) <= max_words:
            return [text]
        
        chunks = []
        start = 0
        while start < len(words):
            end = start + max_words
            chunk_words = words[start:end]
            chunks.append(' '.join(chunk_words))
            start = end - overlap_words  # Overlap
        
        return chunks
    
    def parse_lecture(self, lecture_file: Path) -> List[LectureChunk]:
        """Parse a single lecture file into chunks."""
        with open(lecture_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract metadata
        lecture_num, lecture_title = self.extract_lecture_metadata(content)
        
        # Extract sections
        sections = self.extract_sections(content)
        
        # Create chunks
        chunks = []
        chunk_position = 0
        
        for sec in sections:
            raw_content = sec['content']
            cleaned_content = self.clean_latex(raw_content)
            
            if not cleaned_content.strip():
                continue
            
            # Detect features
            has_code, has_math = self.detect_features(raw_content)
            
            # Split if too long
            sub_chunks = self.chunk_section(cleaned_content)
            
            for sub_idx, sub_text in enumerate(sub_chunks):
                chunk_id = f"lec{lecture_num:02d}_sec{chunk_position:02d}"
                if sec['subsection']:
                    chunk_id += f"_sub{sub_idx}"
                
                chunk = LectureChunk(
                    chunk_id=chunk_id,
                    lecture_num=lecture_num,
                    lecture_title=lecture_title,
                    section=sec['section'],
                    subsection=sec['subsection'],
                    chunk_position=chunk_position,
                    text=sub_text,
                    has_code=has_code,
                    has_math=has_math,
                    word_count=len(sub_text.split())
                )
                chunks.append(chunk)
                chunk_position += 1
        
        return chunks
    
    def parse_all_lectures(self) -> List[LectureChunk]:
        """Parse all lectures in the directory."""
        all_chunks = []
        
        lecture_files = sorted(self.lectures_dir.glob("L*.tex"))
        
        for lecture_file in lecture_files:
            print(f"Parsing {lecture_file.name}...")
            chunks = self.parse_lecture(lecture_file)
            all_chunks.extend(chunks)
        
        print(f"\nTotal chunks created: {len(all_chunks)}")
        return all_chunks
    
    def save_chunks(self, chunks: List[LectureChunk], output_file: str = "lecture_chunks.json"):
        """Save chunks to JSON for processing."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([c.to_dict() for c in chunks], f, indent=2)
        print(f"Saved {len(chunks)} chunks to {output_file}")


if __name__ == "__main__":
    parser = LaTeXLectureParser(lectures_dir="lecs/")
    chunks = parser.parse_all_lectures()
    parser.save_chunks(chunks)
    
    # Display sample
    if chunks:
        print("\n--- Sample Chunk ---")
        sample = chunks[0]
        print(f"ID: {sample.chunk_id}")
        print(f"Lecture {sample.lecture_num}: {sample.lecture_title}")
        print(f"Section: {sample.section}")
        print(f"Text preview: {sample.text[:200]}...")