import json
import numpy as np
import faiss
from typing import List, Dict, Tuple
from openai import OpenAI
import os
from dotenv import load_dotenv

class ECE350RAGAssistant:
    """
    RAG assistant for ECE 350
    ensures answers are strictly based on lecture content (https://github.com/jzarnett/ece350/tree/main/lectures)
    """
    
    def __init__(
        self, 
        chunks_file: str = "lecture_chunks.json",
        embedding_model: str = "text-embedding-3-small",
        llm_model: str = "gpt-4o-mini"
    ):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        
        # Load chunks
        with open(chunks_file, 'r') as f:
            self.chunks = json.load(f)
        
        self.index = None
        self.embeddings = None
        
    def create_embeddings(self, save_path: str = "embeddings.npy"):
        """Generate embeddings for all chunks."""
        print("Generating embeddings...")
        
        texts = [chunk['text'] for chunk in self.chunks]
        
        # Batch embed (OpenAI allows up to 2048 texts per request)
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
        np.save(save_path, self.embeddings)
        print(f"Saved embeddings to {save_path}")
        
        return self.embeddings
    
    def load_embeddings(self, load_path: str = "embeddings.npy"):
        """Load pre-computed embeddings"""
        self.embeddings = np.load(load_path)
        print(f"Loaded {len(self.embeddings)} embeddings")
    
    def build_faiss_index(self):
        """Build FAISS index for fast similarity search."""
        if self.embeddings is None:
            raise ValueError("Embeddings not loaded. Call create_embeddings() or load_embeddings() first.")
        
        dimension = self.embeddings.shape[1]        
        faiss.normalize_L2(self.embeddings)
        
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(self.embeddings)
        
        print(f"Built FAISS index with {self.index.ntotal} vectors")
    
    def retrieve_context(
        self, 
        query: str, 
        top_k: int = 5,
        min_score: float = 0.3
    ) -> List[Dict]:
        """
        Retrieve most relevant chunks for a query.
        
        Args:
            query: User question
            top_k: Number of chunks to retrieve
            min_score: Minimum similarity score (0-1)
        
        Returns:
            List of relevant chunks with scores
        """
        # Embed query
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=[query]
        )
        query_embedding = np.array([response.data[0].embedding], dtype='float32')
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, top_k)
        
        # Filter by minimum score and format results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score >= min_score:
                chunk = self.chunks[idx].copy()
                chunk['relevance_score'] = float(score)
                results.append(chunk)
        
        return results
    
    def format_context(self, chunks: List[Dict]) -> str:
        """Format retrieved chunks into context string."""
        if not chunks:
            return "No relevant lecture content found."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            header = f"[Lecture {chunk['lecture_num']}: {chunk['lecture_title']}]"
            section = f"Section: {chunk['section']}"
            if chunk['subsection']:
                section += f" > {chunk['subsection']}"
            
            context_parts.append(
                f"--- Context {i} (relevance: {chunk['relevance_score']:.2f}) ---\n"
                f"{header}\n{section}\n\n{chunk['text']}\n"
            )
        
        return "\n".join(context_parts)
    
    def generate_grounded_response(
        self, 
        query: str, 
        context: str,
        temperature: float = 0.0
    ) -> Dict[str, str]:
        """
        Generate response using LLM with strict grounding constraints.
        
        Returns:
            Dict with 'answer', 'confidence', and 'sources'
        """
        system_prompt = """You are a knowledgeable teaching assistant for ECE 350 (Operating Systems) at the University of Waterloo.

Your CRITICAL CONSTRAINTS:
1. Answer ONLY based on the provided lecture context
2. If the context doesn't contain the answer, you MUST say: "This topic is not covered in the available lecture notes."
3. NEVER use outside knowledge or make assumptions
4. Quote specific lectures when possible (e.g., "According to Lecture 2, section 'Past is Prologue', subsection 'The Process and the Thread'...")
5. If context is partial, acknowledge limitations explicitly

Your goal is to help students learn accurately from their course material."""

        user_prompt = f"""Question: {query}

Lecture Context:
{context}

Instructions:
- Answer the question using ONLY the context above
- If you cannot answer from the context, say so clearly
- Cite which lecture(s) you're referencing
- Be concise but complete"""

        response = self.client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature
        )
        
        answer = response.choices[0].message.content
        
        # Simple confidence heuristic
        confidence = "high" if "not covered" not in answer.lower() else "low"
        
        return {
            "answer": answer,
            "confidence": confidence,
            "model_used": self.llm_model
        }
    
    def ask(
        self, 
        query: str, 
        top_k: int = 5,
        verbose: bool = False
    ) -> Dict:
        """
        Main query interface.
        
        Args:
            query: Student question
            top_k: Number of context chunks to retrieve
            verbose: Print retrieval details
        
        Returns:
            Dict with answer, sources, and metadata
        """
        # Retrieve relevant chunks
        retrieved_chunks = self.retrieve_context(query, top_k=top_k)
        
        if verbose:
            print(f"\nRetrieved {len(retrieved_chunks)} relevant chunks:")
            for chunk in retrieved_chunks:
                print(f"  - Lecture {chunk['lecture_num']}: {chunk['section']} (score: {chunk['relevance_score']:.3f})")
        
        # Format context
        context = self.format_context(retrieved_chunks)
        
        # Generate response
        response = self.generate_grounded_response(query, context)
        
        # Add sources
        sources = [
            {
                "lecture_num": c['lecture_num'],
                "lecture_title": c['lecture_title'],
                "section": c['section'],
                "score": c['relevance_score']
            }
            for c in retrieved_chunks
        ]
        
        return {
            "question": query,
            "answer": response["answer"],
            "confidence": response["confidence"],
            "sources": sources,
            "num_chunks_retrieved": len(retrieved_chunks)
        }


# Setup and usage example
if __name__ == "__main__":
    # Initialize assistant
    assistant = ECE350RAGAssistant(
        chunks_file="lecture_chunks.json",
        embedding_model="text-embedding-3-small",
        llm_model="gpt-4o-mini"
    )
    
    assistant.load_embeddings()
    assistant.build_faiss_index()
    
    # Example queries
    print("\n=== Example Queries ===\n")
    
    questions = [
        "What is a context switch and why is it expensive?",
        "Explain the difference between threads and processes",
        "What is quantum computing?",  # Should return "not covered"
    ]
    
    for question in questions:
        print(f"Q: {question}")
        result = assistant.ask(question, verbose=True)
        print(f"\nA: {result['answer']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Sources: {len(result['sources'])} lectures")
        print("-" * 80 + "\n")