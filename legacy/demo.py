from rag_pipeline import ECE350RAGAssistant
import os


def main(): 
    # Load assistant
    assistant = ECE350RAGAssistant()
    
    if not os.path.exists("embeddings.npy"):
        ans = input("First-time setup: generating embeddings? (**requires OpenAI API credits, will cost ~$0.50**) (y/n): ").strip().lower()
        if ans == 'y':
            assistant.create_embeddings()
        else:
            print("Skipping embedding generation. Exiting.")
            return
    else:
        assistant.load_embeddings()
    
    assistant.build_faiss_index()
    
    print("ECE 350 AI Study Assistant")
    print("=" * 50)
    print("Ask questions about ECE350: RTOS")
    print("Type 'quit' to exit.\n")
    
    while True:
        question = input("You: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            break
        
        if not question:
            continue
        
        result = assistant.ask(question, verbose=True)
        
        print(f"\nAssistant: {result['answer']}\n")
        print(f"📚 Sources: {len(result['sources'])} lectures")
        print(f"Confidence: {result['confidence']}")
        print("-" * 50 + "\n")

if __name__ == "__main__":
    main()