import os
import pprint
from dotenv import load_dotenv
from .loaders import DocumentLoader
from .chunking import DocumentChunker
from .embedding import EmbeddingGenerator
from .vectorstore import VectorStoreManager
from .retriever import HybridRetriever
from .LLM import AgentManager
from .memory import MemoryManager
from langchain_groq import ChatGroq
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")


FILE_PATH = "text_1.pdf"
VECTOR_STORE_PATH = "faiss_index"
USER_QUERY = "What checks should be done before operating the BWTS, give steps in detail and long answer and explain every step that how to do it because i am a beginner"
SESSION_ID = "tesing003"

def main():
    """
    Main function to run the loading and chunking stages of the RAG pipeline.
    """
    print("--- Starting RAG Pipeline ---")




    print("\n[STEP 1] Initializing document loader...")

    loader = DocumentLoader(use_ocr=True) 

    try:
        print(f"Loading document: {FILE_PATH}")
        documents = loader.load_document(FILE_PATH)
        if not documents:
            print("No documents were loaded. Exiting.")
            return
        print(f"Successfully loaded {len(documents)} document(s)/page(s).")
    except FileNotFoundError:
        print(f"Error: The file '{FILE_PATH}' was not found.")
        print("Please update the FILE_PATH variable with the correct path to your document.")
        return
    except Exception as e:
        print(f"An unexpected error occurred during document loading: {e}")
        return






    print("\n[STEP 2] Initializing embedding model...")
    embedding_generator = EmbeddingGenerator(
        model_name="sentence-transformers/all-mpnet-base-v2",
        device="cpu" 
    )





    print("\n[STEP 3] Initializing document chunker...")
    chunker = DocumentChunker(
        chunk_size=1000, 
        chunk_overlap=200, 
        strategy="recursive"
    )
    
    print("Chunking documents...")
    chunks = chunker.chunk_documents(documents)
    print(f"Documents split into {len(chunks)} chunks.")


    print("\n--- Chunking Summary ---")
    chunker.summarize_chunks(chunks)
    
    print("\n--- Chunk Preview ---")
    chunker.preview_chunks(chunks, n=2)



    print("\n[STEP 4] Managing FAISS Vector Store...")
    vector_store_manager = VectorStoreManager(
        embedding_model=embedding_generator,
        index_path=VECTOR_STORE_PATH
    )

    if os.path.exists(VECTOR_STORE_PATH):
        print(f"Found existing vector store at '{VECTOR_STORE_PATH}'. Loading it.")
        vector_store_manager.load_index()
    else:
        print("No existing vector store found. Building a new one...")
        vector_store_manager.build_from_documents(chunks)
        print("Saving vector store...")
        vector_store_manager.save_index()

    vector_store_manager.get_index_stats()




    print("\n[STEP 5] Initializing Hybrid Retriever...")
    if not vector_store_manager.vectorstore:
        raise ValueError("Vector store not initialized. Cannot proceed.")

    llm = ChatGroq(temperature=0.3, model_name="llama-3.1-8b-instant", api_key=groq_api_key) 

    retriever = HybridRetriever(
        vectorstore=vector_store_manager.vectorstore,
        llm=llm, 
        enable_debug=True
    )

    print("\n--- Querying Phase ---")
    print(f"User Query: \"{USER_QUERY}\"")




    print("\n[STEP 6] Initializing Conversation Memory...")
    memory_manager = MemoryManager(session_id=SESSION_ID)
    conversation_memory = memory_manager.get_memory()
    if not conversation_memory.chat_memory.messages:
        print(f"No previous history found for session '{SESSION_ID}'. Starting a new conversation.")

    print("\n[STEP 7] Initializing the MarineMind Agent...")
    agent_manager = AgentManager(
        retriever=retriever,
        memory=conversation_memory
    )

    print("\n[STEP 8] Running the agent to get a structured response...")
    print(f"--- User Query: \"{USER_QUERY}\" ---")
    
    agent_response = agent_manager.run(USER_QUERY)

    print("\n--- Final Agent Output ---")
    pprint.pprint(agent_response)
    print("--------------------------")

    print("\n[STEP 9] Saving conversation history...")
    memory_manager.save_history()
    print(f"History for session '{SESSION_ID}' saved successfully.")

    print("\n--- RAG Pipeline Finished ---")

if __name__ == "__main__":
    main()