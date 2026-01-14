"""
console demo showcasing structured retrieval and ability to trace back.
"""

import os
import json
from rag_pipeline import ECE350RAG
from data_models import RetrievalResult

class RAGDemo:    
    def __init__(self):
        print("="*80)
        print("ECE 350 RAG ASSISTANT")
        print("="*80)
        print("\nInitializing...")
        
        self.rag = ECE350RAG(
            chunks_file="lecture_chunks.json",
            embedding_model="text-embedding-3-small",
            llm_model="gpt-4o-mini"
        )
        
        # Load or create embeddings
        if os.path.exists("embeddings.npy"):
            self.rag.load_embeddings("embeddings.npy")
        else:
            print("\nFirst-time setup: generating embeddings...")
            self.rag.create_embeddings("embeddings.npy")
        
        self.rag.build_faiss_index()
        
        print("\n✓ System ready!")
        print("="*80 + "\n")
    
    def display_result(self, result: RetrievalResult, show_json: bool = False):
        print(f"\n{'='*80}")
        print(f"QUESTION: {result.query}")
        print(f"{'='*80}\n")
        
        # Retrieved chunks section
        if result.sources:
            print(f"📚 Retrieved {len(result.sources)} relevant source(s):\n")
            
            for i, chunk in enumerate(result.sources, 1):
                print(f"  [{i}] Lecture {chunk.hierarchy.lecture_num}: {chunk.hierarchy.lecture_title}")
                print(f"      └─ Section: {chunk.hierarchy.section_title}")
                
                if chunk.hierarchy.subsection_title:
                    print(f"         └─ Subsection: {chunk.hierarchy.subsection_title}")
                
                print(f"      📍 Location: {chunk.source.tex_file}")
                print(f"         Lines {chunk.source.line_start}-{chunk.source.line_end} "
                      f"(~{chunk.word_count} words)")
                
                if chunk.source.pdf_file and chunk.source.pdf_page_start:
                    print(f"         PDF: pages {chunk.source.pdf_page_start}-{chunk.source.pdf_page_end}")
                
                print(f"      🎯 Relevance: {chunk.relevance_score:.3f}")
                
                # Show features if interesting
                features = []
                if chunk.features.has_math:
                    features.append("math")
                if chunk.features.has_code:
                    features.append("code")
                if chunk.features.has_images:
                    features.append(f"{len(chunk.features.has_images)} image(s)")
                
                if features:
                    print(f"      🏷️  Features: {', '.join(features)}")
                
                print()
        else:
            print("⚠️  No relevant sources found.\n")
        
        # Answer section
        print(f"{'─'*80}")
        print(f"ANSWER:\n")
        print(result.answer)
        print(f"\n{'─'*80}")
        
        # Metadata
        print(f"\nConfidence: {result.confidence}")
        print(f"Performance: {result.retrieval_stats.get('retrieval_time_ms', 0)}ms retrieval, "
              f"{result.generation_time_ms}ms generation")
        print(f"Model: {result.model_used}")
        
        # Optional: show JSON structure
        if show_json:
            print(f"\n{'─'*80}")
            print("API RESPONSE PREVIEW (first 500 chars):")
            print(f"{'─'*80}")
            json_str = json.dumps(result.to_dict(), indent=2)
            print(json_str[:500] + "...\n")
    
    def run_example_queries(self):
        """Run example queries to showcase functionality."""
        print("\n" + "="*80)
        print("EXAMPLE QUERIES")
        print("="*80)
        
        examples = [
            "Explain the difference between threads and processes",
            "What is a context switch and why is it expensive?",
            "How does virtual memory work?",
            "What is quantum computing?"  # Should return "not covered"
        ]
        
        for query in examples:
            result = self.rag.ask(query, top_k=5, verbose=False)
            self.display_result(result)
            
            input("\nPress Enter for next example...")
    
    def interactive_mode(self):
        """Interactive Q&A loop."""
        print("\n" + "="*80)
        print("INTERACTIVE MODE")
        print("="*80)
        print("\nCommands:")
        print("  - Ask any question about ECE 350")
        print("  - Type 'json' to toggle JSON preview")
        print("  - Type 'context <chunk_id>' to see surrounding context")
        print("  - Type 'examples' to see example queries")
        print("  - Type 'quit' to exit")
        print()
        
        show_json = False
        
        while True:
            try:
                user_input = input("\n🎓 You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                if user_input.lower() == 'json':
                    show_json = not show_json
                    print(f"✓ JSON preview {'enabled' if show_json else 'disabled'}")
                    continue
                
                if user_input.lower() == 'examples':
                    self.run_example_queries()
                    continue
                
                if user_input.lower().startswith('context '):
                    chunk_id = user_input.split(' ', 1)[1]
                    self.show_surrounding_context(chunk_id)
                    continue
                
                # Process question
                result = self.rag.ask(user_input, top_k=5, verbose=False)
                self.display_result(result, show_json=show_json)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("Please try again.")
    
    def show_surrounding_context(self, chunk_id: str):
        """Display surrounding chunks for expanded context."""
        print(f"\n{'='*80}")
        print(f"SURROUNDING CONTEXT: {chunk_id}")
        print(f"{'='*80}\n")
        
        surrounding = self.rag.get_surrounding_chunks(chunk_id, context_size=2)
        
        if not surrounding:
            print("❌ Chunk not found.")
            return
        
        for chunk in surrounding:
            is_central = chunk.chunk_id == chunk_id
            marker = "→ [CENTRAL]" if is_central else "  "
            
            print(f"{marker} {chunk.chunk_id}")
            print(f"    {chunk.hierarchy.breadcrumb}")
            print(f"    {chunk.text[:150]}...")
            print()


def main():
    """Main entry point."""
    demo = RAGDemo()
    
    # Choose mode
    print("Select mode:")
    print("  [1] Interactive Q&A")
    print("  [2] Example queries")
    print("  [3] Both (examples first, then interactive)")
    
    choice = input("\nChoice (default: 1): ").strip() or "1"
    
    if choice == "2":
        demo.run_example_queries()
    elif choice == "3":
        demo.run_example_queries()
        demo.interactive_mode()
    else:
        demo.interactive_mode()


if __name__ == "__main__":
    main()