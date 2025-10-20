import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_groq import ChatGroq


from backend.RAG.embedding import EmbeddingGenerator
from backend.RAG.vectorstore import VectorStoreManager
from backend.RAG.retriever import HybridRetriever
from backend.RAG.api import router as rag_router

load_dotenv()


app = FastAPI(
    title="MarineMind AI API",
    description="A unified API for MarineMind AI features.",
    version="1.0.0"
)


origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """
    Load all necessary components for the application when the server starts.
    This is where we initialize models, vector stores, etc., to avoid reloading them on each request.
    """
    """print("--- Server starting up: Initializing components... ---")
    

    VECTOR_STORE_PATH = "faiss_index"
    groq_api_key = os.getenv("GROQ_API_KEY")

    if not os.path.exists(VECTOR_STORE_PATH):
        raise RuntimeError(
            f"Vector store not found at '{VECTOR_STORE_PATH}'. "
            "Please run the ingestion script (ingest.py) to create it before starting the server."
        )

    print("[1/3] Loading embedding model...")
    embedding_generator = EmbeddingGenerator(model_name="sentence-transformers/all-mpnet-base-v2", device="cpu")

    print("[2/3] Loading vector store...")
    vector_store_manager = VectorStoreManager(embedding_model=embedding_generator, index_path=VECTOR_STORE_PATH)
    vector_store_manager.load_index()
    vector_store_manager.get_index_stats()

    print("[3/3] Initializing LLM and Retriever...")
    llm = ChatGroq(temperature=0.3, model_name="llama-3.1-8b-instant", api_key=groq_api_key)
    retriever = HybridRetriever(vectorstore=vector_store_manager.vectorstore, llm=llm, enable_debug=False)


    app.state.rag_components = {'retriever': retriever}"""



    
    print("--- Server started. Waiting for requests. ---")



app.include_router(rag_router)


@app.get("/")
def read_root():
    return {"status": "MarineMind AI API is running"}