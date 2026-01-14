"""
Additional techniques to prevent hallucinations in RAG responses
"""

import re
from typing import List, Dict

class HallucinationSafeguards:
    @staticmethod
    def detect_out_of_scope(query: str, course_keywords: List[str]) -> bool:
        """Pre-filter queries that are clearly outside course scope"""
        query_lower = query.lower()
        
        # Check if any course keyword appears
        has_course_keyword = any(kw in query_lower for kw in course_keywords)
        
        # shortlist of clearly off-topic indicators
        off_topic_patterns = [
            r'\b(recipe|cooking|food)\b',
            r'\b(movie|film|actor)\b',
            r'\b(sports|football|basketball)\b',
            r'\b(weather)\b',
            r'\b(stock market|trading)\b'
        ]
        
        is_off_topic = any(re.search(p, query_lower) for p in off_topic_patterns)
        
        return is_off_topic and not has_course_keyword
    
    @staticmethod
    def verify_answer_grounding(answer: str, context: str) -> Dict[str, any]:
        """
        Verify that answer content appears in context.
        Returns grounding score and specific issues.
        """
        # Extract factual claims
        # Look for sentences with numbers, proper nouns, technical terms
        answer_sentences = answer.split('.')
        
        grounding_issues = []
        grounded_count = 0
        
        for sentence in answer_sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            # Check if key terms from sentence appear in context
            key_terms = re.findall(r'\b[A-Z][a-z]+\b|\b\d+\b', sentence)
            
            if key_terms:
                terms_in_context = sum(1 for term in key_terms if term in context)
                if terms_in_context / len(key_terms) < 0.5:
                    grounding_issues.append(sentence)
                else:
                    grounded_count += 1
        
        total_sentences = len([s for s in answer_sentences if len(s.strip()) > 10])
        grounding_score = grounded_count / total_sentences if total_sentences > 0 else 1.0
        
        return {
            "grounding_score": grounding_score,
            "suspicious_sentences": grounding_issues,
            "is_grounded": grounding_score > 0.7
        }
    
    @staticmethod
    def add_uncertainty_markers(answer: str, confidence: str) -> str:
        """Add explicit uncertainty if confidence is low."""
        if confidence == "low":
            prefix = "⚠️ Limited information available in lectures: "
            return prefix + answer
        return answer
    
    @staticmethod
    def implement_two_stage_verification(
        query: str,
        retrieved_chunks: List[Dict],
        client,
        model: str = "gpt-4o-mini"
    ) -> bool:
        """
        Two-stage approach: First check if question is answerable.
        
        Stage 1: "Can this question be answered from the context?" (Yes/No)
        Stage 2: If Yes, generate answer; if No, return "not covered"
        """
        context = "\n\n".join([c['text'] for c in retrieved_chunks[:3]])
        
        verification_prompt = f"""Context from ECE 350 lecture notes:
{context}

Question: {query}

Can this question be fully answered using ONLY the information in the context above?
Answer with exactly one word: YES or NO

If NO, it means important information is missing or the topic isn't covered."""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You verify if questions can be answered from given context."},
                {"role": "user", "content": verification_prompt}
            ],
            temperature=0.0,
            max_tokens=5
        )
        
        decision = response.choices[0].message.content.strip().upper()
        return "YES" in decision


# Integration example: Enhanced RAG assistant
class ECE350RAGAssistant:
    """
    Extended RAG assistant with hallucination safeguards.
    """
    
    def __init__(self, base_assistant):
        self.base = base_assistant
        self.safeguards = HallucinationSafeguards()
        
        # Define course scope keywords
        self.course_keywords = [
            'operating system', 'process', 'thread', 'scheduling',
            'memory', 'virtual memory', 'paging', 'segmentation',
            'file system', 'inode', 'disk', 'i/o', 'input output',
            'synchronization', 'semaphore', 'mutex', 'deadlock',
            'race condition', 'context switch', 'kernel', 'system call',
            'concurrency', 'cpu', 'cache', 'tlb', 'page table'
        ]
    
    def ask_with_safeguards(
        self, 
        query: str,
        use_two_stage: bool = True,
        verbose: bool = False
    ) -> Dict:
        """Enhanced query with safeguards."""
        
        # Safeguard 1: Pre-filter out-of-scope
        if self.safeguards.detect_out_of_scope(query, self.course_keywords):
            return {
                "question": query,
                "answer": "This question appears to be outside the scope of ECE 350. Please ask about topics covered in the course lectures.",
                "confidence": "out_of_scope",
                "sources": [],
                "num_chunks_retrieved": 0
            }
        
        # Retrieve context
        retrieved_chunks = self.base.retrieve_context(query, top_k=5)
        
        if not retrieved_chunks:
            return {
                "question": query,
                "answer": "No relevant lecture content found for this question.",
                "confidence": "no_context",
                "sources": [],
                "num_chunks_retrieved": 0
            }
        
        # Safeguard 2: Two-stage verification
        if use_two_stage:
            is_answerable = self.safeguards.implement_two_stage_verification(
                query, retrieved_chunks, self.base.client, self.base.llm_model
            )
            
            if not is_answerable:
                return {
                    "question": query,
                    "answer": "While related topics are mentioned in the lectures, there isn't sufficient information to fully answer this specific question.", 
                    "confidence": "insufficient",
                    "sources": [],
                    "num_chunks_retrieved": len(retrieved_chunks)
                }
        
        # Generate answer
        result = self.base.ask(query, verbose=verbose)
        
        # Safeguard 3: Verify grounding
        context_text = "\n".join([c['text'] for c in retrieved_chunks])
        grounding_check = self.safeguards.verify_answer_grounding(
            result['answer'], context_text
        )
        
        if verbose:
            print(f"\nGrounding score: {grounding_check['grounding_score']:.2f}")
            if grounding_check['suspicious_sentences']:
                print("⚠️ Potentially ungrounded sentences:")
                for sent in grounding_check['suspicious_sentences']:
                    print(f"  - {sent}")
        
        # Add uncertainty markers if needed
        if not grounding_check['is_grounded']:
            result['answer'] = self.safeguards.add_uncertainty_markers(
                result['answer'], "low"
            )
            result['confidence'] = "uncertain"
        
        result['grounding_score'] = grounding_check['grounding_score']
        
        return result


# Usage example
if __name__ == "__main__":
    from rag_pipeline import ECE350RAGAssistant
    
    # Initialize base assistant
    base = ECE350RAGAssistant()
    base.load_embeddings()
    base.build_faiss_index()
    
    # Wrap with safeguards
    enhanced = ECE350RAGAssistant(base)
    
    # Test queries
    test_queries = [
        "What is a context switch?",  # Should work
        "What's the best pizza in Waterloo?",  # Out of scope
        "Explain quantum entanglement in OS",  # Partial match, insufficient
    ]
    
    for q in test_queries:
        print(f"\nQ: {q}")
        result = enhanced.ask_with_safeguards(q, verbose=True)
        print(f"A: {result['answer']}")
        print(f"Confidence: {result['confidence']}")
        print("-" * 80)