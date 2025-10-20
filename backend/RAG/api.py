import os
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel



router = APIRouter(
    prefix="/rag",
    tags=["RAG"]
)

class QueryRequest(BaseModel):
    query: str
    session_id: str


def process_and_ingest_document(file_path: str, index_path: str):
    """
    Loads a document, chunks it, creates embeddings, and saves it to a FAISS vector store.
    """
    from .loaders import DocumentLoader
    from .chunking import DocumentChunker
    from .embedding import EmbeddingGenerator
    from .vectorstore import VectorStoreManager

    print(f"--- Starting ingestion for document: {file_path} ---")
    

    os.makedirs(os.path.dirname(index_path), exist_ok=True)

    loader = DocumentLoader(use_ocr=True)
    documents = loader.load_document(file_path)
    
    chunker = DocumentChunker(chunk_size=1000, chunk_overlap=200)
    chunks = chunker.chunk_documents(documents)

    embedding_generator = EmbeddingGenerator(model_name="sentence-transformers/all-mpnet-base-v2", device="cpu")
    
    vector_store_manager = VectorStoreManager(embedding_model=embedding_generator, index_path=index_path)
    vector_store_manager.build_from_documents(chunks)
    vector_store_manager.save_index()
    
    print(f"--- Ingestion complete. Index saved to: {index_path} ---")


@router.post("/upload")
async def upload_document(session_id: str = Form(...), file: UploadFile = File(...)):
    """
    Endpoint to upload a document, process it, and create a session-specific vector store.
    """

    index_path = os.path.join("session_indexes", f"faiss_index_{session_id}")
    temp_file_path = f"temp_{file.filename}"


    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        process_and_ingest_document(temp_file_path, index_path)
        return {"message": "File processed successfully", "index_path": index_path}
    except Exception as e:
        print(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.post("/query")
async def process_query(request: QueryRequest):
    """
    Endpoint to handle user queries. It now loads the session-specific retriever on-demand.
    """
    from .retriever import HybridRetriever
    from .vectorstore import VectorStoreManager
    from .embedding import EmbeddingGenerator
    from .memory import MemoryManager
    from .LLM import AgentManager
    from langchain_groq import ChatGroq

    print(f"\nReceived query for session '{request.session_id}': '{request.query}'")
    index_path = os.path.join("session_indexes", f"faiss_index_{request.session_id}")

    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="No document has been uploaded for this session. Please upload a document first.")

    try:
        print(f"Loading index for session '{request.session_id}' from {index_path}")
        embedding_generator = EmbeddingGenerator(model_name="sentence-transformers/all-mpnet-base-v2", device="cpu")
        vector_store_manager = VectorStoreManager(embedding_model=embedding_generator, index_path=index_path)
        vector_store_manager.load_index()

        llm = ChatGroq(temperature=0.3, model_name="llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY"))
        retriever = HybridRetriever(vectorstore=vector_store_manager.vectorstore, llm=llm)

        memory_manager = MemoryManager(session_id=request.session_id)
        conversation_memory = memory_manager.get_memory()

        agent_manager = AgentManager(retriever=retriever, memory=conversation_memory)
        agent_response = agent_manager.run(request.query)

        memory_manager.save_history()
        return agent_response

    except Exception as e:
        print(f"An error occurred during query processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))