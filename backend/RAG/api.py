import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from loaders import DocumentLoader
from chunking import DocumentChunker
from embedding import EmbeddingGenerator
from vectorstore import VectorStoreManager
from retriever import HybridRetriever
from LLM import AgentManager
from memory import MemoryManager
from langchain_groq import ChatGroq

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
VECTOR_STORE_PATH = "faiss_index"


class QueryRequest(BaseModel):
    query: str
    session_id: str


app = FastAPI(
    title="MarineMind RAG API",
    description="An API for querying documents using a Retrieval-Augmented Generation pipeline.",
    version="1.0.0"
)


origins = [
    "http://localhost:3000",
    "http://localhost:5173"
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.state.rag_components = {}


@app.on_event("startup")
async def startup_event():
    """
    Load all necessary components for the RAG pipeline when the server starts.
    This includes the embedding model, the vector store, the LLM, and the retriever.
    """
    print("--- Server starting up: Initializing RAG components... ---")


    if not os.path.exists(VECTOR_STORE_PATH):
        raise RuntimeError(
            f"Vector store not found at '{VECTOR_STORE_PATH}'. "
            "Please run your original ingestion script (main.py or a new one) "
            "to create the vector store before starting the API server."
        )

    print("[1/4] Loading embedding model...")
    embedding_generator = EmbeddingGenerator(
        model_name="sentence-transformers/all-mpnet-base-v2", device="cpu"
    )

    print("[2/4] Loading vector store...")
    vector_store_manager = VectorStoreManager(
        embedding_model=embedding_generator, index_path=VECTOR_STORE_PATH
    )
    vector_store_manager.load_index()
    vector_store_manager.get_index_stats()

    print("[3/4] Loading LLM...")
    llm = ChatGroq(temperature=0.3, model_name="llama-3.1-8b-instant", api_key=groq_api_key)


    print("[4/4] Initializing retriever...")
    retriever = HybridRetriever(
        vectorstore=vector_store_manager.vectorstore, llm=llm, enable_debug=False
    )


    app.state.rag_components['retriever'] = retriever
    print("--- RAG components successfully initialized. Server is ready. ---")



@app.get("/")
def read_root():
    """A simple endpoint to check if the API is running."""
    return {"status": "MarineMind RAG API is running"}







@app.post("/query")
async def process_query(request: QueryRequest):
    """
    The main endpoint to handle user queries.
    It uses the pre-loaded RAG components to generate a response.
    """
    print(f"\nReceived query for session '{request.session_id}': '{request.query}'")
    
    
    try:

        retriever = app.state.rag_components.get('retriever')
        if not retriever:
            raise HTTPException(status_code=500, detail="Retriever not initialized.")


        memory_manager = MemoryManager(session_id=request.session_id)
        conversation_memory = memory_manager.get_memory()


        agent_manager = AgentManager(
            retriever=retriever,
            memory=conversation_memory
        )


        agent_response = agent_manager.run(request.query)


        memory_manager.save_history()
        print(f"History for session '{request.session_id}' saved.")

        return agent_response

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))