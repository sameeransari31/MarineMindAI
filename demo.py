from langchain.schema import Document
from RAG.embedding import EmbeddingGenerator
from RAG.chunking import DocumentChunker

# Step 1: Create some sample documents
docs = [
    Document(page_content="""Artificial Intelligence (AI) is transforming industries. 
    Machine learning and deep learning are subsets of AI that focus on training models 
    to recognize patterns and make decisions. 
    Meanwhile, natural language processing helps computers understand human language.
    """)
]

# Step 2: Initialize embedding model (for semantic/hybrid strategies)
embedding_generator = EmbeddingGenerator()
embedding_model = embedding_generator.embedding_model

# Step 3a: Recursive chunking (rule-based)
print("\n=== Recursive Chunking ===")
recursive_chunker = DocumentChunker(strategy="recursive", chunk_size=80, chunk_overlap=20)
recursive_chunks = recursive_chunker.chunk_documents(docs)
recursive_chunker.preview_chunks(recursive_chunks, n=2)

# Step 3b: Semantic chunking (needs embedding)
print("\n=== Semantic Chunking ===")
semantic_chunker = DocumentChunker(strategy="semantic", embedding=embedding_model)
semantic_chunks = semantic_chunker.chunk_documents(docs)
semantic_chunker.preview_chunks(semantic_chunks, n=2)

# Step 3c: Hybrid chunking (recursive + semantic)
print("\n=== Hybrid Chunking ===")
hybrid_chunker = DocumentChunker(strategy="hybrid", embedding=embedding_model, chunk_size=80, chunk_overlap=20)
hybrid_chunks = hybrid_chunker.chunk_documents(docs)
hybrid_chunker.preview_chunks(hybrid_chunks, n=2)