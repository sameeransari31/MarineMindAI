# File: backend/RAG/api.py

import os
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from langchain_groq import ChatGroq


from .loaders import DocumentLoader
from .chunking import DocumentChunker
from .embedding import EmbeddingGenerator
from .vectorstore import VectorStoreManager
from .retriever import HybridRetriever
from .LLM import AgentManager
from .memory import MemoryManager


router = APIRouter(
    prefix="/rag",
    tags=["RAG"]
)

class QueryRequest(BaseModel):
    query: str
    session_id: str

def get_retriever(request: Request):
    return request.app.state.rag_components['retriever']

@router.post("/query")
async def process_query(request: QueryRequest, retriever: HybridRetriever = Depends(get_retriever)):
    """
    Main endpoint for user queries.
    Uses preloaded RAG components to generate responses.
    """
    print(f"\nReceived query for session '{request.session_id}': '{request.query}'")
    
    try:
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
