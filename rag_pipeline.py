"""
RAG pipeline that returns structured, frontend-ready responses.
"""

import json
from dotenv import load_dotenv
import numpy as np
import faiss
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
import os
import time
from data_models import Chunk, RetrievalResult

class ECE350RAG:
    """
    RAG system with full traceability and structured responses.
    Ready for future API integration.
    """
    
    def __init__(
        self,
        chunks_file: str = "chunks.json",
        embedding_model: str = "text-embedding-3-small",
        llm_model: str = "gpt-4o-mini"
    ):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        
        # Load chunks
        print(f"Loading chunks from {chunks_file}...")
        with open(chunks_file, 'r') as f:
            chunk_dicts = json.load(f)
        
        # Reconstruct Chunk objects
        self.chunks = self._reconstruct_chunks(chunk_dicts)
        print(f"✓ Loaded {len(self.chunks)} chunks")
        
        self.index = None
        self.embeddings = None
    
    def _reconstruct_chunks(self, chunk_dicts: List[Dict]) -> List[Chunk]:
        """Reconstruct Chunk objects from JSON."""
        from data_models import SourceLocation, HierarchyPath, ContentFeatures
        
        chunks = []
        for d in chunk_dicts:
            source = SourceLocation(**d['source'])
            hierarchy = HierarchyPath(**{k: v for k, v in d['hierarchy'].items() 
                                        if k not in ['breadcrumb', 'short_breadcrumb']})
            features = ContentFeatures(**d['features'])
            
            chunk = Chunk(
                chunk_id=d['chunk_id'],
                source=source,
                hierarchy=hierarchy,
                chunk_position_in_section=d['chunk_position_in_section'],
                total_chunks_in_section=d['total_chunks_in_section'],
                chunk_position_in_lecture=d['chunk_position_in_lecture'],
                text=d['text'],
                text_length=d['text_length'],
                word_count=d['word_count'],
                features=features
            )
            chunks.append(chunk)
        
        return chunks
    
    def create_embeddings(self, save_path: str = "embeddings.npy"):
        """Generate embeddings for all chunks."""
        print("Generating embeddings...")
        
        texts = [chunk.text for chunk in self.chunks]
        all_embeddings = []
        batch_size = 100
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=batch
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
            print(f"  Processed {min(i + batch_size, len(texts))}/{len(texts)}")
        
        self.embeddings = np.array(all_embeddings, dtype='float32')
        
        # Store embeddings in chunks (for potential export)
        for chunk, embedding in zip(self.chunks, all_embeddings):
            chunk.embedding = embedding
        
        np.save(save_path, self.embeddings)
        print(f"✓ Saved embeddings to {save_path}")
        
        return self.embeddings
    
    def load_embeddings(self, load_path: str = "embeddings.npy"):
        """Load pre-computed embeddings."""
        self.embeddings = np.load(load_path)
        print(f"✓ Loaded {len(self.embeddings)} embeddings")
    
    def build_faiss_index(self):
        """Build FAISS index."""
        if self.embeddings is None:
            raise ValueError("Embeddings not loaded")
        
        dimension = self.embeddings.shape[1]
        faiss.normalize_L2(self.embeddings)
        
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(self.embeddings)
        
        print(f"✓ Built FAISS index with {self.index.ntotal} vectors")
    
    def retrieve_chunks(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> Tuple[List[Chunk], Dict]:
        """
        Retrieve relevant chunks with statistics.
        
        Returns:
            (chunks, stats_dict)
        """
        start_time = time.time()
        
        # Embed query
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=[query]
        )
        query_embedding = np.array([response.data[0].embedding], dtype='float32')
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, top_k)
        
        # Filter and annotate chunks
        retrieved = []
        for score, idx in zip(scores[0], indices[0]):
            if score >= min_score:
                chunk = self.chunks[idx]
                chunk.relevance_score = float(score)
                retrieved.append(chunk)
        
        retrieval_time = int((time.time() - start_time) * 1000)
        
        stats = {
            "total_candidates": self.index.ntotal,
            "retrieved": len(retrieved),
            "avg_score": float(np.mean([c.relevance_score for c in retrieved])) if retrieved else 0.0,
            "retrieval_time_ms": retrieval_time
        }
        
        return retrieved, stats
    
    def format_context_for_llm(self, chunks: List[Chunk]) -> str:
        """Format chunks into LLM context."""
        if not chunks:
            return "No relevant lecture content found."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            header = f"[Lecture {chunk.hierarchy.lecture_num}: {chunk.hierarchy.lecture_title}]"
            location = f"Section: {chunk.hierarchy.section_title}"
            if chunk.hierarchy.subsection_title:
                location += f" > {chunk.hierarchy.subsection_title}"
            
            context_parts.append(
                f"--- Source {i} (relevance: {chunk.relevance_score:.3f}) ---\n"
                f"{header}\n"
                f"{location}\n"
                f"Location: {chunk.source.tex_file} (lines {chunk.source.line_start}-{chunk.source.line_end})\n\n"
                f"{chunk.text}\n"
            )
        
        return "\n".join(context_parts)
    
    def generate_answer(
        self,
        query: str,
        context: str,
        temperature: float = 0.0
    ) -> Tuple[str, str, int]:
        """
        Generate grounded answer.
        
        Returns:
            (answer, confidence, generation_time_ms)
        """
        start_time = time.time()
        
        system_prompt = """You are a knowledgeable teaching assistant for ECE 350 (Operating Systems).

CRITICAL CONSTRAINTS:
1. Answer ONLY using information from the provided lecture context
2. If the context doesn't contain enough information, explicitly state: "This topic is not sufficiently covered in the available lecture notes."
3. NEVER use outside knowledge or make assumptions
4. When referencing information, cite the specific lecture and section (e.g., "According to Lecture 5, Section on Context Switching...")
5. If the context is partial or ambiguous, acknowledge this explicitly

Your goal is accuracy over completeness. It's better to say "I don't know" than to provide ungrounded information."""

        user_prompt = f"""Question: {query}

Lecture Context:
{context}

Instructions:
- Answer using ONLY the context above
- Cite specific lectures and sections
- If information is insufficient, say so clearly
- Be precise and concise"""

        response = self.client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature
        )
        
        answer = response.choices[0].message.content
        generation_time = int((time.time() - start_time) * 1000)
        
        # Determine confidence
        not_covered_phrases = [
            "not covered", "not sufficiently covered", "not mentioned",
            "don't have enough information", "insufficient information"
        ]
        confidence = "low" if any(phrase in answer.lower() for phrase in not_covered_phrases) else "high"
        
        return answer, confidence, generation_time
    
    def ask(
        self,
        query: str,
        top_k: int = 5,
        verbose: bool = False
    ) -> RetrievalResult:
        """
        Main query interface - returns structured result ready for frontend.
        
        Args:
            query: User question
            top_k: Number of chunks to retrieve
            verbose: Print detailed info to console
        
        Returns:
            RetrievalResult with complete metadata
        """
        # Retrieve
        chunks, retrieval_stats = self.retrieve_chunks(query, top_k=top_k)
        
        if not chunks:
            return RetrievalResult(
                query=query,
                answer="No relevant content found in the lecture notes for this question.",
                confidence="no_context",
                sources=[],
                retrieval_stats=retrieval_stats,
                model_used=self.llm_model
            )
        
        # Format context
        context = self.format_context_for_llm(chunks)
        
        # Generate answer
        answer, confidence, gen_time = self.generate_answer(query, context)
        
        # Create result
        result = RetrievalResult(
            query=query,
            answer=answer,
            confidence=confidence,
            sources=chunks,
            retrieval_stats=retrieval_stats,
            model_used=self.llm_model,
            generation_time_ms=gen_time
        )
        
        if verbose:
            result.print_structured()
        
        return result
    
    def export_result_for_frontend(self, result: RetrievalResult) -> Dict:
        """
        Export result in frontend-ready format.
        This is what your Next.js API will return.
        """
        return result.to_dict()
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Chunk]:
        """Retrieve specific chunk by ID (useful for "show full context" feature)."""
        for chunk in self.chunks:
            if chunk.chunk_id == chunk_id:
                return chunk
        return None
    
    def get_surrounding_chunks(self, chunk_id: str, context_size: int = 2) -> List[Chunk]:
        """
        Get surrounding chunks from same lecture (for expanded context view).
        
        Args:
            chunk_id: Central chunk
            context_size: Number of chunks before/after to include
        
        Returns:
            List of chunks in order
        """
        central_chunk = self.get_chunk_by_id(chunk_id)
        if not central_chunk:
            return []
        
        # Find chunks from same lecture
        lecture_num = central_chunk.hierarchy.lecture_num
        same_lecture = [c for c in self.chunks if c.hierarchy.lecture_num == lecture_num]
        same_lecture.sort(key=lambda c: c.chunk_position_in_lecture)
        
        # Find position
        try:
            idx = same_lecture.index(central_chunk)
            start = max(0, idx - context_size)
            end = min(len(same_lecture), idx + context_size + 1)
            return same_lecture[start:end]
        except ValueError:
            return [central_chunk]


# Example usage
if __name__ == "__main__":
    # Initialize
    rag = ECE350RAG(
        chunks_file="chunks.json",
        embedding_model="text-embedding-3-small",
        llm_model="gpt-4o-mini"
    )
    
    rag.load_embeddings("embeddings.npy")
    rag.build_faiss_index()
    
    # Test query with verbose output
    print("\n" + "="*80)
    print("RAG DEMO")
    print("="*80)
    
    result = rag.ask(
        "Explain the difference between threads and processes",
        verbose=True
    )
    
    print("\n" + "="*80)
    print("FRONTEND-READY JSON")
    print("="*80)
    
    frontend_json = rag.export_result_for_frontend(result)
    print(json.dumps(frontend_json, indent=2)[:1000] + "...")
    
    # Test surrounding context feature
    if result.sources:
        print("\n" + "="*80)
        print("SURROUNDING CONTEXT DEMO")
        print("="*80)
        
        first_chunk_id = result.sources[0].chunk_id
        surrounding = rag.get_surrounding_chunks(first_chunk_id, context_size=1)
        
        print(f"\nShowing context around chunk: {first_chunk_id}")
        for chunk in surrounding:
            marker = "→" if chunk.chunk_id == first_chunk_id else " "
            print(f"{marker} {chunk.chunk_id}: {chunk.text[:80]}...")